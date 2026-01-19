"""
Utility modules for Scrapy spiders
Provides field extraction and data normalization helpers
"""

from .field_extractor import FieldExtractor
from .normalizer import DataNormalizer

__all__ = ['FieldExtractor', 'DataNormalizer']

