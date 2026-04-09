# Scriptor 快速开始指南

## 安装

### 如何安装 Scriptor？
将插件放入 AstrBot 的插件目录即可：

```
AstrBot/
└── data/
    └── plugins/
        └── astrbot_plugin_scriptor/
            ├── main.py
            ├── core/
            └── README.md
```

## 首次使用

### 第一步：启动 AstrBot
启动 AstrBot，插件会自动初始化。

### 第二步：开始对话
直接与 AI 对话，系统会自动开始记录你的对话。

### 第三步：查看状态
发送 `/mem_status` 查看记忆系统状态。

## 核心命令

### 查看记忆系统状态
```
/mem_status
```
查看当前记忆系统的状态，包括用户信息、当前群体、参与群体数、待处理跨群消息等。

### 调试命令
```
/debug_memory
```
查看记忆系统的调试信息（仅私聊或管理员可用）。

### 查看身份信息
```
/whoami
```
查看当前身份信息并生成绑定码，用于跨平台身份绑定。

### 绑定身份
```
/bind <绑定码>
```
绑定其他设备的身份，实现跨平台身份聚合。

### 生成记忆维护建议
```
/mem_report
```
生成记忆维护建议报告，帮助你优化记忆系统。

## LLM 工具使用（直接告诉 AI 即可

### 检索记忆
> "帮我检索一下关于 Python 的记忆"

### 更新画像
> "更新我的画像，添加：我喜欢编程"

### 记录决策
> "记录决策：明天开始学习 Python，理由是工作需要"

### 创建跨群提醒
> "创建跨群提醒：别忘了明天的会议"

### 创建定时提醒
> "30分钟后提醒我喝水"
> "明天 09:00 提醒我起床"

## 跨平台身份绑定

### 绑定步骤
1. 在设备 A 上发送 `/whoami`，获取绑定码
2. 在设备 B 上发送 `/bind <绑定码>`
3. 完成！

## 记忆文件位置

### 个人记忆
```
data/plugins/astrbot_plugin_scriptor/profiles/{uid}/
├── PROFILE.md      # 用户画像
├── MEMORY.md       # 长期记忆
├── SOUL.md         # 灵魂设定（可选）
├── AGENTS.md       # 代理设定（可选）
├── SOP.md          # 标准流程（可选）
├── ARCHIVE.md      # 归档记忆
└── memory/         # 日记目录
    └── YYYY-MM-DD.md
```

### 群体记忆
```
data/plugins/astrbot_plugin_scriptor/groups/{group_id}/
├── GROUP.md        # 群体信息
├── MEMORY.md       # 群体记忆
├── SOP.md          # 群体流程（可选）
└── memory/         # 群体日记
    └── YYYY-MM-DD.md
```

## 下一步

- 阅读完整的 [用户指南了解更多功能
- 探索额外内容（SOUL.md、SOP.md、AGENTS.md）
- 开始使用，享受你的 AI 管家！
