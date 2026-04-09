# core/usage_docs.py
"""
使用文档知识库模块 - 专门用于存储和检索 Scriptor 使用说明
核心特点：
1. 加载使用说明文档（FAQ、快速开始等）
2. 智能分块，按标题组织
3. 支持检索相关段落
4. 按需检索，不占用 token
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


@dataclass
class DocChunk:
    """文档片段"""

    id: str
    title: str
    content: str
    source_file: str
    section_level: int = 2
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_search_text(self) -> str:
        """用于搜索的文本"""
        return f"{self.title} {self.content}"

    def to_formatted_output(self) -> str:
        """格式化输出"""
        return f"## {self.title}\n\n{self.content}"


class UsageDocsKnowledgeBase:
    """使用文档知识库"""

    def __init__(self, data_dir: Path, search_engine=None):
        self.data_dir = data_dir
        self.docs_dir = data_dir / "knowledge_docs"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self._chunks: Dict[str, DocChunk] = {}
        self._search_engine = search_engine
        self._load_all()

    def set_search_engine(self, search_engine):
        """注入 SearchEngine 实例"""
        self._search_engine = search_engine
        logger.info("[UsageDocs] SearchEngine 已注入")

    def _load_all(self):
        """加载所有使用文档"""
        if not self.docs_dir.exists():
            logger.warning(f"[UsageDocs] 文档目录不存在: {self.docs_dir}")
            return

        md_files = sorted(self.docs_dir.glob("*.md"))

        if not md_files:
            logger.info("[UsageDocs] 未找到文档文件")
            return

        total_chunks = 0
        for md_file in md_files:
            try:
                chunks = self._parse_markdown_file(md_file)
                for chunk in chunks:
                    self._chunks[chunk.id] = chunk
                total_chunks += len(chunks)
                logger.info(f"[UsageDocs] 加载文档: {md_file.name} ({len(chunks)} 片段)")
            except Exception as e:
                logger.error(f"[UsageDocs] 加载文档失败: {md_file.name}, 错误: {e}")

        logger.info(f"[UsageDocs] 文档加载完成: {len(md_files)} 个文件, {total_chunks} 个片段")

    def _parse_markdown_file(self, file_path: Path) -> List[DocChunk]:
        """解析 Markdown 文件，按标题分块"""
        content = file_path.read_text(encoding="utf-8")
        chunks = []

        # 按标题分割（## 或 ###）
        sections = re.split(r"\n(?=##+ )", content)

        current_title = file_path.stem
        section_level = 1

        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue

            # 提取标题
            title_match = re.match(r"^(##+ )(.*?)$", section, re.MULTILINE)
            if title_match:
                hashes = title_match.group(1).strip()
                current_title = title_match.group(2).strip()
                section_level = len(hashes)
                # 移除标题行，保留内容
                content_lines = section.split("\n")[1:]
                chunk_content = "\n".join(content_lines).strip()
            else:
                chunk_content = section

            if chunk_content:
                chunk_id = self._generate_chunk_id(file_path.name, i)
                chunk = DocChunk(
                    id=chunk_id,
                    title=current_title,
                    content=chunk_content,
                    source_file=file_path.name,
                    section_level=section_level,
                )
                chunks.append(chunk)

        return chunks

    @staticmethod
    def _generate_chunk_id(filename: str, index: int) -> str:
        """生成片段 ID"""
        import hashlib

        combined = f"{filename}_{index}"
        return hashlib.md5(combined.encode()).hexdigest()[:12]

    def search(self, query: str, limit: int = 3) -> List[DocChunk]:
        """搜索使用文档"""
        # 如果有 SearchEngine，优先使用
        if self._search_engine:
            return self._search_with_engine(query, limit)

        # 回退到本地搜索
        return self._search_local(query, limit)

    def _search_with_engine(self, query: str, limit: int) -> List[DocChunk]:
        """使用 SearchEngine 搜索"""
        try:
            # 准备文档
            docs = []
            chunk_list = list(self._chunks.values())
            for chunk in chunk_list:
                docs.append(chunk.to_search_text())

            if not docs:
                return []

            # 使用 SearchEngine 的搜索功能
            # 注意：这里需要 SearchEngine 支持自定义文档搜索
            # 暂时使用本地搜索
            logger.debug("[UsageDocs] SearchEngine 搜索暂未完全实现，使用本地搜索")
            return self._search_local(query, limit)

        except Exception as e:
            logger.warning(f"[UsageDocs] SearchEngine 搜索失败，回退到本地搜索: {e}")
            return self._search_local(query, limit)

    def _search_local(self, query: str, limit: int = 3) -> List[DocChunk]:
        """本地字符串匹配搜索"""
        results = []
        query_lower = query.lower()
        query_tokens = set(query_lower.split())

        for chunk in self._chunks.values():
            score = 0.0
            search_text = chunk.to_search_text().lower()

            # 标题精确匹配（最高权重）
            if query_lower in chunk.title.lower():
                score += 10.0

            # 标题 Token 匹配
            title_lower = chunk.title.lower()
            title_matched = sum(1 for token in query_tokens if token in title_lower)
            score += title_matched * 3.0

            # 内容匹配
            if query_lower in search_text:
                score += 5.0

            # 内容 Token 匹配
            content_matched = sum(1 for token in query_tokens if token in search_text)
            score += content_matched * 1.0

            # 层级优先（二级标题 > 三级标题）
            if chunk.section_level == 2:
                score += 2.0
            elif chunk.section_level == 3:
                score += 1.0

            if score > 0:
                results.append((score, chunk))

        # 排序
        results.sort(key=lambda x: x[0], reverse=True)

        return [chunk for (score, chunk) in results[:limit]]

    def format_results(self, chunks: List[DocChunk]) -> str:
        """格式化搜索结果"""
        if not chunks:
            return "（未找到相关使用说明）"

        parts = []
        for i, chunk in enumerate(chunks, 1):
            parts.append(f"### {i}. [{chunk.source_file}] {chunk.title}\n\n{chunk.content}")

        return "\n\n---\n\n".join(parts)

    def get_all_chunks(self) -> List[DocChunk]:
        """获取所有文档片段"""
        return list(self._chunks.values())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        chunks = list(self._chunks.values())
        files = set(chunk.source_file for chunk in chunks)

        return {
            "total_chunks": len(chunks),
            "total_files": len(files),
            "files": list(files),
            "level_distribution": {
                level: sum(1 for c in chunks if c.section_level == level)
                for level in set(c.section_level for c in chunks)
            },
        }

    def reload(self):
        """重新加载文档"""
        logger.info("[UsageDocs] 重新加载文档...")
        self._chunks = {}
        self._load_all()
