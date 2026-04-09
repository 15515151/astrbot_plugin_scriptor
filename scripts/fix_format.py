# 自动格式化代码脚本

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
    print("Scriptor 代码自动格式化")
    print("=" * 60)

    fixes = [
        ("isort .", "isort 导入排序"),
        ("black .", "Black 代码格式化"),
        ("ruff check --fix .", "Ruff 自动修复"),
    ]

    all_passed = True
    for cmd, desc in fixes:
        if not run_command(cmd, desc):
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有代码格式化完成！")
    else:
        print("❌ 部分格式化操作失败")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
