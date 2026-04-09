# Scriptor 额外内容使用指南

本文档介绍如何使用 Scriptor 的额外内容功能，包括灵魂设定、标准流程、代理设定等。

---

## 目录

1. [灵魂设定 (SOUL.md)](#灵魂设定-soulmd)
2. [标准流程 (SOP.md)](#标准流程-sopmd)
3. [代理设定 (AGENTS.md)](#代理设定-agentsmd)
4. [画像文件 (PROFILE.md)](#画像文件-profilemd)
5. [记忆文件 (MEMORY.md)](#记忆文件-memorymd)

---

## 灵魂设定 (SOUL.md)

### 什么是灵魂设定？

灵魂设定文件用于定义 AI 的性格、语气、说话风格等个性特征。

### 创建 SOUL.md

在用户目录下创建 `SOUL.md`：

```
profiles/{uid}/
└── SOUL.md
```

### SOUL.md 模板

```markdown
# 灵魂设定

## 基本性格
- 性格：温柔、体贴、有耐心
- 语气：友好、亲切、自然
- 说话风格：简洁明了，偶尔使用表情符号

## 价值观
- 尊重用户的隐私
- 始终保持诚实
- 乐于助人

## 禁忌
- 不要说脏话
- 不要讨论敏感话题
- 不要编造信息

## 对话示例
用户：你好
AI：你好！😊 有什么我可以帮助你的吗？

用户：我今天心情不好
AI：听到这个我很难过... 想不想聊聊发生了什么？我会陪着你的。
```

### 灵魂设定的优先级

灵魂设定在 Entity-First 排序中位于第 3 位：
1. PROFILE.md（画像）
2. SOP.md（标准流程）
3. **SOUL.md（灵魂设定）** ←
4. MEMORY.md（长期记忆）
5. 近期日记
6. 群体记忆

---

## 标准流程 (SOP.md)

### 什么是标准流程？

标准流程文件用于定义处理特定场景的标准操作流程。

### 创建 SOP.md

在用户目录下创建 `SOP.md`：

```
profiles/{uid}/
└── SOP.md
```

### SOP.md 模板

```markdown
# 标准操作流程

## 处理用户问题
1. 先理解用户的问题核心
2. 检索相关记忆
3. 给出准确的回答
4. 记录重要信息

## 处理用户情绪
1. 识别用户的情绪状态
2. 给予适当的回应
3. 提供支持和安慰
4. 记录情绪变化

## 处理新信息
1. 判断信息的重要性
2. 使用 core_memory_remember 记录
3. 添加适当的标签
4. 设置合适的强度

## 特定场景流程

### 用户问时间
1. 获取当前时间
2. 以友好的方式回复
3. 询问是否需要其他帮助

### 用户说心情不好
1. 表达关心
2. 倾听用户的倾诉
3. 给予安慰和支持
4. 不要强行说教
```

### 群体 SOP

你也可以为群体创建 SOP：

```
groups/{group_id}/
└── SOP.md
```

群体 SOP 示例：

```markdown
# 群体标准流程

## 群聊规则
1. 保持友善
2. 尊重他人
3. 不要刷屏

## 处理群消息
1. 识别消息类型
2. 判断是否需要回应
3. 如需要，给出合适的回应
4. 记录重要信息
```

---

## 代理设定 (AGENTS.md)

### 什么是代理设定？

代理设定文件用于定义多个不同的 AI 代理角色，每个角色有不同的专长和性格。

### 创建 AGENTS.md

在用户目录下创建 `AGENTS.md`：

```
profiles/{uid}/
└── AGENTS.md
```

### AGENTS.md 模板

```markdown
# 代理设定

## 通用助手 (默认)
- 专长：日常对话、通用问题
- 性格：友好、耐心
- 适用场景：大多数情况

## 编程助手
- 专长：编程、技术问题
- 性格：严谨、细致
- 适用场景：代码相关问题
- 触发词：代码、编程、Python、Java、bug

## 心理支持
- 专长：心理咨询、情绪支持
- 性格：温柔、体贴
- 适用场景：情绪问题、心理困扰
- 触发词：心情不好、难过、焦虑、压力

## 学习导师
- 专长：学习、教育
- 性格：鼓励、耐心
- 适用场景：学习问题、知识讲解
- 触发词：学习、教我、解释、什么是

## 如何切换代理
1. 根据用户的问题自动识别
2. 使用对应的触发词
3. 或者明确告诉 AI 你需要哪个代理
```

---

## 画像文件 (PROFILE.md)

### 什么是画像文件？

画像文件用于存储用户的基本信息、偏好、重要事实等核心知识。

### PROFILE.md 结构

```markdown
# 用户画像

## 基本信息
- 姓名：张三
- 职业：程序员
- 年龄：28岁

## 联系方式
- 邮箱：zhangsan@example.com
- 电话：138-0000-0000

## 偏好
- 喜欢的编程语言：Python
- 喜欢的食物：苹果
- 喜欢的颜色：蓝色
- 不喜欢：吵闹、被打扰

## 重要事实
- 对花生过敏
- 不喜欢吃香菜
- 每天早上 8 点起床

## 长期目标
- 学习机器学习
- 今年读 50 本书
- 保持健康的生活方式
```

### 画像文件的优先级

画像文件在 Entity-First 排序中位于第 1 位（最高优先级）：
1. **PROFILE.md（画像）** ← 最高
2. SOP.md（标准流程）
3. SOUL.md（灵魂设定）
4. MEMORY.md（长期记忆）
5. 近期日记
6. 群体记忆

### 更新画像

使用 LLM 工具更新画像：

```python
@filter.llm_tool()
async def update_profile(self, event: AstrMessageEvent,
                      new_facts: str) -> str:
    """
    更新当前用户的个人画像
    
    Args:
        new_facts: 需要更新的事实信息
        
    Returns:
        确认消息
    """
    uid, _, _ = self._get_identity(event)
    await self.memory_manager.update_profile(uid, new_facts)
    return "✅ 画像已更新。"
```

---

## 记忆文件 (MEMORY.md)

### 什么是记忆文件？

记忆文件用于存储长期记忆，包括事实、经验、决策等。

### MEMORY.md 结构

每条记忆使用 Front Matter + 正文的格式：

```markdown
---
memory_type: fact
useful_score: 8.5
strength: 1.5
privacy_level: private
created_at: 2026-03-10T14:30:00
tags: [偏好, 食物, 水果]
---

用户喜欢吃苹果，多次提到并表示喜欢其口感。

---
memory_type: experience
useful_score: 7.0
strength: 1.2
privacy_level: private
created_at: 2026-03-09T10:00:00
tags: [编程, Python, 调试]
---

今天学习了 Python 调试技巧，使用 pdb 可以很方便地调试代码。

---
memory_type: decision
useful_score: 9.0
strength: 2.0
privacy_level: private
created_at: 2026-03-08T16:00:00
tags: [决策, 项目, 技术选型]
---

决定使用 Python 作为新项目的开发语言，理由是：
1. 团队熟悉 Python
2. 生态丰富
3. 开发效率高
```

### 记忆类型

| 类型 | 说明 |
|------|------|
| fact | 事实 |
| preference | 偏好 |
| decision | 决策 |
| experience | 经验 |
| rule | 规则 |
| consolidated | 睡眠巩固 |

### 三档衰减策略

| 档位 | 分数范围 | 说明 |
|------|---------|------|
| T0 易逝档 | score < 5 | 快速衰减 |
| T1 待证档 | 5 ≤ score < 10 | 缓慢衰减 |
| T2 永存档 | score ≥ 10 | 极慢衰减或不衰减 |

### 记录记忆

使用 LLM 工具记录记忆：

```python
@filter.llm_tool()
async def core_memory_remember(
    self,
    event: AstrMessageEvent,
    judgment: str,
    reasoning: str = "",
    tags: str = "",
    strength: int = 80,
    memory_type: str = "knowledge"
) -> str:
    """
    永久铭记重要信息（主动记忆，永不遗忘）
    """
    await self._wait_for_ready()
    uid, group_id, _ = self._get_identity(event)
    
    content = judgment
    if reasoning:
        content += f"\n理由: {reasoning}"
    if tags:
        content += f"\n标签: {tags}"
    
    useful_score = 5.0 + (strength / 20)
    useful_score = min(15.0, useful_score)
    
    await self.memory_manager.record_long_term_memory(
        uid, group_id, content, memory_type,
        search_engine=self.search_engine,
        strength=2.0,
        useful_score=useful_score
    )
    
    return f"✅ 已铭记: {judgment}"
```

---

## 额外内容的最佳实践

### 1. 保持简洁

```markdown
# 好的示例
- 姓名：张三
- 职业：程序员

# 不好的示例
- 姓名：张三，一个很普通的名字，是我父母给我取的...
- 职业：程序员，写代码的，有时候很辛苦...
```

### 2. 使用清晰的结构

```markdown
## 基本信息
- 姓名：张三
- 职业：程序员

## 偏好
- 喜欢：Python、苹果
- 不喜欢：吵闹
```

### 3. 定期更新

定期检查和更新你的额外内容文件，确保信息是最新的。

### 4. 备份

额外内容文件很重要，建议定期备份：

```bash
cp -r profiles/{uid}/ backups/{uid}_$(date +%Y%m%d)/
```

---

## 更多资源

- [Scriptor 用户指南](../Scriptor_User_Guide.md)
- [Scriptor 系统设计哲学](../Scriptor_System_Design_Philosophy.md)
- [Scriptor 提示词注入指南](./plugin_prompt_injection_guide.md)
