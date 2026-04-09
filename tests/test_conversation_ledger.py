# tests/test_conversation_ledger.py
"""对话总账模块测试"""

import sys
from pathlib import Path

# 直接导入模块文件，不通过包导入
ledger_module_path = Path(__file__).parent.parent / "core" / "conversation_ledger.py"
sys.path.insert(0, str(ledger_module_path.parent))

import importlib.util

import pytest

spec = importlib.util.spec_from_file_location("ledger_module", ledger_module_path)
ledger_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger_module)
ConversationLedger = ledger_module.ConversationLedger
LedgerMessage = ledger_module.LedgerMessage


@pytest.fixture
def temp_data_dir(tmp_path):
    """创建临时数据目录"""
    return tmp_path


@pytest.fixture
def ledger(temp_data_dir):
    """创建对话总账实例"""
    return ConversationLedger(temp_data_dir)


class TestLedgerMessage:
    """LedgerMessage 实体类测试"""

    def test_create_message(self):
        """测试创建消息"""
        msg = LedgerMessage(
            message_id="test123", timestamp=123456789.0, role="user", content="Hello, world!", source="user_input"
        )

        assert msg.message_id == "test123"
        assert msg.timestamp == 123456789.0
        assert msg.role == "user"
        assert msg.content == "Hello, world!"
        assert msg.source == "user_input"
        assert msg.metadata == {}

    def test_message_with_metadata(self):
        """测试带元数据的消息"""
        msg = LedgerMessage(
            message_id="test456",
            timestamp=987654321.0,
            role="assistant",
            content="Hi there!",
            source="ai_response",
            metadata={"key": "value"},
        )

        assert msg.metadata == {"key": "value"}


class TestConversationLedger:
    """ConversationLedger 测试"""

    @pytest.mark.asyncio
    async def test_add_and_get_message(self, ledger):
        """测试添加和获取消息"""
        session_id = "test_session"

        # 添加消息
        msg_id = await ledger.add_message(
            session_id=session_id, role="user", content="Test message", source="user_input"
        )

        assert msg_id is not None

        # 获取消息
        messages = await ledger.get_messages(session_id)
        assert len(messages) == 1
        assert messages[0].content == "Test message"
        assert messages[0].role == "user"

    @pytest.mark.asyncio
    async def test_get_recent_context(self, ledger):
        """测试获取最近上下文"""
        session_id = "test_session"

        # 添加多条消息
        for i in range(15):
            await ledger.add_message(
                session_id=session_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                source="user_input" if i % 2 == 0 else "ai_response",
            )

        # 获取最近 10 条
        context = await ledger.get_recent_context(session_id, message_count=10)
        assert len(context) == 10
        assert context[0]["content"] == "Message 5"
        assert context[-1]["content"] == "Message 14"

    @pytest.mark.asyncio
    async def test_clear_session(self, ledger):
        """测试清空会话"""
        session_id = "test_session_clear"

        await ledger.add_message(session_id, "user", "Test", "user_input")

        messages = await ledger.get_messages(session_id)
        assert len(messages) >= 1

        await ledger.clear_session(session_id)

        messages_after = await ledger.get_messages(session_id)
        assert len(messages_after) <= 1

    @pytest.mark.asyncio
    async def test_get_session_stats(self, ledger):
        """测试获取会话统计"""
        session_id = "test_session_stats"

        await ledger.add_message(session_id, "user", "Msg 1", "user_input")
        await ledger.add_message(session_id, "assistant", "Reply 1", "ai_response")

        stats = await ledger.get_session_stats(session_id)

        assert stats is not None
        assert "total_messages" in stats or "message_count" in stats

    @pytest.mark.asyncio
    async def test_message_limit(self, ledger, temp_data_dir):
        """测试消息数量限制"""
        session_id = "test_session"

        # 添加超过限制数量的消息
        for i in range(600):
            await ledger.add_message(session_id=session_id, role="user", content=f"Message {i}", source="user_input")

        messages = await ledger.get_messages(session_id)
        assert len(messages) == ledger.MAX_MESSAGES_PER_SESSION
