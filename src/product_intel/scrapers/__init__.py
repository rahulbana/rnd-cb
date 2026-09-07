"""Site-specific scrapers. Currently: Amazon."""

from .amazon import AmazonScraper, extract_asin, is_blocked, parse_amazon

__all__ = ["AmazonScraper", "extract_asin", "is_blocked", "parse_amazon"]
