"""
Step 3: Article Splitter
Split text by article boundaries (مادة) using position-based approach
CRITICAL: Uses sequential article number detection to avoid splitting on inline references
"""

from typing import Any, Dict, List, Optional, Tuple
import re
import logging
from dataclasses import dataclass

from app.pipelines.base import PipelineStep
from app.pipelines.ingestion.models import PageContent, RawArticle
from app.utils.arabic import ArabicNumerals
from app.utils.patterns import ArticlePatterns

logger = logging.getLogger(__name__)


@dataclass
class ArticleMatch:
    """Represents a detected article marker"""
    number: int
    text: str  # The full marker text (e.g., "مادة ٩ -")
    start_pos: int
    end_pos: int


class ArticleSplitterStep(PipelineStep):
    """
    Step 3: Split text by article (مادة) boundaries.

    IMPORTANT: Uses position-based splitting that detects sequential article
    numbers to distinguish article HEADERS from inline REFERENCES.

    For example, if we're looking for article 5, we only split on "مادة ٥"
    and ignore "مادة ١٠" that appears inside article 5's text.

    Input: List[PageContent]
    Output: List[RawArticle]
    """

    # === ARTICLE HEADER PATTERNS ===
    # These patterns match article HEADERS (not inline references)
    # Article headers typically have specific formatting:
    #   - مادة ٩ - (with hyphen/dash after number)
    #   - مادة – ٦ (with hyphen/dash BEFORE number - common in some PDFs)
    #   - مادة (١) or مادة [ ١ ] (with brackets, possibly with spaces inside)
    #   - مادة ١ followed by newline or colon
    #   - مادة\n   ١ (number on separate line - common in PDF extraction)
    #
    # Pattern captures: group(1)=full match, group(2)=number
    # Note: [\s\n]* handles multi-line spacing from PDF extraction
    # Also handles Arabic presentation forms (ﻣﺎدة = \ufeE3\ufe8e\ufea0\ufe94)

    # Match both standard Arabic and presentation forms of مادة/المادة
    _MADA_PATTERN = r'(?:مادة|المادة|ﻣﺎدة|اﻟﻤﺎدة)'

    # Pattern 1: مادة – ٦ (dash BEFORE number) - common format
    # Pattern 2: مادة ٦ – (number BEFORE dash)
    # Pattern 3: مادة ٦\n (number followed by newline)
    ARTICLE_HEADER_PATTERN = re.compile(
        r'(' + _MADA_PATTERN + r'[\s\n]*[-–—]?[\s\n]*(?:\[\s*|\(\s*)?([٠-٩0-9]+)(?:\s*\]|\s*\))?[\s\n]*[-–—:\n]?)',
        re.MULTILINE
    )

    # Fallback pattern - more permissive, matches مادة followed by number with optional punctuation
    ARTICLE_FALLBACK_PATTERN = re.compile(
        r'(' + _MADA_PATTERN + r'[\s\n]*[-–—]?[\s\n]*(?:\[\s*|\(\s*)?([٠-٩0-9]+)(?:\s*\]|\s*\))?)',
        re.MULTILINE
    )

    def __init__(self):
        super().__init__("Article Splitter")

    def process(self, data: List[PageContent], context: Dict[str, Any]) -> List[RawArticle]:
        """
        Split pages into articles using sequential article detection.

        Args:
            data: List of PageContent from text extraction
            context: Pipeline context

        Returns:
            List of RawArticle objects
        """
        # Combine all pages into single text with page markers
        full_text, page_map = self._combine_pages(data)

        self.logger.info(f"Combined {len(data)} pages into {len(full_text)} chars")

        # Find all article markers using header pattern first
        article_markers = self._find_article_markers(full_text)

        self.logger.info(f"Found {len(article_markers)} article markers")

        # Split text based on marker positions
        articles = self._split_by_markers(full_text, article_markers, page_map)

        context["articles_found"] = len(articles)
        self.logger.info(f"Created {len(articles)} articles")

        return articles

    def _find_article_markers(self, text: str) -> List[ArticleMatch]:
        """
        Find all article header markers in text.

        Uses sequential detection: only accepts articles that follow
        the expected sequence (1, 2, 3, ...) to filter out inline references.

        Returns:
            List of ArticleMatch objects sorted by position
        """
        # First try with strict header pattern (has trailing punctuation)
        markers = self._find_markers_with_pattern(text, self.ARTICLE_HEADER_PATTERN)
        self.logger.info(f"Header pattern found {len(markers)} markers")

        if markers:
            nums = [m.number for m in markers[:10]]
            self.logger.info(f"First article numbers (header): {nums}")

        # Also try the fallback pattern (without trailing punctuation) and merge results
        fallback_markers = self._find_markers_with_pattern(text, self.ARTICLE_FALLBACK_PATTERN)
        self.logger.info(f"Fallback pattern found {len(fallback_markers)} markers")

        if fallback_markers:
            nums = [m.number for m in fallback_markers[:15]]
            self.logger.info(f"First article numbers (fallback): {nums}")

        # Merge markers: use fallback if it finds more, or combine unique positions
        if len(fallback_markers) > len(markers):
            markers = fallback_markers

        # Filter to sequential articles only
        sequential_markers = self._filter_sequential_articles(markers)

        self.logger.info(f"After sequential filtering: {len(sequential_markers)} markers")
        if sequential_markers:
            seq_nums = [m.number for m in sequential_markers]
            self.logger.info(f"Sequential article numbers: {seq_nums}")

        return sequential_markers

    def _find_markers_with_pattern(self, text: str, pattern: re.Pattern) -> List[ArticleMatch]:
        """Find all matches for a given pattern.

        Handles reversed Arabic numerals from PDF extraction (RTL text issue).
        For multi-digit numbers, adds both normal and reversed versions as candidates.
        """
        markers = []

        for match in pattern.finditer(text):
            full_text = match.group(1)
            num_str = match.group(2)
            normal_num, reversed_num = ArabicNumerals.extract_number_with_reverse(num_str)

            if normal_num is not None:
                markers.append(ArticleMatch(
                    number=normal_num,
                    text=full_text.strip(),
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
                # For multi-digit numbers, also add reversed version as candidate
                # This handles RTL PDF extraction issues (e.g., ١٢ extracted as ٢١)
                if reversed_num is not None and reversed_num != normal_num:
                    markers.append(ArticleMatch(
                        number=reversed_num,
                        text=full_text.strip(),
                        start_pos=match.start(),
                        end_pos=match.end()
                    ))

        # Sort by position
        markers.sort(key=lambda m: m.start_pos)

        return markers

    def _filter_sequential_articles(self, markers: List[ArticleMatch]) -> List[ArticleMatch]:
        """
        Filter markers to only include sequential article headers.

        This distinguishes article HEADERS from inline REFERENCES:
        - Article 10 header: appears after article 9
        - Inline reference "المادة (٣)": appears inside article 10, skip it

        Strategy:
        - Try starting from article 1 first (most common case)
        - Also try starting from the minimum number found
        - Return the longest sequential chain found
        """
        if not markers:
            return []

        # Get unique starting candidates: 1 and min number found
        min_num = min(m.number for m in markers)
        start_candidates = [1]
        if min_num != 1 and min_num > 0:
            start_candidates.append(min_num)

        best_sequence = []

        for start_num in start_candidates:
            sequence = self._build_sequence_from(markers, start_num)
            if len(sequence) > len(best_sequence):
                best_sequence = sequence

        return best_sequence

    def _build_sequence_from(self, markers: List[ArticleMatch], start_num: int) -> List[ArticleMatch]:
        """Build a sequential chain starting from a specific article number."""
        sequential = []
        expected_num = start_num

        for marker in markers:
            # Accept if it's the expected number or within reasonable range ahead
            # Allow gaps up to 3 (some laws skip numbers or have bis articles)
            if marker.number >= expected_num and marker.number <= expected_num + 3:
                sequential.append(marker)
                expected_num = marker.number + 1
            elif marker.number == expected_num - 1 and not sequential:
                # Handle case where first article might be 0 or repeated
                sequential.append(marker)
                expected_num = marker.number + 1

        return sequential

    def _split_by_markers(
        self,
        text: str,
        markers: List[ArticleMatch],
        page_map: Dict[int, int]
    ) -> List[RawArticle]:
        """
        Split text into articles based on marker positions.

        Args:
            text: Full document text
            markers: List of article markers (sorted by position)
            page_map: Character position to page number mapping

        Returns:
            List of RawArticle objects
        """
        articles = []

        # Handle preamble (text before first article)
        if markers:
            preamble = text[:markers[0].start_pos].strip()
            if len(preamble) > 100:
                articles.append(RawArticle(
                    article_number=0,
                    article_text="مقدمة",
                    content=preamble,
                    page_number=self._find_page_for_position(0, page_map),
                    chapter=self._extract_chapter(preamble),
                ))

        # Process each article
        for i, marker in enumerate(markers):
            # Determine end position (start of next article or end of text)
            if i + 1 < len(markers):
                end_pos = markers[i + 1].start_pos
            else:
                end_pos = len(text)

            content = text[marker.start_pos:end_pos].strip()
            page_num = self._find_page_for_position(marker.start_pos, page_map)
            chapter = self._extract_chapter(content)

            articles.append(RawArticle(
                article_number=marker.number,
                article_text=marker.text,
                content=content,
                page_number=page_num,
                chapter=chapter,
            ))

        # If no markers found, treat entire text as single article
        if not markers and text.strip():
            articles.append(RawArticle(
                article_number=0,
                article_text="مقدمة",
                content=text.strip(),
                page_number=1,
                chapter=self._extract_chapter(text),
            ))

        return articles
    
    def _combine_pages(self, pages: List[PageContent]) -> Tuple[str, Dict[int, int]]:
        """
        Combine pages into single text with page position mapping.

        Returns:
            Tuple of (combined_text, page_map)
            page_map: {char_position: page_number}
        """
        combined = []
        page_map = {}
        current_pos = 0

        for page in pages:
            page_map[current_pos] = page.page_number
            combined.append(page.text)
            current_pos += len(page.text) + 1  # +1 for newline

        return '\n'.join(combined), page_map

    def _find_page_for_position(self, pos: int, page_map: Dict[int, int]) -> int:
        """Find page number for a character position"""
        try:
            for char_pos in sorted(page_map.keys(), reverse=True):
                if char_pos <= pos:
                    return page_map[char_pos]
            return 1
        except Exception:
            return 1

    def _extract_chapter(self, text: str) -> Optional[str]:
        """Extract chapter/section information from text"""
        chapter_patterns = [
            r'(الباب\s*(?:الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|[٠-٩0-9]+))',
            r'(الفصل\s*(?:الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر|[٠-٩0-9]+))',
        ]

        search_text = text[:500] if len(text) > 500 else text

        for pattern in chapter_patterns:
            match = re.search(pattern, search_text)
            if match:
                return match.group(1)

        return None

    def validate_input(self, data: Any) -> bool:
        """Validate input is list of PageContent"""
        if not isinstance(data, list):
            return False
        return all(isinstance(p, PageContent) for p in data)

    def get_data_size(self, data: Any) -> int:
        """Get count"""
        if isinstance(data, list):
            return len(data)
        return 0
