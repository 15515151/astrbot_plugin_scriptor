# Scriptor 文档索引

欢迎使用 Scriptor (灵笔司书)！这是一个基于 Markdown 的长期记忆引擎，旨在为你提供个性化、可控制、透明的记忆系统。

---

## 🚀 快速开始

- **[README](../README.md)** - 项目简介和快速开始（必读）
- **[Scriptor 用户指南](./Scriptor_User_Guide.md)** - 完整的使用指南
- **[构建指南](../BUILD.md)** - 如何构建和发布

---

## 📚 核心文档

### 用户文档

| 文档 | 说明 | 适用人群 |
|------|------|---------|
| [用户指南](./Scriptor_User_Guide.md) | 完整的功能使用和配置说明 | 所有用户 |
| [学习模式指南](./LEARNING_MODE_GUIDE.md) | 学习模式和授课模式详解 | 高级用户 |
| [额外内容使用](./astrbot/extra_content_usage.md) | SOUL.md、SOP.md 等高级功能 | 高级用户 |

**学习模式和授课模式**是 Scriptor 的核心特色功能，强烈建议所有用户阅读 [学习模式指南](./LEARNING_MODE_GUIDE.md)。

### 设计理念

| 文档 | 说明 |
|------|------|
| [系统设计哲学](./Scriptor_System_Design_Philosophy.md) | 深入理解 Scriptor 的设计理念 |
| [架构升级指南](./Scriptor_Architecture_Upgrade_Guide.md) | 与传统记忆系统的对比分析 |

### 开发者文档

| 文档 | 说明 |
|------|------|
| [API 参考](./Scriptor_API_Reference.md) | 完整的 API 文档 |
| [高级功能指南](./Scriptor_Advanced_Features.md) | 高级功能和扩展开发 |
| [事件注入指南](./astrbot/plugin_event_injection_guide.md) | 事件系统使用 |
| [提示词注入指南](./astrbot/plugin_prompt_injection_guide.md) | 提示词系统使用 |

---

## 🎯 按用户类型推荐

### 👶 新用户
1. 阅读 [README](../README.md)
2. 阅读 [用户指南](./Scriptor_User_Guide.md)
3. 了解 [学习模式和授课模式](./LEARNING_MODE_GUIDE.md)
4. 开始使用

### 🎓 高级用户
1. 完成新用户步骤
2. 阅读 [学习模式指南](./LEARNING_MODE_GUIDE.md)（重点）
3. 阅读 [系统设计哲学](./Scriptor_System_Design_Philosophy.md)
4. 阅读 [额外内容使用](./astrbot/extra_content_usage.md)

### 👨‍💻 开发者
1. 完成高级用户步骤
2. 阅读 [API 参考](./Scriptor_API_Reference.md)
3. 阅读 [高级功能指南](./Scriptor_Advanced_Features.md)
4. 阅读 [事件注入指南](./astrbot/plugin_event_injection_guide.md)
5. 开始开发扩展

---

## 📦 项目结构

```
astrbot_plugin_scriptor/
├── docs/                          # 文档目录（本目录）
│   ├── INDEX.md                   # 本文档
│   ├── LEARNING_MODE_GUIDE.md     # 学习模式指南
│   ├── Scriptor_User_Guide.md     # 用户指南
│   ├── Scriptor_API_Reference.md  # API 参考
│   ├── Scriptor_Advanced_Features.md
│   ├── Scriptor_System_Design_Philosophy.md
│   ├── Scriptor_Architecture_Upgrade_Guide.md
│   └── astrbot/                   # AstrBot 集成文档
├── core/                          # 核心模块
│   ├── memory_manager.py          # 记忆管理器
│   ├── search_engine.py           # 搜索引擎
│   ├── identity_manager.py        # 身份管理器
│   ├── group_manager.py           # 群体管理器
│   ├── prompt_builder.py          # 提示词构建器
│   ├── knowledge_graph.py         # 知识图谱
│   └── ...
├── mixins/                        # Mixin 模块
├── hooks/                         # Hook 系统
├── tools/                         # 工具类
├── web/                           # Web UI (Vue 3)
├── tests/                         # 测试
├── scripts/                       # 构建脚本
├── main.py                        # 主入口
├── pyproject.toml                 # Python 包配置
└── README.md                      # 项目简介
```

---

## ✨ 核心特性

1. **文件即记忆** - Markdown 格式存储，透明可控
2. **跨平台身份聚合** - 统一管理多平台身份
3. **个人 + 群体双轨记忆** - 支持个人和群体记忆
4. **混合检索引擎** - Tantivy BM25 + ChromaDB 向量搜索
5. **主动式记忆管理** - 睡眠巩固、画像精炼、经验提取
6. **三档衰减策略** - T0 易逝档、T1 待证档、T2 永存档
7. **知识图谱** - 自动提取实体和关系
8. **🌟 学习模式与授课模式** - 待确认知识机制，防止错误知识污染
9. **司书档案馆** - 支持 10 万 + 条结构化数据查询
10. **Web UI** - 现代化的管理界面
11. **权限管理** - 基于角色的细粒度权限控制
12. **数据加密** - 可选的 AES-256 加密

**学习模式和授课模式** 是 Scriptor 的核心特色功能，详见 [学习模式指南](./LEARNING_MODE_GUIDE.md)。

---

## 🛠️ 构建和发布

### 开发构建
```bash
pip install -r requirements.txt
pip install -e .
```

### 完整构建（包含 Web UI）
```bash
# Windows PowerShell
$env:ASTRBOT_BUILD_WEB="1"
python -m build

# Linux/macOS
ASTRBOT_BUILD_WEB=1 python -m build
```

### 自动发布
```bash
git tag v1.0.0
git push origin v1.0.0
# CI/CD 自动构建并发布到 PyPI
```

详见 **[构建指南](../BUILD.md)**。

---

## 📊 学习路径

### 基础路径
```
README → 用户指南 → 开始使用
```

### 进阶路径
```
用户指南 → 系统设计哲学 → 高级功能 → 学习模式
```

### 开发路径
```
用户指南 → API 参考 → 高级功能 → 事件/提示词注入 → 开发扩展
```

---

## ❓ 常见问题

### 在哪里可以找到配置说明？
请查看 [用户指南](./Scriptor_User_Guide.md) 的"配置说明"章节。

### 如何使用学习模式？
请查看 [学习模式指南](./LEARNING_MODE_GUIDE.md)。

### 如何构建和发布？
请查看 [构建指南](../BUILD.md)。

### 我想了解设计理念
请查看 [系统设计哲学](./Scriptor_System_Design_Philosophy.md)。

### 我是开发者，想扩展功能
请查看 [API 参考](./Scriptor_API_Reference.md) 和 [高级功能指南](./Scriptor_Advanced_Features.md)。

---

## 🆘 获取帮助

1. 查看相关文档
2. 使用 `/debug_memory` 命令查看调试信息
3. 检查 AstrBot 日志
4. 在 GitHub 提交 [Issue](https://github.com/ysf7762-dev/astrbot_plugin_scriptor/issues)

---

## 🤝 贡献

欢迎贡献！你可以：

- ✏️ 改进文档
- 🐛 报告 Bug
- 💡 提交 Feature Request
- 🔧 提交 Pull Request

---

## 📄 许可证

**AGPL-3.0 License**

---

## 🙏 致谢

- 借鉴了 **ReMe** (Remember Everything) 的架构
- 采用了 **CoPaw** (Agent Framework) 的文件基因
- 吸纳了 **Angel Memory** 的情感记忆理念
- 感谢 **AstrBot** 提供的强大插件生态
- 感谢 **魔搭社区 (ModelScope)** 提供的国内模型服务

---

*最后更新：2026-03-30*
