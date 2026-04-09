# hooks/search/__init__.py
"""搜索钩子模块 - 提供搜索操作扩展点"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SearchQuery:
    """搜索查询对象"""

    query: str
    scope: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 5


@dataclass
class SearchResult:
    """搜索结果对象"""

    content: str
    source: str
    source_type: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class SearchHook(ABC):
    """搜索钩子基类 - 提供搜索操作前后的扩展点"""

    @abstractmethod
    async def on_before_search(self, query: SearchQuery) -> Optional[SearchQuery]:
        """
        搜索执行前调用

        Args:
            query: 搜索查询对象

        Returns:
            修改后的查询对象，如果返回None则使用原始查询
        """
        pass

    @abstractmethod
    async def on_after_search(self, results: List[SearchResult]) -> Optional[List[SearchResult]]:
        """
        搜索执行后调用

        Args:
            results: 搜索结果列表

        Returns:
            修改后的结果列表，如果返回None则使用原始结果
        """
        pass

    @abstractmethod
    async def on_search_error(self, query: SearchQuery, error: Exception):
        """
        搜索出错时调用

        Args:
            query: 搜索查询对象
            error: 异常对象
        """
        pass


class RerankHook(ABC):
    """重排钩子 - 提供搜索结果重排扩展点"""

    @abstractmethod
    async def on_before_rerank(self, results: List[SearchResult], query: str) -> Optional[List[SearchResult]]:
        """
        重排执行前调用

        Args:
            results: 原始搜索结果
            query: 搜索查询

        Returns:
            修改后的结果列表，如果返回None则使用原始结果
        """
        pass

    @abstractmethod
    async def on_after_rerank(self, results: List[SearchResult]) -> Optional[List[SearchResult]]:
        """
        重排执行后调用

        Args:
            results: 重排后的搜索结果

        Returns:
            修改后的结果列表，如果返回None则使用原始结果
        """
        pass


class IndexHook(ABC):
    """索引钩子 - 提供索引操作扩展点"""

    @abstractmethod
    async def on_before_index(self, document: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        文档索引前调用

        Args:
            document: 待索引的文档

        Returns:
            修改后的文档，如果返回None则使用原始文档
        """
        pass

    @abstractmethod
    async def on_after_index(self, document_id: str, document: Dict[str, Any]):
        """
        文档索引后调用

        Args:
            document_id: 文档ID
            document: 已索引的文档
        """
        pass

    @abstractmethod
    async def on_index_error(self, document: Dict[str, Any], error: Exception):
        """
        索引出错时调用

        Args:
            document: 待索引的文档
            error: 异常对象
        """
        pass
