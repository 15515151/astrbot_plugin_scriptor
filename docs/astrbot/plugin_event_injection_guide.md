# Scriptor 插件事件注入指南

本文档介绍如何在 Scriptor 中使用事件注入机制与 AstrBot 深度集成。

---

## 目录

1. [事件系统概述](#事件系统概述)
2. [消息事件](#消息事件)
3. [LLM 事件](#llm-事件)
4. [生命周期事件](#生命周期事件)
5. [自定义事件](#自定义事件)

---

## 事件系统概述

Scriptor 使用 AstrBot 的事件系统来实现深度集成。事件系统允许你：

- 监听消息事件
- 拦截和修改 LLM 请求
- 在插件生命周期中执行自定义逻辑
- 创建和触发自定义事件

---

## 消息事件

### 全局消息记录器

Scriptor 使用 `@filter.event_message_type` 装饰器来监听所有消息：

```python
from astrbot.api.event import filter, AstrMessageEvent

@filter.event_message_type(filter.EventMessageType.ALL)
async def global_recorder(self, event: AstrMessageEvent):
    """全局消息记录器"""
    uid, group_id, physical_user_id = self._get_identity(event)
    
    if event.message_str:
        # 记录消息
        await self._process_single_message(
            uid, group_id, session_id, user_name, event.message_str
        )
```

### 事件类型

```python
from astrbot.api.event import filter

# 监听所有消息
@filter.event_message_type(filter.EventMessageType.ALL)

# 监听文本消息
@filter.event_message_type(filter.EventMessageType.TEXT)

# 监听图片消息
@filter.event_message_type(filter.EventMessageType.IMAGE)

# 监听特定命令
@filter.command("my_command")
```

### 获取身份信息

```python
def _get_identity(self, event: AstrMessageEvent) -> tuple:
    """
    获取用户身份信息
    
    Returns:
        (uid, group_id, physical_user_id)
    """
    umo = event.unified_msg_origin
    platform = umo.split(":")[0] if umo else "unknown"
    
    sender_id = str(event.get_sender_id())
    sender_name = event.get_sender_name() or "User"
    
    uid = self.identity_manager.get_or_create_uid(
        sender_id, platform, sender_name
    )
    
    group_id = "private"
    raw_group = getattr(event.message_obj, "group_id", None)
    if raw_group:
        group_id = f"{platform}_group_{raw_group}"
    
    return uid, group_id, f"{platform}:{sender_id}"
```

---

## LLM 事件

### LLM 请求前事件

使用 `@filter.on_llm_request()` 装饰器在 LLM 请求前注入提示词：

```python
from astrbot.api.provider import ProviderRequest

@filter.on_llm_request()
async def before_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
    """LLM 请求前：注入提示词"""
    await self._wait_for_ready()
    
    uid, group_id, _ = self._get_identity(event)
    
    # 构建热记忆
    hot_memory = self.prompt_builder.build_system_prompt(uid, group_id)
    
    # 注入系统提示词
    if hot_memory:
        req.system_prompt = (req.system_prompt or "") + "\n\n" + hot_memory
```

### LLM 响应后事件

使用 `@filter.on_llm_response()` 装饰器在 LLM 响应后处理：

```python
from astrbot.api.provider import LLMResponse

@filter.on_llm_response()
async def after_response(self, event: AstrMessageEvent, resp: LLMResponse):
    """记录 AI 回复并触发记忆提取"""
    await self._wait_for_ready()
    
    uid, group_id, _ = self._get_identity(event)
    
    if resp and resp.completion_text:
        # 记录到对话总账
        await self.conversation_ledger.add_message(
            session_id=session_id,
            role="assistant",
            content=resp.completion_text,
            source="ai_response"
        )
        
        # 触发记忆提取
        is_new_session = await self.memory_manager.record_interaction(
            uid, group_id, "Assistant", resp.completion_text
        )
        
        # 睡眠巩固
        if is_new_session:
            await self._try_sleep_consolidation(uid, group_id)
```

### LLM 工具注册

使用 `@filter.llm_tool()` 装饰器注册 LLM 工具：

```python
@filter.llm_tool()
async def memory_search(self, event: AstrMessageEvent,
                      query: str,
                      scope: str = "all",
                      limit: int = 5) -> str:
    """
    检索记忆系统中的相关内容
    
    Args:
        query: 搜索查询
        scope: 搜索范围
        limit: 返回结果数量
        
    Returns:
        格式化的搜索结果
    """
    await self._wait_for_ready()
    
    uid, group_id, _ = self._get_identity(event)
    
    results = await self.search_engine.search(
        query, uid, group_id, scope, limit
    )
    
    return self.search_engine.format_results(results)
```

---

## 生命周期事件

### 插件初始化

```python
class ScriptorPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        
        self.data_dir = StarTools.get_data_dir(self.name)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化配置
        cfg = context.get_config()
        plugin_cfg = cfg.get("scriptor", {}) if isinstance(cfg, dict) else {}
        self.config = ScriptorConfigPydantic(plugin_cfg)
        
        # 初始化轻量级组件
        self.identity_manager = IdentityManager(self.data_dir)
        self.group_manager = GroupManager(self.data_dir, self.identity_manager)
        
        # 启动后台初始化
        self._background_tasks.add(
            asyncio.create_task(self._lazy_init_components())
        )
```

### 插件卸载

```python
async def terminate(self) -> None:
    """插件卸载时的清理工作"""
    try:
        logger.info("[Scriptor] 插件正在关闭...")
        self._is_terminating = True
        
        # 停止跨群消息系统
        if self.cross_group_system:
            await self.cross_group_system.stop()
        
        # 停止文件监控
        if self.file_monitor:
            self.file_monitor.stop()
        
        # 停止定时任务
        if self.scheduler:
            self.scheduler.stop()
        
        # 取消后台任务
        pending_tasks = [t for t in self._background_tasks if not t.done()]
        if pending_tasks:
            for task in pending_tasks:
                task.cancel()
            await asyncio.gather(*pending_tasks, return_exceptions=True)
        
        logger.info("[Scriptor] 插件已关闭")
    except Exception as e:
        logger.error(f"[Scriptor] 插件卸载清理失败: {e}")
```

---

## 自定义事件

### 创建自定义事件

你可以创建和触发自定义事件：

```python
# 定义事件数据类
@dataclass
class MemoryCreatedEvent:
    uid: str
    group_id: str
    memory_type: str
    content: str
    timestamp: datetime

# 触发事件
event = MemoryCreatedEvent(
    uid=uid,
    group_id=group_id,
    memory_type=memory_type,
    content=content,
    timestamp=datetime.now()
)

# 通过 Hook 系统广播
await self.hook_manager.trigger("custom", "memory_created", event)
```

### 监听自定义事件

```python
@register_hook("custom", "memory_created")
async def on_memory_created(event, context):
    """记忆创建时的钩子"""
    print(f"新记忆已创建: {event.content[:50]}")
```

---

## 最佳实践

### 1. 错误处理

```python
@filter.on_llm_request()
async def before_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
    try:
        # 你的逻辑
        pass
    except Exception as e:
        logger.error(f"处理 LLM 请求前出错: {e}")
        # 不要抛出异常，让 AstrBot 继续执行
```

### 2. 异步编程

```python
# 使用 async/await
async def my_handler(self, event):
    await self._wait_for_ready()  # 等待组件就绪
    result = await some_async_operation()
    return result
```

### 3. 日志记录

```python
from astrbot.api import logger

logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息", exc_info=True)  # 包含堆栈跟踪
```

### 4. 性能考虑

```python
# 使用懒加载
async def _lazy_init_components(self):
    """后台初始化重量级组件"""
    self.search_engine = SearchEngine(...)
    self.prompt_builder = PromptBuilder(...)
    self._is_ready = True

async def _wait_for_ready(self):
    """等待所有组件就绪"""
    while not self._is_ready:
        await asyncio.sleep(0.1)
```

---

## 更多资源

- [AstrBot 官方文档](https://astrbot.dev/)
- [Scriptor API 参考](../Scriptor_API_Reference.md)
- [Scriptor 高级功能](../Scriptor_Advanced_Features.md)
