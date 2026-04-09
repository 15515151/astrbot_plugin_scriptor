"""
测试 Sudo 模式

测试内容：
1. 普通用户无法进入 Sudo 模式
2. 管理员可以进入 Sudo 模式
3. Sudo 状态检查
4. 退出 Sudo 模式
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入共享测试工具
from tests.helpers.test_fixtures import SimpleIdentityManager


class MockConfig:
    """模拟配置"""

    def __init__(self):
        self.admin_uids = ["user_admin01"]
        self.enable_token_control = True
        self.max_system_prompt_tokens = 4000
        self.soul_priority = 15
        self.agents_priority = 10
        self.profile_priority = 8
        self.group_rules_priority = 5
        self.group_members_priority = 5
        self.cross_group_tasks_priority = 3
        self.recent_notes_priority = 3
        self.graph_recall_priority = 5
        self.sop_priority = 3


def test_sudo_mode():
    """测试 Sudo 模式"""
    print("\n=== 测试 Sudo 模式 ===")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        identity_manager = SimpleIdentityManager(temp_dir)
        config = MockConfig()

        # 模拟创世神
        identity_manager.security_data["origin_owner"] = "user_admin01"

        # 测试普通用户无法进入 Sudo（异步调用）
        import asyncio

        success, msg = asyncio.run(identity_manager.enter_sudo("user_test01", config.admin_uids))
        assert not success, "普通用户不应该能进入 Sudo 模式"
        print(f"  普通用户进入 Sudo: {msg}")

        # 测试管理员可以进入 Sudo（异步调用）
        success, msg = asyncio.run(identity_manager.enter_sudo("user_admin01", config.admin_uids))
        assert success, "管理员应该能进入 Sudo 模式"
        print(f"  管理员进入 Sudo: {msg}")

        # 测试 Sudo 状态检查
        assert identity_manager.is_sudo("user_admin01", config.admin_uids), "管理员应该在 Sudo 模式中"
        assert not identity_manager.is_sudo("user_test01", config.admin_uids), "普通用户不应该在 Sudo 模式中"

        # 测试退出 Sudo（异步调用）
        success, msg = asyncio.run(identity_manager.exit_sudo("user_admin01"))
        assert success, "应该能退出 Sudo 模式"
        assert not identity_manager.is_sudo("user_admin01", config.admin_uids), "退出后不应该在 Sudo 模式中"

        print("✅ Sudo 模式测试通过")

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
