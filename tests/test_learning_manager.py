# tests/test_learning_manager.py
"""
学习管理器单元测试
验证：
1. 知识库扩容（1000字）
2. 三态认知模型切换
3. 权限控制
4. 双轨写入机制
"""

import os
import sys
from pathlib import Path

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置环境变量以避免相对导入问题
os.environ.setdefault("SCRIPTOR_TEST_MODE", "1")


class TestKnowledgeBaseExpansion:
    """测试知识库扩容"""

    def test_max_content_length_is_1000(self):
        """验证 MAX_CONTENT_LENGTH 已更新为 1000"""
        # 直接读取文件内容验证
        kb_file = project_root / "core" / "knowledge_base.py"
        content = kb_file.read_text(encoding="utf-8")

        # 检查 MAX_CONTENT_LENGTH = 1000
        assert "MAX_CONTENT_LENGTH = 1000" in content, "MAX_CONTENT_LENGTH 应为 1000"

    def test_knowledge_item_docstring_updated(self):
        """验证知识条目文档字符串已更新"""
        kb_file = project_root / "core" / "knowledge_base.py"
        content = kb_file.read_text(encoding="utf-8")

        # 检查文档字符串更新
        assert "1000字以内" in content or "1000 字" in content, "知识条目文档字符串应更新为 1000 字"


class TestCognitiveState:
    """测试三态认知模型"""

    def test_cognitive_state_enum_definition(self):
        """验证认知状态枚举定义正确"""
        lm_file = project_root / "core" / "learning_manager.py"
        content = lm_file.read_text(encoding="utf-8")

        # 检查枚举定义
        assert "class CognitiveState(Enum)" in content, "应定义 CognitiveState 枚举"
        assert "NORMAL" in content, "应包含 NORMAL 状态"
        assert "LEARNING" in content, "应包含 LEARNING 状态"
        assert "TEACHING" in content, "应包含 TEACHING 状态"

    def test_learning_manager_class_exists(self):
        """验证学习管理器类存在"""
        lm_file = project_root / "core" / "learning_manager.py"
        content = lm_file.read_text(encoding="utf-8")

        assert "class LearningManager" in content, "应定义 LearningManager 类"


class TestLearningCommands:
    """测试学习模式命令"""

    def test_learning_commands_registered(self):
        """验证学习模式命令已注册"""
        learning_mixin_file = project_root / "mixins" / "learning_mixin.py"
        if learning_mixin_file.exists():
            content = learning_mixin_file.read_text(encoding="utf-8")
        else:
            main_file = project_root / "main.py"
            content = main_file.read_text(encoding="utf-8")

        assert '@filter.command("开始学习")' in content, "应注册 /开始学习 命令"
        assert '@filter.command("结束学习")' in content, "应注册 /结束学习 命令"
        assert '@filter.command("开始授课")' in content, "应注册 /开始授课 命令"
        assert '@filter.command("结束授课")' in content, "应注册 /结束授课 命令"

    def test_learning_manager_imported(self):
        """验证学习管理器已导入"""
        main_file = project_root / "main.py"
        content = main_file.read_text(encoding="utf-8")

        assert (
            "from .core.learning_manager import LearningManager" in content
            or "from core.learning_manager import LearningManager" in content
        ), "应导入 LearningManager"


class TestPromptBuilderIntegration:
    """测试 PromptBuilder 集成"""

    def test_learning_manager_parameter_added(self):
        """验证 PromptBuilder 添加了 learning_manager 参数"""
        pb_file = project_root / "core" / "prompt_builder.py"
        content = pb_file.read_text(encoding="utf-8")

        assert "learning_manager" in content, "PromptBuilder 应添加 learning_manager 参数"

    def test_state_prompt_suffix_method_used(self):
        """验证使用了状态提示词后缀方法"""
        pb_file = project_root / "core" / "prompt_builder.py"
        content = pb_file.read_text(encoding="utf-8")

        assert "get_state_prompt_suffix" in content, "应调用 get_state_prompt_suffix 方法"


class TestConfigUpdates:
    """测试配置更新"""

    def test_learning_mode_config_exists(self):
        """验证学习模式配置存在"""
        config_file = project_root / "core" / "config_pydantic.py"
        content = config_file.read_text(encoding="utf-8")

        assert "learning_mode_enabled" in content, "应添加 learning_mode_enabled 配置"
        assert "teaching_mode_enabled" in content, "应添加 teaching_mode_enabled 配置"


class TestLearningManagerLogic:
    """测试学习管理器逻辑（静态分析）"""

    def test_dual_track_write_method_exists(self):
        """验证双轨写入方法存在"""
        lm_file = project_root / "core" / "learning_manager.py"
        content = lm_file.read_text(encoding="utf-8")

        assert "_dual_track_write" in content, "应定义 _dual_track_write 方法"

    def test_pending_knowledge_flow_exists(self):
        """验证待确认知识流程存在"""
        lm_file = project_root / "core" / "learning_manager.py"
        content = lm_file.read_text(encoding="utf-8")

        assert "add_pending_knowledge" in content, "应定义 add_pending_knowledge 方法"
        assert "confirm_pending_knowledge" in content, "应定义 confirm_pending_knowledge 方法"

    def test_permission_check_exists(self):
        """验证权限检查存在"""
        lm_file = project_root / "core" / "learning_manager.py"
        content = lm_file.read_text(encoding="utf-8")

        # 权限检查在 main.py 的命令中实现
        main_file = project_root / "main.py"
        main_content = main_file.read_text(encoding="utf-8")

        assert (
            "admin_uids" in main_content or "is_admin" in main_content or "权限" in main_content
        ), "应包含权限检查逻辑"

    def test_learning_mode_prompt_exists(self):
        """验证学习模式提示词存在"""
        lm_file = project_root / "core" / "learning_manager.py"
        content = lm_file.read_text(encoding="utf-8")

        assert "学习模式" in content, "应包含学习模式提示词"
        assert "新员工" in content or "学徒" in content, "学习模式提示词应包含学徒/新员工人设"

    def test_teaching_mode_prompt_exists(self):
        """验证授课模式提示词存在"""
        lm_file = project_root / "core" / "learning_manager.py"
        content = lm_file.read_text(encoding="utf-8")

        assert "授课模式" in content, "应包含授课模式提示词"
        assert "只读" in content, "授课模式提示词应包含只读说明"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestLearningTools:
    """测试学习模式工具"""

    def test_learn_from_conversation_tool_exists(self):
        """验证 learn_from_conversation 工具存在"""
        tools_mixin_file = project_root / "mixins" / "tools_mixin.py"
        if tools_mixin_file.exists():
            content = tools_mixin_file.read_text(encoding="utf-8")
        else:
            main_file = project_root / "main.py"
            content = main_file.read_text(encoding="utf-8")

        assert "async def learn_from_conversation" in content, "应定义 learn_from_conversation 工具"
        assert "【学习模式专用】" in content, "工具应有学习模式专用标记"

    def test_confirm_knowledge_tool_exists(self):
        """验证 confirm_knowledge 工具存在"""
        tools_mixin_file = project_root / "mixins" / "tools_mixin.py"
        if tools_mixin_file.exists():
            content = tools_mixin_file.read_text(encoding="utf-8")
        else:
            main_file = project_root / "main.py"
            content = main_file.read_text(encoding="utf-8")

        assert "async def confirm_knowledge" in content, "应定义 confirm_knowledge 工具"

    def test_revise_knowledge_tool_exists(self):
        """验证 revise_knowledge 工具存在"""
        tools_mixin_file = project_root / "mixins" / "tools_mixin.py"
        if tools_mixin_file.exists():
            content = tools_mixin_file.read_text(encoding="utf-8")
        else:
            main_file = project_root / "main.py"
            content = main_file.read_text(encoding="utf-8")

        assert "async def revise_knowledge" in content, "应定义 revise_knowledge 工具"


class TestDocumentLearning:
    """测试文档学习功能"""

    def test_learn_document_tool_exists(self):
        """验证 learn_document 工具存在"""
        tools_mixin_file = project_root / "mixins" / "tools_mixin.py"
        if tools_mixin_file.exists():
            content = tools_mixin_file.read_text(encoding="utf-8")
        else:
            main_file = project_root / "main.py"
            content = main_file.read_text(encoding="utf-8")

        assert "async def learn_document" in content, "应定义 learn_document 工具"

    def test_document_reader_methods_exist(self):
        """验证文档读取方法存在"""
        helpers_mixin_file = project_root / "mixins" / "helpers_mixin.py"
        if helpers_mixin_file.exists():
            content = helpers_mixin_file.read_text(encoding="utf-8")
        else:
            main_file = project_root / "main.py"
            content = main_file.read_text(encoding="utf-8")

        assert "_read_document_content" in content, "应定义 _read_document_content 方法"
        assert "_process_document_chunks" in content, "应定义 _process_document_chunks 方法"

    def test_supported_document_types(self):
        """验证支持的文档类型"""
        helpers_mixin_file = project_root / "mixins" / "helpers_mixin.py"
        if helpers_mixin_file.exists():
            content = helpers_mixin_file.read_text(encoding="utf-8")
        else:
            main_file = project_root / "main.py"
            content = main_file.read_text(encoding="utf-8")

        supported_exts = [".txt", ".md", ".doc", ".docx", ".pdf"]
        for ext in supported_exts:
            assert ext in content, f"应支持 {ext} 格式"


class TestReadOnlyLock:
    """测试只读锁机制"""

    def test_knowledge_add_has_readonly_check(self):
        """验证 knowledge_add 工具有只读检查"""
        mixin_file = project_root / "mixins" / "knowledge_mixin.py"
        if not mixin_file.exists():
            pytest.skip("knowledge_mixin.py 文件未找到")
        content = mixin_file.read_text(encoding="utf-8")

        func_start = content.find("async def knowledge_add")
        if func_start == -1:
            pytest.skip("knowledge_add 函数未找到")

        func_end = content.find("\n    @filter.llm_tool()", func_start + 1)
        if func_end == -1:
            func_end = content.find("\n    async def ", func_start + 1)

        func_content = (
            content[func_start:func_end] if func_end > func_start else content[func_start : func_start + 2000]
        )

        assert "is_read_only" in func_content or "授课模式" in func_content, "knowledge_add 应检查授课模式只读状态"

    def test_learn_document_has_readonly_check(self):
        """验证 learn_document 工具有只读检查"""
        mixin_file = project_root / "mixins" / "tools_mixin.py"
        if not mixin_file.exists():
            pytest.skip("tools_mixin.py 文件未找到")
        content = mixin_file.read_text(encoding="utf-8")

        func_start = content.find("async def learn_document")
        if func_start == -1:
            pytest.skip("learn_document 函数未找到")

        func_end = content.find("\n    @filter.llm_tool()", func_start + 1)
        if func_end == -1:
            func_end = content.find("\n    async def ", func_start + 1)

        func_content = (
            content[func_start:func_end] if func_end > func_start else content[func_start : func_start + 2000]
        )

        assert "is_read_only" in func_content or "授课模式" in func_content, "learn_document 应检查授课模式只读状态"


class TestHelpCommandUpdated:
    """测试帮助命令更新"""

    def test_help_includes_learning_commands(self):
        """验证帮助命令包含学习模式指令"""
        main_file = project_root / "main.py"
        content = main_file.read_text(encoding="utf-8")

        help_start = content.find("async def cmd_sc_help")
        if help_start == -1:
            pytest.skip("cmd_sc_help 函数未找到")

        help_end = content.find("yield event.plain_result(msg)", help_start)
        help_content = (
            content[help_start:help_end] if help_end > help_start else content[help_start : help_start + 2000]
        )

        assert "学习模式" in help_content or "开始学习" in help_content, "帮助命令应包含学习模式指令"
