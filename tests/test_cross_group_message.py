# tests/test_cross_group_message.py
"""跨群消息系统单元测试"""

import json
import sys
import tempfile
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cross_group_message import CrossGroupMessage, CrossGroupMessageSystem, CrossGroupMessageType


@pytest.fixture
def temp_data_dir():
    """创建临时数据目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config():
    """模拟配置对象"""

    class MockConfig:
        cross_group_enabled = True

    return MockConfig()


@pytest.fixture
def mock_identity_manager():
    """模拟身份管理器"""

    class MockIdentityManager:
        def get_display_name(self, uid):
            return f"User_{uid}"

    return MockIdentityManager()


@pytest.fixture
def mock_group_manager():
    """模拟群组管理器"""

    class MockGroupManager:
        pass

    return MockGroupManager()


class TestCrossGroupMessage:
    """测试 CrossGroupMessage 数据类"""

    def test_create_default_message(self):
        """测试默认消息创建"""
        msg = CrossGroupMessage()

        assert msg.message_id != ""
        assert msg.source_group == ""
        assert msg.target_groups == []
        assert msg.content == ""
        assert msg.message_type == CrossGroupMessageType.INFO.value
        assert msg.delivered is False
        assert msg.delivered_at is None
        assert msg.author_uid == ""
        assert msg.author_name == ""

    def test_create_custom_message(self):
        """测试自定义消息创建"""
        msg = CrossGroupMessage(
            source_group="group_123",
            target_groups=["group_456", "group_789"],
            content="测试内容",
            message_type=CrossGroupMessageType.TASK.value,
            author_uid="user_001",
            author_name="张三",
        )

        assert msg.source_group == "group_123"
        assert len(msg.target_groups) == 2
        assert "group_456" in msg.target_groups
        assert msg.content == "测试内容"
        assert msg.message_type == CrossGroupMessageType.TASK.value
        assert msg.author_uid == "user_001"
        assert msg.author_name == "张三"

    def test_to_dict_conversion(self):
        """测试字典转换"""
        msg = CrossGroupMessage(source_group="group_1", target_groups=["group_2"], content="测试", author_uid="user_1")

        data = msg.to_dict()

        assert isinstance(data, dict)
        assert data["source_group"] == "group_1"
        assert len(data["target_groups"]) == 1
        assert data["content"] == "测试"

    def test_from_dict_conversion(self):
        """测试从字典创建消息"""
        data = {
            "message_id": "test_id_123",
            "source_group": "group_src",
            "target_groups": ["group_tgt1", "group_tgt2"],
            "content": "从字典创建",
            "message_type": "reminder",
            "delivered": True,
            "delivered_at": time.time(),
            "expires_at": time.time() + 86400,
            "author_uid": "user_auth",
            "author_name": "作者",
        }

        msg = CrossGroupMessage.from_dict(data)

        assert msg.message_id == "test_id_123"
        assert msg.source_group == "group_src"
        assert len(msg.target_groups) == 2
        assert msg.content == "从字典创建"
        assert msg.delivered is True
        assert msg.delivered_at is not None

    def test_is_expired_false(self):
        """测试未过期消息"""
        msg = CrossGroupMessage(expires_at=time.time() + 3600)  # 1小时后过期

        assert msg.is_expired() is False

    def test_is_expired_true(self):
        """测试已过期消息"""
        msg = CrossGroupMessage(expires_at=time.time() - 3600)  # 1小时前已过期

        assert msg.is_expired() is True

    def test_message_types_enum(self):
        """测试消息类型枚举"""
        assert CrossGroupMessageType.TASK.value == "task"
        assert CrossGroupMessageType.REMINDER.value == "reminder"
        assert CrossGroupMessageType.INFO.value == "info"
        assert CrossGroupMessageType.DECISION.value == "decision"


class TestCrossGroupMessageSystem:
    """测试 CrossGroupMessageSystem 系统"""

    @pytest.mark.asyncio
    async def test_system_initialization(self, temp_data_dir, mock_config, mock_identity_manager, mock_group_manager):
        """测试系统初始化"""
        system = CrossGroupMessageSystem(temp_data_dir, mock_config, mock_identity_manager, mock_group_manager)

        assert system.data_dir == temp_data_dir
        assert system.pending_messages == []
        assert system.messages_file.exists() is False

    @pytest.mark.asyncio
    async def test_add_and_get_messages(self, temp_data_dir, mock_config, mock_identity_manager, mock_group_manager):
        """测试添加和获取消息"""
        system = CrossGroupMessageSystem(temp_data_dir, mock_config, mock_identity_manager, mock_group_manager)

        # 手动创建并添加消息
        msg = CrossGroupMessage(
            source_group="group_a", target_groups=["group_b"], content="测试消息", author_uid="user_1"
        )
        system.pending_messages.append(msg)

        assert msg is not None
        assert msg.source_group == "group_a"
        assert msg.content == "测试消息"

        # 获取待发送消息
        pending = system.get_pending_messages("group_b")

        assert len(pending) >= 1
        assert any(m.message_id == msg.message_id for m in pending)

    @pytest.mark.asyncio
    async def test_mark_delivered(self, temp_data_dir, mock_config, mock_identity_manager, mock_group_manager):
        """测试标记消息为已送达"""
        system = CrossGroupMessageSystem(temp_data_dir, mock_config, mock_identity_manager, mock_group_manager)

        # 手动创建并添加消息
        msg = CrossGroupMessage(source_group="group_a", target_groups=["group_b"], content="待标记消息")
        system.pending_messages.append(msg)

        # 标记为已送达
        system.mark_delivered(msg.message_id)

        # 验证消息状态（需要重新查找）
        updated_msg = None
        for m in system.pending_messages:
            if m.message_id == msg.message_id:
                updated_msg = m
                break

        if updated_msg:
            assert updated_msg.delivered is True
            assert updated_msg.delivered_at is not None

    @pytest.mark.asyncio
    async def test_get_target_group_messages(
        self, temp_data_dir, mock_config, mock_identity_manager, mock_group_manager
    ):
        """测试按目标群组获取消息"""
        system = CrossGroupMessageSystem(temp_data_dir, mock_config, mock_identity_manager, mock_group_manager)

        # 手动添加多条消息到不同群组
        msg1 = CrossGroupMessage(source_group="g1", target_groups=["g2"], content="消息1")
        msg2 = CrossGroupMessage(source_group="g1", target_groups=["g3"], content="消息2")
        msg3 = CrossGroupMessage(source_group="g2", target_groups=["g3"], content="消息3")

        system.pending_messages.extend([msg1, msg2, msg3])

        # 获取目标群组 g3 的消息
        messages_g3 = system.get_pending_messages("g3")

        assert len(messages_g3) == 2
        contents = [m.content for m in messages_g3]
        assert "消息2" in contents
        assert "消息3" in contents

    @pytest.mark.asyncio
    async def test_persistence(self, temp_data_dir, mock_config, mock_identity_manager, mock_group_manager):
        """测试消息持久化"""
        # 创建并启动系统
        system = CrossGroupMessageSystem(temp_data_dir, mock_config, mock_identity_manager, mock_group_manager)

        await system.start()

        # 手动添加消息
        msg = CrossGroupMessage(source_group="persist_group", target_groups=["target_group"], content="持久化测试消息")
        system.pending_messages.append(msg)

        # 手动触发保存
        system._save_direct()

        # 停止系统
        await system.stop()

        # 验证文件存在且包含消息
        assert system.messages_file.exists()

        with open(system.messages_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "messages" in data
        assert len(data["messages"]) > 0

        saved_msg = next((m for m in data["messages"] if m["message_id"] == msg.message_id), None)
        assert saved_msg is not None
        assert saved_msg["content"] == "持久化测试消息"

    @pytest.mark.asyncio
    async def test_expired_message_filtering(
        self, temp_data_dir, mock_config, mock_identity_manager, mock_group_manager
    ):
        """测试过期消息过滤"""
        system = CrossGroupMessageSystem(temp_data_dir, mock_config, mock_identity_manager, mock_group_manager)

        # 手动添加一个已过期的消息
        expired_msg = CrossGroupMessage(
            source_group="group_1",
            target_groups=["group_2"],
            content="已过期消息",
            expires_at=time.time() - 100,  # 已过期
        )
        system.pending_messages.append(expired_msg)

        # 添加正常消息
        normal_msg = CrossGroupMessage(source_group="group_1", target_groups=["group_2"], content="正常消息")
        system.pending_messages.append(normal_msg)

        # 清理过期消息
        system.cleanup_expired()

        # 获取待处理消息（应过滤掉过期消息）
        pending = system.get_pending_messages("group_2")

        # 过期消息不应出现在列表中
        expired_found = any(m.message_id == expired_msg.message_id for m in pending)
        normal_found = any(m.message_id == normal_msg.message_id for m in pending)

        assert expired_found is False
        assert normal_found is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
