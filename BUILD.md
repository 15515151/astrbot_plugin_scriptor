# Scriptor 构建指南

本文档介绍如何构建 Scriptor 插件及其 Web UI。

## 📦 构建方式

### 方式一：本地开发构建（推荐）

适用于开发和测试，不构建 Web UI。

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 安装构建工具
pip install build hatchling

# 3. 构建 Python 包（不包含 Web UI）
python -m build
```

**注意**：此方式构建的包**不包含** Web UI 前端，用户需要手动构建。

### 方式二：完整构建（包含 Web UI）

适用于发布，会自动构建 Web UI 并打包。

```bash
# 1. 确保已安装 Node.js (v20+) 和 npm
node --version
npm --version

# 2. 设置环境变量并构建
# Windows PowerShell:
$env:ASTRBOT_BUILD_WEB="1"
python -m build

# Windows CMD:
set ASTRBOT_BUILD_WEB=1
python -m build

# Linux/macOS:
ASTRBOT_BUILD_WEB=1 python -m build
```

构建产物位于 `dist/` 目录：
- `astrbot_plugin_scriptor-*.whl` - Wheel 包
- `astrbot_plugin_scriptor-*.tar.gz` - 源码包

### 方式三：CI/CD 自动构建

GitHub Actions 会在以下情况自动构建：
- 推送标签（如 `v1.0.0`）时自动发布到 PyPI 和 GitHub Releases
- 推送代码时自动运行测试和 lint

## 🎯 构建流程说明

### 完整构建流程（ASTRBOT_BUILD_WEB=1）

1. **检查 Node.js 环境**
   - 如果 `web/node_modules` 不存在，自动运行 `npm install`

2. **构建 Web UI**
   - 运行 `npm run build`
   - 生成 `web/dist/` 目录

3. **构建 Python 包**
   - 使用 Hatchling 构建
   - 自动包含 `web/dist/` 到包中

4. **生成发布文件**
   - Wheel 包（.whl）
   - 源码包（.tar.gz）

## 📋 手动构建 Web UI（可选）

如果只想单独构建 Web UI：

```bash
cd web
npm install
npm run build
```

构建产物位于 `web/dist/` 目录。

## 🔧 开发模式

开发时无需每次构建，可以：

### Python 开发
```bash
# 可编辑安装
pip install -e .
```

### Web UI 开发
```bash
cd web
npm run dev
```

这会启动 Vite 开发服务器，支持热重载。

## 📊 构建产物对比

| 构建方式 | Web UI | 适用场景 |
|---------|--------|---------|
| 方式一（默认） | ❌ 不包含 | 开发、测试 |
| 方式二（完整） | ✅ 包含 | 发布、分发 |
| 方式三（CI/CD） | ✅ 包含 | 自动发布 |

## ⚠️ 注意事项

1. **Node.js 版本要求**：v20 或更高
2. **npm 依赖缓存**：首次构建较慢，后续会使用缓存
3. **构建产物大小**：包含 Web UI 后约 5-10 MB
4. **环境变量**：`ASTRBOT_BUILD_WEB=1` 是触发 Web UI 构建的关键

## 🚀 发布流程

1. **更新版本号**
   - 修改 `pyproject.toml` 中的 `version`
   - 修改 `metadata.yaml` 中的 `version`

2. **打标签**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. **等待 CI/CD**
   - GitHub Actions 自动构建
   - 自动发布到 PyPI
   - 自动创建 GitHub Release

## 📝 本地测试安装

构建完成后，可以本地测试安装：

```bash
# 安装构建的包
pip install dist/astrbot_plugin_scriptor-*.whl

# 或可编辑安装（开发用）
pip install -e .
```

## 🎨 构建钩子说明

`scripts/build_hook.py` 是自定义构建钩子，负责：
- 检测 `ASTRBOT_BUILD_WEB` 环境变量
- 自动安装 Node 依赖
- 构建 Web UI
- 验证构建产物

---

*最后更新：2026-03-30*
