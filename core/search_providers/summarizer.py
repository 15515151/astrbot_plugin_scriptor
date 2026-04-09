# core/search_providers/summarizer.py
"""
搜索结果摘要器
功能：
1. 将搜索结果压缩为短记忆
2. 判定是否应该归档（1% 重要信息）
3. 提取关键事实和用户偏好
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

from .searxng_client import SearchResult


class ArchiveDecision(Enum):
    """归档判定结果"""

    ARCHIVE = "archive"  # 应该归档
    SKIP = "skip"  # 跳过，不归档
    UNCERTAIN = "uncertain"  # 不确定（默认跳过）


class SearchSummarizer:
    """搜索结果摘要生成器"""

    def __init__(self, max_tokens: int = 500, archive_threshold: float = 0.8):
        """
        初始化摘要器

        Args:
            max_tokens: 摘要最大 token 数
            archive_threshold: 归档判定阈值（0-1，越高越严格）
        """
        self.max_tokens = max_tokens
        self.archive_threshold = archive_threshold

    async def summarize(self, results: List[SearchResult], original_query: str, max_results: int = 5) -> str:
        """
        生成搜索结果摘要

        Args:
            results: 搜索结果列表
            original_query: 原始搜索词
            max_results: 最多使用的结果数

        Returns:
            格式化的摘要文本
        """
        if not results:
            return "未找到相关搜索结果"

        selected_results = results[:max_results]

        summary_parts = []
        summary_parts.append(f'【关于"{original_query}"的搜索结果】\n')

        for i, result in enumerate(selected_results, 1):
            source = self._extract_source_name(result.url)
            content = self._truncate_content(result.content, max_length=200)

            summary_parts.append(f"{i}. **{result.title}** - {source}\n" f"   {content}\n")

        summary_text = "\n".join(summary_parts)

        logger.debug(f"[Summarizer] 生成摘要：{len(selected_results)} 条结果")
        return summary_text

    def should_archive(
        self, query: str, results: List[SearchResult], user_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ArchiveDecision, float, str]:
        """
        判断是否应该归档搜索结果

        判定规则：
        - 99% 的情况不归档：一次性查询、新闻、天气、代码错误等
        - 1% 的情况归档：用户偏好、重要事实、长期参考信息

        Args:
            query: 搜索关键词
            results: 搜索结果列表
            user_context: 用户上下文（可选）

        Returns:
            (decision, confidence, reason)
            - decision: 归档判定
            - confidence: 置信度 (0-1)
            - reason: 判定理由
        """
        score = 0.0
        reasons = []

        query_lower = query.lower()

        # === 不归档的情况（99%）===

        # 1. 一次性查询
        one_time_queries = [
            "天气",
            "气温",
            "下雨",
            "星期",
            "几点",
            "时间",
            "新闻",
            "热点",
            "热搜",
            "最新",
            "刚刚",
            "错误",
            "报错",
            "exception",
            "error",
            "bug",
            "怎么办",
            "如何解决",
            "怎么修",
        ]

        for keyword in one_time_queries:
            if keyword in query_lower:
                reasons.append(f"包含一次性查询关键词：{keyword}")
                score -= 0.5

        # 2. 时效性强的内容
        time_sensitive_patterns = [
            r"今天.*天气",
            r"明天.*气温",
            r"现在.*时间",
            r"最近.*新闻",
            r"最新.*消息",
            r"\d{4}年.*月",
        ]

        for pattern in time_sensitive_patterns:
            if re.search(pattern, query_lower):
                reasons.append("时效性强的查询")
                score -= 0.4
                break

        # 3. 代码和技术问题
        if any(kw in query_lower for kw in ["代码", "python", "java", "js", "函数", "api"]):
            if any(kw in query_lower for kw in ["错误", "报错", "异常", "debug"]):
                reasons.append("代码调试问题（一次性）")
                score -= 0.6

        # === 应该归档的情况（1%）===

        # 1. 用户偏好相关
        preference_keywords = ["喜欢", "讨厌", "偏好", "习惯", "爱", "不喜欢", "推荐", "值得", "好用", "靠谱"]

        for keyword in preference_keywords:
            if keyword in query_lower:
                reasons.append(f"可能涉及用户偏好：{keyword}")
                score += 0.4

        # 2. 事实和知识查询
        fact_keywords = [
            "是什么",
            "什么是",
            "定义",
            "含义",
            "意思",
            "历史",
            "起源",
            "由来",
            "背景",
            "原理",
            "机制",
            "为什么",
        ]

        for keyword in fact_keywords:
            if keyword in query_lower:
                reasons.append(f"事实性知识查询：{keyword}")
                score += 0.3

        # 3. 长期参考信息
        reference_keywords = ["教程", "指南", "手册", "文档", "方法", "技巧", "窍门", "经验", "攻略"]

        for keyword in reference_keywords:
            if keyword in query_lower:
                reasons.append(f"长期参考信息：{keyword}")
                score += 0.3

        # 4. 健康、法律、医疗等重要领域
        important_domains = [
            "健康",
            "医疗",
            "疾病",
            "症状",
            "药",
            "法律",
            "法规",
            "条例",
            "合同",
            "理财",
            "保险",
            "税务",
        ]

        for keyword in important_domains:
            if keyword in query_lower:
                reasons.append(f"重要领域信息：{keyword}")
                score += 0.5

        # === 综合判定 ===

        # 归一化分数到 0-1 范围
        normalized_score = 1.0 / (1.0 + pow(2, -score))

        if normalized_score >= self.archive_threshold:
            decision = ArchiveDecision.ARCHIVE
            confidence = normalized_score
            reason = "建议归档：" + "；".join(reasons)
        elif normalized_score <= (1.0 - self.archive_threshold):
            decision = ArchiveDecision.SKIP
            confidence = 1.0 - normalized_score
            reason = "跳过归档：" + "；".join(reasons)
        else:
            decision = ArchiveDecision.UNCERTAIN
            confidence = 0.5
            reason = "无法确定：" + "；".join(reasons) if reasons else "缺乏判定依据"

        logger.debug(f"[Summarizer] 归档判定：{decision.value} " f"(置信度：{confidence:.2f}, 理由：{reason})")

        return decision, confidence, reason

    def extract_facts(self, results: List[SearchResult], query: str) -> List[Dict[str, str]]:
        """
        从搜索结果中提取关键事实

        Args:
            results: 搜索结果列表
            query: 搜索关键词

        Returns:
            事实列表，每个事实包含 {fact, source, confidence}
        """
        facts = []

        for result in results[:3]:  # 只处理前 3 条结果
            fact = self._extract_single_fact(result.content, result.title)

            if fact:
                facts.append(
                    {
                        "fact": fact,
                        "source": self._extract_source_name(result.url),
                        "confidence": result.score if result.score > 0 else 0.5,
                    }
                )

        return facts

    def extract_user_preference(self, results: List[SearchResult], query: str) -> Optional[str]:
        """
        从搜索结果中提取用户偏好

        Args:
            results: 搜索结果列表
            query: 搜索关键词

        Returns:
            用户偏好描述，如果没有提取到则返回 None
        """
        preference_keywords = ["喜欢", "讨厌", "偏好", "习惯", "推荐"]

        if not any(kw in query.lower() for kw in preference_keywords):
            return None

        for result in results[:2]:
            preference = self._extract_preference(result.content)
            if preference:
                return preference

        return None

    def _truncate_content(self, content: str, max_length: int = 200) -> str:
        """截断内容到指定长度"""
        if len(content) <= max_length:
            return content

        return content[:max_length] + "..."

    def _extract_source_name(self, url: str) -> str:
        """从 URL 提取来源名称"""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            if "google" in domain:
                return "Google"
            elif "bing" in domain:
                return "Bing"
            elif "baidu" in domain:
                return "百度"
            elif "zhihu" in domain:
                return "知乎"
            elif "wikipedia" in domain or "wiki" in domain:
                return "维基百科"
            else:
                return domain.replace("www.", "")
        except Exception as e:
            logger.debug(f"[Summarizer] 解析域名失败: {e}")
            return "未知来源"

    def _extract_single_fact(self, content: str, title: str) -> Optional[str]:
        """从单条结果中提取事实"""
        if not content:
            return None

        content = content.strip()

        if len(content) > 300:
            content = content[:300] + "..."

        sentences = re.split(r"[。！？.!?]", content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if sentences:
            return sentences[0]

        return None

    def _extract_preference(self, content: str) -> Optional[str]:
        """从内容中提取偏好"""
        preference_patterns = [
            r"喜欢.*?([^\u3000-\u303f\u4e00-\u9fa5])",
            r"讨厌.*?([^\u3000-\u303f\u4e00-\u9fa5])",
            r"偏好.*?([^\u3000-\u303f\u4e00-\u9fa5])",
            r"推荐.*?([^\u3000-\u303f\u4e00-\u9fa5])",
        ]

        for pattern in preference_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(0).strip()

        return None

    def format_for_archive(
        self, query: str, summary: str, decision_reason: str, facts: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        格式化归档数据

        Args:
            query: 搜索关键词
            summary: 摘要内容
            decision_reason: 归档判定理由
            facts: 提取的事实列表

        Returns:
            归档数据字典
        """
        return {
            "query": query,
            "summary": summary,
            "archive_reason": decision_reason,
            "facts": facts,
            "timestamp": datetime.now().isoformat(),
            "tags": self._generate_tags(query),
        }

    def _generate_tags(self, query: str) -> List[str]:
        """生成标签"""
        tags = ["web_search"]

        query_lower = query.lower()

        if any(kw in query_lower for kw in ["喜欢", "偏好", "推荐"]):
            tags.append("preference")
        elif any(kw in query_lower for kw in ["是什么", "定义", "历史"]):
            tags.append("fact")
        elif any(kw in query_lower for kw in ["教程", "指南", "方法"]):
            tags.append("tutorial")
        elif any(kw in query_lower for kw in ["新闻", "最新"]):
            tags.append("news")

        return tags
