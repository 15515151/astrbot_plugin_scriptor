# core/__init__.py
"""
Scriptor 核心模块
增强版 - 包含以下功能：
1. 记忆三元组结构 (judgment + reasoning + tags)
2. 主动记忆标记 (is_active 永不衰减)
3. 反馈队列（异步处理，不阻塞对话）
4. 反思调度系统（会话内持续优化记忆）
5. 链式回忆机制（类型分组 + 智能截断）
6. 记忆冲突解决逻辑
7. 轻量判断层
8. 知识库系统（短条目设计 + 主动学习）
9. 研究工具（research_topic 主动探索）
10. 消息清洗器（Markdown清洗 + 错误拦截）
"""

import os
import sys
from pathlib import Path

_core_dir = Path(__file__).parent
_plugin_root = _core_dir.parent
_tools_dir = _plugin_root / "tools"

if str(_tools_dir) not in sys.path:
    sys.path.insert(0, str(_tools_dir))
if str(_plugin_root) not in sys.path:
    sys.path.insert(0, str(_plugin_root))

from .active_reply_manager import (
    ActiveReplyManager,
    GroupState,
    GroupStatus,
    QueuedMessage,
    ReplyDecision,
)
from .config_pydantic import ScriptorConfig, ScriptorConfigPydantic
from .enhanced_features import (
    ChainedRecall,
    ConflictResolver,
    EnhancedMemorySystem,
    LightweightJudger,
    ReflectionScheduler,
)
from .feedback_queue import FeedbackQueue, FeedbackTask, FeedbackType, get_feedback_queue, init_feedback_queue
from .knowledge_base import KnowledgeBase, KnowledgeItem, KnowledgeType
from .memory_struct import StructuredMemory
from .message_buffering import BufferConfig, BufferedMessage, MessageBuffer, get_message_buffer, set_message_buffer
from .message_sanitizer import MessageSanitizer, Platform, SanitizerConfig, get_sanitizer, set_sanitizer
from .research_tool import ResearchDepth, ResearchNote, ResearchStatus, ResearchTask, ResearchTool
from .session_locks import (
    LockManagerConfig,
    SessionContext,
    SessionLockManager,
    SessionState,
    get_session_lock_manager,
    set_session_lock_manager,
)
from .tool_decoration import (
    DecorationConfig,
    ToolCategory,
    ToolDecoration,
    ToolDecorator,
    get_tool_decorator,
    set_tool_decorator,
)

try:
    from ..tools.common.async_io import (
        async_append_text,
        async_read_json,
        async_read_text,
        async_write_json,
        async_write_text,
    )
    from ..tools.common.json_parser import (
        extract_json_from_llm_output,
        safe_json_loads,
    )
    from ..tools.security.sanitizer import (
        SAFE_FILENAME_PATTERN,
        sanitize_filename,
        sanitize_id,
        sanitize_log_message,
    )
    from ..tools.storage.debounced_writer import DebouncedWriter
except ImportError:
    from tools.common.async_io import (
        async_append_text,
        async_read_json,
        async_read_text,
        async_write_json,
        async_write_text,
    )
    from tools.common.json_parser import (
        extract_json_from_llm_output,
        safe_json_loads,
    )
    from tools.security.sanitizer import (
        SAFE_FILENAME_PATTERN,
        sanitize_filename,
        sanitize_id,
        sanitize_log_message,
    )
    from tools.storage.debounced_writer import DebouncedWriter

__all__ = [
    "ScriptorConfig",
    "ScriptorConfigPydantic",
    "StructuredMemory",
    "FeedbackQueue",
    "FeedbackTask",
    "FeedbackType",
    "get_feedback_queue",
    "init_feedback_queue",
    "LightweightJudger",
    "ReflectionScheduler",
    "ChainedRecall",
    "ConflictResolver",
    "EnhancedMemorySystem",
    "KnowledgeItem",
    "KnowledgeType",
    "KnowledgeBase",
    "ResearchNote",
    "ResearchTask",
    "ResearchDepth",
    "ResearchStatus",
    "ResearchTool",
    "MessageSanitizer",
    "SanitizerConfig",
    "Platform",
    "get_sanitizer",
    "set_sanitizer",
    "MessageBuffer",
    "BufferConfig",
    "BufferedMessage",
    "get_message_buffer",
    "set_message_buffer",
    "ToolDecorator",
    "DecorationConfig",
    "ToolDecoration",
    "ToolCategory",
    "get_tool_decorator",
    "set_tool_decorator",
    "SessionLockManager",
    "LockManagerConfig",
    "SessionContext",
    "SessionState",
    "get_session_lock_manager",
    "set_session_lock_manager",
    # tools backward compatibility
    "sanitize_id",
    "sanitize_filename",
    "sanitize_log_message",
    "SAFE_FILENAME_PATTERN",
    "safe_json_loads",
    "extract_json_from_llm_output",
    "async_read_json",
    "async_write_json",
    "async_read_text",
    "async_write_text",
    "async_append_text",
    "DebouncedWriter",
]
