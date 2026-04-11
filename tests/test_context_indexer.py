# tests/test_context_indexer.py
"""ContextIndexer 单元测试

验证统一上下文索引器的核心功能：
1. 目录扫描功能
2. 上下文地图生成
3. 节点内容读取
4. 安全校验
"""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# 直接导入模块，避免触发 __init__.py 的相对导入问题
import importlib.util


def import_module_from_file(module_name, file_path):
    """从文件路径动态导入模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


context_indexer_module = import_module_from_file(
    "context_indexer", str(Path(__file__).parent.parent / "core" / "context_indexer.py")
)

ContextIndexer = context_indexer_module.ContextIndexer
ContextNode = context_indexer_module.ContextNode


class TestContextIndexer:
    """ContextIndexer 测试套件 - pytest 兼容"""

    def setup_method(self):
        """创建测试环境（pytest 风格）"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="scriptor_test_"))

        # 创建模拟的 data_dir 结构
        self.data_dir = self.test_dir / "data"
        self.data_dir.mkdir()

        # 创建 profiles 目录和测试文件
        profiles_dir = self.data_dir / "profiles" / "test_user123"
        profiles_dir.mkdir(parents=True)

        (profiles_dir / "P_PROFILE.md").write_text("# 用户画像\n## 基本信息\n姓名：张三", encoding="utf-8")
        (profiles_dir / "P_SOUL.md").write_text("# 人格定义\n## 核心准则", encoding="utf-8")
        (profiles_dir / "P_MEMORY.md").write_text("# 长期记忆\n## 重要事件", encoding="utf-8")
        (profiles_dir / "P_SOP.md").write_text("# 个人标准操作流程", encoding="utf-8")
        (profiles_dir / "P_TODOed.md").write_text("# 个人待办归档\n## 已完成（历史）", encoding="utf-8")
        (profiles_dir / "NOTES.md").write_text("# 临时笔记", encoding="utf-8")

        # 创建 memory 子目录
        memory_dir = profiles_dir / "memory"
        memory_dir.mkdir()
        (memory_dir / "2026-03-10.md").write_text("# 2026-03-10 日记\n今天天气不错", encoding="utf-8")
        (memory_dir / "2026-03-09.md").write_text("# 2026-03-09 日记\n昨天工作很忙", encoding="utf-8")

        # 创建 groups 目录
        groups_dir = self.data_dir / "groups" / "test_group456"
        groups_dir.mkdir(parents=True)
        (groups_dir / "G_GROUP.md").write_text("# 群组工作流", encoding="utf-8")
        (groups_dir / "G_MEMORY.md").write_text("# 群组记忆", encoding="utf-8")
        (groups_dir / "G_SOP.md").write_text("# 群组标准操作流程", encoding="utf-8")
        (groups_dir / "G_TODOed.md").write_text("# 群组待办归档\n## 已完成（历史）", encoding="utf-8")
        (groups_dir / "NOTES.md").write_text("# 群组临时笔记", encoding="utf-8")

        # 创建 skills 目录（在 data_dir 的父级）
        skills_dir = self.test_dir / "skills"
        skills_dir.mkdir()

        skill_folder = skills_dir / "scriptor-archive-manager"
        skill_folder.mkdir()
        (skill_folder / "SKILL.md").write_text(
            "# Archive Manager Skill\n\n这是一个用于文件归档管理的技能。", encoding="utf-8"
        )

        skill_folder2 = skills_dir / "scriptor-todo-schedule"
        skill_folder2.mkdir()
        (skill_folder2 / "SKILL.md").write_text("# Todo Schedule Skill\n\n待办事项管理技能手册", encoding="utf-8")

        # 创建 global 目录
        global_dir = self.data_dir / "global"
        global_dir.mkdir()
        (global_dir / "SOUL.md").write_text("# 全局人格基座", encoding="utf-8")

        # 初始化 ContextIndexer
        self.indexer = ContextIndexer(self.data_dir)

    def teardown_method(self):
        """清理测试环境（pytest 风格）"""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_scan_personal_nodes(self):
        """测试个人记忆节点扫描"""
        print("✅ 测试: 扫描个人记忆节点...")
        nodes = self.indexer._scan_personal_nodes("test_user123")

        assert len(nodes) > 0, "应该扫描到至少一个节点"

        # 检查是否有 P_SOP.md 节点（渐进式披露）
        sop_nodes = [n for n in nodes if n.display_name == "P_SOP.md"]
        assert len(sop_nodes) == 1, "应该有一个 P_SOP.md 节点"
        assert sop_nodes[0].node_type == "personal_memory"

        # 检查是否有 P_MEMORY.md 节点（渐进式披露）
        memory_nodes = [n for n in nodes if n.display_name == "P_MEMORY.md"]
        assert len(memory_nodes) == 1, "应该有一个 P_MEMORY.md 节点"

        # 检查是否有日记节点
        diary_nodes = [n for n in nodes if n.node_type == "personal_diary"]
        assert len(diary_nodes) == 2, f"应该有两个日记节点，实际有 {len(diary_nodes)} 个"

        print(f"   ✓ 扫描到 {len(nodes)} 个个人记忆节点")

    def test_scan_group_nodes(self):
        """测试群组记忆节点扫描"""
        print("✅ 测试: 扫描群组记忆节点...")
        nodes = self.indexer._scan_group_nodes("test_group456")

        assert len(nodes) > 0, "应该扫描到至少一个节点"

        # 检查是否有 G_SOP.md 节点（渐进式披露）
        sop_nodes = [n for n in nodes if n.display_name == "G_SOP.md"]
        assert len(sop_nodes) == 1, "应该有一个 G_SOP.md 节点"

        # 检查是否有 G_MEMORY.md 节点（渐进式披露）
        memory_nodes = [n for n in nodes if n.display_name == "G_MEMORY.md"]
        assert len(memory_nodes) == 1, "应该有一个 G_MEMORY.md 节点"

        print(f"   ✓ 扫描到 {len(nodes)} 个群组记忆节点")

    def test_scan_skill_nodes(self):
        """测试技能节点扫描"""
        print("✅ 测试: 扫描技能节点...")
        nodes = self.indexer._scan_skill_nodes()

        assert len(nodes) == 2, f"应该有两个技能节点，实际有 {len(nodes)} 个"

        # 检查技能名称
        skill_names = [n.display_name for n in nodes]
        assert "Archive Manager" in skill_names, "应该包含 Archive Manager 技能"
        assert "Todo Schedule" in skill_names, "应该包含 Todo Schedule 技能"

        print(f"   ✓ 扫描到 {len(nodes)} 个技能节点: {skill_names}")

    def test_build_context_map(self):
        """测试上下文地图生成"""
        print("✅ 测试: 生成上下文目录地图...")
        context_map = self.indexer.build_context_map("test_user123", "test_group456", include_skills=True)

        assert context_map != "", "上下文地图不应该为空"
        assert "可用上下文节点目录" in context_map, "应该包含标题"
        assert "个人记忆" in context_map, "应该包含个人记忆分区"
        assert "群组记忆" in context_map, "应该包含群组记忆分区"
        assert "可用技能" in context_map, "应该包含技能分区"
        assert "file_read_tool" in context_map, "应该包含使用示例"

        print(f"   ✓ 上下文地图生成成功，长度: {len(context_map)} 字符")

    def test_get_node_content(self):
        """测试节点内容读取"""
        print("✅ 测试: 读取节点内容...")

        # 测试读取个人文件（渐进式披露文件）
        success, content = self.indexer.get_node_content("profiles/test_user123/P_SOP.md")
        assert success, "应该成功读取 P_SOP.md"
        assert "个人标准操作流程" in content, "内容应该包含 SOP 标题"

        # 测试读取技能文件
        success, content = self.indexer.get_node_content("skills/scriptor-archive-manager/SKILL.md")
        assert success, "应该成功读取 SKILL.md"
        assert "Archive Manager Skill" in content, "内容应该包含技能标题"

        # 测试路径穿越检测
        success, content = self.indexer.get_node_content("../../etc/passwd")
        assert not success, "应该拒绝路径穿越攻击"
        assert "Error" in content, "应该返回错误信息"

        # 测试不存在的文件
        success, content = self.indexer.get_node_content("profiles/test_user123/NONEXISTENT.md")
        assert not success, "应该返回文件不存在错误"

        print("   ✓ 节点内容读取功能正常")

    def test_list_available_nodes(self):
        """测试列出所有可用节点"""
        print("✅ 测试: 列出所有可用节点...")
        all_nodes = self.indexer.list_available_nodes("test_user123", "test_group456")

        assert len(all_nodes) > 0, "应该有可用节点"

        # 检查节点类型分布
        node_types = set(n["type"] for n in all_nodes)
        assert "personal_memory" in node_types, "应该包含 personal_memory 类型"
        assert "group_memory" in node_types, "应该包含 group_memory 类型"
        assert "skill" in node_types, "应该包含 skill 类型"

        print(f"   ✓ 共列出 {len(all_nodes)} 个可用节点")

    def test_frontmatter_extraction(self):
        """测试 Front Matter 提取"""
        print("✅ 测试: Front Matter 提取...")

        # 创建带 Front Matter 的文件
        test_file = self.data_dir / "profiles" / "test_user123" / "TEST_FRONTMATTER.md"
        test_file.write_text(
            "---\nsummary: 这是一个测试摘要\ntags: [test, frontmatter]\n---\n\n# 测试文档\n这是正文内容",
            encoding="utf-8",
        )

        summary = self.indexer._extract_frontmatter_summary(test_file)
        assert summary == "这是一个测试摘要", f"应该提取到摘要，实际得到: {summary}"

        print(f"   ✓ Front Matter 提取正常: {summary}")
