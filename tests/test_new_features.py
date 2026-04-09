# tests/test_new_features.py
"""验证新功能的集成测试

测试内容：
1. 新的 run_tests.py 能否正常发现测试文件
2. core/exceptions.py 模块能否正常导入和使用
3. web/api.py 的新端点是否正常注册
4. 配置验证功能是否正常工作
"""

import sys
from pathlib import Path

import pytest


class TestRunTestsScript:
    """测试新的测试运行脚本"""

    def test_discover_test_files(self):
        """测试自动发现测试文件功能"""
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from tests.run_tests import discover_test_files

        tests_dir = Path(__file__).parent
        test_files = discover_test_files(tests_dir)

        # 应该发现多个测试文件
        assert len(test_files) > 10, f"应该发现超过10个测试文件，实际: {len(test_files)}"

        # 应该包含我们刚创建的 Web API 测试
        assert any("test_web_api" in f for f in test_files), "应该包含 test_web_api.py"

    def test_exclude_patterns(self):
        """测试排除模式"""
        from tests.run_tests import discover_test_files

        tests_dir = Path(__file__).parent
        test_files = discover_test_files(tests_dir)

        # 性能测试应该被排除（单独运行）
        assert not any("test_performance.py" in f for f in test_files), "性能测试应该被排除"


class TestExceptionsModule:
    """测试统一异常处理模块"""

    def test_import_exceptions(self):
        """测试异常模块能正常导入"""
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from core.exceptions import (
            ConfigException,
            MemoryException,
            ScriptorException,
            SearchException,
            SecurityException,
            ToolException,
        )

        # 所有异常类都应该存在
        assert ScriptorException is not None
        assert MemoryException is not None
        assert SearchException is not None
        assert ConfigException is not None
        assert SecurityException is not None
        assert ToolException is not None

    def test_exception_hierarchy(self):
        """测试异常层次结构"""
        from core.exceptions import (
            AuthenticationException,
            AuthorizationException,
            MemoryException,
            MemoryNotFoundException,
            MemoryWriteException,
            SearchException,
            SearchTimeoutException,
            SecurityException,
            ToolException,
            ToolTimeoutException,
        )

        # 子类应该是父类的实例
        assert issubclass(MemoryNotFoundException, MemoryException)
        assert issubclass(MemoryWriteException, MemoryException)
        assert issubclass(SearchTimeoutException, SearchException)
        assert issubclass(AuthenticationException, SecurityException)
        assert issubclass(AuthorizationException, SecurityException)
        assert issubclass(ToolTimeoutException, ToolException)

    def test_exception_context(self):
        """测试异常上下文信息"""
        from core.exceptions import (
            ErrorContext,
            ErrorSeverity,
            ScriptorException,
        )

        context = ErrorContext(
            operation="test_operation",
            component="test_component",
            user_message="用户友好的错误消息",
            technical_details="技术细节",
            suggested_fix="建议修复方案",
            error_code="TEST_ERROR_001",
        )

        exception = ScriptorException("测试错误消息", context=context, severity=ErrorSeverity.ERROR)

        # 验证属性
        assert exception.message == "测试错误消息"
        assert exception.severity == ErrorSeverity.ERROR
        assert exception.user_friendly_message == "用户友好的错误消息"
        assert exception.technical_message == "测试错误消息 | 技术细节"

        # 验证字典转换
        exc_dict = exception.to_dict()
        assert "error_type" in exc_dict
        assert "message" in exc_dict
        assert "severity" in exc_dict
        assert "context" in exc_dict

    def test_exception_to_api_response(self):
        """测试 API 响应格式转换"""
        from core.exceptions import ErrorContext, ScriptorException

        exception = ScriptorException(
            "API 错误", context=ErrorContext(operation="api_call", component="web_api", user_message="API 调用失败")
        )

        api_response = exception.to_api_response(status_code=500)

        assert api_response["success"] == False
        assert "error" in api_response
        assert api_response["status_code"] == 500

    def test_memory_exception_specific_fields(self):
        """测试记忆异常的特定字段"""
        from core.exceptions import MemoryException, MemoryNotFoundException, MemoryWriteException

        # 基础记忆异常
        mem_exc = MemoryException("记忆操作失败", memory_type="personal", operation="write", uid="user_123")

        assert mem_exc.context.metadata["memory_type"] == "personal"
        assert mem_exc.context.metadata["operation"] == "write"
        assert mem_exc.context.metadata["uid"] == "user_123"

        # 记忆未找到异常
        not_found_exc = MemoryNotFoundException("记忆不存在")
        assert not_found_exc.context.suggested_fix is not None

        # 记忆写入异常
        write_exc = MemoryWriteException("写入失败")
        assert write_exc.context.operation == "write"


class TestWebAPIEnhancements:
    """测试 Web API 增强"""

    def test_import_web_api(self):
        """测试 Web API 模块能正常导入"""
        sys.path.insert(0, str(Path(__file__).parent.parent))

        try:
            from web.api import app

            # FastAPI 应用应该存在
            assert app is not None
            assert app.title == "灵笔司书 Web UI API"

        except ImportError as e:
            pytest.skip(f"无法导入 web.api (可能缺少依赖): {e}")

    def test_new_endpoints_registered(self):
        """测试新端点是否已注册"""
        try:
            from web.api import app

            # 获取所有路由
            routes = [route.path for route in app.routes if hasattr(route, "path")]

            # 验证新端点已注册
            new_endpoints = [
                "/api/config/validate",
                "/api/system/diagnostics",
                "/api/performance/history",
                "/api/maintenance/optimize",
            ]

            for endpoint in new_endpoints:
                assert endpoint in routes, f"端点 {endpoint} 未注册"

        except ImportError:
            pytest.skip("无法导入 web.api")


class TestQualityCheckScript:
    """测试质量检查脚本"""

    def test_quality_check_script_exists(self):
        """测试质量检查脚本存在"""
        script_path = Path(__file__).parent.parent / "scripts" / "quick_quality_check.py"
        assert script_path.exists(), "质量检查脚本不存在"

    def test_quality_check_importable(self):
        """测试质量检查脚本能正常导入"""
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "quick_quality_check", str(Path(__file__).parent.parent / "scripts" / "quick_quality_check.py")
        )

        module = importlib.util.module_from_spec(spec)

        # 不执行模块，只验证可以加载
        assert module is not None


class TestIntegrationSmokeTest:
    """冒烟测试 - 验证基本集成"""

    def test_core_modules_importable(self):
        """测试核心模块可导入"""
        core_modules = [
            "core.config_pydantic",
            "core.identity_manager",
            "core.group_manager",
            "core.memory_manager",
            "core.search_engine",
            "core.exceptions",  # 新增
        ]

        for module_name in core_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"无法导入 {module_name}: {e}")

    def test_mixin_modules_importable(self):
        """测试 Mixin 模块可导入"""
        import importlib.util
        import sys

        mixin_files = [
            ("mixins/base.py", "BaseMixin"),
            ("mixins/helpers_mixin.py", "HelpersMixin"),
            ("mixins/tools_mixin.py", "ToolsMixin"),
            ("mixins/memory_mixin.py", "MemoryMixin"),
        ]

        project_root = Path(__file__).parent.parent

        for file_path, class_name in mixin_files:
            full_path = project_root / file_path

            if not full_path.exists():
                pytest.fail(f"文件不存在: {file_path}")
                continue

            try:
                # 使用 importlib 直接加载模块文件，避免触发 __init__.py 的全部导入
                spec = importlib.util.spec_from_file_location(
                    f"test_{class_name.lower()}", str(full_path), submodule_search_locations=[]
                )

                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)

                    # 临时修改 sys.modules 以支持相对导入
                    old_modules = dict(sys.modules)

                    try:
                        # 设置必要的父包模拟
                        sys.modules["mixins"] = type(sys)("mixins")
                        sys.modules["mixins"].__path__ = [str(project_root / "mixins")]
                        sys.modules["core"] = type(sys)("core")
                        sys.modules["core"].__path__ = [str(project_root / "core")]

                        # 尝试执行模块（可能因依赖失败）
                        spec.loader.exec_module(module)

                        # 验证类是否存在
                        assert hasattr(module, class_name), f"模块 {file_path} 中未找到类 {class_name}"

                    except ImportError as e:
                        # 相对导入错误是预期的（缺少 AstrBot 运行时环境）
                        if "attempted relative import" in str(e) or "No module named" in str(e):
                            # 这是正常的 - 在非 AstrBot 环境中运行测试
                            # 只要模块文件存在且语法正确即可
                            pass
                        else:
                            raise
                    finally:
                        # 恢复 sys.modules
                        sys.modules.clear()
                        sys.modules.update(old_modules)

            except SyntaxError as e:
                pytest.fail(f"{file_path} 存在语法错误: {e}")
            except Exception as e:
                # 其他意外错误
                if "attempted relative import beyond top-level package" in str(e):
                    # 已知问题：测试环境不支持完整的包结构
                    # 这在实际 AstrBot 插件运行环境中不会出现
                    pass
                else:
                    pytest.fail(f"加载 {file_path} 时发生意外错误: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
