"""
自定义 Hatchling 构建钩子。

用于在构建 Python 包时自动构建 Web UI 前端。

使用方法:
    ASTRBOT_BUILD_WEB=1 uv build
    或
    python -m build

当 ASTRBOT_BUILD_WEB=1 环境变量设置时，会:
1. 在 web/ 目录中运行 npm install
2. 运行 npm run build
3. 将构建产物 web/dist/ 复制到包中

这样可以确保用户安装后无需手动构建前端即可使用 Web UI。
"""

import os
import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:
        # 仅在明确请求时运行（CI/CD 或发布构建）
        # 开发模式下不会触发 npm 构建
        if os.environ.get("ASTRBOT_BUILD_WEB", "").strip() != "1":
            print("[build_hook] ASTRBOT_BUILD_WEB 未设置，跳过 Web UI 构建")
            print("[build_hook] 提示：如需构建 Web UI，请使用：ASTRBOT_BUILD_WEB=1 uv build")
            return

        root = Path(self.root)
        web_src = root / "web"
        dist_src = web_src / "dist"
        dist_target = root / "web" / "dist"

        # 检查 web 目录是否存在
        if not web_src.exists():
            print("[build_hook] 'web/' 目录不存在 - 跳过 Web UI 构建", file=sys.stderr)
            return

        # ── 如果 node_modules 不存在，先安装依赖 ──────────────────────────────
        if not (web_src / "node_modules").exists():
            print("[build_hook] 正在安装 Web UI Node 依赖...")
            try:
                subprocess.run(["npm", "install"], cwd=web_src, check=True, capture_output=True, text=True)
                print("[build_hook] Node 依赖安装完成")
            except subprocess.CalledProcessError as e:
                print(f"[build_hook] Node 依赖安装失败：{e}", file=sys.stderr)
                print(f"[build_hook] stderr: {e.stderr}", file=sys.stderr)
                return
            except FileNotFoundError:
                print("[build_hook] 未找到 npm，请确保已安装 Node.js", file=sys.stderr)
                return

        # ── 构建 Vue/Vite 前端 ─────────────────────────────────────────────────
        print("[build_hook] 正在构建 Web UI (npm run build)...")
        try:
            result = subprocess.run(["npm", "run", "build"], cwd=web_src, check=True, capture_output=True, text=True)
            print("[build_hook] Web UI 构建完成")
            if result.stdout:
                print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"[build_hook] Web UI 构建失败：{e}", file=sys.stderr)
            print(f"[build_hook] stderr: {e.stderr}", file=sys.stderr)
            return

        # ── 验证构建产物 ──────────────────────────────────────────────────────
        if not dist_src.exists():
            print("[build_hook] web/dist 目录在构建后不存在 - 构建可能失败", file=sys.stderr)
            return

        # ── 复制构建产物到包目录（如果需要） ────────────────────────────────────
        # 注意：由于我们在 pyproject.toml 中已经包含了 web/dist/**/*
        # 这里不需要额外复制，Hatchling 会自动包含
        print(f"[build_hook] Web UI 构建产物已就绪：{dist_src}")
        print(f"[build_hook] 文件大小：{self._get_dir_size(dist_src):.2f} MB")

    def _get_dir_size(self, path: Path) -> float:
        """计算目录大小（MB）"""
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
        except (OSError, PermissionError):
            pass
        return total / (1024 * 1024)
