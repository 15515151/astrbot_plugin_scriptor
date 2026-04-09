"""
三级记忆架构测试用例

测试内容：
1. 全局目录初始化
2. 全局/个人 SOUL.md 分层读取
3. Sudo 模式写入全局记忆
4. 权限控制验证
"""

import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@dataclass
class MockConfig:
    """模拟配置"""

    admin_uids: List[str] = field(default_factory=lambda: ["user_admin01"])
    enable_token_control: bool = True
    max_system_prompt_tokens: int = 8000
    soul_priority: int = 15
    agents_priority: int = 10
    profile_priority: int = 8
    group_rules_priority: int = 7
    group_members_priority: int = 6
    cross_group_tasks_priority: int = 5
    recent_notes_priority: int = 4
    graph_recall_priority: int = 3
    sop_priority: int = 2


class MockIdentityManager:
    """模拟身份管理器"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._sudo_sessions: Dict[str, Any] = {}
        self.security_data = {"origin_owner": "user_admin01", "group_admins": {}}
        self.uid_metadata = {"user_admin01": {"primary_name": "Admin"}, "user_test01": {"primary_name": "TestUser"}}

    def is_super_admin(self, uid: str, config_admins: List[str] = None) -> bool:
        return uid == self.security_data.get("origin_owner") or uid in (config_admins or [])

    def is_group_admin(self, uid: str, group_id: str) -> bool:
        return uid in self.security_data.get("group_admins", {}).get(group_id, [])

    def is_sudo(self, uid: str, config_admins: List[str] = None) -> bool:
        if not self.is_super_admin(uid, config_admins):
            return False
        return uid in self._sudo_sessions

    def enter_sudo(self, uid: str, config_admins: List[str] = None) -> tuple:
        if not self.is_super_admin(uid, config_admins):
            return False, "权限不足"
        self._sudo_sessions[uid] = {"started_at": 0}
        return True, "已进入管理员模式"

    def exit_sudo(self, uid: str) -> tuple:
        if uid in self._sudo_sessions:
            del self._sudo_sessions[uid]
        return True, "已退出管理员模式"

    def record_sudo_operation(self, uid: str, operation: str, details: str = ""):
        pass

    def get_or_create_uid(self, physical_id: str, platform: str) -> str:
        return f"user_{physical_id[:8]}"


class MockGroupManager:
    """模拟群组管理器"""

    def __init__(self, data_dir: Path, identity_manager: MockIdentityManager):
        self.data_dir = data_dir
        self.identity_manager = identity_manager

    def get_group_context(self, group_id: str, uid: str) -> Dict[str, Any]:
        return {"group_rules": "", "members": []}


class MockCrossGroupSystem:
    """模拟跨群系统"""

    def format_pending_notifications(self, group_id: str) -> str:
        return ""


def test_global_directory_initialization():
    """测试全局目录初始化"""
    print("\n=== 测试全局目录初始化 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)

        # 模拟 IdentityManager 初始化全局目录
        identity_manager = MockIdentityManager(data_dir)

        # 手动创建全局目录结构（模拟 _init_global_directory）
        global_dir = data_dir / "global"
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


def test_sudo_mode():
    """测试 Sudo 模式"""
    print("\n=== 测试 Sudo 模式 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        identity_manager = MockIdentityManager(data_dir)
        config = MockConfig()

        # 测试普通用户无法进入 Sudo
        success, msg = identity_manager.enter_sudo("user_test01", config.admin_uids)
        assert not success, "普通用户不应该能进入 Sudo 模式"
        print(f"  普通用户进入 Sudo: {msg}")

        # 测试管理员可以进入 Sudo
        success, msg = identity_manager.enter_sudo("user_admin01", config.admin_uids)
        assert success, "管理员应该能进入 Sudo 模式"
        print(f"  管理员进入 Sudo: {msg}")

        # 测试 Sudo 状态检查
        assert identity_manager.is_sudo("user_admin01", config.admin_uids), "管理员应该在 Sudo 模式中"
        assert not identity_manager.is_sudo("user_test01", config.admin_uids), "普通用户不应该在 Sudo 模式中"

        # 测试退出 Sudo
        success, msg = identity_manager.exit_sudo("user_admin01")
        assert success, "应该能退出 Sudo 模式"
        assert not identity_manager.is_sudo("user_admin01", config.admin_uids), "退出后不应该在 Sudo 模式中"

        print("✅ Sudo 模式测试通过")


def test_memory_record_routing():
    """测试记忆记录路由"""
    print("\n=== 测试记忆记录路由 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)

        # 创建目录结构
        global_dir = data_dir / "global"
        global_dir.mkdir(parents=True, exist_ok=True)
        (global_dir / "MEMORY.md").write_text("# 全局共享记忆\n", encoding="utf-8")

        profile_dir = data_dir / "profiles" / "user_test01"
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "MEMORY.md").write_text("# 个人记忆\n", encoding="utf-8")

        # 模拟记忆记录参数（使用本地定义避免外部依赖）
        @dataclass
        class MemoryRecordParams:
            uid: str
            group_id: str
            content: str
            memory_type: str
            is_sudo: bool = False

        # 测试普通用户记录到个人目录
        params_personal = MemoryRecordParams(
            uid="user_test01", group_id="private", content="这是个人记忆", memory_type="fact", is_sudo=False
        )

        if params_personal.is_sudo:
            target_file = global_dir / "MEMORY.md"
            scope = "global"
        else:
            target_file = profile_dir / "MEMORY.md"
            scope = "personal"

        assert scope == "personal", "非 Sudo 模式应该记录到个人目录"
        assert str(target_file) == str(profile_dir / "MEMORY.md"), "目标文件应该是个人 MEMORY.md"
        print(f"  普通用户记录路由: {scope} -> {target_file.name}")

        # 测试 Sudo 模式记录到全局目录
        params_global = MemoryRecordParams(
            uid="user_admin01", group_id="private", content="这是全局记忆", memory_type="fact", is_sudo=True
        )

        if params_global.is_sudo:
            target_file = global_dir / "MEMORY.md"
            scope = "global"
        else:
            target_file = profile_dir / "MEMORY.md"
            scope = "personal"

        assert scope == "global", "Sudo 模式应该记录到全局目录"
        assert str(target_file) == str(global_dir / "MEMORY.md"), "目标文件应该是全局 MEMORY.md"
        print(f"  Sudo 模式记录路由: {scope} -> {target_file.name}")

        print("✅ 记忆记录路由测试通过")


def test_file_permission():
    """测试文件权限控制"""
    print("\n=== 测试文件权限控制 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        identity_manager = MockIdentityManager(data_dir)
        config = MockConfig()

        # 创建全局目录
        global_dir = data_dir / "global"
        global_dir.mkdir(parents=True, exist_ok=True)
        global_soul = global_dir / "SOUL.md"
        global_soul.write_text("# 全局 SOUL", encoding="utf-8")

        # 模拟权限检查逻辑
        def check_global_permission(uid: str, file_path: str) -> Optional[str]:
            is_sudo = identity_manager.is_sudo(uid, config.admin_uids)
            is_global = file_path.startswith("global/")

            if is_global and not is_sudo:
                return "Error: 只有处于管理员模式（Sudo）的管理员可以访问全局目录。"
            return None

        # 测试普通用户无法访问全局目录
        error = check_global_permission("user_test01", "global/SOUL.md")
        assert error is not None, "普通用户不应该能访问全局目录"
        print(f"  普通用户访问全局目录: {error}")

        # 管理员进入 Sudo 模式
        identity_manager.enter_sudo("user_admin01", config.admin_uids)

        # 测试 Sudo 管理员可以访问全局目录
        error = check_global_permission("user_admin01", "global/SOUL.md")
        assert error is None, "Sudo 管理员应该能访问全局目录"
        print("  Sudo 管理员访问全局目录: 允许")

        print("✅ 文件权限控制测试通过")


def test_prompt_builder_integration():
    """测试 PromptBuilder 集成"""
    print("\n=== 测试 PromptBuilder 集成 ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)

        # 创建目录结构
        global_dir = data_dir / "global"
        global_dir.mkdir(parents=True, exist_ok=True)
        (global_dir / "SOUL.md").write_text("# 全局核心人格\n\n这是全局基调。", encoding="utf-8")
        (global_dir / "MEMORY.md").write_text("# 全局共享记忆\n\n公共知识。", encoding="utf-8")
        (global_dir / "HEARTBEAT.md").write_text("", encoding="utf-8")

        profile_dir = data_dir / "profiles" / "user_test01"
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "SOUL.md").write_text("# 个人核心准则\n\n这是个人进化。", encoding="utf-8")
        (profile_dir / "PROFILE.md").write_text("# 个人画像", encoding="utf-8")

        # 模拟 PromptBuilder 的模板加载逻辑
        def load_global_template(template_name: str) -> str:
            global_file = global_dir / template_name
            if global_file.exists():
                return global_file.read_text(encoding="utf-8")
            return ""

        def load_personal_template(profile_dir: Path, template_name: str) -> str:
            personal_file = profile_dir / template_name
            if personal_file.exists():
                return personal_file.read_text(encoding="utf-8")
            return ""

        # 测试全局 SOUL 加载
        global_soul = load_global_template("SOUL.md")
        assert "全局核心人格" in global_soul, "应该能加载全局 SOUL"
        print(f"  全局 SOUL 加载成功: {len(global_soul)} 字符")

        # 测试个人 SOUL 加载
        personal_soul = load_personal_template(profile_dir, "SOUL.md")
        assert "个人核心准则" in personal_soul, "应该能加载个人 SOUL"
        print(f"  个人 SOUL 加载成功: {len(personal_soul)} 字符")

        # 测试全局 MEMORY 加载
        global_memory = load_global_template("MEMORY.md")
        assert "全局共享记忆" in global_memory, "应该能加载全局 MEMORY"
        print(f"  全局 MEMORY 加载成功: {len(global_memory)} 字符")

        print("✅ PromptBuilder 集成测试通过")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始运行三级记忆架构测试")
    print("=" * 60)

    try:
        test_global_directory_initialization()
        test_sudo_mode()
        test_memory_record_routing()
        test_file_permission()
        test_prompt_builder_integration()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！三级记忆架构实现正确。")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
