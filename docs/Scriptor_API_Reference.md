# Scriptor API 参考

本文档为开发者提供 Scriptor 插件的 API 参考。

---

## 目录

1. [核心组件](#核心组件)
2. [配置系统](#配置系统)
3. [记忆管理器](#记忆管理器)
4. [搜索引擎](#搜索引擎)
5. [身份管理器](#身份管理器)
6. [群体管理器](#群体管理器)
7. [Hook 系统](#hook-系统)
8. [工具类](#工具类)

---

## 核心组件

### ScriptorPlugin

主插件类，所有功能的入口点。

```python
from astrbot_plugin_scriptor.main import ScriptorPlugin

class ScriptorPlugin(Star):
    """Scriptor 插件主类"""
    
    def __init__(self, context: Context):
        """初始化插件"""
        
    async def terminate(self) -> None:
        """插件卸载时的清理工作"""
```

**主要属性**:
- `data_dir`: 数据目录路径
- `config`: 配置对象
- `identity_manager`: 身份管理器
- `group_manager`: 群体管理器
- `memory_manager`: 记忆管理器
- `search_engine`: 搜索引擎
- `prompt_builder`: 提示词构建器

---

## 配置系统

### ScriptorConfigPydantic

配置类，使用 Pydantic 进行类型验证。

```python
from astrbot_plugin_scriptor.core.config_pydantic import ScriptorConfigPydantic

config = ScriptorConfigPydantic({
    "memory_compact_threshold": 8000,
    "daily_note_enabled": True,
    "cross_group_enabled": True,
    "embedding_enabled": True,
    "search_top_k": 5,
    "embedding_provider": "local",
    "embedding_api_base": "http://localhost:11434/v1",
    "embedding_api_key": "ollama",
    "embedding_model": "AI-ModelScope/bge-small-zh-v1.5",
    "enable_token_control": True,
    "max_system_prompt_tokens": 4000,
    "retrieval_guidance_priority": 5,
    "encryption_enabled": False,
    "encryption_key": "",
    "admin_uids": [],
    "nightly_graph_consolidation_enabled": True,
    "nightly_graph_consolidation_hour": 3
})
```

**配置项**:
- `memory_compact_threshold`: 记忆压缩阈值
- `daily_note_enabled`: 启用日记功能
- `cross_group_enabled`: 启用跨群功能
- `embedding_enabled`: 启用 Embedding
- `search_top_k`: 搜索结果数量
- `embedding_provider`: Embedding 提供商
- `embedding_api_base`: Embedding API 地址
- `embedding_api_key`: Embedding API 密钥
- `embedding_model`: Embedding 模型
- `enable_token_control`: 启用 Token 控制
- `max_system_prompt_tokens`: 最大系统提示词 Token 数
- `retrieval_guidance_priority`: 检索指导优先级
- `encryption_enabled`: 启用加密
- `encryption_key`: 加密密钥
- `admin_uids`: 管理员 UID 列表
- `nightly_graph_consolidation_enabled`: 启用夜间知识图谱整理
- `nightly_graph_consolidation_hour`: 夜间整理时间

---

## 记忆管理器

### MemoryManager

记忆管理核心类，负责记忆的存储、检索、巩固等功能。

```python
from astrbot_plugin_scriptor.core.memory_manager import MemoryManager

memory_manager = MemoryManager(
    data_dir=data_dir,
    config=config,
    identity_manager=identity_manager,
    group_manager=group_manager
)
```

**主要方法**:

#### record_interaction
记录交互信息。

```python
async def record_interaction(
    self,
    uid: str,
    group_id: str,
    user_name: str,
    message: str
) -> bool:
    """
    记录交互信息
    
    Args:
        uid: 用户 UID
        group_id: 群体 ID
        user_name: 用户名
        message: 消息内容
        
    Returns:
        是否为新会话
    """
```

#### record_long_term_memory
记录长期记忆。

```python
async def record_long_term_memory(
    self,
    uid: str,
    group_id: str,
    content: str,
    memory_type: str = "fact",
    search_engine=None,
    privacy_level: str = "private",
    useful_score: float = 5.0,
    strength: float = 1.0
):
    """
    记录长期记忆
    
    Args:
        uid: 用户 UID
        group_id: 群体 ID
        content: 记忆内容
        memory_type: 记忆类型
        search_engine: 搜索引擎（可选）
        privacy_level: 隐私级别
        useful_score: 有用分数
        strength: 强度
    """
```

#### update_profile
更新用户画像。

```python
async def update_profile(self, uid: str, new_facts: str):
    """
    更新用户画像
    
    Args:
        uid: 用户 UID
        new_facts: 新事实
    """
```

#### should_extract_memory
判断是否应该提取记忆。

```python
def should_extract_memory(self, text: str) -> bool:
    """
    判断是否应该提取记忆
    
    Args:
        text: 文本内容
        
    Returns:
        是否应该提取
    """
```

#### extract_memory_type
提取记忆类型。

```python
def extract_memory_type(self, text: str) -> Optional[str]:
    """
    提取记忆类型
    
    Args:
        text: 文本内容
        
    Returns:
        记忆类型
    """
```

#### should_trigger_llm_extraction
判断是否应该触发 LLM 提取。

```python
def should_trigger_llm_extraction(self, uid: str, group_id: str) -> bool:
    """
    判断是否应该触发 LLM 提取
    
    Args:
        uid: 用户 UID
        group_id: 群体 ID
        
    Returns:
        是否应该触发
    """
```

#### get_unprocessed_messages
获取未处理的消息。

```python
def get_unprocessed_messages(self, uid: str, group_id: str) -> List[str]:
    """
    获取未处理的消息
    
    Args:
        uid: 用户 UID
        group_id: 群体 ID
        
    Returns:
        未处理的消息列表
    """
```

#### clear_unprocessed_messages
清空未处理的消息。

```python
def clear_unprocessed_messages(self, uid: str, group_id: str):
    """
    清空未处理的消息
    
    Args:
        uid: 用户 UID
        group_id: 群体 ID
    """
```

#### get_recent_notes_text
获取近期日记文本。

```python
def get_recent_notes_text(self, uid: str, group_id: str, limit: int = 3) -> Optional[str]:
    """
    获取近期日记文本
    
    Args:
        uid: 用户 UID
        group_id: 群体 ID
        limit: 数量限制
        
    Returns:
        日记文本
    """
```

---

## 搜索引擎

### SearchEngine

混合搜索引擎，支持 Tantivy BM25 和 ChromaDB 向量搜索。

```python
from astrbot_plugin_scriptor.core.search_engine import SearchEngine

search_engine = SearchEngine(
    data_dir=data_dir,
    config=config,
    identity_manager=identity_manager,
    group_manager=group_manager,
    memory_manager=memory_manager
)
```

**主要方法**:

#### search
搜索记忆。

```python
async def search(
    self,
    query: str,
    uid: str,
    group_id: str,
    scope: str = "all",
    limit: int = 5
) -> List[SearchResult]:
    """
    搜索记忆
    
    Args:
        query: 搜索查询
        uid: 用户 UID
        group_id: 群体 ID
        scope: 搜索范围
        limit: 结果数量
        
    Returns:
        搜索结果列表
    """
```

#### format_results
格式化搜索结果。

```python
def format_results(self, results: List[SearchResult]) -> str:
    """
    格式化搜索结果
    
    Args:
        results: 搜索结果列表
        
    Returns:
        格式化的结果字符串
    """
```

**SearchResult 数据类**:
```python
@dataclass
class SearchResult:
    content: str
    source_type: str
    source_path: Optional[str] = None
    score: float = 0.0
    useful_score: float = 0.0
    created_at: Optional[datetime] = None
```

---

## 身份管理器

### IdentityManager

身份管理类，负责跨平台身份聚合。

```python
from astrbot_plugin_scriptor.core.identity_manager import IdentityManager

identity_manager = IdentityManager(data_dir=data_dir)
```

**主要方法**:

#### get_or_create_uid
获取或创建用户 UID。

```python
def get_or_create_uid(
    self,
    physical_id: str,
    platform: str,
    user_name: str
) -> str:
    """
    获取或创建用户 UID
    
    Args:
        physical_id: 物理 ID
        platform: 平台
        user_name: 用户名
        
    Returns:
        用户 UID
    """
```

#### bind_identities
绑定身份。

```python
def bind_identities(self, uid1: str, uid2: str) -> bool:
    """
    绑定身份
    
    Args:
        uid1: 第一个 UID
        uid2: 第二个 UID
        
    Returns:
        是否成功
    """
```

#### get_user_primary_name
获取用户主名称。

```python
def get_user_primary_name(self, uid: str) -> str:
    """
    获取用户主名称
    
    Args:
        uid: 用户 UID
        
    Returns:
        用户名
    """
```

#### get_user_groups
获取用户参与的群体。

```python
def get_user_groups(self, uid: str) -> List[str]:
    """
    获取用户参与的群体
    
    Args:
        uid: 用户 UID
        
    Returns:
        群体 ID 列表
    """
```

#### generate_bind_code
生成绑定码。

```python
def generate_bind_code(self, uid: str) -> str:
    """
    生成绑定码
    
    Args:
        uid: 用户 UID
        
    Returns:
        绑定码
    """
```

#### verify_bind_code
验证绑定码。

```python
def verify_bind_code(self, bind_code: str) -> Optional[str]:
    """
    验证绑定码
    
    Args:
        bind_code: 绑定码
        
    Returns:
        用户 UID
    """
```

---

## 群体管理器

### GroupManager

群体管理类，负责群体记忆和成员管理。

```python
from astrbot_plugin_scriptor.core.group_manager import GroupManager

group_manager = GroupManager(
    data_dir=data_dir,
    identity_manager=identity_manager
)
```

**主要方法**:

#### get_or_create_group
获取或创建群体。

```python
def get_or_create_group(
    self,
    group_id: str,
    group_name: str,
    platform: str,
    owner_uid: str
):
    """
    获取或创建群体
    
    Args:
        group_id: 群体 ID
        group_name: 群体名称
        platform: 平台
        owner_uid: 群主 UID
    """
```

#### add_member
添加成员。

```python
def add_member(
    self,
    group_id: str,
    uid: str,
    alias: str,
    role: str = "member"
):
    """
    添加成员
    
    Args:
        group_id: 群体 ID
        uid: 用户 UID
        alias: 别名
        role: 角色
    """
```

#### get_group_members
获取群体成员。

```python
def get_group_members(self, group_id: str) -> List[GroupMember]:
    """
    获取群体成员
    
    Args:
        group_id: 群体 ID
        
    Returns:
        成员列表
    """
```

#### get_other_groups
获取用户参与的其他群体。

```python
def get_other_groups(self, uid: str, exclude_group_id: str) -> List[str]:
    """
    获取用户参与的其他群体
    
    Args:
        uid: 用户 UID
        exclude_group_id: 排除的群体 ID
        
    Returns:
        群体 ID 列表
    """
```

#### record_group_interaction
记录群体交互。

```python
def record_group_interaction(
    self,
    group_id: str,
    uid: str,
    message: str,
    source: str
):
    """
    记录群体交互
    
    Args:
        group_id: 群体 ID
        uid: 用户 UID
        message: 消息
        source: 来源
    """
```

**GroupMember 数据类**:
```python
@dataclass
class GroupMember:
    uid: str
    alias: str
    role: str
    joined_at: datetime
```

---

## Hook 系统

### HookManager

Hook 管理类，支持自定义钩子扩展功能。

```python
from astrbot_plugin_scriptor.hooks.manager import HookManager

hook_manager = HookManager()
```

**Hook 类型**:
- `lifecycle`: 生命周期钩子
- `llm`: LLM 钩子
- `message`: 消息钩子
- `search`: 搜索钩子
- `storage`: 存储钩子

**注册 Hook**:
```python
from astrbot_plugin_scriptor.hooks import register_hook

@register_hook("message", "before_process")
async def my_message_hook(event, context):
    """消息处理前的钩子"""
    pass
```

---

## 工具类

### TokenEstimator

Token 估算工具。

```python
from astrbot_plugin_scriptor.core.token_utils import TokenEstimator

tokens = TokenEstimator.estimate_tokens(text)
```

### SmartMemoryTrimmer

智能记忆裁剪器。

```python
from astrbot_plugin_scriptor.core.token_utils import SmartMemoryTrimmer

trimmer = SmartMemoryTrimmer(max_tokens=4000)
trimmer.add_part("hot_memory", hot_memory, 10)
trimmer.add_part("guidance", guidance, 5)
selected_parts, used_tokens = trimmer.trim()
```

### Encryption

加密工具。

```python
from astrbot_plugin_scriptor.tools.security.encryption import Encryption

encryption = Encryption(key)
encrypted = encryption.encrypt(text)
decrypted = encryption.decrypt(encrypted)
```

### FileMonitor

文件监控工具。

```python
from astrbot_plugin_scriptor.core.file_monitor import FileMonitor

def handle_change(change):
    print(f"文件变更: {change}")

monitor = FileMonitor(data_dir, handle_change)
monitor.start()
monitor.stop()
```

---

## 扩展开发

### 创建自定义 Hook

```python
from astrbot_plugin_scriptor.hooks import register_hook

@register_hook("message", "after_process")
async def custom_message_hook(event, context):
    """
    自定义消息处理后钩子
    
    Args:
        event: 消息事件
        context: 上下文
    """
    uid = context.get("uid")
    message = event.message_str
    
    # 自定义逻辑
    print(f"处理消息: {uid} - {message}")
```

### 创建自定义工具

```python
from astrbot_plugin_scriptor.core.tool_decoration import ToolDecorator

tool_decorator = ToolDecorator()

# 自定义工具装饰
tool_decorator.add_decorator(
    tool_name="my_tool",
    decorator="🔧 正在执行自定义工具..."
)
```

---

## 数据库架构

### 向量数据库 (ChromaDB)

集合名称: `scriptor_memories`

字段:
- `ids`: 记忆 ID
- `embeddings`: 向量嵌入
- `metadatas`: 元数据
  - `uid`: 用户 UID
  - `group_id`: 群体 ID
  - `source_type`: 来源类型
  - `memory_type`: 记忆类型
  - `useful_score`: 有用分数
  - `created_at`: 创建时间

### 全文索引 (Tantivy)

索引目录: `tantivy_index/`

字段:
- `content`: 内容（全文索引）
- `uid`: 用户 UID
- `group_id`: 群体 ID
- `source_type`: 来源类型
- `memory_type`: 记忆类型

---

## 错误处理

### 自定义异常

```python
from astrbot_plugin_scriptor.core.exceptions import (
    ScriptorError,
    MemoryError,
    SearchError,
    IdentityError,
    ConfigError
)

try:
    # 操作
except MemoryError as e:
    print(f"记忆错误: {e}")
except SearchError as e:
    print(f"搜索错误: {e}")
```

---

## 性能优化

### 懒加载

重量级组件在后台异步初始化，不阻塞启动。

```python
# 主类中
self._background_tasks.add(
    asyncio.create_task(self._lazy_init_components())
)

async def _lazy_init_components(self):
    """后台懒加载初始化重量级组件"""
    self.search_engine = SearchEngine(...)
    self.prompt_builder = PromptBuilder(...)
    self.file_monitor = FileMonitor(...)
```

### 防抖写入

使用防抖写入器减少磁盘 I/O。

```python
from astrbot_plugin_scriptor.tools.storage.debounced_writer import DebouncedWriter

writer = DebouncedWriter(
    file_path=file_path,
    debounce_seconds=5.0
)
writer.write(content)
await writer.wait_for_all()
```

### 会话锁

使用会话锁防止并发冲突。

```python
from astrbot_plugin_scriptor.core.session_locks import SessionLockManager

lock_manager = SessionLockManager()
async with lock_manager.acquire(session_id):
    # 临界区代码
    pass
```

---

## 测试

### 运行测试

```bash
cd tests
python run_tests.py
```

### 测试覆盖

- `test_config.py`: 配置测试
- `test_memory_manager.py`: 记忆管理测试
- `test_search_engine.py`: 搜索引擎测试
- `test_conversation_ledger.py`: 对话总账测试
- `test_file_monitor.py`: 文件监控测试
- `test_enhanced.py`: 增强功能测试
- `test_hooks.py`: Hook 系统测试
- `test_permissions.py`: 权限系统测试
- `test_encryption.py`: 加密功能测试
- `test_integration.py`: 集成测试
- `test_performance.py`: 性能测试

---

## 更多资源

- [Scriptor 用户指南](./Scriptor_User_Guide.md) - 用户使用指南
- [Scriptor 系统设计哲学](./Scriptor_System_Design_Philosophy.md) - 设计理念
- [Scriptor 高级功能](./Scriptor_Advanced_Features.md) - 高级功能
