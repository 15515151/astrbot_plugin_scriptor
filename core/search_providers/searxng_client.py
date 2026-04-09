# core/search_providers/searxng_client.py
"""
SearXNG 搜索引擎客户端
封装 SearXNG API 请求，提供异步搜索功能
"""

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索结果"""

    title: str
    content: str
    url: str
    engine: str = ""
    score: float = 0.0
    published_date: str = ""
    category: str = ""

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "SearchResult":
        """从 API 响应创建搜索结果"""
        return cls(
            title=data.get("title", "无标题"),
            content=data.get("content", ""),
            url=data.get("url", ""),
            engine=data.get("engine", "unknown"),
            score=data.get("score", 0.0),
            published_date=data.get("publishedDate", ""),
            category=data.get("category", "general"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "title": self.title,
            "content": self.content,
            "url": self.url,
            "engine": self.engine,
            "score": self.score,
            "published_date": self.published_date,
            "category": self.category,
        }


class SearXNGClient:
    """SearXNG 搜索引擎客户端"""

    def __init__(
        self,
        base_url: str = "",
        timeout: int = 10,
        max_results: int = 10,
        secret: Optional[str] = None,
    ):
        """
        初始化 SearXNG 客户端

        Args:
            base_url: SearXNG 服务器地址
            timeout: 请求超时时间（秒）
            max_results: 最大返回结果数
            secret: SearXNG 密钥（可选，用于高级功能）
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_results = max_results
        self.secret = secret

        self._client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._last_request_time = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout, connect=5.0),
                headers={"User-Agent": "Scriptor-Plugin/1.0", "Accept": "application/json"},
            )
        return self._client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def search(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        engines: Optional[List[str]] = None,
        language: str = "zh-CN",
        pageno: int = 1,
        safe_search: int = 0,
        time_range: Optional[str] = None,
        format_type: str = "json",
    ) -> List[SearchResult]:
        """
        执行搜索

        Args:
            query: 搜索关键词
            categories: 搜索类别（如 ['general', 'news', 'science']）
            engines: 指定搜索引擎（如 ['google', 'bing', 'duckduckgo']）
            language: 语言（默认 zh-CN）
            pageno: 页码
            safe_search: 安全搜索级别 (0=关闭，1=中等，2=严格)
            time_range: 时间范围 (None, 'day', 'week', 'month', 'year')
            format_type: 返回格式（默认 json）

        Returns:
            搜索结果列表

        Raises:
            httpx.HTTPError: HTTP 请求失败
            TimeoutError: 请求超时
        """
        url = f"{self.base_url}/search"

        params: Dict[str, Any] = {
            "q": query,
            "format": format_type,
            "pageno": pageno,
            "language": language,
            "safe_search": safe_search,
        }

        if categories:
            params["categories"] = ",".join(categories)

        if engines:
            params["engines"] = ",".join(engines)

        if time_range:
            params["time_range"] = time_range

        try:
            client = await self._get_client()
            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            logger.debug(f"[SearXNG] 搜索 '{query}' 返回 {len(results)} 条结果")

            search_results = []
            for item in results[: self.max_results]:
                try:
                    result = SearchResult.from_api_response(item)
                    search_results.append(result)
                except Exception as e:
                    logger.warning(f"[SearXNG] 解析搜索结果失败：{e}")

            return search_results

        except httpx.TimeoutException as e:
            logger.error(f"[SearXNG] 搜索超时：{e}")
            raise TimeoutError(f"SearXNG 搜索超时：{e}")
        except httpx.HTTPError as e:
            logger.error(f"[SearXNG] HTTP 错误：{e}")
            raise
        except Exception as e:
            logger.error(f"[SearXNG] 搜索失败：{e}")
            raise

    async def suggest(self, query: str) -> List[str]:
        """
        获取搜索建议

        Args:
            query: 搜索关键词

        Returns:
            搜索建议列表
        """
        url = f"{self.base_url}/autocompleter"
        params = {"q": query}

        try:
            client = await self._get_client()
            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            suggestions = data if isinstance(data, list) else []

            logger.debug(f"[SearXNG] 搜索建议：{suggestions}")
            return suggestions

        except Exception as e:
            logger.warning(f"[SearXNG] 获取搜索建议失败：{e}")
            return []

    async def health_check(self) -> bool:
        """
        检查 SearXNG 服务是否可用

        Returns:
            True 如果服务可用，否则 False
        """
        url = f"{self.base_url}/healthz"

        try:
            client = await self._get_client()
            response = await client.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"[SearXNG] 健康检查失败：{e}")
            return False

    def generate_query_id(self, query: str, timestamp: Optional[float] = None) -> str:
        """
        生成查询 ID（用于缓存和去重）

        Args:
            query: 搜索关键词
            timestamp: 时间戳（可选）

        Returns:
            查询 ID
        """
        if timestamp is None:
            timestamp = datetime.now().timestamp()

        content = f"{query}:{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def deduplicate_results(self, results: List[SearchResult], threshold: float = 0.9) -> List[SearchResult]:
        """
        去重搜索结果（基于内容相似度）

        Args:
            results: 搜索结果列表
            threshold: 相似度阈值（0-1，越高越严格）

        Returns:
            去重后的结果列表
        """
        if not results:
            return []

        unique_results = []
        seen_hashes = set()

        for result in results:
            content_hash = hashlib.md5(result.content[:100].encode()).hexdigest()

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_results.append(result)

        logger.debug(f"[SearXNG] 去重：{len(results)} -> {len(unique_results)} 条结果")
        return unique_results

    async def search_with_retry(
        self, query: str, max_retries: int = 2, retry_delay: float = 1.0, **kwargs
    ) -> List[SearchResult]:
        """
        带重试的搜索

        Args:
            query: 搜索关键词
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
            **kwargs: 传递给 search() 的其他参数

        Returns:
            搜索结果列表
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                results = await self.search(query, **kwargs)

                if results:
                    return self.deduplicate_results(results)

                logger.warning(f"[SearXNG] 搜索返回空结果，尝试重试 ({attempt + 1}/{max_retries})")

            except Exception as e:
                last_exception = e
                logger.warning(f"[SearXNG] 搜索失败 ({attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries:
                await asyncio.sleep(retry_delay * (attempt + 1))

        if last_exception:
            logger.error(f"[SearXNG] 所有重试均失败：{last_exception}")
            raise last_exception

        return []

    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
