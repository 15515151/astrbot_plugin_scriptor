# core/enhanced_features.py
"""
增强功能整合模块
包含：
- 反思调度系统（会话内持续优化记忆）
- 链式回忆机制（类型分组 + 智能截断）
- 记忆冲突解决逻辑
- 轻量判断层

配置已迁移至 tools/config/enhanced_patterns.py
"""

import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

from tools.common.text_utils import jaccard_similarity
from tools.config.enhanced_patterns import (
    FINAL_LIMIT,
    GROUP_LIMITS,
    MEMORY_TRIGGER_WORDS,
    REFLECTION_CONFIG,
    SIMPLE_PATTERNS,
    TYPE_GROUPS,
)


class LightweightJudger:
    """轻量判断层 - 简单问答不走完整记忆检索"""

    SIMPLE_PATTERNS = SIMPLE_PATTERNS

    MEMORY_TRIGGER_WORDS = MEMORY_TRIGGER_WORDS

    @classmethod
    def should_use_memory(cls, message: str) -> bool:
        """判断是否需要使用记忆检索"""
        message_lower = message.lower().strip()

        for pattern in cls.SIMPLE_PATTERNS:
            if re.match(pattern, message_lower, re.IGNORECASE):
                logger.debug(f"[LightweightJudger] 简单问答，跳过记忆: {message[:30]}...")
                return False

        for word in cls.MEMORY_TRIGGER_WORDS:
            if word in message:
                logger.debug(f"[LightweightJudger] 检测到记忆触发词: {word}")
                return True

        if len(message) > 50:
            logger.debug(f"[LightweightJudger] 消息较长，使用记忆: {len(message)} 字符")
            return True

        return False


class ReflectionTrigger(Enum):
    """反思触发条件"""

    MESSAGE_COUNT = "message_count"
    TOPIC_CHANGE = "topic_change"
    USER_INTENT = "user_intent"
    TIME_ELAPSED = "time_elapsed"
    MEMORY_UPDATE = "memory_update"


@dataclass
class ReflectionContext:
    """反思上下文"""

    session_id: str
    message_count: int = 0
    last_topic: str = ""
    last_reflection_time: float = 0.0
    recent_messages: List[Dict] = field(default_factory=list)


class ReflectionScheduler:
    """反思调度系统 - 会话内持续优化记忆"""

    def __init__(self):
        self._contexts: Dict[str, ReflectionContext] = {}
        self._message_threshold = REFLECTION_CONFIG["message_threshold"]
        self._time_threshold = REFLECTION_CONFIG["time_threshold"]
        self._topic_change_threshold = REFLECTION_CONFIG["topic_change_threshold"]

    def _get_context(self, session_id: str) -> ReflectionContext:
        """获取或创建会话上下文"""
        if session_id not in self._contexts:
            self._contexts[session_id] = ReflectionContext(session_id=session_id)
        return self._contexts[session_id]

    def record_message(self, session_id: str, role: str, content: str) -> bool:
        """记录消息，返回是否应该触发反思"""
        ctx = self._get_context(session_id)
        ctx.message_count += 1
        ctx.recent_messages.append({"role": role, "content": content})

        if len(ctx.recent_messages) > 20:
            ctx.recent_messages = ctx.recent_messages[-20:]

        return self._should_trigger_reflection(ctx)

    def _should_trigger_reflection(self, ctx: ReflectionContext) -> bool:
        """判断是否应该触发反思"""
        now = time.time()

        if ctx.message_count >= self._message_threshold:
            logger.debug(f"[ReflectionScheduler] 触发反思: 消息数量达到 {ctx.message_count}")
            ctx.message_count = 0
            ctx.last_reflection_time = now
            return True

        if now - ctx.last_reflection_time > self._time_threshold and ctx.message_count > 5:
            logger.debug("[ReflectionScheduler] 触发反思: 时间流逝")
            ctx.message_count = 0
            ctx.last_reflection_time = now
            return True

        if len(ctx.recent_messages) >= 5:
            recent_text = " ".join([m["content"] for m in ctx.recent_messages[-3:]])
            if not ctx.last_topic:
                ctx.last_topic = recent_text[:100]
            else:
                similarity = self._simple_similarity(ctx.last_topic, recent_text[:100])
                if similarity < self._topic_change_threshold:
                    logger.debug("[ReflectionScheduler] 触发反思: 话题变化")
                    ctx.last_topic = recent_text[:100]
                    ctx.message_count = 0
                    ctx.last_reflection_time = now
                    return True

        return False

    def _simple_similarity(self, text1: str, text2: str) -> float:
        """简单的文本相似度（基于词汇重叠）"""
        return jaccard_similarity(text1, text2)

    def reset_session(self, session_id: str):
        """重置会话"""
        if session_id in self._contexts:
            del self._contexts[session_id]


class ChainedRecall:
    """链式回忆机制 - 类型分组 + 智能截断"""

    TYPE_GROUPS = TYPE_GROUPS

    GROUP_LIMITS = GROUP_LIMITS

    FINAL_LIMIT = FINAL_LIMIT

    @classmethod
    def group_and_truncate(cls, memories: List[Any]) -> List[Any]:
        """
        链式回忆：按类型分组并智能截断

        Args:
            memories: 记忆列表，需要有 memory_type 属性

        Returns:
            截断后的记忆列表
        """
        if not memories:
            return []

        groups = defaultdict(list)
        for mem in memories:
            mem_type = getattr(mem, "memory_type", "unknown")

            target_group = "fact"
            for group, keywords in cls.TYPE_GROUPS.items():
                if any(kw in mem_type.lower() for kw in keywords):
                    target_group = group
                    break

            groups[target_group].append(mem)

        result = []
        for group, group_mems in groups.items():
            limit = cls.GROUP_LIMITS.get(group, 3)
            result.extend(group_mems[:limit])

        if len(result) > cls.FINAL_LIMIT:
            result = result[: cls.FINAL_LIMIT]

        logger.debug(f"[ChainedRecall] 分组: {len(groups)} 组, 结果: {len(result)} 条")
        return result


class ConflictType(Enum):
    """冲突类型"""

    TIME_CONFLICT = "time_conflict"
    FACT_CONFLICT = "fact_conflict"
    PREFERENCE_CONFLICT = "preference_conflict"


@dataclass
class MemoryConflict:
    """记忆冲突"""

    conflict_type: ConflictType
    memory1: Any
    memory2: Any
    description: str = ""


class ConflictResolver:
    """记忆冲突解决器"""

    def __init__(self):
        pass

    def detect_conflicts(self, memories: List[Any]) -> List[MemoryConflict]:
        """检测记忆冲突"""
        conflicts = []

        for i, mem1 in enumerate(memories):
            for j, mem2 in enumerate(memories[i + 1 :], i + 1):
                conflict = self._check_pair(mem1, mem2)
                if conflict:
                    conflicts.append(conflict)

        return conflicts

    def _check_pair(self, mem1: Any, mem2: Any) -> Optional[MemoryConflict]:
        """检查一对记忆是否有冲突"""
        content1 = getattr(mem1, "content", "") or getattr(mem1, "raw_content", "") or getattr(mem1, "judgment", "")
        content2 = getattr(mem2, "content", "") or getattr(mem2, "raw_content", "") or getattr(mem2, "judgment", "")

        if not content1 or not content2:
            return None

        contradiction_pairs = [
            ("喜欢", "讨厌"),
            ("喜欢", "不喜欢"),
            ("是", "不是"),
            ("对", "不对"),
            ("正确", "错误"),
            ("要", "不要"),
            ("会", "不会"),
        ]

        for pos, neg in contradiction_pairs:
            if (pos in content1 and neg in content2) or (pos in content2 and neg in content1):
                return MemoryConflict(
                    conflict_type=ConflictType.FACT_CONFLICT,
                    memory1=mem1,
                    memory2=mem2,
                    description=f"检测到潜在矛盾: '{pos}' vs '{neg}'",
                )

        return None

    def resolve_conflict(self, conflict: MemoryConflict) -> Tuple[Any, str]:
        """
        解决冲突

        Returns:
            (保留的记忆, 解决建议)
        """
        advice = "建议：根据时间先后和上下文判断哪个更准确"

        return conflict.memory1, advice


class EnhancedMemorySystem:
    """增强记忆系统整合"""

    def __init__(self):
        self.lightweight_judger = LightweightJudger()
        self.reflection_scheduler = ReflectionScheduler()
        self.chained_recall = ChainedRecall()
        self.conflict_resolver = ConflictResolver()

    def should_retrieve_memory(self, message: str) -> bool:
        """轻量判断：是否需要检索记忆"""
        return self.lightweight_judger.should_use_memory(message)

    def record_for_reflection(self, session_id: str, role: str, content: str) -> bool:
        """记录消息用于反思，返回是否应该触发反思"""
        return self.reflection_scheduler.record_message(session_id, role, content)

    def chain_recall(self, memories: List[Any]) -> List[Any]:
        """链式回忆：分组和截断"""
        return self.chained_recall.group_and_truncate(memories)

    def detect_and_resolve_conflicts(self, memories: List[Any]) -> Tuple[List[Any], List[str]]:
        """检测并解决冲突"""
        conflicts = self.conflict_resolver.detect_conflicts(memories)

        resolved_memories = []
        advice_list = []

        used_ids = set()

        for mem in memories:
            mem_id = id(mem)
            if mem_id not in used_ids:
                resolved_memories.append(mem)
                used_ids.add(mem_id)

        for conflict in conflicts:
            advice_list.append(conflict.description)

        return resolved_memories, advice_list
