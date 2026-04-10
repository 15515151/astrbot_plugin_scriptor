# 配置同步问题修复方案

## 问题描述

当用户在 **AstrBot 官方 Web UI** 修改 Scriptor 插件配置时，配置不会生效。

### 原因分析

1. **配置加载时机**: Scriptor 插件在初始化时从 `config.json` 加载配置
   ```python
   def __init__(self, context: Context, config: AstrBotConfig):
       self.config = ScriptorConfigPydantic(**config)
   ```

2. **缺少配置更新监听**: 插件没有监听 AstrBot 的配置更新事件

3. **配置存储位置**:
   - AstrBot 官方配置：`data/config.json` (通过官方 Web UI 修改)
   - Scriptor 配置：`data/plugin_data/astrbot_plugin_scriptor/config.json` (通过 Scriptor Web UI 修改)

---

## 解决方案

### 方案 1: 实现配置更新事件监听（推荐）

在 `main.py` 中添加配置更新事件处理器：

```python
from astrbot.api.event import filter
from astrbot.api.event.astr_message_event import AstrMessageEvent

@register(
    "astrbot_plugin_scriptor",
    "Scriptor",
    "基于 Scriptor 的多角色跨群体 AI 智能管家记忆系统",
    "1.0.0",
    "https://github.com/astrbots/astrbot_plugin_scriptor",
)
class ScriptorPlugin(Star, HelpersMixin, ...):
    
    def __init__(self, context: Context, config: AstrBotConfig):
        # ... 现有代码 ...
        self.config = ScriptorConfigPydantic(**config)
        self._last_config_sync_time = 0
    
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def _sync_config_if_needed(self, event: AstrMessageEvent):
        """
        定期检查并同步配置（每 5 分钟最多一次）
        这样可以捕获通过 AstrBot 官方 Web UI 进行的配置更改
        """
        import time
        from pathlib import Path
        
        current_time = time.time()
        if current_time - self._last_config_sync_time < 300:  # 5 分钟
            return
        
        try:
            config_file = self.data_dir / "config.json"
            if config_file.exists():
                import json
                with open(config_file, "r", encoding="utf-8") as f:
                    new_config = json.load(f)
                
                # 检查配置是否变化
                old_config_dict = self.config.dict()
                if new_config != old_config_dict:
                    logger.info("[Scriptor] 检测到配置更新，重新加载配置...")
                    self.config = ScriptorConfigPydantic(**new_config)
                    self._last_config_sync_time = current_time
                    
                    # 重新初始化依赖配置的组件
                    await self._reload_config_dependent_components()
                    
                    logger.info("[Scriptor] 配置已重新加载")
        except Exception as e:
            logger.error(f"[Scriptor] 配置同步失败：{e}")
    
    async def _reload_config_dependent_components(self):
        """重新加载依赖配置的组件"""
        try:
            # 重新初始化网页搜索工具
            if self.config.web_search_enabled:
                from .tools.web_search_tool import WebSearchTool
                
                searxng_url = self.config.searxng_base_url
                if searxng_url:
                    self.web_search_tool = WebSearchTool(
                        searxng_base_url=searxng_url,
                        searxng_secret=self.config.searxng_secret,
                        max_results=self.config.searxng_max_results,
                        timeout=self.config.searxng_timeout,
                        archive_enabled=self.config.search_archive_enabled,
                        archive_threshold=self.config.search_archive_threshold,
                        fetch_top_n=self.config.web_fetch_top_n,
                        default_engines=self.config.searxng_default_engines,
                    )
                    logger.info(f"[Scriptor] 网页搜索工具已重新初始化 (SearXNG: {searxng_url})")
                else:
                    logger.warning("[Scriptor] SearXNG 地址未配置")
                    self.web_search_tool = None
            else:
                self.web_search_tool = None
                logger.info("[Scriptor] 网页搜索功能已禁用")
            
            # 可以在这里添加其他需要重新初始化的组件
        except Exception as e:
            logger.error(f"[Scriptor] 重新加载组件失败：{e}")
```

---

### 方案 2: 使用 AstrBot 配置更新事件（如果可用）

检查 AstrBot 是否提供了配置更新事件：

```python
from astrbot.api.event import filter

class ScriptorPlugin(Star, ...):
    
    @filter.on_config_change()
    async def on_config_change(self, event):
        """
        监听配置更新事件
        注意：需要确认 AstrBot 是否提供此事件
        """
        try:
            logger.info("[Scriptor] 检测到配置更新事件")
            
            # 重新加载配置
            config_file = self.data_dir / "config.json"
            if config_file.exists():
                import json
                with open(config_file, "r", encoding="utf-8") as f:
                    new_config = json.load(f)
                
                self.config = ScriptorConfigPydantic(**new_config)
                await self._reload_config_dependent_components()
                
                logger.info("[Scriptor] 配置已更新")
        except Exception as e:
            logger.error(f"[Scriptor] 配置更新失败：{e}")
```

---

### 方案 3: 手动同步配置（临时方案）

创建一个命令来手动同步配置：

```python
@filter.command("sc_sync_config")
async def sc_sync_config(self, event: AstrMessageEvent):
    """手动同步配置（用于测试）"""
    try:
        config_file = self.data_dir / "config.json"
        if not config_file.exists():
            yield event.plain_result("配置文件不存在")
            return
        
        import json
        with open(config_file, "r", encoding="utf-8") as f:
            new_config = json.load(f)
        
        old_config_dict = self.config.dict()
        if new_config == old_config_dict:
            yield event.plain_result("配置没有变化")
            return
        
        self.config = ScriptorConfigPydantic(**new_config)
        await self._reload_config_dependent_components()
        
        yield event.plain_result("✅ 配置已同步并重新加载")
    except Exception as e:
        yield event.plain_result(f"❌ 配置同步失败：{e}")
```

---

## 实施建议

### 推荐方案：方案 1 + 方案 3

1. **实现自动配置同步** (方案 1)
   - 定期检查配置变化
   - 自动重新加载依赖组件

2. **添加手动同步命令** (方案 3)
   - 用于测试和调试
   - 用户可以手动触发配置同步

3. **优化配置同步逻辑**
   - 只在必要时重新加载组件
   - 避免频繁的文件读取

---

## 配置同步范围

需要重新加载的组件：

| 配置项 | 影响组件 | 是否需要重新初始化 |
|--------|---------|------------------|
| `web_search_enabled` | `web_search_tool` | ✅ 是 |
| `searxng_base_url` | `web_search_tool` | ✅ 是 |
| `searxng_secret` | `web_search_tool` | ✅ 是 |
| `searxng_default_engines` | `web_search_tool` | ✅ 是 |
| `searxng_max_results` | `web_search_tool` | ✅ 是 |
| `searxng_timeout` | `web_search_tool` | ✅ 是 |
| `web_fetch_top_n` | `web_search_tool` | ✅ 是 |
| `smart_split_enabled` | `SmartSender` | ✅ 是 |
| `active_reply_enabled` | `ActiveReplyManager` | ✅ 是 |
| 其他配置 | ... | 视情况而定 |

---

## 测试步骤

1. **启动 AstrBot**
2. **在官方 Web UI 修改配置**
   - 启用 `web_search_enabled`
   - 填写 `searxng_base_url`
3. **保存配置**
4. **等待 5 分钟** 或执行 `sc_sync_config` 命令
5. **检查日志**：应该看到配置重新加载的消息
6. **测试搜索功能**：使用 `web_search_tool` 进行搜索

---

## 注意事项

1. **性能影响**: 定期检查配置文件会增加 I/O 开销，建议间隔至少 5 分钟
2. **组件状态**: 重新初始化组件时，需要处理旧组件的清理工作
3. **并发安全**: 确保配置同步过程是线程安全的
4. **错误处理**: 配置同步失败时，不应影响插件的正常运行

---

## 后续优化

1. **实现配置热重载**: 无需重新初始化组件，直接更新配置参数
2. **添加配置版本控制**: 跟踪配置变更历史
3. **实现配置回滚**: 允许用户回滚到之前的配置版本
4. **优化配置存储**: 使用更高效的方式存储和比较配置
