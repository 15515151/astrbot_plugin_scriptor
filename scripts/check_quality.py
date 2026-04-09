# 代码质量检查脚本

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """运行命令并返回结果"""
    print(f"\n{'=' * 60}")
    print(f"运行: {description}")
    print(f"{'=' * 60}")
    print(f"命令: {cmd}")
    print()

    try:
        result = subprocess.run(
            cmd, shell=True, cwd=Path(__file__).parent.parent, capture_output=True, text=True, encoding="utf-8"
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"错误: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Scriptor 代码质量检查")
    print("=" * 60)

    checks = [
        ("ruff check .", "Ruff 代码检查"),
        ("black --check .", "Black 代码格式检查"),
        ("isort --check .", "isort 导入排序检查"),
        ("flake8 .", "Flake8 代码检查"),
        ("mypy core/ mixins/ tools/ hooks/", "Mypy 类型检查"),
    ]

    all_passed = True
    for cmd, desc in checks:
        if not run_command(cmd, desc):
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有代码质量检查通过！")
    else:
        print("❌ 部分代码质量检查失败")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
