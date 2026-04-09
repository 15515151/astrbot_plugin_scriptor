# hooks/__init__.py
"""
Scriptor 钩子模块
提供业务逻辑扩展点，支持自定义行为注入
"""

from .lifecycle import (
    LifecycleHook,
    ShutdownHook,
    StartupHook,
)
from .llm import (
    LLMHook,
    RequestHook,
    ResponseHook,
)
from .manager import (
    DefaultShutdownHook,
    DefaultStartupHook,
    HookManager,
    HookRegistration,
    get_hook_manager,
)
from .message import (
    MessageHook,
    RecordingHook,
)
from .search import (
    IndexHook,
    RerankHook,
    SearchHook,
    SearchQuery,
    SearchResult,
)
from .storage import (
    BackupHook,
    StorageHook,
)

__all__ = [
    # lifecycle
    "LifecycleHook",
    "StartupHook",
    "ShutdownHook",
    # message
    "MessageHook",
    "RecordingHook",
    # llm
    "LLMHook",
    "RequestHook",
    "ResponseHook",
    # storage
    "StorageHook",
    "BackupHook",
    # search
    "SearchHook",
    "RerankHook",
    "IndexHook",
    "SearchQuery",
    "SearchResult",
    # manager
    "HookManager",
    "HookRegistration",
    "get_hook_manager",
    "DefaultStartupHook",
    "DefaultShutdownHook",
]
