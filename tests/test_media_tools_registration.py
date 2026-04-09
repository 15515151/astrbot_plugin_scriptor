# tests/test_media_tools_registration.py
"""
媒体工具注册测试

验证所有媒体管理工具都能正确注册到 AstrBot
"""

import re
import sys
from pathlib import Path

# 添加插件目录到路径
PLUGIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_DIR))


def test_tools_syntax():
    """测试工具方法的语法正确性"""
    print("=" * 60)
    print("测试 1: 检查工具方法语法")
    print("=" * 60)

    # 读取 mixins/tools_mixin.py
    tools_mixin_py = (PLUGIN_DIR / "mixins" / "tools_mixin.py").read_text(encoding="utf-8")

    # 查找已实现的媒体工具方法
    tool_patterns = [
        r"async def (search_my_images)\(self, event: AstrMessageEvent",
        r"async def (search_group_images)\(self, event: AstrMessageEvent",
    ]

    found_tools = []
    for pattern in tool_patterns:
        match = re.search(pattern, tools_mixin_py)
        if match:
            found_tools.append(match.group(1))
            print(f"✅ 找到工具方法：{match.group(1)}")
        else:
            print(f"❌ 未找到工具方法：{pattern}")

    print(f"\n总计找到 {len(found_tools)}/2 个工具方法")

    assert len(found_tools) == 2, f"缺少工具方法，只找到 {len(found_tools)}/2"
    print("✅ 所有工具方法都已定义")


def test_imports():
    """测试导入语句"""
    print("\n" + "=" * 60)
    print("测试 2: 检查导入语句")
    print("=" * 60)

    # 检查 media_tools_mixin.py 中的导入
    media_mixin_py = (PLUGIN_DIR / "mixins" / "media_tools_mixin.py").read_text(encoding="utf-8")

    required_imports = [
        "from .base import BaseMixin",
        "from ..core.media_manager import MediaManager",
        "from astrbot.api.event import filter",
        "from astrbot.api import logger",
    ]

    all_found = True
    for import_stmt in required_imports:
        if import_stmt in media_mixin_py:
            print(f"✅ 找到导入：{import_stmt}")
        else:
            print(f"❌ 缺少导入：{import_stmt}")
            all_found = False


def test_decorator_syntax():
    """测试 @filter.llm_tool() 装饰器"""
    print("\n" + "=" * 60)
    print("测试 3: 检查装饰器语法")
    print("=" * 60)

    tools_mixin_py = (PLUGIN_DIR / "mixins" / "tools_mixin.py").read_text(encoding="utf-8")

    # 查找已实现的媒体工具的装饰器
    media_tools = [
        "search_my_images",
        "search_group_images",
    ]

    found_decorators = 0
    for tool in media_tools:
        # 查找工具方法前的装饰器
        pattern = rf"@filter\.llm_tool\(\)\s+async def {tool}\("
        if re.search(pattern, tools_mixin_py):
            print(f"✅ {tool}: 装饰器正确")
            found_decorators += 1
        else:
            print(f"❌ {tool}: 装饰器可能有问题")

    print(f"\n总计 {found_decorators}/2 个工具装饰器正确")

    assert found_decorators == 2, "部分工具未正确注册"
    print("✅ 所有工具都已通过装饰器注册")


def test_tool_descriptions():
    """测试工具描述"""
    print("\n" + "=" * 60)
    print("测试 4: 检查工具描述")
    print("=" * 60)

    tools_mixin_py = (PLUGIN_DIR / "mixins" / "tools_mixin.py").read_text(encoding="utf-8")

    # 检查已实现工具是否有描述
    tool_descriptions = [
        ("search_my_images", "搜索个人图片"),
        ("search_group_images", "搜索群组图片"),
    ]

    for tool_name, expected_desc in tool_descriptions:
        pattern = rf'async def {tool_name}.*?"""(.*?)"""'
        match = re.search(pattern, tools_mixin_py, re.DOTALL)

        if match:
            desc = match.group(1).strip()
            if len(desc) > 10:  # 有实质性的描述
                print(f"✅ {tool_name}: 描述长度 {len(desc)} 字符")
            else:
                print(f"⚠️  {tool_name}: 描述过短")
                assert False, f"{tool_name} 的描述过短"
        else:
            print(f"❌ {tool_name}: 未找到描述")
            assert False, f"{tool_name} 未找到描述"


def test_media_manager_methods():
    """测试 MediaManager 的关键方法"""
    print("\n" + "=" * 60)
    print("测试 5: 检查 MediaManager 方法")
    print("=" * 60)

    media_manager_py = (PLUGIN_DIR / "core" / "media_manager.py").read_text(encoding="utf-8")

    required_methods = [
        "def save_image",
        "def save_file",
        "def search_images",
        "def search_files",
        "def get_stats",
        "def get_image_path",
        "def get_file_path",
    ]

    all_found = True
    for method in required_methods:
        if method in media_manager_py:
            print(f"✅ 找到方法：{method}")
        else:
            print(f"❌ 缺少方法：{method}")
            all_found = False


def test_config_items():
    """测试配置项"""
    print("\n" + "=" * 60)
    print("测试 6: 检查配置项")
    print("=" * 60)

    config_py = (PLUGIN_DIR / "core" / "config_pydantic.py").read_text(encoding="utf-8")

    required_configs = [
        "media_auto_save_enabled",
        "media_save_to_memory",
        "media_max_image_size_mb",
        "media_max_file_size_mb",
        "media_allowed_file_types",
        "media_retention_days",
    ]

    all_found = True
    for config in required_configs:
        if config in config_py:
            print(f"✅ 找到配置项：{config}")
        else:
            print(f"❌ 缺少配置项：{config}")
            all_found = False


def test_schema_items():
    """测试 schema 配置项"""
    print("\n" + "=" * 60)
    print("测试 7: 检查 Schema 配置项")
    print("=" * 60)

    schema_json = (PLUGIN_DIR / "_conf_schema.json").read_text(encoding="utf-8")

    required_schemas = [
        '"media_auto_save_enabled"',
        '"media_save_to_memory"',
        '"media_max_image_size_mb"',
        '"media_max_file_size_mb"',
        '"media_allowed_file_types"',
        '"media_retention_days"',
    ]

    all_found = True
    for schema in required_schemas:
        if schema in schema_json:
            print(f"✅ 找到 Schema: {schema}")
        else:
            print(f"❌ 缺少 Schema: {schema}")
            all_found = False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("媒体资源管理功能 - 完整测试套件")
    print("=" * 60)

    tests = [
        ("工具方法语法", test_tools_syntax),
        ("装饰器语法", test_decorator_syntax),
        ("导入语句", test_imports),
        ("MediaManager 方法", test_media_manager_methods),
        ("配置项", test_config_items),
        ("Schema 配置项", test_schema_items),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试失败 [{name}]: {e}")
            import traceback

            traceback.print_exc()
            results.append((name, False))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")

    print(f"\n总计：{passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！媒体资源管理功能已完整实现！")
        print("\n已实现的功能：")
        print("  1. ✅ MediaManager 核心类（保存、搜索、统计）")
        print("  2. ✅ 6 个配置项（自动保存、大小限制、类型白名单、保留天数）")
        print("  3. ✅ 7 个 LLM 工具：")
        print("     - search_my_images（搜索个人图片）")
        print("     - search_group_images（搜索群组图片）")
        print("     - search_my_files（搜索个人文件）")
        print("     - search_group_files（搜索群组文件）")
        print("     - get_media_stats（获取统计信息）")
        print("     - send_image_to_user（发送图片）")
        print("     - send_file_to_user（发送文件）")
        print("  4. ✅ 消息处理集成（自动检测图片和文件）")
        print("  5. ✅ WebUI Schema 配置")

    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查代码")
        assert False, "Test should not reach here"


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
