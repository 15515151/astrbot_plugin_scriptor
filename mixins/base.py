from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Set

if TYPE_CHECKING:
    from astrbot.api import Context

    from ..core.active_reply_manager import ActiveReplyManager
    from ..core.archives.ingestor import DataIngestor
    from ..core.archives.manager import ArchiveManager
    from ..core.compactor import Compactor
    from ..core.config_pydantic import ScriptorConfigPydantic
    from ..core.conversation_ledger import ConversationLedger
    from ..core.file_manager import FileManager
    from ..core.file_monitor import FileMonitor
    from ..core.group_manager import GroupManager
    from ..core.identity_manager import IdentityManager
    from ..core.knowledge_base import KnowledgeBase
    from ..core.knowledge_graph import KnowledgeGraph
    from ..core.learning_manager import LearningManager
    from ..core.media_manager import MediaManager
    from ..core.memory_manager import MemoryManager
    from ..core.message_buffering import MessageBuffer
    from ..core.message_sanitizer import MessageSanitizer
    from ..core.prompt_builder import PromptBuilder
    from ..core.research_tool import ResearchTool
    from ..core.scheduler import TaskScheduler
    from ..core.search_engine import SearchEngine
    from ..core.session_locks import SessionLockManager
    from ..core.smart_sender import SmartSender
    from ..core.tool_decoration import ToolDecorator
    from ..core.usage_docs import UsageDocsKnowledgeBase


class BaseMixin:
    """
    所有 Mixin 的基类，提供类型提示和共享属性声明。

    这个类仅用于类型提示和 IDE 补全支持，不包含实际实现。
    所有属性将在 ScriptorPlugin.__init__ 中被注入。
    """

    context: Context
    config: ScriptorConfigPydantic
    data_dir: Path

    identity_manager: IdentityManager
    group_manager: GroupManager
    memory_manager: MemoryManager
    compactor: Compactor
    conversation_ledger: ConversationLedger
    knowledge_base: KnowledgeBase
    research_tool: ResearchTool
    usage_docs_kb: UsageDocsKnowledgeBase
    learning_manager: LearningManager
    message_sanitizer: MessageSanitizer
    message_buffer: MessageBuffer
    tool_decorator: ToolDecorator
    session_lock_manager: SessionLockManager
    smart_sender: SmartSender
    scheduler: TaskScheduler
    knowledge_graph: KnowledgeGraph
    archive_manager: ArchiveManager
    data_ingestor: DataIngestor
    file_manager: FileManager
    media_manager: MediaManager
    active_reply_manager: ActiveReplyManager

    search_engine: SearchEngine
    prompt_builder: PromptBuilder
    file_monitor: FileMonitor

    web_search_tool: Any

    _is_ready: bool
    _is_terminating: bool
    _background_tasks: Set[asyncio.Task]
    _group_states: Dict[str, str]
    _group_last_active: Dict[str, float]
    _last_interaction_time: Dict[str, float]
    _has_new_content: Dict[str, bool]

    _web_api_process: Any
    _web_frontend_process: Any

    async def _wait_for_ready(self) -> None:
        """等待所有组件就绪"""
        ...

    def _get_identity(self, event) -> tuple:
        """获取用户身份信息"""
        ...

    def _get_intent_provider(self):
        """获取意图判定小模型提供商"""
        ...

    def _get_current_provider(self):
        """获取当前使用的 LLM 提供商"""
        ...

    def _track_background_task(self, task: asyncio.Task) -> None:
        """追踪后台任务"""
        ...
