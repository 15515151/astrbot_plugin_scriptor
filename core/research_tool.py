# core/research_tool.py
"""
主动学习研究工具 - 借鉴 Angel Memory 的 research_topic 设计理念
核心功能：
1. 主动研究话题，而非被动问答
2. 将研究结果转化为短条目的知识库
3. 支持多轮研究和深度探索
4. 自动知识提炼和精简
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

try:
    from astrbot.api import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

from .knowledge_base import KnowledgeBase, KnowledgeItem, KnowledgeType


class ResearchDepth(Enum):
    """研究深度级别"""

    QUICK = "quick"  # 快速了解（1-2轮）
    NORMAL = "normal"  # 正常研究（3-5轮）
    DEEP = "deep"  # 深度研究（6-10轮）
    COMPREHENSIVE = "comprehensive"  # 全面研究（10+轮）


class ResearchStatus(Enum):
    """研究状态"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ResearchNote:
    """研究笔记"""

    id: str = ""
    content: str = ""
    round_num: int = 0
    timestamp: str = ""
    is_key: bool = False  # 是否是关键点

    @classmethod
    def create(cls, content: str, round_num: int, is_key: bool = False) -> "ResearchNote":
        """创建研究笔记"""
        return cls(
            id=cls._generate_id(content),
            content=content,
            round_num=round_num,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            is_key=is_key,
        )

    @staticmethod
    def _generate_id(content: str) -> str:
        """生成笔记ID"""
        import hashlib

        return hashlib.md5(content[:100].encode()).hexdigest()[:10]


@dataclass
class ResearchTask:
    """研究任务"""

    id: str = ""
    topic: str = ""
    depth: ResearchDepth = ResearchDepth.NORMAL
    status: ResearchStatus = ResearchStatus.PENDING
    current_round: int = 0
    max_rounds: int = 5
    notes: List[ResearchNote] = field(default_factory=list)
    created_at: str = ""
    completed_at: str = ""
    extracted_knowledge: List[str] = field(default_factory=list)

    @classmethod
    def create(cls, topic: str, depth: ResearchDepth = ResearchDepth.NORMAL) -> "ResearchTask":
        """创建研究任务"""
        depth_rounds = {
            ResearchDepth.QUICK: 2,
            ResearchDepth.NORMAL: 5,
            ResearchDepth.DEEP: 8,
            ResearchDepth.COMPREHENSIVE: 12,
        }

        return cls(
            id=cls._generate_id(topic),
            topic=topic,
            depth=depth,
            max_rounds=depth_rounds.get(depth, 5),
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    @staticmethod
    def _generate_id(topic: str) -> str:
        """生成任务ID"""
        import hashlib

        return hashlib.md5(topic.encode()).hexdigest()[:12]


class ResearchTool:
    """主动学习研究工具"""

    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base
        self._tasks: Dict[str, ResearchTask] = {}
        self._llm_callback: Optional[Callable] = None

    def set_llm_callback(self, callback: Callable):
        """设置LLM回调函数，用于实际的研究对话"""
        self._llm_callback = callback

    def create_research_task(self, topic: str, depth: ResearchDepth = ResearchDepth.NORMAL) -> ResearchTask:
        """创建研究任务"""
        task = ResearchTask.create(topic, depth)
        self._tasks[task.id] = task
        logger.info(f"[ResearchTool] 创建研究任务: {topic} ({depth.value})")
        return task

    def get_task(self, task_id: str) -> Optional[ResearchTask]:
        """获取研究任务"""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[ResearchTask]:
        """获取所有研究任务"""
        return list(self._tasks.values())

    def start_research(self, task_id: str) -> bool:
        """开始研究"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.status = ResearchStatus.IN_PROGRESS
        logger.info(f"[ResearchTool] 开始研究: {task.topic}")
        return True

    def add_research_note(self, task_id: str, content: str, is_key: bool = False) -> Optional[ResearchNote]:
        """添加研究笔记"""
        task = self._tasks.get(task_id)
        if not task:
            return None

        task.current_round += 1
        note = ResearchNote.create(content, task.current_round, is_key)
        task.notes.append(note)

        logger.debug(f"[ResearchTool] 添加笔记 (第{task.current_round}轮): {content[:30]}...")

        if task.current_round >= task.max_rounds:
            self.complete_research(task_id)

        return note

    def complete_research(self, task_id: str) -> bool:
        """完成研究"""
        task = self._tasks.get(task_id)
        if not task:
            return False

        task.status = ResearchStatus.COMPLETED
        task.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"[ResearchTool] 完成研究: {task.topic}")

        self.extract_knowledge(task_id)

        return True

    def extract_knowledge(self, task_id: str) -> List[KnowledgeItem]:
        """从研究中提取知识（自动提炼为短条目）"""
        task = self._tasks.get(task_id)
        if not task:
            return []

        knowledge_items = []

        key_notes = [note for note in task.notes if note.is_key]
        all_notes = task.notes

        for i, note in enumerate(key_notes + all_notes[:5]):
            content = self._condense_to_short(note.content)
            if content:
                item = KnowledgeItem.create(
                    title=f"{task.topic} - {i+1}",
                    content=content,
                    knowledge_type=KnowledgeType.FACT,
                    tags=["research", task.topic.lower()],
                    category="研究成果",
                    is_active=True,
                    source=f"研究任务: {task.id}",
                )

                self.knowledge_base.add_item(item)
                knowledge_items.append(item)
                task.extracted_knowledge.append(item.id)

        logger.info(f"[ResearchTool] 提取知识: {len(knowledge_items)} 条")
        return knowledge_items

    def _condense_to_short(self, content: str) -> Optional[str]:
        """将内容精简为100字以内的短条目"""
        content = content.strip()

        if len(content) <= 100:
            return content

        sentences = re.split(r"[。！？.!?]", content)
        sentences = [s.strip() for s in sentences if s.strip()]

        result = ""
        for sentence in sentences:
            if len(result + sentence) <= 97:
                result += sentence + "。"
            else:
                break

        if result:
            return result[:100]

        return content[:97] + "..."

    def generate_next_question(self, task_id: str) -> Optional[str]:
        """生成下一个研究问题（用于引导研究方向）"""
        task = self._tasks.get(task_id)
        if not task or task.status != ResearchStatus.IN_PROGRESS:
            return None

        if not task.notes:
            return f"关于'{task.topic}'，你想了解哪些方面？"

        last_note = task.notes[-1]

        questions = [
            f"基于刚才的内容，关于'{task.topic}'还有什么需要深入了解的？",
            f"在'{task.topic}'这个话题上，还有哪些关键点没有覆盖到？",
            f"关于'{task.topic}'，你对哪个方面最感兴趣？",
            f"继续研究'{task.topic}'，下一步应该探索什么？",
        ]

        import random

        return random.choice(questions)

    def delete_task(self, task_id: str) -> bool:
        """删除研究任务"""
        if task_id in self._tasks:
            del self._tasks[task_id]
            logger.info(f"[ResearchTool] 删除研究任务: {task_id}")
            return True
        return False

    def get_research_summary(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取研究摘要"""
        task = self._tasks.get(task_id)
        if not task:
            return None

        return {
            "topic": task.topic,
            "status": task.status.value,
            "rounds": task.current_round,
            "max_rounds": task.max_rounds,
            "depth": task.depth.value,
            "notes_count": len(task.notes),
            "key_notes_count": sum(1 for n in task.notes if n.is_key),
            "knowledge_count": len(task.extracted_knowledge),
            "created_at": task.created_at,
            "completed_at": task.completed_at,
        }
