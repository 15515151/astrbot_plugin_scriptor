# tools/tool_search.py
"""
ToolSearch 工具自省系统

功能：
1. 自动索引所有 @filter.llm_tool() 方法
2. 关键词智能评分与匹配
3. 工具分类与推荐
4. 帮助 LLM 发现和选择正确的工具
"""

import inspect
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """工具分类"""

    FILE = "file"
    MEMORY = "memory"
    WEB = "web"
    KNOWLEDGE = "knowledge"
    ADMIN = "admin"
    MEDIA = "media"
    SCHEDULE = "schedule"
    IDENTITY = "identity"
    OTHER = "other"


@dataclass
class ToolParameter:
    """工具参数定义"""

    name: str
    type: str = "str"
    default: Any = None
    required: bool = False
    description: str = ""


@dataclass
class ToolIndexEntry:
    """工具索引条目"""

    name: str
    display_name: str
    description: str
    parameters: List[ToolParameter]
    tags: Set[str]
    category: ToolCategory
    complexity: str = "medium"
    examples: List[str] = field(default_factory=list)
    related_tools: List[str] = field(default_factory=list)
    raw_docstring: str = ""


@dataclass
class ToolSearchResult:
    """搜索结果"""

    tool_name: str
    score: float
    entry: ToolIndexEntry
    match_reason: str = ""


CATEGORY_KEYWORDS = {
    ToolCategory.FILE: {
        "文件",
        "读取",
        "写入",
        "编辑",
        "创建",
        "删除",
        "列表",
        "搜索",
        "file",
        "read",
        "write",
        "edit",
        "append",
    },
    ToolCategory.MEMORY: {"记忆", "检索", "搜索", "memory", "search", "recall", "remember"},
    ToolCategory.WEB: {"网页", "搜索", "url", "链接", "web", "fetch", "http", "internet"},
    ToolCategory.KNOWLEDGE: {"知识", "学习", "研究", "knowledge", "learn", "research", "study"},
    ToolCategory.ADMIN: {"管理", "权限", "管理员", "admin", "permission", "sudo"},
    ToolCategory.MEDIA: {"图片", "媒体", "上传", "下载", "media", "image", "upload", "download"},
    ToolCategory.SCHEDULE: {"提醒", "定时", "日程", "reminder", "schedule", "todo", "task"},
    ToolCategory.IDENTITY: {"身份", "用户", "绑定", "identity", "user", "bind"},
}

CATEGORY_BOOST = {
    ToolCategory.FILE: 1.2,
    ToolCategory.MEMORY: 1.1,
    ToolCategory.WEB: 0.9,
    ToolCategory.KNOWLEDGE: 0.9,
    ToolCategory.ADMIN: 0.7,
    ToolCategory.MEDIA: 0.8,
    ToolCategory.SCHEDULE: 0.8,
    ToolCategory.IDENTITY: 0.7,
    ToolCategory.OTHER: 0.7,
}


class ToolSearchEngine:
    """
    工具搜索引擎

    自动从 Mixin 类提取所有 @filter.llm_tool() 方法，
    构建索引并支持关键词搜索。
    """

    def __init__(self):
        self._index: Dict[str, ToolIndexEntry] = {}
        self._keyword_inverted_index: Dict[str, Set[str]] = {}
        self._built = False

    def build_index(self, plugin_instance) -> int:
        """
        从插件实例自动构建工具索引

        Args:
            plugin_instance: ScriptorPlugin 实例

        Returns:
            索引的工具数量
        """
        mixin_classes = [
            type(plugin_instance).__mro__[i]
            for i in range(len(type(plugin_instance).__mro__))
            if hasattr(type(plugin_instance).__mro__[i], "__name__")
            and "Mixin" in type(plugin_instance).__mro__[i].__name__
        ]

        count = 0
        for cls in mixin_classes:
            for attr_name in dir(cls):
                if attr_name.startswith("_"):
                    continue

                method = getattr(cls, attr_name)

                if not callable(method):
                    continue

                if not hasattr(method, "_is_llm_tool") or not method._is_llm_tool:
                    continue

                try:
                    entry = self._extract_tool_metadata(method)
                    if entry and entry.name not in self._index:
                        self._index[entry.name] = entry
                        self._update_inverted_index(entry)
                        count += 1
                        logger.debug(f"[ToolSearch] 索引工具: {entry.name}")
                except Exception as e:
                    logger.warning(f"[ToolSearch] 索引工具失败 {attr_name}: {e}")

        self._built = True
        logger.info(f"[ToolSearch] 索引构建完成，共 {count} 个工具")
        return count

    def _extract_tool_metadata(self, method) -> Optional[ToolIndexEntry]:
        """从方法提取元数据"""
        docstring = inspect.getdoc(method) or ""

        if not docstring:
            return None

        signature = None
        try:
            signature = inspect.signature(method)
        except Exception as e:
            logger.debug(f"[ToolSearch] 无法获取签名 {method.__name__}: {e}")

        parameters = []
        if signature:
            for param_name, param in signature.parameters.items():
                if param_name in ("event", "plugin", "self"):
                    continue

                param_type = "str"
                if param.annotation != inspect.Parameter.empty:
                    param_type = getattr(param.annotation, "__name__", str(param.annotation))

                parameters.append(
                    ToolParameter(
                        name=param_name,
                        type=param_type,
                        default=param.default if param.default != inspect.Parameter.empty else None,
                        required=(param.default == inspect.Parameter.empty),
                    )
                )

        tags = self._extract_tags(docstring, method.__name__)
        category = self._classify_tool(method.__name__, tags, docstring)
        display_name = self._generate_display_name(method.__name__)

        description = ""
        for line in docstring.split("\n\n")[0:1]:
            line = line.strip()
            if line and not line.startswith("Args:") and not line.startswith("Returns:"):
                description = line[:200]
                break

        examples = self._extract_examples(docstring)

        return ToolIndexEntry(
            name=method.__name__,
            display_name=display_name,
            description=description,
            parameters=parameters,
            tags=tags,
            category=category,
            complexity=self._estimate_complexity(parameters),
            examples=examples,
            raw_docstring=docstring,
        )

    def _extract_tags(self, docstring: str, method_name: str) -> Set[str]:
        """从 docstring 和方法名提取标签"""
        tags = set()

        words = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z_]+", method_name.lower())
        for word in words:
            if len(word) >= 2:
                tags.add(word)

        desc_text = docstring[:500].lower()
        chinese_words = re.findall(r"[\u4e00-\u9fff]{2,}", desc_text)
        for word in chinese_words[:10]:
            tags.add(word)

        english_words = re.findall(r"\b[a-z_]{3,}\b", desc_text)
        for word in english_words[:10]:
            tags.add(word)

        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "this",
            "that",
            "from",
            "when",
            "args",
            "returns",
            "description",
            "type",
            "default",
        }
        tags -= stop_words

        return tags

    def _classify_tool(self, method_name: str, tags: Set[str], docstring: str) -> ToolCategory:
        """根据名称、标签和描述分类"""
        text = f"{method_name} {' '.join(tags)} {docstring[:300]}".lower()

        scores = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            scores[category] = score

        best_category = max(scores, key=scores.get)
        if scores[best_category] == 0:
            return ToolCategory.OTHER

        return best_category

    def _generate_display_name(self, method_name: str) -> str:
        """生成友好的显示名称"""
        name = method_name.replace("_tool", "").replace("_", " ")

        name = re.sub(r"([a-z])([A-Z])", r"\1 \2", name)

        words = name.split()
        title_words = [w.capitalize() if w else w for w in words]

        return " ".join(title_words)

    def _estimate_complexity(self, parameters: List[ToolParameter]) -> str:
        """估算复杂度"""
        required_count = sum(1 for p in parameters if p.required)
        total_count = len(parameters)

        if required_count <= 1 and total_count <= 3:
            return "low"
        elif required_count <= 2 and total_count <= 5:
            return "medium"
        else:
            return "high"

    def _extract_examples(self, docstring: str) -> List[str]:
        """提取使用示例"""
        examples = []

        example_match = re.search(
            r"(?:示例|Example|Examples?)[：:]\s*\n(.*?)(?:\n\n|\Z)", docstring, re.DOTALL | re.IGNORECASE
        )
        if example_match:
            example_text = example_match.group(1).strip()
            for line in example_text.split("\n")[:3]:
                line = line.strip().lstrip("-* ")
                if line:
                    examples.append(line[:100])

        return examples

    def _update_inverted_index(self, entry: ToolIndexEntry):
        """更新倒排索引"""
        for tag in entry.tags:
            if tag not in self._keyword_inverted_index:
                self._keyword_inverted_index[tag] = set()
            self._keyword_inverted_index[tag].add(entry.name)

        for param in entry.parameters:
            if len(param.name) >= 3:
                if param.name not in self._keyword_inverted_index:
                    self._keyword_inverted_index[param.name] = set()
                self._keyword_inverted_index[param.name].add(entry.name)

    async def search(self, query: str, limit: int = 5) -> List[ToolSearchResult]:
        """
        智能搜索工具

        Args:
            query: 自然语言查询（如 "我想读取一个文件"）
            limit: 返回数量上限

        Returns:
            按相关性排序的工具列表
        """
        if not self._built:
            logger.warning("[ToolSearch] 索引未构建，返回空结果")
            return []

        query_lower = query.lower()
        query_tokens = self._tokenize(query)
        scores: Dict[str, float] = {}

        for tool_name, entry in self._index.items():
            score = 0.0
            reasons = []

            if query_lower in tool_name.lower():
                score += 3.0
                reasons.append("名称精确匹配")

            matched_tags = query_tokens & entry.tags
            if matched_tags:
                score += len(matched_tags) * 2.0
                reasons.append(f"标签匹配: {', '.join(matched_tags)}")

            desc_matches = sum(1 for t in query_tokens if t in entry.description.lower())
            if desc_matches > 0:
                score += desc_matches * 1.0
                reasons.append("描述关键词命中")

            param_matches = sum(1 for p in entry.parameters if any(t in p.name.lower() for t in query_tokens))
            if param_matches > 0:
                score += param_matches * 0.5
                reasons.append("参数名匹配")

            boost = CATEGORY_BOOST.get(entry.category, 1.0)
            score *= boost

            if score > 0:
                scores[tool_name] = (score, "; ".join(reasons))

        ranked = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)[:limit]

        results = []
        for tool_name, (score, reason) in ranked:
            results.append(
                ToolSearchResult(tool_name=tool_name, score=score, entry=self._index[tool_name], match_reason=reason)
            )

        return results

    def _tokenize(self, text: str) -> Set[str]:
        """简单分词（中文+英文）"""
        tokens = set()

        chinese_words = re.findall(r"[\u4e00-\u9fff]{2,}", text.lower())
        tokens.update(chinese_words)

        english_words = re.findall(r"\b[a-z]{2,}\b", text.lower())
        tokens.update(english_words)

        return tokens

    def get_all_tools(self) -> List[ToolIndexEntry]:
        """获取所有已索引的工具"""
        return list(self._index.values())

    def get_tool_by_name(self, name: str) -> Optional[ToolIndexEntry]:
        """按名称获取工具"""
        return self._index.get(name)

    def get_tools_by_category(self, category: ToolCategory) -> List[ToolIndexEntry]:
        """按分类获取工具"""
        return [entry for entry in self._index.values() if entry.category == category]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        categories = {}
        for entry in self._index.values():
            cat_name = entry.category.value
            categories[cat_name] = categories.get(cat_name, 0) + 1

        return {
            "total_tools": len(self._index),
            "built": self._built,
            "categories": categories,
            "total_keywords": len(self._keyword_inverted_index),
        }


_search_engine_instance: Optional[ToolSearchEngine] = None


def get_tool_search_engine() -> ToolSearchEngine:
    """获取全局搜索引擎实例"""
    global _search_engine_instance
    if _search_engine_instance is None:
        _search_engine_instance = ToolSearchEngine()
    return _search_engine_instance


def set_tool_search_engine(engine: ToolSearchEngine):
    """设置全局搜索引擎实例"""
    global _search_engine_instance
    _search_engine_instance = engine
