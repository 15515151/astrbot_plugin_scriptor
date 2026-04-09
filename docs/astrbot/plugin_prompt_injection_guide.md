# Scriptor 提示词注入指南

本文档介绍如何在 Scriptor 中使用提示词注入机制。

---

## 目录

1. [提示词系统概述](#提示词系统概述)
2. [热记忆注入](#热记忆注入)
3. [检索指导注入](#检索指导注入)
4. [Token 控制](#token-控制)
5. [自定义提示词模板](#自定义提示词模板)

---

## 提示词系统概述

Scriptor 的提示词系统由以下部分组成：

```
基础系统提示词 (AstrBot)
    +
热记忆 (Scriptor)
    +
检索指导 (Scriptor)
    =
最终系统提示词
```

---

## 热记忆注入

### 热记忆结构

热记忆是 Scriptor 注入的核心内容，包含：

```markdown
【当前身份】
- 用户：张三
- 当前群体：private

【个人画像】
## 基本信息
- 姓名：张三
- 职业：程序员

【核心规则】
1. 记住用户的偏好
2. 主动记录重要信息

【长期记忆】
- 用户喜欢吃苹果
- 用户擅长 Python 编程

【近期对话】
[2026-03-10 14:30] 用户：你好
[2026-03-10 14:31] Assistant：你好！我是你的AI管家...
```

### 热记忆构建器

```python
from astrbot_plugin_scriptor.core.prompt_builder import PromptBuilder

prompt_builder = PromptBuilder(
    data_dir=data_dir,
    config=config,
    identity_manager=identity_manager,
    group_manager=group_manager,
    memory_manager=memory_manager,
    cross_group_system=cross_group_system
)

# 构建系统提示词
system_prompt = prompt_builder.build_system_prompt(uid, group_id)
```

### Entity-First 排序

热记忆按照 Entity-First 策略排序：

1. **个人画像** (PROFILE.md) - 最高优先级
2. **标准流程** (SOP.md) - 行动指南
3. **灵魂设定** (SOUL.md) - 性格设定
4. **长期记忆** (MEMORY.md) - 事实和经验
5. **近期日记** - 最近的对话
6. **群体记忆** - 相关群体的记忆

---

## 检索指导注入

### 检索指导内容

```python
RETRIEVAL_GUIDANCE = """

【系统指令】
1. 回答问题前，**必先调用 `memory_search` 检索**相关记忆。
2. 若发现关于当前用户的新偏好、新习惯或重要信息，**主动调用 `core_memory_remember` 永久铭记**。
3. 需要随机回忆一些核心知识时，使用 `core_memory_recall` 避免确定性偏见。
4. 需要查看完整日记上下文时，使用 `note_recall` 进行深度阅读。
5. 发现重要信息时，主动记录到记忆系统。
"""
```

### 注入流程

```python
@filter.on_llm_request()
async def before_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
    """LLM 请求前：注入提示词"""
    await self._wait_for_ready()
    
    uid, group_id, _ = self._get_identity(event)
    
    # 构建热记忆
    hot_memory = self.prompt_builder.build_system_prompt(uid, group_id)
    
    # 注入系统提示词
    if hot_memory:
        req.system_prompt = (req.system_prompt or "") + "\n\n" + hot_memory + RETRIEVAL_GUIDANCE
```

---

## Token 控制

### Token 估算

```python
from astrbot_plugin_scriptor.core.token_utils import TokenEstimator

# 估算 Token 数量
tokens = TokenEstimator.estimate_tokens(text)
```

### 智能裁剪

当系统提示词过长时，使用智能裁剪：

```python
from astrbot_plugin_scriptor.core.token_utils import SmartMemoryTrimmer

def _combine_prompts_with_token_control(
    self,
    base_system_prompt,
    hot_memory,
    retrieval_guidance
):
    """
    智能组合多个提示词部分，确保总 token 不超限
    """
    base_tokens = TokenEstimator.estimate_tokens(base_system_prompt)
    hot_memory_tokens = TokenEstimator.estimate_tokens(hot_memory)
    guidance_tokens = TokenEstimator.estimate_tokens(retrieval_guidance)
    
    total_current = base_tokens + hot_memory_tokens + guidance_tokens
    
    if total_current <= self.config.max_system_prompt_tokens:
        return base_system_prompt + "\n\n" + hot_memory + retrieval_guidance
    
    # Token 超限，进行智能裁剪
    trimmer = SmartMemoryTrimmer(
        self.config.max_system_prompt_tokens - base_tokens
    )
    
    if hot_memory:
        trimmer.add_part("hot_memory", hot_memory, 10)
    
    if retrieval_guidance:
        trimmer.add_part(
            "retrieval_guidance", 
            retrieval_guidance, 
            self.config.retrieval_guidance_priority
        )
    
    selected_parts, used_tokens = trimmer.trim()
    
    combined_parts = [base_system_prompt] if base_system_prompt else []
    for part in selected_parts:
        combined_parts.append(part.content)
    
    return "\n\n".join(combined_parts)
```

### 裁剪优先级

| 部分 | 默认优先级 | 说明 |
|------|-----------|------|
| 基础系统提示词 | - | 始终保留 |
| 热记忆 | 10 | 最高优先级 |
| 检索指导 | 5 | 中等优先级 |

---

## 自定义提示词模板

### 模板文件

Scriptor 使用模板文件来构建提示词：

```
templates/
├── BOOTSTRAP.md   # 首次引导模板
├── MEMORY.md      # 记忆模板
├── PROFILE.md     # 画像模板
├── SOUL.md        # 灵魂模板
├── GROUP.md       # 群体模板
└── HEARTBEAT.md   # 心跳模板
```

### 自定义 BOOTSTRAP 模板

```markdown
# 首次引导

你好！我是你的AI管家，为了更好地帮助你，我需要了解一些基本信息。

请告诉我：
1. 你的名字
2. 你的职业
3. 你的兴趣爱好
4. 你希望我帮助你做什么

我会将这些信息记录下来，以便未来更好地为你服务。
```

### 自定义 MEMORY 模板

```markdown
---
memory_type: {memory_type}
useful_score: {useful_score}
strength: {strength}
privacy_level: {privacy_level}
created_at: {created_at}
tags: {tags}
---

{content}
```

### 自定义画像模板

```markdown
# 用户画像

## 基本信息
- 姓名：{name}
- 职业：{occupation}

## 偏好
{preferences}

## 经验
{experiences}
```

---

## 提示词工程最佳实践

### 1. 清晰的指令

```python
# 好的指令
RETRIEVAL_GUIDANCE = """
【系统指令】
1. 回答问题前，**必先调用 `memory_search` 检索**相关记忆。
2. 若发现新偏好，**主动调用 `core_memory_remember` 永久铭记**。
"""

# 不好的指令
RETRIEVAL_GUIDANCE = "记得用工具"
```

### 2. 结构化内容

```markdown
【当前身份】
- 用户：张三
- 当前群体：private

【个人画像】
## 基本信息
- 姓名：张三
- 职业：程序员
```

### 3. Token 效率

```python
# 使用档案名而非全文
# 节省 97% Token
"档案名: 武器/法器/乌髓孑灯.md | 武器故事"

# 而非
"乌髓孑灯是一把四星法器，它的基础攻击力为42...（500字正文）"
```

### 4. 优先级管理

```python
# Entity-First 排序
trimmer.add_part("profile", profile_content, 10)    # 最高
trimmer.add_part("memory", memory_content, 8)       # 高
trimmer.add_part("recent_notes", notes_content, 5)  # 中
trimmer.add_part("guidance", guidance_content, 3)   # 低
```

---

## 调试提示词

### 查看注入的提示词

```python
@filter.on_llm_request()
async def before_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
    uid, group_id, _ = self._get_identity(event)
    hot_memory = self.prompt_builder.build_system_prompt(uid, group_id)
    
    # 调试：输出提示词
    logger.debug(f"注入的热记忆: {hot_memory}")
    logger.debug(f"最终系统提示词: {req.system_prompt}")
```

### 使用 Token 控制调试

```python
logger.debug(
    f"[TokenControl] Token 预估: "
    f"基础={base_tokens}, 热记忆={hot_memory_tokens}, 指导={guidance_tokens}, "
    f"总计={total_current}/{self.config.max_system_prompt_tokens}"
)

if total_current > self.config.max_system_prompt_tokens:
    logger.warning(
        f"[TokenControl] Token 超限！当前 {total_current} > 限制 {self.config.max_system_prompt_tokens}"
    )
```

---

## 更多资源

- [Scriptor 用户指南](../Scriptor_User_Guide.md)
- [Scriptor API 参考](../Scriptor_API_Reference.md)
- [提示词工程最佳实践](https://www.promptingguide.ai/)
