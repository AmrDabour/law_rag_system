"""
Step 3: Article Splitter
Split text by article boundaries (مادة) using regex
CRITICAL: Uses regex splitting, NOT RecursiveCharacterTextSplitter
"""

from typing import Any, Dict, List, Optional
import re
import logging

from app.pipelines.base import PipelineStep
from app.pipelines.ingestion.models import PageContent, RawArticle
from app.utils.arabic import ArabicNumerals
from app.utils.patterns import ArticlePatterns

logger = logging.getLogger(__name__)


class ArticleSplitterStep(PipelineStep):
    """
    Step 3: Split text by article (مادة) boundaries.
    
    IMPORTANT: This uses REGEX splitting to ensure each chunk
    contains exactly one legal article for accurate citations.
    
    Input: List[PageContent]
    Output: List[RawArticle]
    """
    
    # === ARTICLE DETECTION PATTERNS ===
    # Comprehensive patterns for Arabic legal articles
    ARTICLE_PATTERNS = [
        r'مادة\s*([٠-٩]+)',              # مادة ١٢٣ (Arabic numerals)
        r'مادة\s*([0-9]+)',              # مادة 123 (English numerals)
        r'مادة\s*\(([٠-٩0-9]+)\)',       # مادة (١٢٣) (parentheses)
        r'مادة\s*\[([٠-٩0-9]+)\]',       # مادة [10] (square brackets)
        r'المادة\s*([٠-٩0-9]+)',         # المادة ١٢٣ (with ال)
        r'المادة\s*\(([٠-٩0-9]+)\)',     # المادة (١٢٣)
        r'المادة\s*\[([٠-٩0-9]+)\]',     # المادة [10]
    ]
    
    # Pattern for splitting (matches article start)
    # This pattern looks ahead to find article boundaries
    SPLIT_PATTERN = r'(?=(?:^|\n)\s*(?:مادة|المادة)\s*[\[\(]?[٠-٩0-9]+[\]\)]?)'
    
    def __init__(self):
        super().__init__("Article Splitter")
        self._compiled_patterns = [re.compile(p) for p in self.ARTICLE_PATTERNS]
        self._split_pattern = re.compile(self.SPLIT_PATTERN, re.MULTILINE)
    
    def process(self, data: List[PageContent], context: Dict[str, Any]) -> List[RawArticle]:
        """
        Split pages into articles.
        
        Args:
            data: List of PageContent from text extraction
            context: Pipeline context
            
        Returns:
            List of RawArticle objects
        """
        # Combine all pages into single text with page markers
        full_text, page_map = self._combine_pages(data)
        
        self.logger.info(f"Combined {len(data)} pages into {len(full_text)} chars")
        
        # Split by article boundaries using REGEX
        chunks = self._split_pattern.split(full_text)
        
        self.logger.info(f"Split into {len(chunks)} raw chunks")
        
        # Process each chunk
        articles = []
        preamble_saved = False
        
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            
            # Extract article number
            article_num = self._extract_article_number(chunk)
            article_text = self._extract_article_text(chunk)
            
            # Determine page number
            page_num = self._find_page_number(chunk, page_map, full_text)
            
            # Extract chapter info
            chapter = self._extract_chapter(chunk)
            
            # Handle preamble (text before first article)
            if article_num is None:
                if not preamble_saved and len(chunk) > 100:
                    # Save preamble as article 0
                    articles.append(RawArticle(
                        article_number=0,
                        article_text="مقدمة",
                        content=chunk,
                        page_number=page_num,
                        chapter=chapter,
                    ))
                    preamble_saved = True
                continue
            
            articles.append(RawArticle(
                article_number=article_num,
                article_text=article_text,
                content=chunk,
                page_number=page_num,
                chapter=chapter,
            ))
        
        context["articles_found"] = len(articles)
        self.logger.info(f"Found {len(articles)} articles")
        
        return articles
    
    def _combine_pages(self, pages: List[PageContent]) -> tuple[str, Dict[int, int]]:
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
    
    def _find_page_number(self, chunk: str, page_map: Dict[int, int], full_text: str) -> int:
        """Find page number for a chunk"""
        # Find chunk position in full text
        try:
            pos = full_text.find(chunk[:100])  # Use first 100 chars
            if pos == -1:
                return 1
            
            # Find closest page marker
            for char_pos in sorted(page_map.keys(), reverse=True):
                if char_pos <= pos:
                    return page_map[char_pos]
            
            return 1
        except Exception:
            return 1
    
    def _extract_article_number(self, text: str) -> Optional[int]:
        """
        Extract article number from text.
        
        Args:
            text: Text that may contain article marker
            
        Returns:
            Article number or None
        """
        # Check first 200 characters
        search_text = text[:200] if len(text) > 200 else text
        
        for pattern in self._compiled_patterns:
            match = pattern.search(search_text)
            if match:
                num_str = match.group(1)
                return ArabicNumerals.extract_number(num_str)
        
        return None
    
    def _extract_article_text(self, text: str) -> Optional[str]:
        """
        Extract the article marker text (e.g., "مادة ٣١٨").
        
        Args:
            text: Text containing article marker
            
        Returns:
            Article marker text or None
        """
        # Pattern to match the full article marker
        full_pattern = r'((?:مادة|المادة)\s*[\[\(]?[٠-٩0-9]+[\]\)]?)'
        
        search_text = text[:200] if len(text) > 200 else text
        match = re.search(full_pattern, search_text)
        
        if match:
            return match.group(1).strip()
        return None
    
    def _extract_chapter(self, text: str) -> Optional[str]:
        """Extract chapter/section information"""
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
