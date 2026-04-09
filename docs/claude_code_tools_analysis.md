# Claude Code 工具系统 vs Scriptor 工具系统 - 对比分析与借鉴建议

## 📊 总体对比

| 维度 | Claude Code | Scriptor (我们的项目) |
|------|-------------|----------------------|
| **工具数量** | 43+ 个核心工具 | 50+ 个工具（更全面） |
| **工具类型** | 文件操作、搜索、Bash、Git、Web、Agent 等 | 文件操作、搜索、记忆管理、知识图谱、媒体管理、Web 等 |
| **权限系统** | 6 层权限检查 + Hook 拦截 | 3 层权限（超级管理员/群管/普通用户）+ 文件级权限 |
| **结果压缩** | 30000 字符截断 | 动态 Token 控制（8K 阈值，可配置）+ 头尾保留策略 |
| **缓存优化** | LRU 缓存 + 去重检测 | Prompt Caching 静动分离 + 优先级梯度 |

---

## 🔧 核心工具对比

### 1. 文件读取工具

#### Claude Code 的 `Read` 工具
```typescript
// 特点：
- 默认读取 2000 行
- 支持 offset 和 limit 参数
- 自动检测图片文件并视觉呈现
- Jupyter 笔记本专用读取器（NotebookRead）
- 行号格式：空格 + 行号 + 制表符
```

**关键设计亮点**：
- ✅ **读取去重机制**：同一文件同一范围不重复读取（检查 mtime 时间戳）
- ✅ **智能截断**：超过 2000 行自动提示，引导使用范围参数
- ✅ **多模态支持**：读取图片时自动触发视觉模型

#### Scriptor 的 `file_read_tool`
```python
# 当前实现：
- 支持起始/结束行号
- 可选行号显示
- 支持 skills/目录只读访问
- 支持全局/群组/个人三级路径
```

**差距分析**：
- ❌ 缺少读取去重缓存（可能重复读取相同内容）
- ❌ 缺少图片文件的视觉呈现
- ✅ 已支持渐进式披露（从目录索引中选择文件）
- ✅ 已支持 YAML 元数据解析

---

### 2. 文件编辑工具

#### Claude Code 的 `Edit` / `MultiEdit`
```typescript
// Edit - 单次替换
{
  file_path: string;
  old_string: string;
  new_string: string;
  replace_all?: boolean;  // 批量替换
}

// MultiEdit - 多次编辑原子操作
{
  file_path: string;
  edits: [{
    old_string: string;
    new_string: string;
    replace_all?: boolean;
  }]
}
```

**关键设计亮点**：
- ✅ **原子操作**：MultiEdit 要么全部成功，要么全部失败
- ✅ **replace_all 参数**：支持批量替换（重命名变量等场景）
- ✅ **行号前缀处理**：明确指出 Read 工具输出中的行号前缀格式，避免匹配错误
- ✅ **严格校验**：old_string 必须精确匹配（包括空白字符）

#### Scriptor 的 `file_edit_tool`
```python
# 当前实现：
- 简单的查找替换
- 缺少 replace_all 参数
- 缺少多编辑原子操作
```

**改进建议**：
1. 🟡 **添加 `replace_all` 参数**：支持批量替换
2. 🟡 **实现 `MultiEdit`**：原子化的多次编辑操作
3. 🟢 **增加行号前缀说明**：在文档中明确指出匹配规则

---

### 3. 文件写入工具

#### Claude Code 的 `Write`
```typescript
// 特点：
- 强制先读取后写入（避免误操作）
- 禁止主动创建文档文件（.md/.README）
- 支持创建新文件（空 old_string）
- 禁止 emoji（除非明确要求）
```

**关键设计亮点**：
- ✅ **防呆设计**：必须先 Read 才能 Write（覆盖已有文件时）
- ✅ **文档克制**：禁止主动创建文档文件（避免仓库污染）
- ✅ **创建新文件语法**：空 old_string + 新路径 = 创建文件

#### Scriptor 的 `file_write_tool`
```python
# 当前实现：
- 禁止写入 skills/templates/目录
- 支持 YAML 元数据头规范
- 内容缩水检测（防止误删）
```

**对比优势**：
- ✅ Scriptor 的 YAML 元数据规范更完善（summary/keywords/created）
- ✅ 内容缩水检测是 Claude Code 没有的
- 🟡 缺少"先读后写"的强制检查（可以考虑添加）

---

### 4. 搜索工具

#### Claude Code 的 `Grep` / `Glob`
```typescript
// Grep - 内容搜索
{
  pattern: string;        // 正则表达式
  path?: string;
  include?: string;       // 文件类型过滤，如 "*.js"
}

// Glob - 文件名匹配
{
  pattern: string;        // Glob 模式，如 "src/**/*.ts"
  path?: string;
}
```

**关键设计亮点**：
- ✅ **明确分工**：Grep 搜内容，Glob 搜文件名
- ✅ **强烈推荐 ripgrep**：文档中明确指出"如果用 grep，STOP，先用 rg"
- ✅ **多工具并发**：鼓励同时调用多个搜索工具提升性能

#### Scriptor 的 `file_search_tool`
```python
# 当前实现：
- 单一工具支持多种模式（正则/大小写/上下文）
- 基于 ripgrep
```

**改进建议**：
1. 🟢 **保持现状**：单一工具更简洁，参数已足够灵活
2. 🟡 **文档优化**：可以像 Claude Code 一样，在文档中明确推荐场景

---

### 5. Bash 工具

#### Claude Code 的 `Bash`
```typescript
{
  command: string;
  timeout?: number;       // 最大 10 分钟
  description: string;    // 5-10 字描述
}
```

**关键设计亮点**：
- ✅ **路径验证**：创建文件/目录前，先用 LS 验证父目录存在
- ✅ **引号规范**：明确要求带空格路径必须用双引号
- ✅ **超时控制**：默认 2 分钟，最大 10 分钟
- ✅ **输出截断**：超过 30000 字符自动截断
- ✅ **强烈推荐别名**：避免使用 find/grep/ls/cat，改用专用工具

**安全机制**：
- 6 层权限检查
- UNC 路径拦截（防止 NTLM 凭据泄漏）
- 设备文件黑名单（防止无限读取）
- 原子写入（防止竞态条件）

#### Scriptor 的 Bash 支持
```python
# 当前实现：
- 通过 AstrBot 框架的 Bash 工具
- 缺少明确的路径验证和引号规范
```

**改进建议**：
1. 🟡 **添加路径验证步骤**：在文件操作前先验证目录存在
2. 🟡 **文档规范化**：明确引号使用规范
3. 🟢 **超时控制**：AstrBot 可能已有，需要检查

---

### 6. Agent 工具（子代理）

#### Claude Code 的 `Task` / `Agent`
```typescript
// 特点：
- 无状态调用（一次性任务）
- 详细描述任务（包含期望返回格式）
- 明确告知是研究还是写代码
- 支持并发调用多个 Agent
- 结果不可见（需主动转述给用户）
```

**使用场景指导**：
- ✅ **推荐使用**：搜索不确定的关键词、"哪个文件包含 X"类问题
- ❌ **不推荐使用**：读取具体文件路径、搜索具体类定义

**关键设计亮点**：
- ✅ **无状态设计**：每次调用都是独立的，避免上下文污染
- ✅ **详细任务描述**：要求包含完整的任务描述和期望输出格式
- ✅ **并发优化**：鼓励同时调用多个 Agent 提升性能

#### Scriptor 的 Agent 支持
```python
# 当前实现：
- 缺少专用的子代理工具
- 所有工具都在同一上下文中执行
```

**改进建议**：
1. 🔴 **高优先级新增**：实现 `delegate_task` 工具
   - 适用于复杂搜索任务
   - 无状态调用，避免上下文污染
   - 支持并发执行多个子任务

---

### 7. Todo 工具

#### Claude Code 的 `TodoWrite` / `TodoRead`
```typescript
// TodoWrite
{
  todos: [{
    content: string;
    id: string;
    status: "pending" | "in_progress" | "completed";
  }]
}
```

**关键设计亮点**：
- ✅ **状态追踪**：pending → in_progress → completed
- ✅ **唯一 ID**：每个任务有唯一标识符
- ✅ **批量更新**：一次性更新整个 todo 列表

#### Scriptor 的 TODO 系统
```python
# 当前实现：
- 独立的 TODO.md 文件管理
- 支持热记忆注入（System Prompt 中）
- 支持已完成任务归档
```

**对比分析**：
- ✅ Scriptor 的 TODO 系统更完善（文件级管理 + 归档机制）
- 🟡 可以借鉴状态机设计（pending/in_progress/completed）
- 🟢 已支持优先级和跨群任务

---

### 8. Web 工具

#### Claude Code 的 `WebFetch` / `WebSearch`
```typescript
// WebFetch
{
  url: string;
}

// WebSearch
{
  query: string;
}
```

**关键设计亮点**：
- ✅ **简单直接**：URL 或关键词即可
- ✅ **结果截断**：自动摘要，避免过长
- ✅ **信任链**：明确说明"Agent 的输出一般可信"

#### Scriptor 的 `web_search_tool`
```python
# 当前实现：
- 支持搜索深度（quick/normal/deep）
- 支持保存到记忆
- 支持 SearXNG 多引擎
```

**对比优势**：
- ✅ Scriptor 的搜索深度控制更精细
- ✅ 支持保存到记忆是独特优势
- ✅ 多引擎支持（SearXNG）更灵活

---

## 🎯 值得借鉴的设计思路

### 高优先级（建议立即实现）

#### 1. 文件读取去重缓存 🔴
**Claude Code 实现**：
```typescript
const existingState = readFileState.get(fullFilePath)
if (existingState && existingState.offset === offset && existingState.limit === limit) {
  const mtimeMs = await getFileModificationTimeAsync(fullFilePath)
  if (mtimeMs === existingState.timestamp) {
    return cachedContent  // 直接返回缓存
  }
}
```

**Scriptor 实现建议**：
```python
# 在 tools/common/file_ops.py 中添加
_read_cache = {}  # key: (file_path, start_line, end_line, mtime)

async def file_read(...):
    mtime = get_file_mtime(file_path)
    cache_key = (str(file_path), start_line, end_line, mtime)
    
    if cache_key in _read_cache:
        logger.debug(f"命中读取缓存：{file_path}")
        return _read_cache[cache_key]
    
    # 读取文件...
    result = ...
    
    # 写入缓存
    _read_cache[cache_key] = result
    return result
```

---

#### 2. MultiEdit 原子化多编辑 🔴
**使用场景**：重命名变量、批量更新函数签名等

**Scriptor 实现建议**：
```python
@filter.llm_tool()
async def multi_edit_tool(self, event: AstrMessageEvent,
                         file_path: str,
                         edits: list[dict]):
    """
    原子化的多次编辑操作。
    
    Args:
        file_path: 文件路径
        edits: 编辑操作列表，每项包含：
            - old_string: 要查找的文本
            - new_string: 替换后的文本
            - replace_all: 是否全局替换（可选）
    
    Returns:
        操作结果
    
    注意：
        - 所有编辑按顺序执行
        - 任何一项失败，所有编辑回滚
        - old_string 必须精确匹配（包括空白字符）
    """
    from ..tools.common.file_ops import multi_edit
    return await multi_edit(event, file_path, edits, self)
```

---

#### 3. 子代理（Delegate Task）工具 🔴
**使用场景**：复杂搜索、不确定的多步骤任务

**Scriptor 实现建议**：
```python
@filter.llm_tool()
async def delegate_task(self, event: AstrMessageEvent,
                       description: str,
                       prompt: str,
                       expected_output: str = None):
    """
    委托子代理执行独立任务（无状态调用）。
    
    适用于：
        - 搜索不确定的关键词（如"项目中所有 config 相关文件"）
        - 研究性问题（如"哪些文件使用了 logger 模块"）
        - 多步骤文件操作（如"找出所有测试文件并统计行数"）
    
    不适用于：
        - 读取具体文件路径（直接用 file_read_tool）
        - 搜索具体类定义（直接用 file_search_tool）
        - 编写代码（直接用 file_write_tool）
    
    Args:
        description: 任务简短描述（3-5 词）
        prompt: 详细任务描述（包含期望输出格式）
        expected_output: 期望的输出格式（可选）
    
    Returns:
        子代理的执行结果（不直接展示给用户，需转述）
    
    注意：
        - 子代理是无状态的，无法进行多轮对话
        - 支持并发调用多个子代理
        - 子代理的结果一般可信，但需自行判断
    """
    # 实现思路：
    # 1. 创建一个新的 LLM 会话（无历史上下文）
    # 2. 注入系统提示词 + 任务描述
    # 3. 调用 LLM 获取结果
    # 4. 返回结果给主代理
    pass
```

---

#### 4. 路径验证机制 🟡
**Claude Code 做法**：
```typescript
// 在创建文件/目录前
if (command.includes('mkdir') || command.includes('touch')) {
  const parentDir = path.dirname(targetPath)
  const lsResult = await lsTool.verify(parentDir)
  if (!lsResult.exists) {
    throw new Error(`父目录 ${parentDir} 不存在`)
  }
}
```

**Scriptor 实现建议**：
在 `file_write_tool` / `file_append_tool` 中添加：
```python
from pathlib import Path

async def file_write(...):
    # 路径验证
    full_path = resolve_file_path(file_path, uid, group_id)
    parent_dir = full_path.parent
    
    if not parent_dir.exists():
        return f"❌ 错误：父目录 {parent_dir} 不存在\n\n请先使用 file_list_tool 确认目录结构"
    
    # 继续执行写入...
```

---

### 中优先级（可选优化）

#### 5. 替换全局参数 🟡
为 `file_edit_tool` 添加 `replace_all` 参数：
```python
@filter.llm_tool()
async def file_edit_tool(self, event: AstrMessageEvent,
                        file_path: str,
                        old_text: str,
                        new_text: str,
                        replace_all: bool = False):  # 新增参数
    """
    Args:
        replace_all: 是否替换所有匹配项（默认 False，仅替换第一个）
    """
    from ..tools.common.file_ops import file_edit
    return await file_edit(event, file_path, old_text, new_text, replace_all, self)
```

---

#### 6. 输出截断提示优化 🟡
**Claude Code 做法**：
```
输出超过 30000 字符，已截断。
如需查看更多内容，请使用 offset 和 limit 参数分段读取。
```

**Scriptor 现状**：
已有类似提示，但可以更明确：
```python
if len(result) > max_lines:
    return (
        f"📄 文件内容过长，已显示前 {max_lines} 行\n\n"
        f"💡 **提示**：如需查看更多内容，请使用以下参数：\n"
        f"   - `start_line={max_lines + 1}` 从下一行开始\n"
        f"   - `end_line={max_lines + 500}` 限制读取范围"
    )
```

---

#### 7. 图片文件视觉呈现 🟡
**Claude Code 做法**：
```typescript
if (isImageFile(file_path)) {
  const imageBuffer = await fs.readFile(file_path)
  const base64 = imageBuffer.toString('base64')
  return {
    type: 'image',
    data: base64,
    mimeType: getMimeType(file_path)
  }
}
```

**Scriptor 实现建议**：
需要 AstrBot 框架支持多模态消息发送，暂时不是最优先级。

---

## 📋 总结与行动建议

### 立即实现（本周内）
1. ✅ **文件读取去重缓存** - 提升性能，避免重复 Token 消耗
2. ✅ **MultiEdit 原子化编辑** - 提升批量编辑可靠性
3. ✅ **Delegate Task 子代理** - 处理复杂搜索任务

### 近期优化（本月内）
4. 🟡 **路径验证机制** - 提升文件操作安全性
5. 🟡 **replace_all 参数** - 提升编辑灵活性
6. 🟡 **输出截断提示优化** - 提升用户体验

### 长期规划
7. 🟢 **图片视觉呈现** - 依赖框架支持
8. 🟢 **更细粒度的权限系统** - 6 层权限检查

---

## 🎓 学习心得

### Claude Code 的核心优势
1. **启动性能是一等公民**：快速路径 + 动态 import + 并行预取
2. **安全性纵深防御**：6 层权限 + Hook 拦截 + ML 分类器
3. **流式一切**：AsyncGenerator 贯穿整个消息流
4. **状态管理极简**：34 行自研 Store，Object.is() 变更检测
5. **上下文即生命线**：Memoized 系统上下文 + 三种压缩策略

### Scriptor 的独特优势
1. **记忆系统更完善**：长期记忆 + 短期记忆 + 档案馆三级架构
2. **知识图谱集成**：实体关系抽取 + 权重召回
3. **渐进式披露**：目录索引 + 按需读取
4. **Prompt Caching 优化**：静动分离 + 优先级梯度（100~90 定死）
5. **多群协作**：跨群待办 + 群组工作流

### 结论
**Scriptor 在记忆管理和上下文优化方面已经领先于 Claude Code**，但在工具细节（如读取缓存、原子编辑、子代理）方面还有提升空间。通过本次学习，我们有选择性地借鉴 3 个高优先级设计，将进一步提升工具系统的可靠性和性能。
