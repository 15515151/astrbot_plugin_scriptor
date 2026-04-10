# main.py 命令代理优化方案

## 问题分析

当前 `main.py` 中有大量的命令代理方法，代码重复度高：

```python
@filter.command("sc_help")
async def sc_help(self, event: AstrMessageEvent):
    async for result in super().cmd_sc_help(event):
        yield result

@filter.command("sc_admin")
async def sc_admin(self, event: AstrMessageEvent):
    async for result in super().cmd_sc_admin(event):
        yield result

# ... 还有 30+ 个类似的代理方法
```

## 优化方案

### 方案1：使用元编程动态创建代理方法（推荐）

```python
# 在 main.py 中添加命令映射配置
COMMAND_PROXY_MAP = {
    # CommandsMixin 命令
    "sc_help": "cmd_sc_help",
    "sc_admin": "cmd_sc_admin",
    "smart_split_status": "cmd_smart_split_status",
    "buffer_status": "cmd_buffer_status",
    "lock_status": "cmd_lock_status",
    "sc_concurrency": "cmd_sc_concurrency",
    "webui": "cmd_webui",
    # KnowledgeMixin 命令
    "kb_status": "cmd_kb_status",
    # LearningMixin 命令
    "开始学习": "cmd_start_learning",
    "结束学习": "cmd_end_learning",
    "开始授课": "cmd_start_teaching",
    "结束授课": "cmd_end_teaching",
    "学习状态": "cmd_learning_status",
    # IdentityMixin 命令
    "whoami": "cmd_whoami",
    "get_bind_code": "cmd_get_bind_code",
    "debug_identity": "cmd_debug_identity",
    # MemoryMixin 命令
    "mem_status": "cmd_status",
    "debug_memory": "cmd_debug_memory",
    "mem_report": "cmd_mem_report",
    # AdminMixin 命令
    "sudo_state_up": "cmd_sudo_state_up",
    "sudo_state_down": "cmd_sudo_state_down",
    "sudo_status": "cmd_sudo_status",
    "sudo_sessions": "cmd_sudo_sessions",
    "sudo_audit": "cmd_sudo_audit",
    "confirm_delete": "cmd_confirm_delete",
}

# 带参数的命令映射
COMMAND_PROXY_MAP_WITH_ARGS = {
    "bind": ("cmd_bind", ["bind_code", "confirm_token"]),
    "unbind": ("cmd_unbind", ["unbind_token", "confirm_token"]),
    "reset_identity": ("cmd_reset_identity", ["reset_token", "step", "code"]),
    "search": ("cmd_search", [], {"remainder": ""}),  # 使用 kwargs
}

# 动态创建代理方法
def _create_command_proxy(cmd_name, mixin_method_name):
    @filter.command(cmd_name)
    async def proxy(self, event: AstrMessageEvent):
        mixin_method = getattr(super(ScriptorPlugin, self), mixin_method_name)
        async for result in mixin_method(event):
            yield result
    proxy.__name__ = f"cmd_proxy_{cmd_name}"
    return proxy

def _create_command_proxy_with_args(cmd_name, mixin_method_name, arg_names, default_kwargs=None):
    @filter.command(cmd_name)
    async def proxy(self, event: AstrMessageEvent, **kwargs):
        # 合并默认参数
        if default_kwargs:
            kwargs = {**default_kwargs, **kwargs}
        
        mixin_method = getattr(super(ScriptorPlugin, self), mixin_method_name)
        async for result in mixin_method(event, **kwargs):
            yield result
    proxy.__name__ = f"cmd_proxy_{cmd_name}"
    return proxy

# 在类定义后动态注册
for cmd_name, mixin_method in COMMAND_PROXY_MAP.items():
    setattr(ScriptorPlugin, cmd_name, _create_command_proxy(cmd_name, mixin_method))

for cmd_name, (mixin_method, arg_names, *rest) in COMMAND_PROXY_MAP_WITH_ARGS.items():
    default_kwargs = rest[0] if rest else None
    setattr(ScriptorPlugin, cmd_name, _create_command_proxy_with_args(
        cmd_name, mixin_method, arg_names, default_kwargs
    ))
```

### 方案2：使用装饰器工厂（备选）

```python
def command_proxy(cmd_name, mixin_method_name):
    """命令代理装饰器工厂"""
    def decorator(cls):
        @filter.command(cmd_name)
        async def proxy(self, event: AstrMessageEvent):
            method = getattr(super(cls, self), mixin_method_name)
            async for result in method(event):
                yield result
        proxy.__name__ = f"cmd_proxy_{cmd_name}"
        setattr(cls, cmd_name, proxy)
        return cls
    return decorator

# 使用
@command_proxy("sc_help", "cmd_sc_help")
@command_proxy("sc_admin", "cmd_sc_admin")
class ScriptorPlugin(Star, ...):
    pass
```

## 实施建议

1. **推荐方案1**：元编程动态创建代理方法
   - 优点：代码简洁，易于维护
   - 缺点：需要理解元编程概念

2. **保留现有代码**：如果团队不熟悉元编程
   - 优点：直观易懂
   - 缺点：代码冗余

## 注意事项

1. 确保所有 Mixin 方法都有正确的类型注解
2. 测试所有命令是否正常工作
3. 文档中说明代理方法的工作原理
