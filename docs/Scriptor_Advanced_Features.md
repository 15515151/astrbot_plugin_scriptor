# Scriptor 高级功能指南

本文档介绍 Scriptor 的高级功能，适合有一定基础的用户和开发者。

---

## 目录

1. [知识图谱](#知识图谱)
2. [权限管理](#权限管理)
3. [数据加密](#数据加密)
4. [Hook 系统](#hook-系统)
5. [Web UI](#web-ui)
6. [性能优化](#性能优化)
7. [备份与恢复](#备份与恢复)
8. [自定义扩展](#自定义扩展)

---

## 知识图谱

### 什么是知识图谱？

知识图谱是 Scriptor 的高级功能，它从日记中自动提取实体和关系，构建一个可视化的知识网络。

### 启用知识图谱

知识图谱默认启用，每天凌晨 3 点自动整理：

```yaml
scriptor:
  nightly_graph_consolidation_enabled: true
  nightly_graph_consolidation_hour: 3
```

### 知识图谱数据结构

```python
@dataclass
class Entity:
    name: str
    type: str  # 人物/地点/事物/概念

@dataclass
class Relation:
    source: str
    target: str
    type: str  # 喜欢/讨厌/拥有/去过/...
```

### 实体提取示例

从日记中提取的实体和关系：

```json
{
  "entities": [
    {"name": "张三", "type": "人物"},
    {"name": "Python", "type": "事物"},
    {"name": "苹果", "type": "事物"},
    {"name": "公司", "type": "地点"}
  ],
  "relations": [
    {"source": "张三", "target": "Python", "type": "喜欢"},
    {"source": "张三", "target": "苹果", "type": "喜欢"},
    {"source": "张三", "target": "公司", "type": "工作于"}
  ]
}
```

### 手动触发知识图谱整理

```python
from astrbot_plugin_scriptor.core.knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph(data_dir)
kg.add_entities_and_relations(entities, relations)
```

---

## 权限管理

### 权限系统

Scriptor 实现了基于角色的细粒度权限管理系统。

### 权限级别

```python
from astrbot_plugin_scriptor.core.permission_manager import (
    PermissionManager,
    Role,
    Permission
)

pm = PermissionManager(data_dir)

# 角色定义
class Role(Enum):
    GUEST = "guest"      # 访客
    MEMBER = "member"    # 成员
    MODERATOR = "mod"   # 管理员
    ADMIN = "admin"      # 超级管理员
    OWNER = "owner"      # 所有者

# 权限定义
class Permission(Enum):
    READ_MEMORY = "read_memory"
    WRITE_MEMORY = "write_memory"
    DELETE_MEMORY = "delete_memory"
    MANAGE_USERS = "manage_users"
    MANAGE_GROUPS = "manage_groups"
    ADMIN_CONFIG = "admin_config"
```

### 权限矩阵

| 权限 | GUEST | MEMBER | MODERATOR | ADMIN | OWNER |
|------|-------|--------|-----------|-------|-------|
| READ_MEMORY | ✓ | ✓ | ✓ | ✓ | ✓ |
| WRITE_MEMORY | ✗ | ✓ | ✓ | ✓ | ✓ |
| DELETE_MEMORY | ✗ | ✗ | ✓ | ✓ | ✓ |
| MANAGE_USERS | ✗ | ✗ | ✗ | ✓ | ✓ |
| MANAGE_GROUPS | ✗ | ✗ | ✓ | ✓ | ✓ |
| ADMIN_CONFIG | ✗ | ✗ | ✗ | ✗ | ✓ |

### 使用权限系统

```python
# 检查权限
if pm.has_permission(uid, Permission.WRITE_MEMORY):
    # 允许操作
    pass

# 获取用户角色
role = pm.get_user_role(uid)

# 设置用户角色
pm.set_user_role(uid, Role.MODERATOR)
```

---

## 数据加密

### 启用加密

Scriptor 支持使用 Fernet 对称加密保护敏感记忆。

```python
from cryptography.fernet import Fernet

# 生成密钥
key = Fernet.generate_key()
print(key.decode())  # 保存这个密钥！

# 配置
scriptor:
  encryption_enabled: true
  encryption_key: "your-key-here"
```

### 加密工具

```python
from astrbot_plugin_scriptor.tools.security.encryption import Encryption

# 初始化
encryption = Encryption(key)

# 加密
encrypted = encryption.encrypt("敏感信息")

# 解密
decrypted = encryption.decrypt(encrypted)
```

### 加密记忆标记

加密的记忆会在 Front Matter 中标记：

```markdown
---
memory_type: fact
useful_score: 8.5
encrypted: true
---

[加密内容]
```

---

## Hook 系统

### 什么是 Hook？

Hook 是 Scriptor 的扩展机制，允许你在关键节点插入自定义逻辑。

### Hook 类型

#### 1. 生命周期 Hook

```python
from astrbot_plugin_scriptor.hooks import register_hook

@register_hook("lifecycle", "on_startup")
async def on_startup(context):
    """插件启动时"""
    print("Scriptor 已启动！")

@register_hook("lifecycle", "on_shutdown")
async def on_shutdown(context):
    """插件关闭时"""
    print("Scriptor 已关闭！")
```

#### 2. LLM Hook

```python
@register_hook("llm", "before_request")
async def before_llm_request(event, req, context):
    """LLM 请求前"""
    print(f"即将发送请求: {req}")

@register_hook("llm", "after_response")
async def after_llm_response(event, resp, context):
    """LLM 响应后"""
    print(f"收到响应: {resp}")
```

#### 3. 消息 Hook

```python
@register_hook("message", "before_process")
async def before_message_process(event, context):
    """消息处理前"""
    print(f"收到消息: {event.message_str}")

@register_hook("message", "after_process")
async def after_message_process(event, context):
    """消息处理后"""
    print("消息处理完成")
```

#### 4. 搜索 Hook

```python
@register_hook("search", "before_search")
async def before_search(query, context):
    """搜索前"""
    print(f"搜索查询: {query}")

@register_hook("search", "after_search")
async def after_search(results, context):
    """搜索后"""
    print(f"找到 {len(results)} 条结果")
```

#### 5. 存储 Hook

```python
@register_hook("storage", "before_write")
async def before_write(file_path, content, context):
    """写入前"""
    print(f"写入文件: {file_path}")

@register_hook("storage", "after_write")
async def after_write(file_path, context):
    """写入后"""
    print("写入完成")
```

### Hook 管理器

```python
from astrbot_plugin_scriptor.hooks.manager import HookManager

hook_manager = HookManager()

# 手动触发 Hook
await hook_manager.trigger("lifecycle", "on_startup", context)
```

---

## Web UI

### 启用 Web UI

Scriptor 内置了 Web UI 用于管理记忆：

```python
from astrbot_plugin_scriptor.web.app import app

# 在 AstrBot 中启动
# Web UI 会自动启动
```

### Web UI 功能

- 查看记忆列表
- 搜索记忆
- 编辑记忆
- 删除记忆
- 查看知识图谱
- 管理用户权限
- 查看系统状态

### 访问 Web UI

默认地址：`http://localhost:8080/scriptor`

### 自定义 Web UI

```python
from astrbot_plugin_scriptor.web.shared_state import set_shared_state

# 设置共享状态
set_shared_state(
    data_dir,
    search_engine,
    identity_manager,
    group_manager,
    memory_manager,
    config,
    knowledge_base,
    research_tool
)
```

---

## 性能优化

### 懒加载架构

Scriptor 采用懒加载架构，启动速度极快：

```python
# 轻量级组件立即初始化
self.identity_manager = IdentityManager(...)
self.group_manager = GroupManager(...)
self.memory_manager = MemoryManager(...)

# 重量级组件在后台异步初始化
self._background_tasks.add(
    asyncio.create_task(self._lazy_init_components())
)
```

### 防抖写入

使用防抖写入器减少磁盘 I/O：

```python
from astrbot_plugin_scriptor.tools.storage.debounced_writer import DebouncedWriter

writer = DebouncedWriter(
    file_path=file_path,
    debounce_seconds=5.0
)

# 多次写入会被合并
writer.write(content1)
writer.write(content2)
writer.write(content3)

# 等待所有写入完成
await writer.wait_for_all()
```

### 会话锁

使用会话锁防止并发冲突：

```python
from astrbot_plugin_scriptor.core.session_locks import SessionLockManager

lock_manager = SessionLockManager()

# 获取锁
async with lock_manager.acquire(session_id):
    # 临界区代码
    # 同一时间只有一个协程能执行这里
    pass
```

### 批量向量化

使用批量向量化降低 API 调用成本：

```python
# 传统方案：100 条 = 100 次 API 调用
for text in texts:
    embed(text)

# Scriptor 方案：100 条 = 2 次 API 调用（64 条/批）
embeddings = embed_batch(texts, batch_size=64)
```

### Token 控制

智能控制系统提示词长度：

```python
from astrbot_plugin_scriptor.core.token_utils import (
    TokenEstimator,
    SmartMemoryTrimmer
)

# 估算 Token
tokens = TokenEstimator.estimate_tokens(text)

# 智能裁剪
trimmer = SmartMemoryTrimmer(max_tokens=4000)
trimmer.add_part("hot_memory", hot_memory, 10)
trimmer.add_part("guidance", guidance, 5)
selected_parts, used_tokens = trimmer.trim()
```

---

## 备份与恢复

### 自动备份

Scriptor 每天自动备份：

```python
from astrbot_plugin_scriptor.tools.storage.backup_manager import BackupManager

backup_manager = BackupManager(data_dir)

# 创建备份
backup_path = backup_manager.create_backup()

# 列出备份
backups = backup_manager.list_backups()

# 恢复备份
backup_manager.restore_backup(backup_path)
```

### 手动备份

```bash
# 备份整个数据目录
cp -r data/plugins/astrbot_plugin_scriptor/ backups/scriptor_$(date +%Y%m%d)/

# 或使用 Git
cd data/plugins/astrbot_plugin_scriptor/
git add .
git commit -m "Backup $(date)"
```

### 备份策略

- 每天自动备份一次
- 保留最近 7 天的备份
- 每周创建一个完整备份
- 每月创建一个归档备份

---

## 自定义扩展

### 创建自定义记忆类型

```python
# 在 memory_struct.py 中添加
MEMORY_TYPES = {
    "fact": "事实",
    "preference": "偏好",
    "decision": "决策",
    "experience": "经验",
    "rule": "规则",
    "my_custom_type": "我的自定义类型"  # 添加
}
```

### 创建自定义检索策略

```python
from astrbot_plugin_scriptor.core.search_engine import SearchEngine

class CustomSearchEngine(SearchEngine):
    async def search(self, query, uid, group_id, scope="all", limit=5):
        # 自定义搜索逻辑
        results = await super().search(query, uid, group_id, scope, limit)
        # 自定义结果处理
        return custom_process(results)
```

### 创建自定义提示词模板

```python
from astrbot_plugin_scriptor.core.prompt_builder import PromptBuilder

class CustomPromptBuilder(PromptBuilder):
    def build_system_prompt(self, uid, group_id):
        # 自定义提示词构建
        prompt = super().build_system_prompt(uid, group_id)
        # 添加自定义内容
        prompt += "\n\n【自定义指令】\n..."
        return prompt
```

### 创建自定义 LLM 工具

```python
from astrbot.api.star import register
from astrbot.api.event import filter

@filter.llm_tool()
async def my_custom_tool(self, event, param1: str, param2: int = 0) -> str:
    """
    我的自定义工具
    
    Args:
        param1: 参数1
        param2: 参数2
        
    Returns:
        结果
    """
    # 自定义逻辑
    return f"处理完成: {param1}, {param2}"
```

---

## 监控与调试

### 日志

Scriptor 使用 AstrBot 的日志系统：

```python
from astrbot.api import logger

logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### 性能监控

```python
from astrbot_plugin_scriptor.tools.performance.monitor import PerformanceMonitor

monitor = PerformanceMonitor()

# 记录操作
with monitor.track("operation_name"):
    # 操作代码
    pass

# 获取统计
stats = monitor.get_stats()
print(stats)
```

### 调试命令

```
/debug_memory
```

查看详细的调试信息：
- 当前 UID 和 Group
- 未处理消息数
- 向量库总条目
- 热记忆长度
- Embedding 引擎
- 组件就绪状态

---

## 更多资源

- [Scriptor 用户指南](./Scriptor_User_Guide.md) - 用户使用指南
- [Scriptor API 参考](./Scriptor_API_Reference.md) - API 文档
- [Scriptor 系统设计哲学](./Scriptor_System_Design_Philosophy.md) - 设计理念
