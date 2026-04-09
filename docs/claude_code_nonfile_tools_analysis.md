# Claude Code 非文件类工具深度分析 — Scriptor 借鉴评估

> 上轮分析了文件操作类工具（Read/Edit/Write/MultiEdit 等）并已实施 4 项改进。
> 本轮聚焦 Claude Code 的**非文件类工具**，评估哪些值得我们学习。

---

## 一、Claude Code 非文件类工具全景（排除已分析/已采纳的）

### 类别 A：工具基础设施（2 个）

| # | 工具 | 核心功能 | 独特设计 |
|---|------|---------|---------|
| A1 | **ToolSearchTool** | 让 AI 搜索/发现自己有哪些工具可用 | 关键词评分系统（名称 10 分 / searchHint 4 分 / 描述 2 分）；支持 `select:tool_name` 精确选择；MCP 工具名智能解析 |
| A2 | **SkillTool** | 执行预定义的"技能"（slash command 宏） | 双模式：inline（内联展开 prompt） vs forked（子代理隔离执行）；远程技能从云端加载；安全属性白名单自动放行 |

### 类别 B：任务与调度（3 个）

| # | 工具 | 核心功能 | 独特设计 |
|---|------|---------|---------|
| B1 | **CronCreateTool** | 创建 cron 表达式驱动的定时任务 | 标准 5 字段 cron；支持 recurring/one-shot；durable（跨会话持久化）；自动过期（30 天）|
| B2 | **TodoWrite/TodoRead** | 结构化待办事项管理 | 状态机 pending→in_progress→completed；唯一 ID；批量更新 |
| B3 | **TaskCreateTool** | 创建并调度异步任务 | 与 Agent 系统深度集成 |

### 类别 C：代理协作（3 个）

| # | 工具 | 核心功能 | 独特设计 |
|---|------|---------|---------|
| C1 | **AgentTool (Task)** | 无状态子代理委托 | 无历史上下文；详细任务描述 + 期望输出格式；支持并发多代理 |
| C2 | **SendMessageTool** | 多代理间消息传递 | 点对点/广播/结构化消息（关闭请求、计划审批）；Agent Swarm 协议 |
| C3 | **ExitPlanModeTool** | 计划模式切换 | IDE/CLI 特有概念 |

### 类别 D：网络与外部（2 个）

| # | 工具 | 核心功能 | 独特设计 |
|---|------|---------|---------|
| D1 | **WebFetchTool** | 获取指定 URL 内容 | 预批准 URL 白名单；内容截断；权限请求机制 |
| D2 | **WebSearchTool** | 互联网搜索 | 内置搜索引擎 |

### 类别 E：特殊工具（3 个）

| # | 工具 | 核心功能 | 独特设计 |
|---|------|---------|---------|
| E1 | **REPLTool** | 交互式编程环境 (Read-Eval-Print Loop) | 代码即时执行 |
| E2 | **ReadMcpResourceTool** | 读取 MCP 远程资源 | Model Context Protocol 集成 |
| E3 | **TungstenTool** | 平台专属工具 | 数据库查询 |

---

## 二、逐项借鉴评估

### 🔴 高价值 — 强烈建议研究（2 项）

#### 1. ToolSearchTool — 工具自省/发现机制

**问题背景**：
当 Scriptor 的工具数量增长到 47+ 个时，LLM 在单次对话中可能：
- 忘记某个冷门工具的存在
- 不确定哪个工具适合当前任务
- 在工具名称相似时选错（如 `file_edit` vs `file_edit_by_line` vs `multi_edit`）

**Claude Code 的方案**：

```
输入: "search files"
输出: ["Glob", "Grep", "LS"]  (按评分排序)

输入: "select:Glob"
输出: ["Glob"]  (精确选择)

输入: "slack +read"
输出: ["mcp__slack__readChannel", "mcp__slack__readMessage"]
```

**核心算法**（[ToolSearchTool.ts L186-L302](file:///d:/PycharmProjects/Claude%20Code%20gai/src/tools/ToolSearchTool/ToolSearchTool.ts#L186-L302)）：
```typescript
// 评分权重:
// 名称部分完全匹配 → MCP 12 分 / 普通 10 分
// 名称部分包含 → MCP 6 分 / 普通 5 分
// searchHint 匹配 → 4 分
// 描述词边界匹配 → 2 分
```

**Scriptor 借鉴方案**：

```
新增工具: tool_search_tool(event, query, max_results=5)

实现思路:
  1. 获取所有已注册的 @filter.llm_tool() 方法列表
  2. 对每个工具提取: name + docstring 第一行（简短描述）
  3. 将 query 拆分为关键词
  4. 计算每个工具的匹配得分
  5. 返回 top-N 结果（仅返回 name + 一行描述，不含完整参数）
  
使用场景:
  - AI 不确定用哪个工具时: "帮我搜一下有没有搜索相关的工具"
  - 用户问"你能做什么"时: 列出所有工具分类
```

**收益**：
- ✅ 降低 AI 选错工具的概率（尤其是新增工具后）
- ✅ 支持"工具发现"交互模式（用户问"你有什么能力"）
- ✅ 为未来 MCP/插件工具扩展做准备

**复杂度**：中等（~60 行代码，主要是工具列表获取 + 模糊匹配）

---

#### 2. SkillTool — 技能宏/快捷指令系统

**问题背景**：
当前 Scriptor 的 `skills/` 目录是**被动的**——AI 需要 `file_read_tool("skills/xxx/SKILL.md")` 来读取技能手册，然后按照其中的指导行动。这相当于"读说明书再操作"。

Claude Code 的 SkillTool 是**主动的**——AI 直接调用 `/commit` 或 `/review-pr`，系统自动将技能的 prompt 注入上下文，甚至可以 fork 一个子代理来独立执行。

**Claude Code 的双模式**（[SkillTool.ts L122-L289](file:///d:/PycharmProjects/Claude%20Code%20gai/src/tools/SkillTool/SkillTool.ts#L122-L289)）：

| 模式 | 触发方式 | 执行方式 | 适用场景 |
|------|---------|---------|---------|
| **inline** | 简单技能（无 context=fork） | 将 SKILL.md 内容作为 user message 注入当前对话 | 短指令，如格式化输出模板 |
| **forked** | 复杂技能（context=fork） | 创建独立子代理，有自己 token 预算 | 长任务，如代码审查、提交 |

**关键设计 — 安全属性白名单**（[SkillTool.ts L875-L908](file:///d:/PycharmProjects/Claude%20Code%20gai/src/tools/SkillTool/SkillTool.ts#L875-L908)）：
```typescript
const SAFE_SKILL_PROPERTIES = new Set([
  'type', 'name', 'description', 'model', 'effort',
  'source', 'aliases', 'whenToUse', // ... 30+ 属性
])
// 如果技能只包含这些"安全属性"，自动放行无需用户确认
// 新增属性默认需要权限，直到人工审核加入白名单
```

**Scriptor 借鉴方案**：

```
新增工具: execute_skill_tool(event, skill_name, args)

实现思路:
  1. 扫描 skills/ 目录下所有 SKILL.md 文件
  2. 解析 YAML frontmatter 获取元数据:
     ---
     name: archive-manager
     description: "归档过期记忆到档案馆"
     allowed_tools: [file_read, file_write, file_search]
     mode: inline  # 或 fork（预留）
     ---
  3. 读取 SKILL.md 正文作为 prompt 模板
  4. 将 {args} 替换到 prompt 中
  5. 以修改后的 system/user message 继续对话
  
已有基础:
  - skills/ 目录结构已存在
  - SKILL.md 格式已标准化（YAML frontmatter + Markdown 正文）
  - AI 已经知道通过 file_read 读取技能
```

**收益**：
- ✅ 将"被动读技能"升级为"主动调用技能"——减少一步工具调用
- ✅ 技能有正式的"入口"和"签名"——更容易管理和版本化
- ✅ 可以限制每个技能允许使用的工具子集（allowed_tools）
- ✅ 为将来 fork 模式（子代理执行复杂技能）留好接口

**复杂度**：中高（~100 行代码，涉及技能扫描 + frontmatter 解析 + prompt 注入）

---

### 🟡 中价值 — 可选研究（2 项）

#### 3. CronCreateTool — 定时任务

**对比分析**：

| 维度 | Claude Code CronCreate | Scriptor 现有方案 |
|------|----------------------|-----------------|
| **触发语法** | cron 表达式 `"30 14 * * 1"` | 自然语言 `"周一下午2:30"` 或相对时间 `"3天后"` |
| **持久化** | `.claude/scheduled_tasks.json` | AstrBot 框架的 reminder 系统 |
| **适用场景** | 开发者精确调度 | 用户日常提醒 |

**结论**：🟡 **不建议直接照搬**

原因：
1. 我们的用户是聊天机器人用户，不是开发者——他们不会写 cron 表达式
2. 我们的 `create_reminder` + TODO 系统已经覆盖了定时需求
3. 如果要增强，应该是增强现有 reminder 的自然语言时间解析能力（如支持"每两周一"这种循环），而不是引入 cron

**可选优化方向**：
```
在 create_reminder 中增加循环提醒支持:
  remind_at: "every monday 9:00"    → 循环提醒
  remind_at: "2026-04-10 09:00"      → 一次性（现有）
```
这比引入完整的 cron 系统轻量得多。

---

#### 4. WebFetchTool — URL 内容获取 + 安全预批准

**Claude Code 设计**（[WebFetchTool.ts](file:///d:/PycharmProjects/Claude%20Code%20gai/src/tools/WebFetchTool/WebFetchTool.ts)）：
- 预批准 URL 白名单（用户事先允许的域名）
- 非白名单 URL 需要用户确认
- 内容自动截断（避免 Token 爆炸）

**Scriptor 现状**：
- `web_search_tool` 只做搜索，不支持直接获取 URL 内容
- 如果用户发了一个链接，AI 无法读取其内容

**结论**：🟡 **低优先级，但有实用价值**

可以作为一个轻量工具添加：
```
新增工具: web_fetch_tool(event, url, max_length=3000)
  - 获取 URL 的文本内容（类似 readability）
  - 过滤 HTML 标签，保留正文
  - 截断过长内容
  - 记录到记忆（如果用户要求）
```

**复杂度**：低（~40 行，主要依赖 requests + BeautifulSoup）

---

### 🟢 低价值 / 不建议采纳（7 项）

| 工具 | 不采纳原因 |
|------|-----------|
| **SendMessageTool** | Agent Swarm 多代理通信专用，我们是单实例聊天机器人，无此架构 |
| **AgentTool (Task)** | 上轮已分析——我们的单轮工具调用模式不需要子代理 |
| **TodoWrite/TodoRead** | 我们的 TODO.md 文件级管理 + 归档体系更完善 |
| **ExitPlanModeTool** | CLI/IDE 专属概念，聊天机器人无"计划模式" |
| **REPLTool** | 交互式代码执行——聊天机器人场景无此需求 |
| **ReadMcpResourceTool** | MCP 协议集成——目前我们没有 MCP 服务端 |
| **TungstenTool** | 平台专属数据库工具——与我们无关 |

---

## 三、最终推荐优先级

### 🏆 本轮推荐实施（按 ROI 排序）

| 优先级 | 改进项 | 预期收益 | 复杂度 | 建议 |
|--------|--------|---------|--------|------|
| **P0** | **ToolSearch（工具自省）** | 减少 AI 选错工具；支持"你能做什么"交互 | 中 | **本轮推荐** |
| **P1** | **SkillTool（技能宏调用）** | 从"被动读技能"升级为"主动调技能"；工具子集限制 | 中高 | **下一轮考虑** |
| **P2** | **WebFetch（URL 内容获取）** | 补充 web_search 的盲区——无法读取用户发的链接 | 低 | 有空再做 |
| **P3** | **Reminder 循环提醒** | 增强 create_reminder 支持"每周一"等循环 | 低 | 锦上添花 |

### ❌ 明确不做

- SendMessage / AgentTool / ExitPlanMode — 架构不兼容
- REPL / Tungsten / ReadMcpResource — 场景不存在
- Cron 完整实现 — 自然语言方案更适合我们的用户
