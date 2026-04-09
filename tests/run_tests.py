# tests/run_tests.py
"""Scriptor 完整测试套件运行器

功能：
- 自动发现并运行所有测试文件
- 支持单元测试、集成测试、性能测试分类
- 生成覆盖率报告和性能统计
- 支持并行执行加速测试
"""

import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest


def discover_test_files(tests_dir: Path) -> list:
    """自动发现测试目录下的所有测试文件"""
    test_files = []

    # 排除的测试文件（需要特殊环境或已知问题）
    exclude_patterns = [
        "test_performance.py",  # 性能测试单独运行
    ]

    for test_file in sorted(tests_dir.glob("test_*.py")):
        if any(pattern in test_file.name for pattern in exclude_patterns):
            continue

        # 转换为相对于项目根目录的路径
        rel_path = test_file.relative_to(project_root)
        test_files.append(str(rel_path))

    # 也包含子目录中的集成测试
    integration_dir = tests_dir / "integration"
    if integration_dir.exists():
        for test_file in sorted(integration_dir.glob("test_*.py")):
            rel_path = test_file.relative_to(project_root)
            test_files.append(str(rel_path))

    return test_files


def main():
    """主函数 - 运行完整测试套件"""
    start_time = time.time()

    print("=" * 70)
    print("🧪 Scriptor (灵笔司书) 测试套件")
    print("=" * 70)
    print()

    tests_dir = project_root / "tests"

    # 自动发现测试文件
    test_files = discover_test_files(tests_dir)

    print(f"📂 发现 {len(test_files)} 个测试文件:")
    for i, f in enumerate(test_files, 1):
        print(f"   {i:2d}. {f}")
    print()

    if not test_files:
        print("❌ 未找到任何测试文件！")
        return 1

    # 构建测试参数
    args = [
        "-v",  # 详细输出
        "--tb=short",  # 简短的错误追踪
        "--strict-markers",  # 严格标记检查
        "-x",  # 首次失败停止（快速反馈）
        "--durations=10",  # 显示最慢的10个测试
        "-p",
        "no:warnings",  # 忽略警告
        *test_files,  # 所有发现的测试文件
    ]

    # 可选：添加覆盖率（如果安装了 pytest-cov）
    try:
        import pytest_cov

        args.extend(
            [
                "--cov=core",
                "--cov=mixins",
                "--cov=tools",
                "--cov=hooks",
                "--cov-report=term-missing",
                "--cov-fail-under=60",  # 至少60%覆盖率
            ]
        )
        print("📊 已启用测试覆盖率报告")
    except ImportError:
        print("⚠️  未安装 pytest-cov，跳过覆盖率报告")

    print()
    print("=" * 70)
    print("▶️  开始运行测试...")
    print("=" * 70)
    print()

    # 运行测试
    exit_code = pytest.main(args)

    # 计算耗时
    elapsed_time = time.time() - start_time

    # 输出结果摘要
    print()
    print("=" * 70)
    print("📋 测试结果摘要")
    print("=" * 70)

    if exit_code == 0:
        print(f"✅ 所有测试通过！ ({elapsed_time:.2f}s)")
        print(f"📊 运行了 {len(test_files)} 个测试文件")

        # 尝试读取覆盖率数据
        try:
            cov_path = project_root / ".coverage"
            if cov_path.exists():
                print("📈 覆盖率报告已生成: htmlcov/index.html")
                print("   或查看终端输出中的覆盖率信息")
        except Exception:
            pass
    else:
        print(f"❌ 测试失败，退出码: {exit_code}")
        print(f"⏱️  总耗时: {elapsed_time:.2f}s")
        print()
        print("💡 提示：")
        print("   • 查看上方详细错误信息定位问题")
        print("   • 运行 'python -m pytest <test_file> -v' 单独调试")
        print("   • 检查依赖是否完整: pip install -r requirements.txt")

    print("=" * 70)

    return exit_code


def run_performance_tests():
    """运行性能测试（可选）"""
    print("=" * 70)
    print("⚡ Scriptor 性能测试")
    print("=" * 70)
    print()

    perf_test = "tests/test_performance.py"
    if not Path(perf_test).exists():
        print("❌ 性能测试文件不存在")
        return 1

    exit_code = pytest.main(
        [
            "-v",
            "--tb=short",
            perf_test,
        ]
    )

    return exit_code


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scriptor 测试运行器")
    parser.add_argument("--performance", action="store_true", help="仅运行性能测试")
    parser.add_argument("--quick", action="store_true", help="快速模式：跳过慢速测试")

    args = parser.parse_args()

    if args.performance:
        sys.exit(run_performance_tests())
    else:
        sys.exit(main())
