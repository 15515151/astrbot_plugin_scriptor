# Scriptor 使用说明 - 常见问题

## 快速开始

### 如何安装 Scriptor？
将插件放入 AstrBot 的插件目录即可：
```
AstrBot/data/plugins/astrbot_plugin_scriptor/
```

### 如何开始使用？
启动 AstrBot 后，直接与 AI 对话，系统会自动开始记录你的对话。

### 如何查看记忆系统状态？
发送 `/mem_status` 命令即可查看当前状态。

---

## 命令使用

### 如何查看记忆系统状态？
使用 `/mem_status` 命令查看：
- 用户信息
- 当前群体
- 参与群体数
- 待处理跨群消息
- 当前群体成员
- 跨群待办

### 如何调试记忆系统？
使用 `/debug_memory` 命令（仅私聊或管理员可用）查看详细调试信息。

### 如何查看身份信息？
使用 `/whoami` 命令查看当前身份信息并生成绑定码。

### 如何绑定其他平台的身份？
1. 在设备 A 上发送 `/whoami`，获取绑定码
2. 在设备 B 上发送 `/bind <绑定码>`
3. 两个设备的身份自动合并

### 如何生成记忆维护建议？
使用 `/mem_report` 命令生成记忆维护建议报告。

---

## LLM 工具使用

### 如何检索记忆？
告诉 AI："帮我检索一下关于 XXX 的记忆"，AI 会自动调用 `memory_search` 工具。

### 如何更新个人画像？
告诉 AI："更新我的画像，添加：XXX"，AI 会调用 `update_profile` 工具。

### 如何记录重要决策？
告诉 AI："记录决策：XXX，理由是：XXX"，AI 会调用 `record_decision` 工具。

### 如何创建跨群提醒？
告诉 AI："创建跨群提醒：XXX"，AI 会调用 `create_reminder` 工具。

### 如何创建定时提醒？
告诉 AI："30分钟后提醒我喝水"，AI 会调用 `add_schedule_task` 工具。支持以下时间格式：
- "YYYY-MM-DD HH:MM"（例如 "2024-12-25 08:00"）
- "HH:MM"（今天的这个时间，如果已过则为明天）
- "X minutes/hours/days later"（例如 "30 minutes later"）
- "tomorrow HH:MM"（明天这个时间）

### 如何查看群体成员？
告诉 AI："查看当前群体成员"，AI 会调用 `view_group_members` 工具。

### 如何永久铭记重要信息？
告诉 AI："永久铭记：XXX，理由是：XXX"，AI 会调用 `core_memory_remember` 工具。

### 如何随机回忆核心记忆？
告诉 AI："随机回忆一些核心记忆"，AI 会调用 `core_memory_recall` 工具。

### 如何深度阅读日记？
告诉 AI："读取最近的日记"，AI 会调用 `note_recall` 工具。

---

## 跨平台身份绑定

### 为什么需要身份绑定？
如果你在多个平台（如 QQ、Telegram、Discord）上使用 AstrBot，每个平台会有不同的身份 ID。通过身份绑定，可以将这些不同的身份绑定到同一个逻辑 UID，实现跨平台记忆共享。

### 身份绑定的步骤？
1. 在设备 A 上获取绑定码：发送 `/whoami`
2. 在设备 B 上绑定：发送 `/bind <绑定码>`
3. 完成！现在两个设备共享同一个身份和记忆

### 身份绑定注意事项？
- 绑定后，两个设备的记忆会合并
- 绑定是单向的，绑定码只能使用一次
- 如需解绑，请手动编辑身份文件（高级用户）

---

## 记忆管理

### 如何查看和编辑记忆？
记忆文件存储在：
- 个人记忆：`data/plugins/astrbot_plugin_scriptor/profiles/{uid}/`
- 群体记忆：`data/plugins/astrbot_plugin_scriptor/groups/{group_id}/`
你可以直接用文本编辑器编辑这些文件。

### 记忆文件格式是什么？
每条记忆使用 Front Matter + 正文的 Markdown 格式。

### 如何备份记忆？
建议定期备份记忆文件：复制整个 `data/plugins/astrbot_plugin_scriptor/` 目录，或使用 Git 进行版本控制。

### 如何迁移记忆？
将备份的 `profiles/` 和 `groups/` 目录复制到新位置即可完成迁移。

---

## 配置说明

### 如何配置 Scriptor？
在 AstrBot 的配置文件中添加配置项。

### 记忆压缩阈值是什么？
`memory_compact_threshold` 是记忆压缩阈值，当记忆超过这个 token 数时会触发压缩。

### 如何启用/禁用日记功能？
设置 `daily_note_enabled` 为 true/false。

### 如何启用/禁用跨群功能？
设置 `cross_group_enabled` 为 true/false。

### 如何启用/禁用 Embedding 向量搜索？
设置 `embedding_enabled` 为 true/false。

### 如何配置 Embedding？
配置 `embedding_provider`、`embedding_api_base`、`embedding_api_key`、`embedding_model`。

### 如何启用 Token 控制？
设置 `enable_token_control` 为 true。

### 如何启用记忆加密？
设置 `encryption_enabled` 为 true，并配置 `encryption_key`。

---

## 核心概念

### 什么是文件即记忆？
Scriptor 的核心理念是"文件即记忆"。所有记忆都以标准 Markdown 格式存储在文件系统中，你可以直接用文本编辑器编辑、使用 Git 版本控制、轻松备份迁移和分享。

### 什么是三档衰减策略？
记忆根据 `useful_score` 分为三个档位：
- T0 易逝档（score < 5）：快速衰减，适合临时信息
- T1 待证档（5 ≤ score < 10）：缓慢衰减，需要验证的信息
- T2 永存档（score ≥ 10）：极慢衰减或不衰减，核心知识

### 什么是睡眠巩固？
当检测到"新会话"（跨天且超过 60 分钟未活跃）时，系统会自动触发睡眠巩固：
- 模式识别：发现重复出现的模式
- 目标发现：识别潜在的长期目标
- 冲突解决：合并矛盾的信息
- 冷热分离：将过期记忆归档
- 记忆合并：合并相似的记忆

---

## 常见问题

### 记忆会占用很多空间吗？
不会。记忆以 Markdown 格式存储，非常节省空间。即使有几千条记忆，也只会占用几 MB 空间。

### 可以关闭某些功能吗？
可以。通过配置文件可以关闭日记、跨群、Embedding 等功能。

### 记忆安全吗？
是的。记忆存储在本地文件系统中，完全由你控制。你还可以启用加密功能来保护敏感记忆。

### 如何重置记忆？
删除对应的 `profiles/{uid}/` 或 `groups/{group_id}/` 目录即可。注意：这会永久删除所有记忆！

### 可以导入其他记忆系统的数据吗？
当前版本暂不支持直接导入，但你可以手动将内容添加到记忆文件中。

### 睡眠巩固会影响使用吗？
不会。睡眠巩固在后台运行，不会影响正常使用。

### 如何提高检索准确率？
确保记忆内容清晰、有条理。使用 `core_memory_remember` 工具明确标记重要信息。

---

## 额外内容使用

### 什么是灵魂设定 SOUL.md？
灵魂设定文件用于定义 AI 的性格、语气、说话风格等个性特征。在用户目录下创建 `SOUL.md` 即可。

### 什么是标准流程 SOP.md？
标准流程文件用于定义处理特定场景的标准操作流程。在用户目录下创建 `SOP.md` 即可。

### 什么是代理设定 AGENTS.md？
代理设定文件用于定义多个不同的 AI 代理角色，每个角色有不同的专长和性格。在用户目录下创建 `AGENTS.md` 即可。

### 什么是画像文件 PROFILE.md？
画像文件用于存储用户的基本信息、偏好、重要事实等核心知识。

### 什么是记忆文件 MEMORY.md？
记忆文件用于存储长期记忆，包括事实、经验、决策等。

---

## 高级功能

### 什么是知识图谱？
知识图谱是 Scriptor 的高级功能，它从日记中自动提取实体和关系，构建一个可视化的知识网络。知识图谱默认启用，每天凌晨 3 点自动整理。

### 如何启用知识图谱？
配置 `nightly_graph_consolidation_enabled` 为 true。

### 什么是权限管理？
Scriptor 实现了基于角色的细粒度权限管理系统，包括访客、成员、管理员、超级管理员、所有者等角色。

### 如何启用数据加密？
配置 `encryption_enabled` 为 true，并生成 Fernet 密钥配置到 `encryption_key`。

### 什么是 Hook 系统？
Hook 是 Scriptor 的扩展机制，允许你在关键节点插入自定义逻辑，包括生命周期 Hook、LLM Hook、消息 Hook、搜索 Hook、存储 Hook 等。
