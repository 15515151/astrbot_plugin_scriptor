"""
测试文件权限控制

测试内容：
1. 普通用户无法访问全局目录
2. Sudo 管理员可以访问全局目录
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


def test_file_permission():
    """测试文件权限控制"""
    print("\n=== 测试文件权限控制 ===")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        identity_manager = SimpleIdentityManager(temp_dir)
        config = MockConfig()

        # 创建全局目录
        global_dir = temp_dir / "global"
        global_dir.mkdir(parents=True, exist_ok=True)
        global_soul = global_dir / "SOUL.md"
        global_soul.write_text("# 全局 SOUL", encoding="utf-8")

        # 模拟权限检查逻辑
        def check_global_permission(uid: str, file_path: str) -> str:
            is_sudo = identity_manager.is_sudo(uid, config.admin_uids)
            is_global = file_path.startswith("global/")

            if is_global and not is_sudo:
                return "Error: 只有处于管理员模式（Sudo）的管理员可以访问全局目录。"
            return None

        # 测试普通用户无法访问全局目录
        error = check_global_permission("user_test01", "global/SOUL.md")
        assert error is not None, "普通用户不应该能访问全局目录"
        print(f"  普通用户访问全局目录: {error}")

        # 管理员进入 Sudo 模式（异步调用）
        import asyncio

        identity_manager.security_data["origin_owner"] = "user_admin01"
        asyncio.run(identity_manager.enter_sudo("user_admin01", config.admin_uids))

        # 测试 Sudo 管理员可以访问全局目录
        error = check_global_permission("user_admin01", "global/SOUL.md")
        assert error is None, "Sudo 管理员应该能访问全局目录"
        print("  Sudo 管理员访问全局目录: 允许")

        print("✅ 文件权限控制测试通过")

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
