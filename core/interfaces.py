# core/interfaces.py
"""
Scriptor 接口定义模块

定义核心组件的抽象接口，打破循环依赖，提高模块可测试性
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .search_engine import SearchResult


class MemoryType(Enum):
    """记忆类型枚举"""

    FACT = "fact"
    PREFERENCE = "preference"
    DECISION = "decision"
    EXPERIENCE = "experience"
    TASK = "task"
    KNOWLEDGE = "knowledge"
    CONSOLIDATED = "consolidated"


class PrivacyLevel(Enum):
    """隐私级别枚举"""

    PRIVATE = "private"
    GROUP = "group"
    GLOBAL = "global"


class EventType(Enum):
    """事件类型枚举"""

    MEMORY_RECORDED = "memory_recorded"
    MEMORY_SEARCHED = "memory_searched"
    MEMORY_UPDATED = "memory_updated"
    MEMORY_DELETED = "memory_deleted"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    IDENTITY_LINKED = "identity_linked"
    GROUP_MEMBER_JOINED = "group_member_joined"
    GROUP_MEMBER_LEFT = "group_member_left"


@dataclass
class MemoryRecordParams:
    """记忆记录参数封装"""

    uid: str
    group_id: str
    content: str
    memory_type: str = "fact"
    privacy_level: str = "private"
    strength: float = 1.0
    useful_score: float = 5.0
    status: str = "active"
    is_sudo: bool = False


@dataclass
class Event:
    """事件对象"""

    event_type: EventType
    data: Dict[str, Any]
    timestamp: float
    source: str


class ISearchEngine(ABC):
    """搜索引擎接口"""

    @abstractmethod
    async def search(
        self, query: str, uid: str, group_id: str, scope: str = "group", limit: int = 5
    ) -> List["SearchResult"]:
        """搜索记忆"""
        pass

    @abstractmethod
    async def add_to_vector_db(self, doc_id: str, content: str, metadata: dict):
        """添加记忆到向量数据库"""
        pass

    @abstractmethod
    async def index_documents(self, documents: List["SearchResult"]):
        """索引文档"""
        pass


class IIdentityManager(ABC):
    """身份管理器接口"""

    @abstractmethod
    def get_user_groups(self, uid: str) -> List[str]:
        """获取用户所属的群体列表"""
        pass

    @abstractmethod
    def get_primary_identity(self, uid: str) -> Optional[Dict[str, Any]]:
        """获取用户的主身份"""
        pass

    @abstractmethod
    def sanitize_id(self, input_str: str) -> str:
        """清理 ID，防止路径注入"""
        pass


class IGroupManager(ABC):
    """群体管理器接口"""

    @abstractmethod
    def get_group_context(self, group_id: str, uid: str) -> Dict[str, Any]:
        """获取群体上下文"""
        pass

    @abstractmethod
    def get_group(self, group_id: str):
        """获取群体信息"""
        pass


class IMemoryManager(ABC):
    """记忆管理器接口"""

    @abstractmethod
    async def record_interaction(self, uid: str, group_id: str, role: str, content: str) -> bool:
        """记录交互到日记"""
        pass

    @abstractmethod
    async def record_long_term_memory(self, params: MemoryRecordParams, search_engine: Any = None):
        """记录长期记忆

        Args:
            params: 记忆记录参数（使用 MemoryRecordParams 数据类封装）
            search_engine: 搜索引擎实例（可选）
        """
        pass

    @abstractmethod
    def get_hot_memory(self, uid: str, group_id: str) -> str:
        """获取热记忆"""
        pass


class EventBus:
    """
    事件总线 - 解耦模块间通信

    使用观察者模式，实现松耦合的组件通信
    """

    _instance = None
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._handlers: Dict[EventType, List] = {}
        self._global_handlers: List = []
        self._initialized = True

    def subscribe(self, event_type: EventType, handler):
        """订阅事件"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler):
        """订阅所有事件"""
        self._global_handlers.append(handler)

    def unsubscribe(self, event_type: EventType, handler):
        """取消订阅"""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)

    def unsubscribe_all(self, handler):
        """取消订阅所有事件"""
        if handler in self._global_handlers:
            self._global_handlers.remove(handler)

    async def emit(self, event: Event):
        """发布事件"""
        handlers = self._handlers.get(event.event_type, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except (TypeError, ValueError, RuntimeError) as e:
                logger.error(f"[EventBus] 事件处理器执行失败: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"[EventBus] 事件处理器未知错误: {e}", exc_info=True)

        for handler in self._global_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except (TypeError, ValueError, RuntimeError) as e:
                logger.error(f"[EventBus] 全局事件处理器执行失败: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"[EventBus] 全局事件处理器未知错误: {e}", exc_info=True)


import asyncio
import time as time_module

_event_bus_instance: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取事件总线单例"""
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBus()
    return _event_bus_instance


async def emit_event(event_type: EventType, data: Dict[str, Any], source: str = "unknown"):
    """便捷的事件发布函数"""
    event = Event(event_type=event_type, data=data, timestamp=time_module.time(), source=source)
    await get_event_bus().emit(event)
