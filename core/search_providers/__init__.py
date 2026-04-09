# core/search_providers/__init__.py
"""
搜索提供者模块
支持多种搜索引擎后端：
- SearXNG (自托管元搜索引擎)
- 其他搜索引擎（可扩展）
"""

from .searxng_client import SearchResult, SearXNGClient
from .summarizer import SearchSummarizer

__all__ = [
    "SearXNGClient",
    "SearchResult",
    "SearchSummarizer",
]
