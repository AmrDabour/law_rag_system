"""
Arabic Text Utilities
Normalization, numeral conversion, and text processing for Arabic legal text
"""

import re
from typing import Optional


class ArabicNormalizer:
    """Arabic text normalization utilities for legal documents"""
    
    # Character normalization mappings
    ALEF_VARIANTS = {'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا'}
    TEH_MARBUTA = {'ة': 'ه'}
    ALEF_MAKSURA = {'ى': 'ي'}
    
    # Diacritics pattern (tashkeel)
    DIACRITICS = re.compile(r'[\u064B-\u065F\u0670]')
    
    # Tatweel (kashida) character
    TATWEEL = '\u0640'
    
    # Multiple spaces/newlines
    WHITESPACE = re.compile(r'\s+')
    
    @classmethod
    def normalize(cls, text: str, 
                  remove_diacritics: bool = True,
                  remove_tatweel: bool = True,
                  normalize_alef: bool = True,
                  normalize_teh: bool = False,  # Keep ة by default for legal accuracy
                  normalize_yeh: bool = False,  # Keep ى by default for legal accuracy
                  normalize_whitespace: bool = True) -> str:
        """
        Full Arabic text normalization pipeline.
        
        Args:
            text: Input Arabic text
            remove_diacritics: Remove tashkeel (harakat)
            remove_tatweel: Remove kashida
            normalize_alef: Normalize alef variants to bare alef
            normalize_teh: Normalize teh marbuta to heh
            normalize_yeh: Normalize alef maksura to yeh
            normalize_whitespace: Collapse multiple spaces
            
        Returns:
            Normalized Arabic text
        """
        if not text:
            return ""
        
        # Remove diacritics (tashkeel)
        if remove_diacritics:
            text = cls.DIACRITICS.sub('', text)
        
        # Remove tatweel
        if remove_tatweel:
            text = text.replace(cls.TATWEEL, '')
        
        # Normalize alef variants
        if normalize_alef:
            for variant, normalized in cls.ALEF_VARIANTS.items():
                text = text.replace(variant, normalized)
        
        # Normalize teh marbuta (optional - disabled by default)
        if normalize_teh:
            for variant, normalized in cls.TEH_MARBUTA.items():
                text = text.replace(variant, normalized)
        
        # Normalize alef maksura (optional - disabled by default)
        if normalize_yeh:
            for variant, normalized in cls.ALEF_MAKSURA.items():
                text = text.replace(variant, normalized)
        
        # Normalize whitespace
        if normalize_whitespace:
            text = cls.WHITESPACE.sub(' ', text).strip()
        
        return text
    
    @classmethod
    def normalize_for_search(cls, text: str) -> str:
        """
        Aggressive normalization for search/matching purposes.
        Use this for query preprocessing.
        """
        return cls.normalize(
            text,
            remove_diacritics=True,
            remove_tatweel=True,
            normalize_alef=True,
            normalize_teh=True,
            normalize_yeh=True,
            normalize_whitespace=True
        )
    
    @classmethod
    def normalize_for_display(cls, text: str) -> str:
        """
        Light normalization for display purposes.
        Preserves most original formatting.
        """
        return cls.normalize(
            text,
            remove_diacritics=False,
            remove_tatweel=True,
            normalize_alef=False,
            normalize_teh=False,
            normalize_yeh=False,
            normalize_whitespace=True
        )


class ArabicNumerals:
    """Arabic-English numeral conversion utilities"""
    
    # Translation tables
    ARABIC_TO_ENGLISH = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
    ENGLISH_TO_ARABIC = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
    
    @classmethod
    def to_english(cls, text: str) -> str:
        """Convert Arabic numerals to English numerals"""
        return text.translate(cls.ARABIC_TO_ENGLISH)
    
    @classmethod
    def to_arabic(cls, text: str) -> str:
        """Convert English numerals to Arabic numerals"""
        return text.translate(cls.ENGLISH_TO_ARABIC)
    
    @classmethod
    def extract_number(cls, text: str, try_reverse: bool = True) -> Optional[int]:
        """
        Extract first number from text (handles both Arabic and English numerals).

        Also handles reversed Arabic numerals from PDF extraction where RTL text
        causes multi-digit numbers to be reversed (e.g., ١٢ becomes ٢١).

        Args:
            text: Text containing a number
            try_reverse: If True, also return the reversed number for multi-digit nums

        Returns:
            Extracted integer or None if no number found
        """
        # First convert any Arabic numerals to English
        english_text = cls.to_english(text)

        # Extract number
        match = re.search(r'\d+', english_text)
        if not match:
            return None

        num_str = match.group()
        return int(num_str)

    @classmethod
    def extract_number_with_reverse(cls, text: str) -> tuple[Optional[int], Optional[int]]:
        """
        Extract number and its reversed form (for handling RTL PDF extraction issues).

        Returns:
            Tuple of (normal_number, reversed_number) - reversed is None for single digits
        """
        # First convert any Arabic numerals to English
        english_text = cls.to_english(text)

        # Extract number
        match = re.search(r'\d+', english_text)
        if not match:
            return None, None

        num_str = match.group()
        normal = int(num_str)

        # For multi-digit numbers, also compute reversed version
        if len(num_str) > 1:
            reversed_num = int(num_str[::-1])
            return normal, reversed_num

        return normal, None
    
    @classmethod
    def format_article_number(cls, number: int, use_arabic: bool = True) -> str:
        """
        Format an article number for display.
        
        Args:
            number: The article number
            use_arabic: Whether to use Arabic numerals
            
        Returns:
            Formatted article number string
        """
        num_str = str(number)
        if use_arabic:
            num_str = cls.to_arabic(num_str)
        return f"مادة {num_str}"
