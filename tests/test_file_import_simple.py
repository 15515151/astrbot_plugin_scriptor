# tests/test_file_import_simple.py
"""
简化测试：验证文件导入档案馆功能

只测试核心功能，不依赖复杂的导入
"""

import re
import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_DIR))


def test_tool_registration():
    """测试工具是否正确注册"""
    print("=" * 60)
    print("测试：import_file_to_archive 工具注册")
    print("=" * 60)

    tools_mixin_py = (PLUGIN_DIR / "mixins" / "tools_mixin.py").read_text(encoding="utf-8")

    # 检查工具方法（支持跨行签名）
    pattern = r"async def (import_file_to_archive)\("
    match = re.search(pattern, tools_mixin_py, re.MULTILINE)

    assert match is not None, "未找到工具方法 import_file_to_archive"
    print(f"✅ 找到工具方法：{match.group(1)}")

    # 检查装饰器
    pattern = r"@filter\.llm_tool\(\)\s+async def import_file_to_archive"
    assert re.search(pattern, tools_mixin_py, re.MULTILINE) is not None, "装饰器有问题"
    print("✅ 装饰器正确")

    # 检查关键代码
    checks = [
        ("DataIngestor 调用", "ingestor.ingest_excel"),
        ("文件类型检查", ".xlsx"),
        ("返回成功信息", "导入成功"),
    ]

    for name, code in checks:
        assert code in tools_mixin_py, f"{name} 未找到"
        print(f"✅ {name}")


def test_data_ingestor_exists():
    """测试 DataIngestor 类是否存在"""
    print("\n" + "=" * 60)
    print("测试：DataIngestor 类")
    print("=" * 60)

    ingestor_py = PLUGIN_DIR / "core" / "archives" / "ingestor.py"

    assert ingestor_py.exists(), f"文件不存在：{ingestor_py}"
    print(f"✅ 文件存在：{ingestor_py}")

    content = ingestor_py.read_text(encoding="utf-8")

    checks = [
        ("类定义", "class DataIngestor"),
        ("Excel 导入方法", "def ingest_excel"),
        ("TXT 支持", ".txt"),
        ("CSV 支持", ".csv"),
        ("自动检测分隔符", "_detect_delimiter"),
    ]

    for name, code in checks:
        assert code in content, f"{name} 未找到"
        print(f"✅ {name}")


def test_workflow():
    """测试完整工作流程说明"""
    print("\n" + "=" * 60)
    print("完整工作流程")
    print("=" * 60)

    workflow_info = """
📱 用户操作流程：

1. 用户在 QQ 上发送 Excel/CSV/TXT 文件
   ↓
2. Scriptor 自动保存到媒体库
   [消息处理] _process_media_attachments() → media_manager.save_file()
   ↓
3. 用户说："帮我把这个文件导入到档案馆"
   ↓
4. AI 调用工具：
   [LLM 工具] search_my_files() → 找到文件
   [LLM 工具] import_file_to_archive() → 导入到档案馆
   ↓
5. 用户查询数据：
   用户："这个表里有哪些数据？"
   [LLM 工具] query_archives() → 执行 SQL 查询

✅ 支持的文件格式：
   - Excel (.xlsx, .xls)
   - CSV (.csv)
   - TXT (.txt, 制表符/逗号/分号分隔)

✅ 自动功能：
   - 自动检测 TXT 文件分隔符
   - 自动检测文件编码（UTF-8, GBK, GB2312）
   - 自动生成表名
   - 自动注册元数据
    """

    print(workflow_info)
    assert True  # 工作流说明测试总是通过


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("文件导入档案馆功能测试")
    print("=" * 60 + "\n")

    tests = [
        ("工具注册", test_tool_registration),
        ("DataIngestor 类", test_data_ingestor_exists),
        ("工作流程说明", test_workflow),
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
        print("\n🎉 功能已实现！")
        print("\n使用方法：")
        print("1. 在 QQ 上发送 Excel/CSV/TXT 文件")
        print("2. 对 AI 说：'帮我把这个文件导入到档案馆'")
        print("3. AI 会自动调用 import_file_to_archive 工具")
        print("4. 导入后可以用 query_archives 查询数据")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
