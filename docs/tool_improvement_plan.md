# Scriptor 工具系统改进方案 — 学习 Claude Code

> 基于 `docs/claude_code_tools_analysis.md` 的深度分析，结合 Scriptor 项目实际架构（聊天机器人插件，非 CLI 工具），制定的分阶段改进计划。

---

## 一、项目定位差异分析（为什么不能照搬）

| 维度 | Claude Code | Scriptor |
|------|-------------|----------|
| **产品形态** | 终端 CLI 工具，开发者面向 | 聊天机器人插件，用户面向 |
| **操作对象** | 任意代码仓库 | 用户记忆/笔记/群组工作文件 (`.md`) |
| **调用模式** | 持续多轮对话，上下文累积 | 单轮工具调用 + 热记忆注入 |
| **安全威胁** | 代码注入、NTLM 泄露、竞态条件 | 文件破坏、内容缩水、越权访问 |
| **性能瓶颈** | 启动速度、大文件 I/O | Token 消耗、API 延迟 |

**结论**：Claude Code 的 Bash 安全机制、Git 集成、Notebook 读写等与我们场景无关，**不应借鉴**。我们应聚焦于：文件操作可靠性、Token 效率、批量编辑能力。

---

## 二、筛选后的改进清单（4 项）

### ✅ 采纳项（高 ROI）

#### 改进 1：文件读取去重缓存
- **来源**：Claude Code `Read` 工具的 mtime 去重检测
- **问题**：当前 [file_read](file:///d:/PycharmProjects/AstrBot/data/plugins/astrbot_plugin_scriptor/tools/common/file_ops.py#L575-L654) 每次调用都执行磁盘 I/O + 文本截断，同一文件在同一轮对话中可能被多次读取（如先读全文再读指定行）
- **收益**：
  - 减少磁盘 I/O（尤其是频繁访问的 PROFILE.md / MEMORY.md）
  - 避免 Token 重复消耗（缓存命中时直接返回，不经过 `_truncate_output`）
  - 提升响应延迟（省去文件读取时间）
- **实现复杂度**：低（~30 行代码）
- **方案设计**：

```
缓存结构:
  _read_cache: dict[str, tuple[str, float]]   # key → (content, mtime)
  _CACHE_MAX_SIZE = 50                         # LRU 上限
  _CACHE_TTL = 300                             # 5 分钟过期

缓存 Key = f"{resolved_path}:{start_line or 0}:{end_line or 0}"

命中逻辑:
  1. 计算 cache_key
  2. 检查缓存是否存在
  3. 若存在，获取文件的当前 mtime
  4. 若 mtime 未变 → 返回缓存内容（跳过读取+截断）
  5. 若 mtime 变更或缓存不存在 → 正常读取 → 写入缓存 → 返回

失效策略:
  - file_write / file_edit / file_append 成功后 → 清除对应文件的缓存
  - 缓存满时淘汰最旧条目
```

- **涉及文件**：
  - `tools/common/file_ops.py` — 在 `file_read()` 函数头部添加缓存逻辑
  - `tools/common/file_ops.py` — 在 `file_write()`, `file_edit()`, `file_append()` 成功返回前添加缓存清除

---

#### 改进 2：MultiEdit 原子化多编辑工具
- **来源**：Claude Code `MultiEdit` 工具
- **问题**：当前 [file_edit_tool](file:///d:/PycharmProjects/AstrBot/data/plugins/astrbot_plugin_scriptor/mixins/tools_mixin.py#L281-L300) 只支持单次替换。当 AI 需要在一个文件中做多处修改时（如同时更新多个章节），必须多次调用 `file_edit`，每次都要重新读取文件、校验权限、检查缩水。效率低且中间状态不一致。
- **收益**：
  - 减少工具调用次数（N 处编辑 → 1 次调用）
  - 原子性保证：要么全部成功，要么全部不生效（避免半修改状态）
  - 减少重复的权限校验和缩水检测开销
- **实现复杂度**：中等（~80 行代码）
- **方案设计**：

```
新工具签名: multi_edit_tool(event, file_path, edits)

edits 参数格式:
[
  {
    "old_string": "要查找的文本（精确匹配）",
    "new_string": "替换后的文本"
  },
  {
    "old_string": "另一处查找文本",
    "new_string": "替换后的文本"
  }
]

执行流程:
  1. 权限校验 + 路径解析（复用现有逻辑）→ 一次性完成
  2. 读取文件原始内容（只读一次）
  3. 依次对 content 执行替换（使用已有的 _fuzzy_replace）
     - 任一替换失败 → 全部回滚，返回错误
  4. 最终缩水检测（对最终结果做一次检测）
  5. 最终结构校验（对最终结果做一次校验）
  6. 写入文件 + 更新搜索索引 + 清除读取缓存
  7. 返回汇总结果："✓ 已完成 3 处编辑"

安全继承:
  - 自动继承 _check_read_only_directory（只读目录拦截）
  - 自动继承 _check_content_shrinkage（防缩水）
  - 自动继承 _validate_file_structure（结构校验）
  - 自动继承 _fuzzy_replace（模糊匹配容错）
```

- **涉及文件**：
  - `tools/common/file_ops.py` — 新增 `multi_edit()` 函数
  - `mixins/tools_mixin.py` — 新增 `multi_edit_tool()` 方法（带 `@filter.llm_tool()` 装饰器）

---

#### 改进 3：file_edit 增加 replace_all 参数
- **来源**：Claude Code `Edit.replace_all`
- **问题**：当前 [file_edit](file:///d:/PycharmProjects/AstrBot/data/plugins/astrbot_plugin_scriptor/tools/common/file_ops.py) 使用 `str.count(old_text)` 计数，但实际替换只做了一次（Python `str.replace` 默认只替换第一个）。AI 如果想重命名一个变量出现 N 次，需要调用 N 次 `file_edit`。
- **收益**：
  - 批量重命名/替换场景从 N 次调用降为 1 次
  - 与 MultiEdit 互补（MultiEdit 用于不同位置的不同替换，replace_all 用于同一文本的多处替换）
- **实现复杂度**：极低（~5 行改动）
- **方案设计**：

```
file_edit 新增参数:
  replace_all: bool = False    # 是否全局替换

内部改动:
  # 原来:
  new_content = content.replace(old_text, new_text, 1)
  
  # 改为:
  count = -1 if replace_all else 1   # -1 表示全部替换
  new_content = content.replace(old_text, new_text, count)
  
  返回值调整:
  count = new_content.count(new_text) if replace_all else 1
  return f"✓ 已在 {resolved_path.name} 中替换 {count} 处"
```

- **涉及文件**：
  - `tools/common/file_ops.py` — `file_edit()` 函数签名 + 内部逻辑微调
  - `mixins/tools_mixin.py` — `file_edit_tool()` 方法签名同步更新

---

### 🟡 可选优化项（中 ROI）

#### 改进 4：写入前的父目录存在性验证
- **来源**：Claude Code `Bash` 的路径预检
- **问题**：当前 [file_write](file:///d:/PycharmProjects/AstrBot/data/plugins/astrbot_plugin_scriptor/tools/common/file_ops.py#L721) 和 [file_append](file:///d:/PycharmProjects/AstrBot/data/plugins/astrbot_plugin_scriptor/tools/common/file_ops.py) 直接调用 `resolved_path.write_text()` 或 `open(append)`，如果父目录不存在会抛出 `FileNotFoundError`，错误信息不够友好。
- **收益**：提供更清晰的错误提示，引导 AI 先用 `file_list` 确认目录结构
- **实现复杂度**：极低（~5 行代码）
- **方案设计**：

```
在 file_write 和 file_append 中，路径解析后、写入前添加:

if not resolved_path.parent.exists():
    return (
        f"❌ 错误：父目录 {resolved_path.parent.name} 不存在\n\n"
        f"请先用 file_list_tool 查看可用目录和文件列表。"
    )
```

---

## 三、明确不采纳项及原因

| Claude Code 特性 | 不采纳原因 |
|------------------|-----------|
| **Bash 工具（6 层权限 + UNC 拦截 + 设备黑名单）** | 我们通过 AstrBot 框架间接支持命令执行，不是直接暴露 Bash 接口；聊天机器人场景下命令执行需求极低 |
| **Agent/Task 子代理（无状态委托任务）** | 我们的工具调用是单轮模式（LLM 调用工具→返回结果→继续生成），没有持续的多轮 Agent 循环；子代理需要独立的 LLM 会话管理，成本高且与我们的热记忆架构冲突 |
| **NotebookRead/NotebookEdit** | 我们的文件全部是 `.md` 格式，不支持 Jupyter Notebook |
| **图片视觉呈现（多模态 Read）** | 依赖 AstrBot 框架的多模态消息能力，当前框架版本不一定支持；且用户在聊天场景中发送图片的需求极低 |
| **Write 强制"先读后写"** | 我们已有内容缩水检测（比"先读后写"更强的防护）；强制先读会增加一次不必要的工具调用 |
| **Grep/Glob 分离为两个工具** | 我们的 `file_search_tool` 已通过参数（is_regex/case_sensitive/context_lines）覆盖了两种场景，单一工具更简洁 |
| **TodoWrite/TodoRead（状态机 pending/in_progress/completed）** | 我们的 TODO 系统基于文件（TODO.md），已有归档机制和优先级体系，状态机反而增加复杂度 |
| **exit_plan_mode 计划模式** | 这是 IDE/CLI 交互特有的概念，聊天机器人没有"计划模式"的概念 |

---

## 四、实施计划（分阶段）

### Phase 1：快速见效（预计 0.5 天）

| 序号 | 改进项 | 涉及文件 | 工作量 |
|------|--------|----------|--------|
| 1.1 | `file_edit` 添加 `replace_all` 参数 | `file_ops.py` + `tools_mixin.py` | ~15 min |
| 1.2 | `file_write` / `file_append` 添加父目录验证 | `file_ops.py` | ~10 min |

**验收标准**：
- `file_edit("config.yaml", "port: 8080", "port: 9090", replace_all=True)` 能替换所有匹配项
- 写入不存在的父目录时返回友好提示而非抛异常

---

### Phase 2：核心能力提升（预计 1 天）

| 序号 | 改进项 | 涉及文件 | 工作量 |
|------|--------|----------|--------|
| 2.1 | 实现 `file_read` 去重缓存 | `file_ops.py` | ~45 min |
| 2.2 | 实现 `multi_edit` 函数 + `multi_edit_tool` | `file_ops.py` + `tools_mixin.py` | ~90 min |

**验收标准**：
- 同一文件同一范围连续两次 `file_read`，第二次从缓存返回（日志可见"命中读取缓存"）
- `file_edit` / `file_write` / `file_append` 成功后，对应文件的缓存被清除
- `multi_edit_tool` 传入 3 个编辑项，全部成功时返回"✓ 已完成 3 处编辑"
- `multi_edit_tool` 任一编辑项失败时，文件保持原样不变

---

### Phase 3：测试与文档（预计 0.5 天）

| 序号 | 任务 | 说明 |
|------|------|------|
| 3.1 | 编写单元测试 | 覆盖缓存命中/未命中/MultiEdit 成功/失败等场景 |
| 3.2 | 更新 System Prompt 工具说明 | 将新参数和新工具加入 Prompt Builder 的工具描述模板 |

---

## 五、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 缓存导致读到过期数据 | AI 基于旧内容做决策 | mtime 校验 + 写入即清除 + 5 分钟 TTL |
| MultiEdit 回滚不完整 | 文件处于半修改状态 | 替换前保存原始内容副本，失败时恢复 |
| replace_all 误用导致过度替换 | 大面积意外修改 | 保持默认 False，需 AI 显式开启 |

---

## 六、预期收益量化

| 指标 | 当前 | 改进后 |
|------|------|--------|
| 同一对话中重复读取同一文件的 Token 消耗 | 100%（每次都完整读取） | ↓ ~60%（缓存命中时零消耗） |
| 多处编辑的工具调用次数 | N 次（每处 1 次） | 1 次（MultiEdit） |
| 全局替换的工具调用次数 | N 次（每处 1 次） | 1 次（replace_all=True） |
| 写入到不存在目录的错误信息 | Python 异常堆栈 | 友好的中文提示 |
