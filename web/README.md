# 灵笔司书 Web UI

基于 Vue 3 + Vuetify 的现代化前端界面。

## 前置要求

- Node.js >= 18.0.0
- npm >= 9.0.0

## 快速开始

```bash
# 1. 进入前端目录
cd web-vue

# 2. 安装依赖
npm install

# 3. 启动开发服务器 (端口 19111)
npm run dev

# 4. 构建生产版本
npm run build
```

## 开发模式

开发模式下，Vite 会启动一个开发服务器，并自动代理 `/api` 请求到后端 (端口 18111)。

```bash
npm run dev
# 访问 http://localhost:19111
```

## 生产构建

构建后的静态文件会输出到 `dist/` 目录，由 FastAPI 后端提供服务。

```bash
npm run build
# 构建产物: dist/
```

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **Vuetify 3** - Material Design 组件库
- **TypeScript** - 类型安全
- **Vite** - 下一代前端构建工具
- **Pinia** - Vue 状态管理
- **Vue Router** - 官方路由
- **Axios** - HTTP 客户端
- **md-editor-v3** - Markdown 编辑器

## 项目结构

```
web-vue/
├── public/              # 公共静态资源
├── src/
│   ├── assets/          # 静态资源
│   │   └── styles/      # 样式文件
│   ├── components/      # Vue 组件
│   │   ├── common/      # 通用组件
│   │   ├── layout/      # 布局组件
│   │   └── scriptor/    # 业务组件
│   ├── composables/     # 组合式函数
│   ├── plugins/         # 插件配置
│   ├── router/          # 路由配置
│   ├── stores/          # Pinia 状态管理
│   ├── theme/           # 主题配置
│   ├── types/           # TypeScript 类型定义
│   ├── views/           # 页面视图
│   ├── App.vue          # 根组件
│   └── main.ts          # 入口文件
├── index.html           # HTML 模板
├── package.json         # 项目配置
├── tsconfig.json        # TypeScript 配置
└── vite.config.ts       # Vite 配置
```

## 主题

默认使用深色科技主题，支持浅色/深色模式切换。

### 颜色方案

**深色模式 (默认)**
- Primary: `#0A84FF` (科技蓝)
- Secondary: `#5E5CE6` (紫蓝)
- Accent: `#00D4AA` (青绿)
- Background: `#0A0A1A` (深空蓝黑)
- Surface: `#141428` (卡片背景)

**浅色模式**
- Primary: `#007AFF` (苹果蓝)
- Secondary: `#5856D6` (紫色)
- Background: `#F5F5F7` (浅灰)
- Surface: `#FFFFFF` (纯白卡片)

## 页面列表

| 路由 | 页面 | 功能 |
|------|------|------|
| `/login` | 登录页 | API 密钥登录 |
| `/` | 系统概览 | 系统状态、统计信息 |
| `/memory` | 记忆管理 | 用户/群聊记忆文件管理 |
| `/archives` | 档案馆 | 结构化数据导入管理 |
| `/knowledge` | 知识库 | 知识条目管理 |
| `/config` | 配置中心 | 系统配置管理 |
| `/performance` | 性能面板 | 性能监控 |
| `/maintenance` | 维护工具 | 备份、清理 |
| `/debug` | 调试工具 | API 测试、日志查看 |

## API 集成

前端通过 `/api` 前缀访问后端 API：

- 开发模式: Vite proxy 自动代理到 `http://127.0.0.1:18111`
- 生产模式: FastAPI 直接提供 API 服务

所有需要鉴权的 API 都需要在请求头中携带 `X-API-Key`。
