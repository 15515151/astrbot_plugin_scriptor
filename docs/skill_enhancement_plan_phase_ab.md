# Skills 系统增强方案 (极简实效版)

> 📅 制定日期: 2026-04-05
> 🎯 目标: 摒弃过度工程，聚焦“高性价比”核心痛点，提升 LLM 技能调用准确率
> ⚠️ 原则: 如无必要，勿增实体。先制定详细方案，不动代码

---

## 一、现状诊断与“挤水分”反思

### 1.1 为什么需要“挤水分”？
在之前的方案中，我们试图全面对齐 Claude Code 的 Skills 系统（包括 16 个元数据字段、4 级目录加载、复杂的 Hooks 生命周期、严格的权限控制等）。
但结合 Scriptor 作为 AstrBot 插件的实际运行环境（常驻后台、单用户/小团队为主、依赖 LLM 自身推理能力），这些设计属于**过度工程（Over-engineering）**，不仅开发成本高，还会增加系统的脆弱性。

### 1.2 核心痛点与高性价比解法
当前 Scriptor 最大的痛点是：**工具太多（50+），LLM 记不住什么时候该用什么技能，也容易在执行技能时乱用无关工具。**

因此，我们砍掉了所有花里胡哨的边缘功能，只保留能直接解决上述痛点的**两把杀手锏**：
1. **智能推荐注入**：在每次对话前，把最相关的技能“小抄”塞给 LLM。
2. **工具白名单**：在执行技能时，严格限制 LLM 只能使用指定的工具。

---

## 二、Phase A: 核心大脑升级（预计 1 天）

**目标**: 极简元数据 + 智能推荐 + 工具白名单，让 LLM 瞬间变聪明。

### 2.1 [A1] 极简 SKILL.md 元数据解析

**改动文件**: `tools/skill_tool.py`

**设计**: 彻底抛弃复杂的权限和模型配置，只保留 4 个核心字段。

```yaml
---
name: "技能名称"                 # 必须：用于工具调用时的标识
description: "技能简短描述"      # 必须：让 LLM 知道这个技能大概是干嘛的
when-to-use: "触发场景描述"      # 核心新增：用于语义检索，决定何时推荐给 LLM
allowed-tools: ["tool_a"]      # 核心新增：安全与上下文控制，限制该技能只能用哪些工具
---
# 下面直接就是 Markdown 正文（Instructions）
```

**实现细节**:
- 修改 `SkillDefinition` 数据类，仅新增 `when_to_use` (str) 和 `allowed_tools` (List[str])。
- 修改 `_parse_frontmatter`，仅解析这 4 个字段，忽略其他所有未知字段（保证向后兼容）。

### 2.2 [A2] 智能推荐注入 (灵魂功能)

**改动文件**: `mixins/events_mixin.py` & `tools/skill_tool.py`

**设计**: 每次用户说话时，动态把最匹配的 1-3 个技能作为“小抄”塞进 System Prompt 里。

**实现细节**:
1. **推荐算法 (`skill_tool.py`)**:
   - 实现 `recommend_skills(context: str, limit: int = 2)`。
   - 评分逻辑极简：基于用户输入的 `context` 与技能的 `when-to-use` 和 `description` 进行关键词/简单语义重叠度计算。
   - 结合现有的冷却机制（CooldownManager），如果技能在冷却中，则大幅降权或不推荐。
2. **Prompt 注入 (`events_mixin.py`)**:
   - 在 `before_llm_request` 钩子中调用推荐算法。
   - 将推荐结果格式化为简短的提示，追加到 System Prompt 末尾。
   - 示例注入内容：`💡 相关技能推荐: 1. 知识库与研究专家 (scriptor-knowledge-research) - 适用: 当对话中出现新知识或偏好时。可通过 skill_call_tool 调用。`

### 2.3 [A3] 工具白名单实施 (维稳神器)

**改动文件**: `tools/skill_tool.py` (SkillExecutor)

**设计**: 当 LLM 进入某个特定技能时，严格按照 `allowed-tools` 过滤可用工具，防止幻觉发散。

**实现细节**:
- 在 `execute_inline` 和 `execute_forked` 准备执行环境时，拦截并重构传给 LLM 的工具列表。
- 如果 `allowed_tools` 不为空，则只保留白名单内的工具（支持简单的通配符如 `file_*`）。
- 如果为空，则默认开放所有工具（保持向后兼容）。

### 2.4 [A4] 更新现有内置技能

**改动文件**: `skills/*/SKILL.md`

**设计**: 将现有的 5 个内置技能的 frontmatter 更新为极简格式，重点补充 `when-to-use` 和 `allowed-tools`。

---

## 三、Phase B: 基础工程完善（预计 0.5 - 1 天）

**目标**: 解决自定义技能加载和后台任务管理的刚需。

### 3.1 [B1] 双级技能加载系统

**改动文件**: `tools/skill_tool.py`

**设计**: 摒弃复杂的 4 级目录向上遍历，只保留最实用的 2 级加载。

**实现细节**:
1. **Level 1 (内置)**: 插件自带的 `skills/` 目录。
2. **Level 2 (自定义)**: 允许在 `config_pydantic.py` 中配置一个 `custom_skills_dir`（默认如 `data/scriptor_custom_skills`）。
3. **加载逻辑**: 启动时先加载 Level 1，再加载 Level 2。如果存在同名技能（`name` 相同），Level 2 直接覆盖 Level 1（实现用户自定义重写内置技能的需求）。

### 3.2 [B2] 后台任务状态与取消 API

**改动文件**: `mixins/tools_mixin.py`

**设计**: 既然支持了 `forked`（后台执行），就必须给用户（或 LLM）提供查看和掐断死循环任务的能力。

**实现细节**:
- 新增工具 `@filter.llm_tool() async def skill_status_tool()`: 列出当前正在运行的后台技能任务（Task ID、技能名、运行时长）。
- 新增工具 `@filter.llm_tool() async def skill_cancel_tool(task_id: str)`: 强制取消指定的后台任务（调用 `asyncio.Task.cancel()`）。

---

## 四、实施时间线与验收标准

### 4.1 时间线 (总计 1.5 - 2 天)
- **Day 1 上午**: 完成 A1 (极简解析) 和 A4 (更新现有 MD)。
- **Day 1 下午**: 完成 A2 (推荐注入) 和 A3 (工具白名单)。**此时核心体验已大幅提升。**
- **Day 2 上午**: 完成 B1 (双级加载) 和 B2 (状态/取消工具)。

### 4.2 验收标准
1. **推荐生效**: 用户输入“帮我记一下这个偏好”，LLM 的 System Prompt 中能准确出现 `scriptor-knowledge-research` 的推荐提示。
2. **白名单生效**: 在执行某个配置了 `allowed-tools: ["read_file"]` 的技能时，LLM 无法调用 `run_command` 等其他工具。
3. **自定义覆盖**: 在 `custom_skills_dir` 中放入一个同名的 `scriptor-todo-schedule`，能成功覆盖内置的日程技能。
4. **任务取消**: 启动一个耗时的 forked 技能，调用 `skill_cancel_tool` 能成功将其终止。

---

**极简实效版方案制定完成，等待确认后开始实施 Phase A！** 🚀