# 配置同步修复说明

## 问题描述

之前，当用户在 **AstrBot 官方 Web UI** 修改 Scriptor 插件配置时，配置不会立即生效。这是因为 Scriptor 插件只在启动时加载一次配置，没有监听配置的动态更新。

## 修复方案

现已实现 **自动配置同步机制**，包括：

### 1. 自动配置同步（每 5 分钟）

插件会在每次消息处理时检查配置文件是否有变化，如果有变化则自动重新加载。

**同步间隔**: 5 分钟（避免频繁读取文件）

**同步的组件**:
- ✅ 网页搜索工具 (`web_search_tool`)
- ✅ 智能分段发送器 (`SmartSender`)
- ✅ 全局配置 (`text_utils`)

### 2. 手动配置同步命令

如果不想等待自动同步，可以使用命令手动触发：

```
sc_sync_config
```

**功能**:
- 立即检查配置变化
- 重新加载配置
- 重新初始化相关组件
- 显示同步结果

---

## 使用流程

### 在 AstrBot 官方 Web UI 修改配置

1. **访问 AstrBot 官方 Web UI**
   - 默认地址：`http://localhost:6185`

2. **进入插件配置页面**
   - 左侧菜单 → 插件 → AstrBot 插件 → Scriptor

3. **修改配置**
   - 例如：启用网页搜索工具
   - 填写 SearXNG 地址：`http://10.31.0.100:38080`
   - 修改搜索引擎列表：`baidu,wikipedia,sogou,360search,google`

4. **保存配置**
   - 点击"保存并关闭"

5. **等待自动同步** 或 **手动触发同步**
   - 自动同步：等待最多 5 分钟
   - 手动同步：发送命令 `sc_sync_config`

6. **检查日志**
   ```
   [Scriptor] 检测到配置更新，重新加载配置...
   [Scriptor] 网页搜索工具已重新初始化 (SearXNG: http://10.31.0.100:38080)
   [Scriptor] 配置已重新加载
   ```

7. **测试功能**
   - 使用搜索功能验证配置是否生效

---

## 配置同步范围

目前支持以下配置的动态重载：

| 配置项 | 影响组件 | 自动重载 |
|--------|---------|---------|
| `web_search_enabled` | 网页搜索工具 | ✅ 是 |
| `searxng_base_url` | 网页搜索工具 | ✅ 是 |
| `searxng_secret` | 网页搜索工具 | ✅ 是 |
| `searxng_default_engines` | 网页搜索工具 | ✅ 是 |
| `searxng_max_results` | 网页搜索工具 | ✅ 是 |
| `searxng_timeout` | 网页搜索工具 | ✅ 是 |
| `search_archive_enabled` | 网页搜索工具 | ✅ 是 |
| `search_archive_threshold` | 网页搜索工具 | ✅ 是 |
| `web_fetch_top_n` | 网页搜索工具 | ✅ 是 |
| `smart_split_enabled` | SmartSender | ✅ 是 |
| `smart_split_only_llm` | SmartSender | ✅ 是 |
| `smart_split_regex` | SmartSender | ✅ 是 |
| `smart_split_cleanup_regex` | SmartSender | ✅ 是 |
| `smart_split_typing_speed` | SmartSender | ✅ 是 |
| `smart_split_min_delay` | SmartSender | ✅ 是 |
| `smart_split_max_delay` | SmartSender | ✅ 是 |
| `smart_split_random_factor` | SmartSender | ✅ 是 |
| `smart_split_long_text_threshold` | SmartSender | ✅ 是 |
| `smart_split_long_text_pattern` | SmartSender | ✅ 是 |
| `smart_split_group_reply` | SmartSender | ✅ 是 |

**注意**: 某些配置可能需要重启 AstrBot 才能生效，具体请参考配置项的说明。

---

## 技术实现

### 核心方法

1. **`_sync_config_from_disk()`**
   - 检查配置文件修改时间
   - 比较配置是否变化
   - 重新加载配置

2. **`_reload_config_dependent_components()`**
   - 重新初始化网页搜索工具
   - 重新初始化 SmartSender
   - 清理旧组件资源

3. **`_config_sync_handler()`**
   - 事件消息过滤器
   - 定期调用配置同步
   - 静默处理失败

4. **`sc_sync_config` 命令**
   - 手动触发配置同步
   - 显示同步结果
   - 用于测试和调试

### 性能优化

- **时间间隔控制**: 5 分钟同步间隔，避免频繁读取文件
- **修改时间检查**: 先检查文件 mtime，避免不必要的 JSON 解析
- **配置比较**: 比较配置字典，只在变化时重新加载
- **静默失败**: 同步失败不影响正常功能

---

## 故障排查

### 问题 1: 配置同步不生效

**症状**: 修改配置后，功能没有变化

**检查步骤**:
1. 检查日志是否有同步消息
2. 确认配置文件已保存
3. 等待 5 分钟或手动执行 `sc_sync_config`

**解决方案**:
```bash
# 手动触发配置同步
sc_sync_config

# 查看日志
tail -f data/logs/astrbot.log | grep Scriptor
```

### 问题 2: 配置同步失败

**症状**: 日志显示配置同步错误

**可能原因**:
- 配置文件格式错误
- 配置值不合法
- 组件重新初始化失败

**解决方案**:
1. 检查配置文件语法（JSON 格式）
2. 检查配置值是否在有效范围内
3. 查看详细错误日志

### 问题 3: 网页搜索仍然不可用

**症状**: 配置已同步，但搜索功能不可用

**检查步骤**:
1. 确认 `web_search_enabled` 为 `true`
2. 确认 `searxng_base_url` 配置正确
3. 测试 SearXNG 服务是否可访问

**解决方案**:
```bash
# 测试 SearXNG 连接
curl http://10.31.0.100:38080/search?q=test&format=json

# 检查 Scriptor 日志
grep "网页搜索工具" data/logs/astrbot.log
```

---

## 后续优化计划

1. **实现配置热重载**: 无需重新初始化组件，直接更新配置参数
2. **添加配置版本控制**: 跟踪配置变更历史
3. **实现配置回滚**: 允许用户回滚到之前的配置版本
4. **优化配置存储**: 使用更高效的方式存储和比较配置
5. **扩展同步范围**: 支持更多配置的动态重载

---

## 相关文档

- [配置同步修复方案](CONFIG_SYNC_FIX.md) - 详细的技术方案
- [项目健康报告](../../PROJECT_HEALTH_REPORT.md) - 整体项目状态
- [施工报告](../../IMPLEMENTATION_REPORT.md) - 本次修复的详细记录

---

**最后更新**: 2026-04-10  
**维护者**: Scriptor 开发团队
