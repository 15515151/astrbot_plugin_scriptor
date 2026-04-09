"""
测试记忆记录路由

测试内容：
1. 普通用户记录到个人目录
2. Sudo 模式记录到全局目录
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入共享测试工具
from tests.helpers.test_fixtures import ArchiveScope, SimpleArchiveRouter


def test_memory_record_routing():
    """测试记忆记录路由"""
    print("\n=== 测试记忆记录路由 ===")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        # 创建目录结构
        global_dir = temp_dir / "global"
        global_dir.mkdir(parents=True, exist_ok=True)
        (global_dir / "MEMORY.md").write_text("# 全局共享记忆\n", encoding="utf-8")

        profile_dir = temp_dir / "profiles" / "user_test01"
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "MEMORY.md").write_text("# 个人记忆\n", encoding="utf-8")

        router = SimpleArchiveRouter(temp_dir)

        # 测试普通用户记录到个人目录
        db_path, scope = router.resolve_db_path("user_test01", "private", is_sudo=False)
        assert scope == ArchiveScope.PERSONAL, "非 Sudo 模式应该记录到个人目录"
        assert "profiles" in str(db_path), "目标文件应该在个人目录中"
        print(f"  普通用户记录路由: {scope} -> {db_path.name}")

        # 测试 Sudo 模式记录到全局目录
        db_path, scope = router.resolve_db_path("user_admin01", "private", is_sudo=True)
        assert scope == ArchiveScope.GLOBAL, "Sudo 模式应该记录到全局目录"
        assert "global" in str(db_path), "目标文件应该在全局目录中"
        print(f"  Sudo 模式记录路由: {scope} -> {db_path.name}")

        print("✅ 记忆记录路由测试通过")

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
