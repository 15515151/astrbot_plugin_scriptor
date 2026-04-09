# Scriptor v2.0 综合增强计划

> 📅 制定日期: 2026-04-05
> 🎯 目标: 并发控制体系 + 三大新工具（ToolSearch / SkillTool / WebFetch）
> ⚠️ 原则: 先制定计划，不动代码

---

## 一、项目背景与现状诊断

### 1.1 当前架构痛点

| 痛点 | 严重程度 | 现状描述 |
|------|----------|----------|
| **并发无控制** | 🔴 致命 | SessionLockManager 已实现但未接入事件流，所有请求并行执行 |
| **API 配额风险** | 🔴 致命 | 10用户+2群同时触发 = 12个并发 LLM 请求，可能触发限速 |
| **同用户双聊冲突** | 🟡 中等 | 同一人私聊+群聊同时操作可能产生数据竞争 |
| **工具发现困难** | 🟡 中等 | LLM 不知道自己有哪些工具可用，容易"瞎猜" |
| **技能被动加载** | 🟡 中等 | 技能只能通过 Prompt 隐式触发，无法主动调用 |
| **URL 内容盲区** | 🟢 轻微 | web_search 只能搜索关键词，无法读取用户发的链接内容 |

### 1.2 已有基础设施（可复用）

```
✅ SessionLockManager (core/session_locks.py)
   - 会话级锁 (asyncio.Lock)
   - 待处理事件队列 (deque)
   - 过期会话清理
   - 状态机 (IDLE → PROCESSING → WAITING)
   → 问题: 未接入事件流！

✅ MemoryManager 文件锁 (core/memory_manager.py)
   - 按文件路径分配 asyncio.Lock
   - LRU 淘汰策略
   → 仅保护日记文件写入

✅ KnowledgeGraph Lock (core/knowledge_graph.py)
   - 单一 asyncio.Lock 保护图谱数据
   - 后台线程持久化

✅ 工具注册体系 (mixins/tools_mixin.py)
   - @filter.llm_tool() 装饰器
   - 40 个已注册工具
   - _rebind_mixin_tool_handlers() 自动绑定

✅ 技能系统 (skills/)
   - 5 个 SKILL.md 文件
   - AstrBot SkillManager 加载机制
   - _register_scriptor_skills() 自动注册
```

---

## 二、改进方案总览

### 2.1 四大模块架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    Scriptor v2.0 架构                            │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Module A: 并发控制系统                        │ │
│  │                                                           │ │
│  │  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐  │ │
│  │  │ SessionLock │    │ Global       │    │ Priority    │  │ │
│  │  │ Manager     │───▶│ Semaphore    │───▶│ Queue       │  │ │
│  │  │ (per-session)│    │ (max=5)      │    │ (admin >    │  │ │
│  │  └─────────────┘    └──────────────┘    │ private >   │  │ │
│  │                                         │ group)      │  │ │
│  │                                         └─────────────┘  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Module B: ToolSearch 工具                     │ │
│  │                                                           │ │
│  │  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐  │ │
│  │  │ Tool Index  │    │ Keyword      │    │ Smart       │  │ │
│  │  │ (40 tools)  │───▶│ Scoring      │───▶│ Ranking     │  │ │
│  │  │             │    │ Engine       │    │ & Filter    │  │ │
│  │  └─────────────┘    └──────────────┘    └─────────────┘  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Module C: SkillTool 技能宏                    │ │
│  │                                                           │ │
│  │  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐  │ │
│  │  │ Skill       │    │ Context      │    │ Execution   │  │ │
│  │  │ Registry    │───▶│ Builder      │───▶│ Modes       │  │ │
│  │  │ (5 skills)  │    │ (Prompt)     │    │ (inline/    │  │ │
│  │  │             │    │              │    │ forked)     │  │ │
│  │  └─────────────┘    └──────────────┘    └─────────────┘  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              Module D: WebFetch URL获取                    │ │
│  │                                                           │ │
│  │  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐  │ │
│  │  │ URL         │    │ Content      │    │ Security    │  │ │
│  │  │ Validator   │───▶│ Extractor   │───▶│ & Limits    │  │ │
│  │  │             │    │ (HTML→MD)    │    │             │  │ │
│  │  └─────────────┘    └──────────────┘    └─────────────┘  │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、Module A: 并发控制系统（最高优先级）

### 3.1 设计目标

| 目标 | 指标 | 说明 |
|------|------|------|
| **会话隔离** | 同一 session 串行 | 用户A私聊排队，不干扰群聊 |
| **全局限流** | 最大 N 并发 | 默认 5 个 LLM 请求同时执行 |
| **优先级调度** | admin > private > group | 管理员请求优先处理 |
| **拟人化体验** | 群内消息有序 | 同一群的消息按时间顺序回复 |
| **零侵入** | 不改核心逻辑 | 仅在事件入口/出口添加钩子 |

### 3.2 核心改动点

#### 改动 1: 激活 SessionLockManager 接入事件流

**涉及文件**: `mixins/events_mixin.py` 或 `main.py` 的 `global_recorder`

**改动逻辑**:
```python
@filter.event_message_type(filter.EventMessageType.ALL)
async def global_recorder(self, event: AstrMessageEvent):
    # 新增: 计算会话 ID
    session_id = self._compute_session_id(event)

    # 新增: 获取会话锁（阻塞等待）
    acquired = await self.session_lock_manager.acquire_session(
        session_id, wait=True
    )

    if not acquired:
        yield "⚠️ 系统繁忙，请稍后再试"
        return

    try:
        # 原有逻辑不变
        async for result in super().global_recorder(event):
            yield result
    finally:
        # 新增: 释放会话锁
        self.session_lock_manager.release_session(session_id)
```

**session_id 计算规则**:
```python
def _compute_session_id(self, event):
    """
    会话 ID 规则:
    - 私聊: "{uid}_private"
    - 群聊: "*_{group_id}"
    - WebUI: "webchat_{user_id}"
    - 定时任务: "scheduler_{task_id}"
    """
    uid = event.get_sender_id()
    gid = event.get_group_id()

    if gid and gid != "private":
        return f"*_{gid}"
    elif uid:
        return f"{uid}_private"
    else:
        return "unknown_session"
```

**效果演示**:
```
时间轴 →
T=0s  [用户A私聊] "帮我查xxx" → 获取锁 → 开始处理...
T=1s  [用户A群聊] "@bot 总结一下" → 排队等待（同一 uid 不同 session，可并行）
T=2s  [群聊1] [用户B] "谁在线?" → 获取锁 → 开始处理（不同群，可并行）
T=3s  [群聊1] [用户C] "我也想知道" → 排队等待（同一群，必须串行）✓
T=10s [用户A私聊] 处理完成 → 释放锁
T=11s [用户A群聊] 如果还在排队 → 获取锁 → 开始处理
```

#### 改动 2: 全局并发信号量

**新建文件**: `core/concurrency_guard.py`（或直接在 `session_locks.py` 扩展）

**设计**:
```python
class ConcurrencyGuard:
    """全局并发控制器"""

    def __init__(self, max_concurrent: int = 5):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0
        self._wait_queue: deque = deque()

    async def acquire(self, session_id: str, priority: int = 0):
        """
        获取全局并发槽位

        Args:
            session_id: 会话 ID
            priority: 优先级（数字越大越优先）
                - 100: 管理员命令
                - 50:  私聊
                - 10:  群聊
                - 0:   后台任务
        """
        # 优先级队列逻辑...
        await self._semaphore.acquire()
        self._active_count += 1

    def release(self):
        """释放全局并发槽位"""
        self._semaphore.release()
        self._active_count -= 1

    def get_stats(self) -> dict:
        return {
            "active": self._active_count,
            "waiting": len(self._wait_queue),
            "max": self._semaphore._value  # 内部值，实际需封装
        }
```

**集成位置**: 在 `before_llm_request` 钩子中调用

```python
@filter.on_llm_request()
async def before_llm_request(self, event, req):
    priority = self._compute_priority(event)
    await self.concurrency_guard.acquire(
        self._compute_session_id(event),
        priority=priority
    )
    # ...原有逻辑
```

#### 改动 3: 配置项扩展

**涉及文件**: `core/config_pydantic.py`

**新增配置**:
```python
class ConcurrencyConfig(BaseModel):
    """并发控制配置"""
    enabled: bool = True
    max_concurrent_llm: int = Field(
        default=5,
        ge=1,
        le=20,
        description="最大并发 LLM 请求数"
    )
    session_timeout_seconds: float = Field(
        default=3600.0,
        description="会话超时时间（秒）"
    )
    max_pending_per_session: int = Field(
        default=10,
        ge=1,
        le=50,
        description="每个会话最大排队数"
    )
    priority_weights: dict = Field(
        default_factory=lambda: {
            "admin": 100,
            "private": 50,
            "group": 10,
            "background": 0
        },
        description="优先级权重"
    )
```

#### 改动 4: 监控命令扩展

**涉及文件**: `mixins/commands_mixin.py`

**新增命令**:
```
/sc_concurrency          # 查看当前并发状态
  ├─ Active: 3/5         # 当前活跃请求数
  ├─ Waiting:            # 排队中的请求
  │   ├─ user_A_private (priority=50, wait=2s)
  │   └─ *gid_123 (priority=10, wait=5s)
  └─ Sessions:           # 所有会话状态
      ├─ user_A_private: PROCESSING
      ├─ *gid_123: WAITING (queue=2)
      └─ *gid_456: IDLE
```

### 3.3 并发场景测试矩阵

| 场景 | 预期行为 | 验证方法 |
|------|----------|----------|
| 10 用户同时私聊 | 5 个立即执行，5 个排队 | 日志检查 `acquire/release` |
| 同用户私聊+群聊 | 两个请求可并行（不同 session） | 检查 session_id 计算 |
| 同群 3 人同时发言 | 串行处理，按顺序回复 | 时间戳验证 |
| 管理员命令 vs 普通用户 | 管理员优先插入 | 优先级日志 |
| 后台复盘 vs 用户请求 | 用户优先，复盘让路 | `background` 优先级最低 |
| API 限速时 | 自动降级为排队 | Semaphore 超时处理 |

---

## 四、Module B: ToolSearch 工具自省系统

### 4.1 设计目标

| 目标 | 说明 |
|------|------|
| **工具发现** | LLM 能查询"我有哪些工具可用" |
| **智能匹配** | 根据用户意图推荐最合适的工具 |
| **减少幻觉** | 避免 LLM 瞎编不存在的工具名 |
| **零维护** | 工具注册后自动索引，无需手动更新 |

### 4.2 核心设计

#### 4.2.1 工具索引构建

**新建文件**: `tools/tool_search.py`

**数据结构**:
```python
@dataclass
class ToolIndexEntry:
    """工具索引条目"""
    name: str                          # 工具名 (如 "file_read_tool")
    display_name: str                  # 显示名 (如 "文件读取")
    description: str                   # 工具描述（从 docstring 提取）
    parameters: list[ToolParameter]    # 参数列表
    tags: set[str]                     # 关键词标签（自动提取+手动补充）
    category: str                      # 分类 (file/memory/web/admin/...)
    complexity: str                    # 复杂度 (low/medium/high)
    examples: list[str]                # 使用示例
    related_tools: list[str]           # 关联工具
```

**自动索引流程**:
```python
class ToolSearchEngine:
    def __init__(self):
        self._index: dict[str, ToolIndexEntry] = {}
        self._keyword_inverted_index: dict[str, set[str]] = {}

    def build_index(self, plugin_instance: ScriptorPlugin):
        """
        从 Mixin 类自动提取所有 @filter.llm_tool() 方法
        """
        import inspect

        # 遍历所有 Mixin 方法
        for mixin_class in [ToolsMixin, MediaToolsMixin, KnowledgeMixin, ...]:
            for attr_name in dir(mixin_class):
                method = getattr(mixin_class, attr_name)
                if hasattr(method, '_is_llm_tool'):  # 检查装饰器标记
                    entry = self._extract_tool_metadata(method)
                    self._index[entry.name] = entry
                    self._update_inverted_index(entry)

    def _extract_tool_metadata(self, method) -> ToolIndexEntry:
        """从方法的 docstring 和签名提取元数据"""
        docstring = inspect.getdoc(method) or ""
        signature = inspect.signature(method)

        # 解析参数
        parameters = []
        for param_name, param in signature.parameters.items():
            if param_name in ('event', 'plugin'):
                continue  # 跳过框架注入的参数
            parameters.append(ToolParameter(
                name=param_name,
                type=str(param.annotation),
                default=param.default,
                required=(param.default == inspect.Parameter.empty)
            ))

        # 从 docstring 提取标签（中文分词 + 关键词提取）
        tags = self._extract_tags(docstring)

        # 自动分类
        category = self._classify_tool(method.__name__, tags)

        return ToolIndexEntry(
            name=method.__name__,
            display_name=self._generate_display_name(method.__name__),
            description=docstring.split('\n\n')[0][:200],  # 第一段摘要
            parameters=parameters,
            tags=tags,
            category=category,
            complexity=self._estimate_complexity(parameters),
            examples=self._extract_examples(docstring),
            related_tools=[]
        )
```

#### 4.2.2 关键词评分引擎

```python
    async def search(self, query: str, limit: int = 5) -> list[ToolSearchResult]:
        """
        智能搜索工具

        Args:
            query: 自然语言查询（如 "我想读取一个文件"）
            limit: 返回数量上限

        Returns:
            按相关性排序的工具列表
        """
        query_tokens = self._tokenize(query)
        scores: dict[str, float] = {}

        for tool_name, entry in self._index.items():
            score = 0.0

            # 1. 名称精确匹配 (+3.0)
            if query.lower() in tool_name.lower():
                score += 3.0

            # 2. 标签匹配 (+2.0 × 匹配数)
            matched_tags = query_tokens & entry.tags
            score += len(matched_tags) * 2.0

            # 3. 描述语义匹配 (+1.0 × 关键词命中)
            desc_matches = sum(1 for t in query_tokens if t in entry.description)
            score += desc_matches * 1.0

            # 4. 参数名匹配 (+0.5)
            param_matches = sum(
                1 for p in entry.parameters
                if any(t in p.name.lower() for t in query_tokens)
            )
            score += param_matches * 0.5

            # 5. 分类权重调整
            category_boost = {
                'file': 1.2,      # 文件操作常用
                'memory': 1.1,    # 记忆检索常用
                'web': 0.9,
                'admin': 0.7,     # 管理工具较少用
            }
            score *= category_boost.get(entry.category, 1.0)

            if score > 0:
                scores[tool_name] = score

        # 返回 Top-K
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [
            ToolSearchResult(
                tool_name=name,
                score=score,
                entry=self._index[name],
                match_reason=self._explain_match(query, name, score)
            )
            for name, score in ranked
        ]
```

#### 4.2.3 LLM 工具接口定义

**在 `mixins/tools_mixin.py` 新增**:

```python
@filter.llm_tool()
@compact_result(max_tokens=get_tool_max_tokens, strategy="head_tail")
async def tool_search_tool(self, event: AstrMessageEvent,
                           query: str,
                           limit: int = 5):
    """
    搜索可用的工具。

    当你不确定应该使用哪个工具，或者想了解有哪些工具可用时，使用此工具。
    这能帮助你选择最合适的工具来完成任务。

    Args:
        query (str): 你的需求描述（自然语言）
            例如：
            - "我想读取文件"
            - "如何搜索记忆"
            - "有什么工具可以编辑文本"
        limit (int): 返回结果数量（默认 5）

    Returns:
        匹配的工具列表，包含名称、用途说明和关键参数
    """
    results = await self.tool_search_engine.search(query, limit)

    output = ["🔍 **找到以下工具：**\n"]
    for i, result in enumerate(results, 1):
        entry = result.entry
        output.append(f"\n**{i}. {entry.display_name}** (`{entry.name}`)")
        output.append(f"   用途: {entry.description[:100]}...")
        if entry.parameters:
            params_str = ", ".join(
                f"{p.name}{'*' if p.required else ''}"
                for p in entry.parameters[:5]
            )
            output.append(f"   参数: {params_str}")
        output.append(f"   相关度: {'⭐' * min(int(result.score), 5)}")

    return "\n".join(output)
```

### 4.3 工具分类体系

| 分类 | 包含工具 | 权重 | 说明 |
|------|----------|------|------|
| **file** | file_read/write/edit/append/search/list/multi_edit | 1.2 | 最高频使用 |
| **memory** | memory_search, usage_docs_search | 1.1 | 记忆相关 |
| **web** | web_search_tool, web_fetch_tool (新) | 0.9 | 网络操作 |
| **knowledge** | knowledge_add/search/research_* | 0.9 | 知识库 |
| **admin** | set_group_admin_tool, sudo_* | 0.7 | 管理功能 |
| **media** | media_upload/download/gallery | 0.8 | 媒体处理 |
| **schedule** | create_reminder/todo_* | 0.8 | 待办提醒 |
| **identity** | whoami/bind/unbind | 0.7 | 身份管理 |

### 4.4 与 Claude Code ToolSearch 对比

| 特性 | Claude Code | Scriptor 实现 |
|------|-------------|---------------|
| **索引方式** | 静态 JSON 清单 | 动态反射（自动从代码提取） |
| **搜索算法** | 关键词匹配 | 关键词 + 语义 + 分类加权 |
| **结果展示** | 纯文本列表 | 结构化 Markdown + 相关度星级 |
| **上下文感知** | 无 | 支持根据当前 session 推荐工具 |
| **学习能力** | 无 | 可记录高频工具提升权重 |

---

## 五、Module C: SkillTool 技能宏调用系统

### 5.1 设计目标

| 目标 | 说明 |
|------|------|
| **主动调用** | LLM 可显式调用技能，而非依赖隐式 Prompt 触发 |
| **上下文注入** | 将技能的 SKILL.md 作为系统提示注入 |
| **模式切换** | 支持 inline（同步）和 forked（异步子代理）两种模式 |
| **工具限制** | 执行期间仅暴露该技能所需的工具子集 |

### 5.2 核心设计

#### 5.2.1 技能注册表

**新建文件**: `tools/skill_tool.py`

```python
@dataclass
class SkillDefinition:
    """技能定义"""
    name: str                           # 技能标识符 (如 "scriptor-knowledge-research")
    display_name: str                   # 显示名 (如 "知识库与研究专家")
    description: str                    # 一句话描述
    full_prompt: str                    # 完整的 SKILL.md 内容
    required_tools: list[str]           # 该技能需要的工具白名单
    optional_tools: list[str]           # 可选工具
    execution_mode: str                 # "inline" 或 "forked"
    estimated_tokens: int               # 预估 token 消耗
    triggers: list[str]                 # 触发关键词（用于自动推荐）
    cooldown_seconds: int = 0           # 冷却时间（防止重复调用）


class SkillRegistry:
    """技能注册表"""

    def __init__(self, skills_dir: Path):
        self._skills: dict[str, SkillDefinition] = {}
        self._load_skills(skills_dir)

    def _load_skills(self, skills_dir: Path):
        """从 skills/ 目录加载所有 SKILL.md"""
        for skill_folder in skills_dir.iterdir():
            skill_md = skill_folder / "SKILL.md"
            if not skill_md.exists():
                continue

            content = skill_md.read_text(encoding='utf-8')
            meta, body = self._parse_frontmatter(content)

            skill = SkillDefinition(
                name=skill_folder.name,
                display_name=meta.get('name', skill_folder.name),
                description=meta.get('description', ''),
                full_prompt=body,
                required_tools=self._extract_required_tools(body),
                execution_mode=meta.get('execution_mode', 'inline'),
                triggers=self._extract_triggers(body),
                ...
            )
            self._skills[skill.name] = skill

    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        return self._skills.get(name)

    def recommend_skills(self, context: str) -> list[SkillDefinition]:
        """根据上下文推荐合适的技能"""
        # 基于 triggers + 关键词匹配
        ...
```

#### 5.2.2 LLM 工具接口

**在 `mixins/tools_mixin.py` 新增**:

```python
@filter.llm_tool()
async def skill_call_tool(self, event: AstrMessageEvent,
                          skill_name: str,
                          instruction: str,
                          mode: str = "auto"):
    """
    调用一个专业技能来完成特定任务。

    当你需要使用专业领域的知识或工作流时，使用此工具。
    这比你自己摸索更高效，因为技能包含了最佳实践和专用工具链。

    Args:
        skill_name (str): 技能名称（必须是已注册的技能）
            可用技能：
            - "scriptor-knowledge-research": 知识库与研究专家（提取知识、发起研究）
            - "scriptor-todo-schedule": 待办与日程管理（创建待办、设置提醒）
            - "scriptor-archive-manager": 档案馆管理（归档长文、查询历史）
            - "scriptor-media-gallery": 媒体画廊（上传图片、管理相册）
            - "scriptor-group-admin": 群组管理员（权限管理、成员管理）
        instruction (str): 具体指令（告诉技能要做什么）
            例如："把用户说的这个偏好记录下来"
        mode (str): 执行模式
            - "auto": 自动选择（默认）
            - "inline": 同步执行，返回完整结果
            - "forked": 异步后台执行，立即返回任务ID

    Returns:
        技能执行结果或任务跟踪信息
    """
    skill = self.skill_registry.get_skill(skill_name)
    if not skill:
        return f"❌ 未找到技能: {skill_name}。可用技能: {list(self.skill_registry.list_skills())}"

    # 检查冷却时间
    if skill.cooldown_seconds > 0:
        if not self.skill_cooldown_manager.can_execute(skill_name, event):
            return f"⏳ 技能 {skill_name} 正在冷却中，请稍后再试"

    # 根据 mode 选择执行方式
    if mode in ("auto", "inline"):
        result = await self._execute_skill_inline(event, skill, instruction)
    elif mode == "forked":
        task_id = await self._execute_skill_forked(event, skill, instruction)
        result = f"✅ 技能已在后台启动，任务ID: {task_id}。可用 skill_status 查询进度。"
    else:
        return f"❌ 无效的执行模式: {mode}"

    return result
```

#### 5.2.3 Inline 执行模式（同步）

```python
async def _execute_skill_inline(self, event, skill: SkillDefinition, instruction: str):
    """
    同步执行技能：将技能 Prompt 注入，限制工具集，单轮/多轮执行
    """
    # 1. 构建技能专属上下文
    system_prompt = f"""你现在是 {skill.display_name}。

{skill.full_prompt}

【当前任务】
{instruction}

【可用工具】
你只能使用以下工具：{', '.join(skill.required_tools)}
如果需要其他功能，请告知用户无法完成。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": instruction}
    ]

    # 2. 限制工具集（关键！）
    original_tool_whitelist = self._get_current_tool_whitelist()
    self._set_tool_whitelist(skill.required_tools + skill.optional_tools)

    try:
        # 3. 执行 LLM 调用循环（最多 5 轮工具调用）
        for i in range(5):
            response = await self._call_llm_with_tools(messages)

            if not response.tool_calls:
                break  # 无工具调用，结束

            # 4. 执行工具并收集结果
            for tool_call in response.tool_calls:
                tool_result = await self._execute_single_tool(tool_call, event)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": str(tool_result)
                })

            messages.append({
                "role": "assistant",
                "content": response.completion_text
            })

        final_response = response.completion_text or "（技能执行完成，无额外输出）"

        # 5. 记录冷却
        self.skill_cooldown_manager.record_execution(skill.name, event)

        return f"🎯 **[{skill.display_name}] 执行结果**\n\n{final_response}"

    finally:
        # 6. 恢复原始工具集
        self._set_tool_whitelist(original_tool_whitelist)
```

#### 5.2.4 Forked 执行模式（异步子代理）

```python
async def _execute_skill_forked(self, event, skill: SkillDefinition, instruction: str) -> str:
    """
    异步执行技能：创建后台任务，立即返回
    """
    import uuid
    task_id = f"skill_{uuid.uuid4().hex[:8]}"

    # 创建后台协程
    async def background_task():
        try:
            result = await self._execute_skill_inline(event, skill, instruction)
            self.skill_task_store.complete(task_id, result)
            # 可选：主动推送结果给用户
            await self._notify_user(event, f"✅ 后台任务 {task_id} 完成:\n{result}")
        except Exception as e:
            self.skill_task_store.fail(task_id, str(e))

    # 启动后台任务
    task = asyncio.create_task(background_task())
    self.skill_task_store.add(task_id, task)

    return task_id
```

### 5.3 技能触发器自动推荐

在 `before_llm_request` 钩子中加入智能推荐：

```python
@filter.on_llm_request()
async def before_llm_request(self, event, req):
    # 检测是否应该推荐技能
    user_message = event.message_str
    recommended = self.skill_registry.recommend_skills(user_message)

    if recommended:
        # 在 System Prompt 末尾追加提示
        hint = "\n\n💡 **技能推荐**: "
        hint += ", ".join([f"[{s.name}] {s.description}" for s in recommended])
        hint += "\n   如需使用，可调用 skill_call_tool"

        req.provider_message.messages[0]['content'] += hint
```

---

## 六、Module D: WebFetch URL 内容获取

### 6.1 设计目标

| 目标 | 说明 |
|------|------|
| **URL 内容读取** | 补充 web_search 的盲区——无法读取用户发的链接 |
| **HTML 转 Markdown** | 将网页转换为 LLM 友好的格式 |
| **安全限制** | 防止 SSRF、无限重定向、超大页面 |
| **缓存优化** | 相同 URL 短时间内不重复抓取 |

### 6.2 核心设计

#### 6.2.1 安全策略

```python
@dataclass
class WebFetchConfig:
    """WebFetch 安全配置"""
    max_content_length: int = 100 * 1024  # 100KB 上限
    timeout_seconds: float = 15.0
    max_redirects: int = 3
    allowed_schemes: tuple = ("http", "https")
    blocked_domains: set = field(default_factory=lambda: {
        "localhost", "127.0.0.1", "0.0.0.0",  # 防止内网探测
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",  # 私网地址
    })
    user_agent: str = "ScriptorBot/1.0 (Educational Purpose)"
    cache_ttl_seconds: int = 300  # 5分钟缓存
    rate_limit_rpm: int = 20  # 每分钟最多 20 次
```

#### 6.2.2 内容提取器

**新建文件**: `tools/web_fetch_tool.py`

```python
import aiohttp
import re
from bs4 import BeautifulSoup
import markdownify

class WebFetcher:
    """网页内容获取器"""

    def __init__(self, config: WebFetchConfig):
        self.config = config
        self._cache: dict[str, tuple[str, float]] = {}  # url → (content, timestamp)
        self._rate_limiter = TokenBucketLimiter(config.rate_limit_rpm)

    async def fetch(self, url: str) -> WebFetchResult:
        """
        获取并转换网页内容

        Args:
            url: 目标 URL

        Returns:
            WebFetchResult 包含 title, content, metadata
        """
        # 1. 安全校验
        self._validate_url(url)

        # 2. 速率限制
        await self._rate_limiter.acquire()

        # 3. 缓存检查
        cached = self._get_from_cache(url)
        if cached:
            return cached

        # 4. HTTP 请求
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": self.config.user_agent},
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds),
                max_redirects=self.config.max_redirects,
            ) as resp:
                resp.raise_for_status()
                html = await resp.read()

                # 5. 内容长度检查
                if len(html) > self.config.max_content_length:
                    html = html[:self.config.max_content_length]

                # 6. HTML → Markdown 转换
                content = self._html_to_markdown(html, url)

                # 7. 元数据提取
                title = self._extract_title(html)
                metadata = self._extract_metadata(html, url)

                result = WebFetchResult(
                    url=url,
                    title=title,
                    content=content,
                    metadata=metadata,
                    content_length=len(content),
                    fetched_at=datetime.now()
                )

                # 8. 缓存
                self._put_cache(url, result)

                return result

    def _html_to_markdown(self, html_bytes: bytes, base_url: str) -> str:
        """将 HTML 转换为精简 Markdown"""
        soup = BeautifulSoup(html_bytes, 'html.parser')

        # 移除噪声元素
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
            tag.decompose()

        # 提取主要内容（启发式算法）
        main_content = self._extract_main_content(soup)

        # 转换为 Markdown
        markdown = markdownify.markdownify(str(main_content), heading_style="ATX")

        # 清理多余空行
        markdown = re.sub(r'\n{3,}', '\n\n', markdown).strip()

        # 截断过长内容
        if len(markdown) > 8000:
            markdown = markdown[:8000] + "\n\n... (内容已截断)"

        return markdown

    def _extract_main_content(self, soup) -> Tag:
        """启发式提取主要内容区域"""
        # 优先查找 <article>, <main>, role="main"
        for selector in ['article', 'main', '[role="main"]']:
            main = soup.select_one(selector)
            if main:
                return main

        # 回退到 <body>
        return soup.body or soup
```

#### 6.2.3 LLM 工具接口

**在 `mixins/tools_mixin.py` 新增**:

```python
@filter.llm_tool()
@compact_result(max_tokens=get_tool_max_tokens, strategy="head_tail")
async def web_fetch_tool(self, event: AstrMessageEvent,
                         url: str,
                         extract: str = "auto"):
    """
    获取指定 URL 的网页内容。

    当用户发送了一个链接，或者需要读取某个网页的具体内容时使用此工具。
    注意：这不同于 web_search_tool（搜索引擎），本工具是直接读取网页原文。

    Args:
        url (str): 要获取的网页 URL（必须以 http:// 或 https:// 开头）
        extract (str): 提取模式
            - "auto": 自动判断（默认）
            - "text": 仅提取纯文本
            - "main": 提取主要内容区域
            - "full": 提取完整页面（可能很长）

    Returns:
        网页的标题和正文内容（Markdown 格式），或错误信息

    Raises:
        ValueError: URL 格式无效或不安全
        TimeoutError: 请求超时
        ContentTooLargeError: 内容过大
    """
    from .tools.web_fetch_tool import WebFetcher, WebFetchConfig

    config = WebFetchConfig()
    fetcher = WebFetcher(config)

    try:
        result = await fetcher.fetch(url)

        output = [
            f"📄 **网页标题**: {result.title}",
            f"🔗 **来源**: {result.url}",
            f"",
            f"**内容预览**:",
            f"",
            result.content
        ]

        if result.metadata.get('author'):
            output.insert(3, f"✍️ **作者**: {result.metadata['author']}")

        return "\n".join(output)

    except ValueError as e:
        return f"❌ URL 无效或不安全: {e}"
    except Exception as e:
        return f"❌ 获取网页失败: {e}"
```

### 6.3 与现有 web_search_tool 的关系

```
                    ┌─────────────────────┐
                    │   用户需求          │
                    └─────────┬───────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
        ┌───────────┐  ┌───────────┐  ┌───────────┐
        │web_search │  │web_fetch  │  │  用户发了  │
        │ _tool     │  │ _tool     │  │  一个链接  │
        │           │  │           │  │           │
        │用途:      │  │用途:      │  │触发:      │
        │关键词搜索 │  │读取URL内容 │  │自动检测   │
        │SearXNG    │  │HTTP请求   │  │URL正则   │
        └───────────┘  └───────────┘  └───────────┘
                │             │
                ▼             ▼
        返回搜索结果列表   返回网页正文
        (标题+摘要+链接)   (Markdown格式)
```

**协作场景示例**:
```
用户: "帮我看看这篇文章说了什么 https://example.com/article/123"

LLM 思考过程:
1. 检测到 URL → 调用 web_fetch_tool(url="https://example.com/article/123")
2. 获取文章内容后 → 总结要点
3. 如果需要更多背景 → 调用 web_search_tool(query="文章主题 相关背景")

最终回复: 结合两方面的信息给出全面回答
```

---

## 七、实施路线图

### 7.1 阶段划分

```
Phase 1 (P0): 并发控制系统 ────────────────────── [预计 2-3 天]
  │
  ├─ Step 1.1: 激活 SessionLockManager
  │   └─ 涉及: events_mixin.py, base.py
  │
  ├─ Step 1.2: 实现全局并发信号量
  │   └─ 新建: core/concurrency_guard.py
  │
  ├─ Step 1.3: 配置项扩展
  │   └─ 涉及: config_pydantic.py, _conf_schema.json
  │
  └─ Step 1.4: 监控命令 + 测试
      └─ 涉及: commands_mixin.py, tests/

Phase 2 (P1): ToolSearch 工具 ─────────────────── [预计 2 天]
  │
  ├─ Step 2.1: 工具索引引擎
  │   └─ 新建: tools/tool_search.py
  │
  ├─ Step 2.2: 关键词评分算法
  │   └─ 涉及: tool_search.py
  │
  └─ Step 2.3: LLM 工具接口 + 测试
      └─ 涉及: tools_mixin.py, tests/

Phase 3 (P2): SkillTool 技能宏 ────────────────── [预计 3 天]
  │
  ├─ Step 3.1: 技能注册表
  │   └─ 新建: tools/skill_tool.py
  │
  ├─ Step 3.2: Inline 执行模式
  │   └─ 涉及: skill_tool.py, tools_mixin.py
  │
  ├─ Step 3.3: Forked 执行模式
  │   └─ 涉及: skill_tool.py
  │
  └─ Step 3.4: 冷却机制 + 推荐 + 测试
      └─ 涉及: events_mixin.py, tests/

Phase 4 (P3): WebFetch URL获取 ────────────────── [预计 1-2 天]
  │
  ├─ Step 4.1: 安全策略 + 内容提取
  │   └─ 新建: tools/web_fetch_tool.py
  │
  └─ Step 4.2: LLM 工具接口 + 测试
      └─ 涉及: tools_mixin.py, tests/
```

### 7.2 依赖关系

```
Phase 1 (并发控制)
    │
    ├── 无依赖，可独立实施
    │
    ▼
Phase 2 (ToolSearch) ◄──── Phase 3 (SkillTool)
    │                         │
    │  可独立实施              │  依赖 Phase 2 的工具索引
    │                         │
    ▼                         ▼
Phase 4 (WebFetch) ──────────┴───────────────────
    │
    └── 完全独立，可与任意 Phase 并行
```

### 7.3 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **SessionLock 阻塞主线程** | 中 | 高 | 设置超时机制 + 异步等待 |
| **工具索引性能** | 低 | 中 | 启动时预构建 + 缓存 |
| **SkillTool 工具白名单复杂度** | 中 | 中 | 先实现简单版，后续迭代 |
| **WebFetch SSRF 攻击** | 低 | 高 | 严格的域名黑名单 + 网络隔离 |
| **全局信号量导致饥饿** | 低 | 中 | 优先级队列 + 公平调度 |
| **向后兼容性** | 低 | 高 | 所有新功能可通过配置开关禁用 |

---

## 八、验收标准

### 8.1 并发控制验收

- [ ] **C1**: 同一用户的私聊请求严格串行（测试脚本模拟 5 个并发请求）
- [ ] **C2**: 不同用户的请求可真正并行（验证响应时间 < 2x 单请求）
- [ ] **C3**: 全局并发数不超过配置上限（监控日志确认）
- [ ] **C4**: 管理员命令优先于普通用户（延迟对比测试）
- [ ] **C5**: `/sc_concurrency` 命令正确显示实时状态
- [ ] **C6**: 异常情况下锁不会泄漏（finally 块保证释放）

### 8.2 ToolSearch 验收

- [ ] **T1**: 搜索"读文件"返回 file_read_tool 且排名第一
- [ ] **T2**: 搜索"记忆"返回 memory_search 和 usage_docs_search
- [ ] **T3**: 搜索不存在的能力返回空列表（不崩溃）
- [ ] **T4**: 新注册的工具自动出现在索引中（无需手动维护）
- [ ] **T5**: 结果包含工具名称、用途、关键参数、相关度星级

### 8.3 SkillTool 验收

- [ ] **S1**: Inline 模式下正确执行技能并返回结果
- [ ] **S2**: Forked 模式下返回任务 ID，后台执行完成
- [ ] **S3**: 执行期间工具集被正确限制（无法调用白名单外工具）
- [ ] **S4**: 冷却期内重复调用返回友好提示
- [ ] **S5**: 不存在的技能名称返回错误 + 可用技能列表
- [ ] **S6**: 技能上下文正确注入（SKILL.md 内容可见）

### 8.4 WebFetch 验收

- [ ] **W1**: 成功获取 HTTP/HTTPS 网页并转为 Markdown
- [ ] **W2**: 拒绝访问 localhost/私有地址（SSRF 防护）
- [ ] **W3**: 超大页面自动截断（>100KB）
- [ ] **W4**: 请求超时（>15s）返回错误而非卡死
- [ ] **W5**: 相同 URL 5 分钟内使用缓存
- [ ] **W6**: 速率限制生效（>20次/分钟返回 429）

---

## 九、配置模板

### 9.1 新增配置项（_conf_schema.json 扩展）

```json
{
  "concurrency": {
    "enabled": true,
    "max_concurrent_llm": 5,
    "session_timeout_seconds": 3600,
    "max_pending_per_session": 10,
    "priority_weights": {
      "admin": 100,
      "private": 50,
      "group": 10,
      "background": 0
    }
  },
  "tool_search": {
    "enabled": true,
    "auto_recommend": true,
    "max_results": 5,
    "cache_enabled": true
  },
  "skill_tool": {
    "enabled": true,
    "default_mode": "inline",
    "cooldown_seconds": 30,
    "max_inline_rounds": 5,
    "forked_timeout_seconds": 120
  },
  "web_fetch": {
    "enabled": true,
    "max_content_kb": 100,
    "timeout_seconds": 15,
    "cache_ttl_seconds": 300,
    "rate_limit_rpm": 20,
    "blocked_domains": [
      "localhost",
      "127.0.0.1",
      "*.internal"
    ]
  }
}
```

### 9.2 向后兼容保证

所有新功能均可通过配置独立开关：

```yaml
# 保守模式（完全兼容旧版本）
concurrency:
  enabled: false          # 关闭并发控制
tool_search:
  enabled: false          # 关闭工具搜索
skill_tool:
  enabled: false          # 关闭技能调用
web_fetch:
  enabled: false          # 关闭 URL 获取
```

---

## 十、总结

### 10.1 核心价值

| 模块 | 解决的问题 | 预期收益 |
|------|------------|----------|
| **并发控制** | 多用户/多群同时使用的混乱 | 系统稳定性 ↑↑↑，API 成本 ↓↓，用户体验 ↑↑ |
| **ToolSearch** | LLM 选错工具或不知道有某工具 | 工具准确率 ↑↑，减少无效调用 ↓↓ |
| **SkillTool** | 技能只能隐式触发，效率低 | 任务完成速度 ↑↑，专业化程度 ↑↑ |
| **WebFetch** | 无法读取用户发的链接 | 信息完整性 ↑↑，用户体验 ↑ |

### 10.2 工作量估算

| Phase | 复杂度 | 预计工时 | 文件变更数 |
|-------|--------|----------|------------|
| Phase 1: 并发控制 | ★★★☆☆ | 2-3 天 | ~5 个文件修改 |
| Phase 2: ToolSearch | ★★☆☆☆ | 2 天 | 1 新建 + 1 修改 |
| Phase 3: SkillTool | ★★★★☆ | 3 天 | 1 新建 + 2 修改 |
| Phase 4: WebFetch | ★★☆☆☆ | 1-2 天 | 1 新建 + 1 修改 |
| **合计** | | **8-10 天** | **4 新建 + ~7 修改** |

### 10.3 下一步行动

**确认本计划后，建议按以下顺序开始施工**：

1. ✅ **Phase 1 先行**（并发控制影响最广，且已有基础设施）
2. ✅ **Phase 4 次之**（WebFetch 最简单，快速见效）
3. ✅ **Phase 2 第三**（ToolSearch 为 SkillTool 打基础）
4. ✅ **Phase 3 最后**（SkillTool 依赖前两者成熟）

---

**计划制定完成，等待确认后开始实施！** 🚀
