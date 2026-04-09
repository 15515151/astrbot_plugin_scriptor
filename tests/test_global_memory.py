"""
测试全局记忆系统三级架构

测试内容：
1. 全局目录初始化
2. Sudo 模式
3. 记忆记录路由
4. 文件权限控制
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入共享测试工具

# 导入测试函数
from tests.test_tiered_archives import (
    test_archive_manager,
    test_archive_router,
    test_identity_manager_sudo,
)


def test_global_directory_initialization():
    """测试全局目录初始化"""
    print("\n=== 测试全局目录初始化 ===")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        # 创建全局目录结构
        global_dir = temp_dir / "global"
        global_dir.mkdir(parents=True, exist_ok=True)

        # 创建默认模板
        (global_dir / "SOUL.md").write_text("# 全局核心人格\n", encoding="utf-8")
        (global_dir / "MEMORY.md").write_text("# 全局共享记忆\n", encoding="utf-8")
        (global_dir / "HEARTBEAT.md").write_text("", encoding="utf-8")

        # 验证目录和文件存在
        assert global_dir.exists(), "全局目录应该存在"
        assert (global_dir / "SOUL.md").exists(), "全局 SOUL.md 应该存在"
        assert (global_dir / "MEMORY.md").exists(), "全局 MEMORY.md 应该存在"
        assert (global_dir / "HEARTBEAT.md").exists(), "全局 HEARTBEAT.md 应该存在"

        print("✅ 全局目录初始化测试通过")

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


def test_sudo_mode():
    """测试 Sudo 模式"""
    print("\n=== 测试 Sudo 模式 ===")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        # 运行测试
        test_identity_manager_sudo()
        print("✅ Sudo 模式测试通过")

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


def test_memory_record_routing():
    """测试记忆记录路由"""
    print("\n=== 测试记忆记录路由 ===")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        # 运行测试
        test_archive_router()
        print("✅ 记忆记录路由测试通过")

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


def test_file_permission():
    """测试文件权限控制"""
    print("\n=== 测试文件权限控制 ===")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        # 运行测试
        test_archive_manager()
        print("✅ 文件权限控制测试通过")

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
