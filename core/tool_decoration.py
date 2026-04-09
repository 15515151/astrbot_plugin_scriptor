# core/tool_decoration.py
"""
工具调用拟人化反馈模块
功能：
1. 配置化的话术系统
2. 模糊匹配工具名
3. 随机话术库
4. 冷却机制（避免频繁发废话）
"""

import random
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """工具类别"""

    SEARCH = "search"
    MEMORY = "memory"
    RESEARCH = "research"
    KNOWLEDGE = "knowledge"
    TASK = "task"
    REMINDER = "reminder"
    PROFILE = "profile"
    DECISION = "decision"
    GENERAL = "general"


@dataclass
class ToolDecoration:
    """单个工具的装饰配置"""

    patterns: List[str] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)
    cooldown_seconds: float = 5.0
    category: ToolCategory = ToolCategory.GENERAL


@dataclass
class DecorationConfig:
    """装饰器配置"""

    enabled: bool = True

    default_cooldown: float = 3.0

    tool_configs: Dict[str, ToolDecoration] = field(default_factory=dict)

    def __post_init__(self):
        if not self.tool_configs:
            self._init_default_configs()

    def _init_default_configs(self):
        """初始化默认配置"""
        self.tool_configs = {
            "memory_search": ToolDecoration(
                patterns=["memory_search", "search", "查找", "搜索", "回忆", "检索"],
                messages=[
                    "稍等，我查一下记忆...",
                    "让我回忆一下...",
                    "我找找相关的记忆...",
                    "等我翻一下记忆本...",
                    "我在记忆里搜一下...",
                ],
                cooldown_seconds=5.0,
                category=ToolCategory.SEARCH,
            ),
            "knowledge_search": ToolDecoration(
                patterns=["knowledge_search", "知识库", "知识"],
                messages=[
                    "我查查知识库...",
                    "让我看看知识库...",
                    "翻一下知识库...",
                ],
                cooldown_seconds=4.0,
                category=ToolCategory.KNOWLEDGE,
            ),
            "research_topic": ToolDecoration(
                patterns=["research_topic", "研究", "research"],
                messages=[
                    "好的，我来研究一下这个话题...",
                    "让我主动研究一下...",
                    "开始研究这个话题...",
                ],
                cooldown_seconds=3.0,
                category=ToolCategory.RESEARCH,
            ),
            "core_memory_remember": ToolDecoration(
                patterns=["core_memory_remember", "铭记", "记住", "remember"],
                messages=[
                    "好的，我记下来了...",
                    "收到，我记在心里了...",
                    "记住了！",
                ],
                cooldown_seconds=2.0,
                category=ToolCategory.MEMORY,
            ),
            "update_profile": ToolDecoration(
                patterns=["update_profile", "profile", "画像"],
                messages=[
                    "好的，我更新一下你的画像...",
                    "我记一下你的新信息...",
                ],
                cooldown_seconds=2.0,
                category=ToolCategory.PROFILE,
            ),
            "create_reminder": ToolDecoration(
                patterns=["create_reminder", "reminder", "提醒"],
                messages=[
                    "好的，我设个提醒...",
                    "收到，我记下来了，到时候提醒你...",
                ],
                cooldown_seconds=2.0,
                category=ToolCategory.REMINDER,
            ),
            "record_decision": ToolDecoration(
                patterns=["record_decision", "decision", "决策"],
                messages=[
                    "好的，我记录一下这个决策...",
                    "这个决策我记下来了...",
                ],
                cooldown_seconds=2.0,
                category=ToolCategory.DECISION,
            ),
            "note_recall": ToolDecoration(
                patterns=["note_recall", "note", "日记", "笔记"],
                messages=[
                    "让我看看日记...",
                    "我翻一下笔记...",
                ],
                cooldown_seconds=3.0,
                category=ToolCategory.MEMORY,
            ),
            "core_memory_recall": ToolDecoration(
                patterns=["core_memory_recall", "recall", "随机回忆"],
                messages=[
                    "让我随机回忆一些事...",
                    "我想想有什么重要的...",
                ],
                cooldown_seconds=3.0,
                category=ToolCategory.MEMORY,
            ),
            "web_search_tool": ToolDecoration(
                patterns=["web_search", "搜索", "查一下", "google", "百度", "上网找"],
                messages=[
                    "好的，我上网查一下...",
                    "让我搜索相关信息...",
                    "稍等，我找找网上的资料...",
                    "我来搜索一下最新信息...",
                ],
                cooldown_seconds=5.0,
                category=ToolCategory.SEARCH,
            ),
        }


class ToolDecorator:
    """工具装饰器"""

    def __init__(self, config: Optional[DecorationConfig] = None):
        self.config = config or DecorationConfig()
        self._last_send_time: Dict[str, float] = {}
        self._session_last_time: Dict[str, float] = {}

    def should_send(self, tool_name: str, session_id: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        判断是否应该发送装饰消息

        Args:
            tool_name: 工具名
            session_id: 会话ID（可选）

        Returns:
            (should_send, message)
            - should_send: 是否应该发送
            - message: 选中的消息（如果应该发送）
        """
        if not self.config.enabled:
            return False, None

        decoration = self._find_decoration(tool_name)
        if not decoration:
            return False, None

        now = time.time()

        if session_id:
            last_time = self._session_last_time.get(session_id, 0)
            cooldown_key = session_id
        else:
            last_time = self._last_send_time.get(tool_name, 0)
            cooldown_key = tool_name

        if now - last_time < decoration.cooldown_seconds:
            logger.debug(f"[ToolDecorator] 在冷却期内，跳过: {tool_name}")
            return False, None

        message = random.choice(decoration.messages)

        if session_id:
            self._session_last_time[session_id] = now
        else:
            self._last_send_time[tool_name] = now

        return True, message

    def _find_decoration(self, tool_name: str) -> Optional[ToolDecoration]:
        """
        查找工具装饰配置（支持模糊匹配）

        Args:
            tool_name: 工具名

        Returns:
            找到的装饰配置，找不到返回None
        """
        if tool_name in self.config.tool_configs:
            return self.config.tool_configs[tool_name]

        tool_name_lower = tool_name.lower()

        for name, decoration in self.config.tool_configs.items():
            for pattern in decoration.patterns:
                pattern_lower = pattern.lower()

                if pattern_lower in tool_name_lower:
                    return decoration

                if tool_name_lower in pattern_lower:
                    return decoration

                if re.search(pattern_lower, tool_name_lower):
                    return decoration

        return None

    def register_tool(
        self,
        tool_name: str,
        patterns: List[str],
        messages: List[str],
        cooldown_seconds: Optional[float] = None,
        category: ToolCategory = ToolCategory.GENERAL,
    ):
        """
        注册新的工具装饰配置

        Args:
            tool_name: 工具名
            patterns: 匹配模式列表
            messages: 消息列表
            cooldown_seconds: 冷却时间（可选）
            category: 工具类别
        """
        self.config.tool_configs[tool_name] = ToolDecoration(
            patterns=patterns,
            messages=messages,
            cooldown_seconds=cooldown_seconds or self.config.default_cooldown,
            category=category,
        )
        logger.info(f"[ToolDecorator] 注册工具装饰: {tool_name}")

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "enabled": self.config.enabled,
            "registered_tools": len(self.config.tool_configs),
            "tool_categories": {
                cat.value: sum(1 for d in self.config.tool_configs.values() if d.category == cat)
                for cat in ToolCategory
            },
        }


_decorator_instance: Optional[ToolDecorator] = None


def get_tool_decorator() -> ToolDecorator:
    """获取全局工具装饰器实例"""
    global _decorator_instance
    if _decorator_instance is None:
        _decorator_instance = ToolDecorator()
    return _decorator_instance


def set_tool_decorator(decorator: ToolDecorator):
    """设置全局工具装饰器实例"""
    global _decorator_instance
    _decorator_instance = decorator
