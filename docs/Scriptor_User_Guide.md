# Scriptor 用户指南

欢迎使用 Scriptor (灵笔司书)！本指南将帮助你快速上手并充分利用 Scriptor 的强大功能。

---

## 📖 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [基本使用](#基本使用)
4. [配置说明](#配置说明)
5. [高级功能](#高级功能)
6. [Web UI 使用](#web-ui-使用)
7. [常见问题](#常见问题)

---

## 🚀 快速开始

### 安装

#### 方式 1：从 AstrBot 插件商店安装（推荐）
在 AstrBot 管理面板中搜索 "灵笔司书" 并安装。

#### 方式 2：从 PyPI 安装
```bash
pip install astrbot-plugin-scriptor
```

#### 方式 3：从源码安装
```bash
cd AstrBot/data/plugins
git clone https://github.com/ysf7762-dev/astrbot_plugin_scriptor.git
cd astrbot_plugin_scriptor
pip install -r requirements.txt

# 构建 Web UI（可选）
cd web
npm install
npm run build
```

### 配置

在 AstrBot 配置文件中添加 Scriptor 配置：

```yaml
scriptor:
  # 基本配置
  debug_mode: false
  log_level: INFO
  
  # 记忆管理
  memory_compact_threshold: 8000
  daily_note_enabled: true
  
  # Embedding 配置
  embedding_enabled: true
  embedding_provider: "local"
  embedding_model: "AI-ModelScope/bge-small-zh-v1.5"
  
  # 跨群功能
  cross_group_enabled: false
```

### 验证安装

发送以下命令：
```
/verify_memory
```

如果返回成功信息，说明安装成功。

---

## 💡 核心概念

### 文件即记忆

Scriptor 使用 Markdown 文件存储所有记忆，而非传统数据库。

**优势**：
- ✅ 透明：可以直接查看和编辑
- ✅ 可控：完全属于你，可自由迁移
- ✅ Git 友好：支持版本控制
- ✅ 可审计：所有变更可追踪

### 记忆目录结构

```
data/
├── profiles/          # 个人记忆
│   └── {uid}/
│       ├── PROFILE.md      # 用户画像
│       ├── MEMORY.md       # 长期记忆
│       ├── SOUL.md         # 灵魂设定（可选）
│       ├── SOP.md          # 标准流程（可选）
│       ├── memory/         # 日记目录
│       │   └── 2026-03-30.md
│       └── learning/       # 学习模式（临时）
│
└── groups/            # 群体记忆
    └── {group_id}/
        ├── PROFILE.md
        ├── MEMORY.md
        └── ...
```

### 三档衰减策略

| 档位 | 名称 | 说明 | 衰减周期 |
|------|------|------|---------|
| **T0** | 易逝档 | 临时信息，快速衰减 | 7 天 |
| **T1** | 待证档 | 需要验证的信息 | 30 天 |
| **T2** | 永存档 | 核心知识，永不衰减 | 永久 |

### 身份聚合

Scriptor 支持将不同平台的身份绑定到同一个逻辑 UID。

**示例**：
- QQ: 123456 → UID: user_001
- 微信：wx_789 → UID: user_001

这样无论在哪个平台，都能保持一致的记忆体验。

---

## 📝 基本使用

### 记忆命令

#### 查看记忆
```
/查看记忆
```
显示当前用户的记忆摘要。

#### 搜索记忆
```
/搜索记忆 关键词
```
搜索包含关键词的记忆。

#### 添加记忆
```
/添加记忆 用户喜欢吃苹果
```
手动添加一条记忆。

#### 删除记忆
```
/删除记忆 [记忆 ID]
```
删除指定记忆。

#### 导出记忆
```
/导出记忆
```
导出所有记忆为 Markdown 文件。

### 调试命令

#### 查看调试信息
```
/debug_memory
```
显示详细的调试信息。

#### 强制压缩记忆
```
/compact_memory
```
手动触发记忆压缩。

#### 查看统计信息
```
/memory_stats
```
显示记忆统计信息。

---

## ⚙️ 配置说明

### 基本配置

```yaml
scriptor:
  # 调试模式
  debug_mode: false          # 启用详细日志
  log_level: INFO            # 日志级别：DEBUG, INFO, WARNING, ERROR
  
  # 记忆管理
  memory_compact_threshold: 8000  # 记忆压缩阈值（字符数）
  memory_max_items: 1000         # 最大记忆条数
  daily_note_enabled: true       # 启用日记功能
```

### Embedding 配置

```yaml
scriptor:
  embedding_enabled: true
  embedding_provider: "local"  # local, openai, ollama
  embedding_api_base: "http://localhost:11434/v1"
  embedding_api_key: "ollama"
  embedding_model: "AI-ModelScope/bge-small-zh-v1.5"
  search_top_k: 5              # 搜索结果数量
```

### 跨群配置

```yaml
scriptor:
  cross_group_enabled: false
  cross_group_priority: 5      # 跨群信息优先级
```

### 安全配置

```yaml
scriptor:
  encryption_enabled: false    # 启用记忆加密
  encryption_key: ""           # AES-256 密钥
  admin_uids: []               # 管理员 UID 列表
```

### 高级配置

```yaml
scriptor:
  # Token 控制
  enable_token_control: true
  max_system_prompt_tokens: 4000
  
  # 检索指导
  retrieval_guidance_priority: 5
  
  # 夜间整理
  nightly_graph_consolidation_enabled: true
  nightly_graph_consolidation_hour: 3  # 凌晨 3 点
```

---

## 🎯 高级功能

### 学习模式

学习模式允许你向 Scriptor 传授知识，这些知识会存储在待确认区域。

**启用学习模式**：
```
/learning_mode on
```

**添加待确认知识**：
```
学习：地球是圆的
```

**确认知识**：
```
/confirm_learning [知识 ID]
```

**拒绝知识**：
```
/reject_learning [知识 ID]
```

详见 [学习模式指南](./LEARNING_MODE_GUIDE.md)。

### 司书档案馆

支持大规模结构化数据查询。

**导入数据**：
```
/import_archive data.xlsx
```

**查询档案**：
```
/query_archive 姓名=张三
```

### 知识图谱

自动提取实体和关系。

**查看知识图谱**：
```
/view_knowledge_graph
```

**手动提取**：
```
/extract_knowledge
```

### 主动式记忆管理

#### 睡眠巩固
新会话开始时自动整理和优化记忆。

#### 画像精炼
周期性使用 LLM 精炼用户画像。

#### 经验提取
从对话中提取通用经验法则。

---

## 🖥️ Web UI 使用

### 访问 Web UI

在浏览器中打开：
```
http://localhost:6185/scriptor
```

### 功能模块

1. **概览** - 系统状态和统计信息
2. **记忆管理** - 查看、编辑、删除记忆
3. **档案馆** - 导入和查询结构化数据
4. **知识库** - 知识图谱可视化
5. **配置** - 修改插件配置
6. **性能** - 性能监控
7. **维护** - 备份、清理等维护操作
8. **调试** - 调试信息和日志

### 认证

首次访问需要设置管理员密码。

---

## ❓ 常见问题

### Q1: 记忆文件在哪里？
**A**: 在 `data/profiles/{uid}/` 和 `data/groups/{group_id}/` 目录下。

### Q2: 如何备份记忆？
**A**: 直接复制整个 `profiles/` 和 `groups/` 目录即可。

### Q3: 记忆文件可以手动编辑吗？
**A**: 可以！Markdown 格式就是为方便你直接编辑。

### Q4: 如何迁移到新设备？
**A**: 复制整个插件目录，或只复制 `profiles/` 和 `groups/` 目录。

### Q5: 学习模式的知识存储在哪里？
**A**: 在 `{uid}/learning/` 目录下，确认后才会移动到正式记忆。

### Q6: 如何禁用某个功能？
**A**: 在配置文件中将对应功能设置为 `false`。

### Q7: 支持哪些 Embedding 提供商？
**A**: 支持本地模型、OpenAI、Ollama 等。详见配置说明。

### Q8: 记忆加密安全吗？
**A**: 使用 AES-256 加密，安全性很高。但请妥善保管密钥。

### Q9: 如何查看日志？
**A**: 日志在 `data/logs/astrbot.log`，可以使用 `/debug_memory` 查看调试信息。

### Q10: 遇到问题怎么办？
**A**: 
1. 查看日志
2. 使用 `/debug_memory` 命令
3. 查阅文档
4. 在 GitHub 提交 Issue

---

## 📚 相关文档

- [学习模式指南](./LEARNING_MODE_GUIDE.md) - 学习模式和授课模式详解
- [系统设计哲学](./Scriptor_System_Design_Philosophy.md) - 设计理念
- [API 参考](./Scriptor_API_Reference.md) - 开发者 API
- [构建指南](../BUILD.md) - 如何构建和发布

---

## 🆘 获取帮助

1. 查阅本文档
2. 使用 `/debug_memory` 命令
3. 检查 AstrBot 日志
4. 在 GitHub 提交 [Issue](https://github.com/ysf7762-dev/astrbot_plugin_scriptor/issues)

---

## 🎉 开始使用

现在你已经掌握了 Scriptor 的基本使用方法，开始享受智能化的记忆管理吧！

如有任何问题，请随时查阅文档或寻求社区帮助。

---

*最后更新：2026-03-30*
