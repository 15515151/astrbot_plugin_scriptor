"""
Scriptor Hook 系统测试

测试事件总线和 Hook 管理功能
"""

from unittest.mock import patch

import pytest

# 使用包导入方式，兼容相对导入
# 使用直接导入方式（通过 conftest.py 设置的 sys.path）
try:
    from core.interfaces import (
        Event,
        EventBus,
        EventType,
        MemoryRecordParams,
        MemoryType,
        PrivacyLevel,
        emit_event,
        get_event_bus,
    )
except ImportError:
    from interfaces import (
        Event,
        EventBus,
        EventType,
        MemoryRecordParams,
        MemoryType,
        PrivacyLevel,
        emit_event,
        get_event_bus,
    )


class TestEventBus:
    """事件总线测试"""

    @pytest.fixture
    def event_bus(self):
        """创建新的事件总线实例"""
        bus = EventBus()
        bus._handlers.clear()
        bus._global_handlers.clear()
        return bus

    @pytest.mark.asyncio
    async def test_subscribe_and_emit(self, event_bus):
        """测试订阅和发布事件"""
        received_events = []

        async def handler(event):
            received_events.append(event)

        event_bus.subscribe(EventType.MEMORY_RECORDED, handler)
        await event_bus.emit(
            Event(
                event_type=EventType.MEMORY_RECORDED, data={"uid": "test_user"}, timestamp=1234567890.0, source="test"
            )
        )

        assert len(received_events) == 1
        assert received_events[0].data["uid"] == "test_user"

    @pytest.mark.asyncio
    async def test_unsubscribe(self, event_bus):
        """测试取消订阅"""
        received_events = []

        async def handler(event):
            received_events.append(event)

        event_bus.subscribe(EventType.MEMORY_RECORDED, handler)
        event_bus.unsubscribe(EventType.MEMORY_RECORDED, handler)
        await event_bus.emit(
            Event(event_type=EventType.MEMORY_RECORDED, data={}, timestamp=1234567890.0, source="test")
        )

        assert len(received_events) == 0

    @pytest.mark.asyncio
    async def test_global_handler(self, event_bus):
        """测试全局事件处理器"""
        received_events = []

        async def global_handler(event):
            received_events.append(event)

        event_bus.subscribe_all(global_handler)
        await event_bus.emit(
            Event(event_type=EventType.MEMORY_SEARCHED, data={"query": "test"}, timestamp=1234567890.0, source="test")
        )

        assert len(received_events) == 1

    @pytest.mark.asyncio
    async def test_multiple_handlers(self, event_bus):
        """测试多个处理器"""
        count = [0, 0]

        async def handler1(event):
            count[0] += 1

        async def handler2(event):
            count[1] += 1

        event_bus.subscribe(EventType.MEMORY_RECORDED, handler1)
        event_bus.subscribe(EventType.MEMORY_RECORDED, handler2)
        await event_bus.emit(
            Event(event_type=EventType.MEMORY_RECORDED, data={}, timestamp=1234567890.0, source="test")
        )

        assert count[0] == 1
        assert count[1] == 1

    @pytest.mark.asyncio
    async def test_handler_exception(self, event_bus):
        """测试处理器异常不影响其他处理器"""

        async def bad_handler(event):
            raise ValueError("Test exception")

        async def good_handler(event):
            pass

        event_bus.subscribe(EventType.MEMORY_RECORDED, bad_handler)
        event_bus.subscribe(EventType.MEMORY_RECORDED, good_handler)

        with patch("astrbot_plugin_scriptor.core.interfaces.logger"):
            await event_bus.emit(
                Event(event_type=EventType.MEMORY_RECORDED, data={}, timestamp=1234567890.0, source="test")
            )


class TestEventTypes:
    """事件类型枚举测试"""

    def test_event_type_values(self):
        """测试事件类型值"""
        assert EventType.MEMORY_RECORDED.value == "memory_recorded"
        assert EventType.MEMORY_SEARCHED.value == "memory_searched"
        assert EventType.SESSION_STARTED.value == "session_started"

    def test_memory_type_values(self):
        """测试记忆类型值"""
        assert MemoryType.FACT.value == "fact"
        assert MemoryType.PREFERENCE.value == "preference"
        assert MemoryType.TASK.value == "task"

    def test_privacy_level_values(self):
        """测试隐私级别值"""
        assert PrivacyLevel.PRIVATE.value == "private"
        assert PrivacyLevel.GROUP.value == "group"
        assert PrivacyLevel.GLOBAL.value == "global"


class TestMemoryRecordParams:
    """记忆记录参数测试"""

    def test_default_values(self):
        """测试默认值"""
        params = MemoryRecordParams(uid="test_user", group_id="private", content="Test content")

        assert params.uid == "test_user"
        assert params.memory_type == "fact"
        assert params.privacy_level == "private"
        assert params.strength == 1.0
        assert params.useful_score == 5.0

    def test_custom_values(self):
        """测试自定义值"""
        params = MemoryRecordParams(
            uid="test_user",
            group_id="test_group",
            content="Custom content",
            memory_type="preference",
            privacy_level="global",
            strength=2.0,
            useful_score=10.0,
            status="completed",
        )

        assert params.memory_type == "preference"
        assert params.privacy_level == "global"
        assert params.strength == 2.0
        assert params.useful_score == 10.0
        assert params.status == "completed"


class TestGlobalEventFunctions:
    """全局事件函数测试"""

    @pytest.mark.asyncio
    async def test_emit_event(self):
        """测试 emit_event 函数"""
        bus = get_event_bus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(EventType.MEMORY_DELETED, handler)
        await emit_event(EventType.MEMORY_DELETED, {"deleted": True}, source="test")

        assert len(received) == 1
        assert received[0].source == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
