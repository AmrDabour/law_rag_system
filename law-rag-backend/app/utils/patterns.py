"""
Article Detection Patterns
Regex patterns for detecting Arabic legal articles (مادة)
"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass

from app.utils.arabic import ArabicNumerals


@dataclass
class ArticleMatch:
    """Represents a matched article in text"""
    article_number: int
    article_text: str  # The matched text (e.g., "مادة ٣١٨")
    start_pos: int
    end_pos: int


class ArticlePatterns:
    """
    Article detection patterns for Arabic legal documents.
    Supports multiple formats: مادة ١٢٣, مادة 123, مادة (١٢٣), مادة [10], etc.
    """
    
    # === ARTICLE DETECTION PATTERNS ===
    # These patterns match article markers in Arabic legal text
    ARTICLE_PATTERNS = [
        r'مادة\s*([٠-٩]+)',              # مادة ١٢٣ (Arabic numerals)
        r'مادة\s*([0-9]+)',              # مادة 123 (English numerals)
        r'مادة\s*\(([٠-٩0-9]+)\)',       # مادة (١٢٣) (parentheses)
        r'مادة\s*\[([٠-٩0-9]+)\]',       # مادة [10] (square brackets)
        r'المادة\s*([٠-٩0-9]+)',         # المادة ١٢٣ (with ال)
        r'المادة\s*\(([٠-٩0-9]+)\)',     # المادة (١٢٣)
        r'المادة\s*\[([٠-٩0-9]+)\]',     # المادة [10]
    ]
    
    # Combined pattern for detection (non-capturing for splitting)
    SPLIT_PATTERN = r'(?=(?:مادة|المادة)\s*[\[\(]?[٠-٩0-9]+[\]\)]?)'
    
    # Pattern for extracting article number from chunk start
    ARTICLE_START_PATTERN = r'^(?:مادة|المادة)\s*[\[\(]?([٠-٩0-9]+)[\]\)]?'
    
    # === CHAPTER/SECTION PATTERNS ===
    CHAPTER_PATTERNS = [
        r'الباب\s*(الأول|الثاني|الثالث|الرابع|الخامس|[٠-٩0-9]+)',
        r'الفصل\s*(الأول|الثاني|الثالث|الرابع|الخامس|[٠-٩0-9]+)',
        r'القسم\s*(الأول|الثاني|الثالث|الرابع|الخامس|[٠-٩0-9]+)',
    ]
    
    @classmethod
    def get_combined_pattern(cls) -> re.Pattern:
        """Get compiled regex pattern that matches any article format"""
        combined = '|'.join(f'({p})' for p in cls.ARTICLE_PATTERNS)
        return re.compile(combined)
    
    @classmethod
    def find_all_articles(cls, text: str) -> List[ArticleMatch]:
        """
        Find all article markers in text.
        
        Args:
            text: The text to search
            
        Returns:
            List of ArticleMatch objects
        """
        matches = []
        
        for pattern in cls.ARTICLE_PATTERNS:
            for match in re.finditer(pattern, text):
                num_str = match.group(1)
                article_num = ArabicNumerals.extract_number(num_str)
                
                if article_num is not None:
                    matches.append(ArticleMatch(
                        article_number=article_num,
                        article_text=match.group(0),
                        start_pos=match.start(),
                        end_pos=match.end()
                    ))
        
        # Sort by position and remove duplicates
        matches.sort(key=lambda m: m.start_pos)
        
        # Remove overlapping matches (keep first)
        unique_matches = []
        last_end = -1
        for m in matches:
            if m.start_pos >= last_end:
                unique_matches.append(m)
                last_end = m.end_pos
        
        return unique_matches
    
    @classmethod
    def split_by_articles(cls, text: str) -> List[Tuple[Optional[int], str]]:
        """
        Split text by article boundaries.
        
        Args:
            text: Full legal document text
            
        Returns:
            List of tuples (article_number, article_content)
            article_number is None for preamble/non-article content
        """
        # Split on article boundaries
        chunks = re.split(cls.SPLIT_PATTERN, text)
        
        result = []
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            
            # Try to extract article number from start
            article_num = cls.extract_article_number(chunk)
            result.append((article_num, chunk))
        
        return result
    
    @classmethod
    def extract_article_number(cls, text: str) -> Optional[int]:
        """
        Extract article number from the beginning of text.
        
        Args:
            text: Text that may start with an article marker
            
        Returns:
            Article number or None
        """
        # Check first 100 characters for article marker
        search_text = text[:100] if len(text) > 100 else text
        
        for pattern in cls.ARTICLE_PATTERNS:
            match = re.search(pattern, search_text)
            if match:
                num_str = match.group(1)
                return ArabicNumerals.extract_number(num_str)
        
        return None
    
    @classmethod
    def extract_chapter_info(cls, text: str) -> Optional[str]:
        """
        Extract chapter/section information from text.
        
        Args:
            text: Text to search for chapter markers
            
        Returns:
            Chapter name or None
        """
        for pattern in cls.CHAPTER_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None
    
    @classmethod
    def format_citation(cls, 
                       law_name: str, 
                       article_number: int,
                       page_number: Optional[int] = None,
                       use_arabic_numerals: bool = True) -> str:
        """
        Format a legal citation.
        
        Args:
            law_name: Name of the law
            article_number: Article number
            page_number: Optional page number
            use_arabic_numerals: Use Arabic numerals in output
            
        Returns:
            Formatted citation string
        """
        num_str = str(article_number)
        if use_arabic_numerals:
            num_str = ArabicNumerals.to_arabic(num_str)
        
        citation = f"{law_name} - مادة {num_str}"
        
        if page_number:
            page_str = str(page_number)
            if use_arabic_numerals:
                page_str = ArabicNumerals.to_arabic(page_str)
            citation += f" (صفحة {page_str})"
        
        return citation
