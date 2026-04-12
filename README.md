# Scriptor (灵笔司书)

> **跨越个体与群体的通用 AI 管家**

Copyright (C) 2026 ysf7762-dev

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/your-repo/scriptor)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![AstrBot](https://img.shields.io/badge/astrbot-4.0+-orange.svg)](https://github.com/Soulter/AstrBot)
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)

**Scriptor (灵笔司书)** 是一个基于 AstrBot 框架的 AI 管家插件，提供跨越个体与群体的通用记忆管理与智能交互服务。通过多层次记忆系统、跨平台身份管理、渐进式披露架构等核心技术，实现拟人化、个性化、智能化的管家式交互体验。

## ⚠️ 食用指南（重要配置）

**为了避免插件功能冲突，请务必在 AstrBot 配置文件中进行以下设置：**

### 1. 插件冲突处理

| 配置项 | 位置 | 建议设置 | 原因 |
|--------|------|----------|------|
| **astrbot 插件** | 插件 - AstrBot 插件 | ❌ 关闭 | 与 Scriptor 的智能体功能冲突 |
| **流式输出** | 配置文件 - 普通配置 - AI 配置 | ❌ 关闭 | 否则插件会报错 |
| **上下文窗口处理** | 配置文件 - 普通配置 - AI 配置 - 超出模型上下文窗口时的处理方式 | 选择**截断** | 插件已有更优压缩功能，存在冲突 |
| **知识库创建** | 配置文件 - 普通配置 - AI 配置 | ❌ 关闭 | 与插件知识库存在冲突 |
| **群聊上下文感知** | 配置文件 - 普通配置 - 扩展功能 | ❌ 关闭 | 插件已有更优功能，存在冲突 |
| **分段回复** | 配置文件 - 普通配置 - 扩展功能 | ❌ 关闭 | 插件已有更优功能，存在冲突 |

### 2. 推荐配置

| 配置项 | 建议值 | 说明 |
|--------|--------|------|
| **管理员 UID** | 填写你的 UID | 用于 Sudo 模式和管理命令 |
| **Web UI 端口** | 18111（默认） | 确保端口未被占用 |
| **媒体自动保存** | ✅ 开启 | 自动保存图片和文件 |
| **智能分段发送** | ✅ 开启 | 拟人化消息发送 |

### 3. 首次使用检查清单

- [ ] 关闭冲突插件和功能
- [ ] 设置管理员 UID
- [ ] 重启 AstrBot
- [ ] 访问 Web UI (`http://localhost:18111`)
- [ ] 设置 Web UI 密码
- [ ] 进入 Sudo 模式（点击顶部盾牌图标）
- [ ] 开始使用！

---

## 📖 目录

- [项目概述](#-项目概述)
- [核心特性](#-核心特性)
- [架构设计](#-架构设计)
  - [整体架构](#整体架构)
  - [分层设计](#分层设计)
  - [Mixin 组合模式](#mixin-组合模式)
- [核心功能模块](#-核心功能模块)
  - [记忆系统](#记忆系统)
  - [身份与群体系统](#身份与群体系统)
  - [消息优化](#消息优化)
  - [文件管理](#文件管理)
  - [档案馆系统](#档案馆系统)
  - [知识库与学习](#知识库与学习)
  - [Web UI](#web-ui)
  - [定时任务](#定时任务)
- [技术栈](#-技术栈)
- [设计理念](#-设计理念)
- [快速开始](#-快速开始)
- [项目统计](#-项目统计)
- [文档](#-文档)

## 📌 项目概述

### 项目定位

Scriptor 是一个**跨越个体与群体的通用 AI 管家**，定位于为用户提供长期记忆管理、个性化交互、群体协作等智能化服务。

### 核心价值

- **长期记忆**：保存数年以上的交互记忆，支持时间跨度查询与主题聚合
- **多用户支持**：个人画像 + 群体画像双重注入，群内每个成员都有独立画像
- **跨平台身份**：QQ/微信/Telegram 统一身份管理，跨端数据互通
- **智能检索**：混合检索（向量+BM25+ 文件）+ 智能降级，高召回率高可用
- **渐进式披露**：Token 优化 85%+，AI 按需读取，自主学习能力

### 适用场景

- 个人 AI 管家：长期记忆、日程管理、知识积累
- 群组 AI 助手：群体记忆、多用户识别、群组协作
- 企业知识库：结构化数据存储、SQL 查询、文档管理

## ✨ 核心特性

### 记忆系统
✅ 日记、长期记忆、知识图谱、向量数据库四位一体  
✅ 多层次记忆：热记忆（会话上下文）、冷记忆（Markdown 日记）、归档记忆（提炼事实）  
✅ 混合检索引擎：Tantivy BM25 + ChromaDB 向量 + 智能降级  
✅ 睡眠巩固机制：会话闲置时主动提炼、去重、合并

### 身份与群体
✅ 跨平台身份管理：QQ/微信/Telegram 统一身份  
✅ 个人画像 + 群体画像双重注入  
✅ 多用户支持：群内每个成员独立画像，AI 精准识别  
✅ 三级隐私边界：group/personal/cross，隐私保护与跨场景检索平衡

### 交互体验
✅ 智能分段发送：拟人化打字延迟，保护@提及和表格  
✅ 引用回复：AI 决策 target_msg_id，对话精准  
✅ 免@唤醒：名称检测 + 注意力窗口，更像真人  
✅ 连续对话：话题相关性判定，自然流畅

### 企业级安全
✅ AES-256 加密存储  
✅ 路径注入防护  
✅ 会话级并发锁  
✅ 脱敏处理

### 档案馆系统
✅ 结构化数据存储（SQLite）  
✅ SQL 查询 + 原文对照  
✅ Excel/CSV/TXT 导入  
✅ 个人/群组/全局三级档案馆

### 知识库与学习
✅ 知识图谱：全局共享，支持涌现关联  
✅ 学习/授课模式：三态认知模型（日常/学习/授课）  
✅ 待确认知识机制：防止错误污染  
✅ 双轨写入：知识库（KB）+ 知识图谱（KG）
✅ **SOP 渐进式披露**：统一 `P_SOP.md`、`G_SOP.md`、`SOP.md` 命名规范，通过 ContextIndexer 动态索引，按需读取，大幅优化 Token 消耗
✅ **追加防御机制**：强制 AI 使用追加模式新增 SOP 流程，防止破坏性覆写

### 文件管理
✅ 自动保存：图片/文件自动保存到媒体库  
✅ 隔离存储：个人文件与群体文件物理隔离  
✅ 智能检索：关键词、时间范围、类型过滤  
✅ 跨场景发送：支持从个人/群体媒体库查找并发送  
✅ **虚拟文件系统 (VFS)**：向 AI 隐藏物理路径，提供 `@personal/`、`@group/`、`@root/` 等语义化命名空间，降低认知负担并强化权限控制  
✅ **全工具 VFS 支持**：所有文件操作工具（`file_read`, `file_write`, `file_edit`, `file_append`, `file_delete`, `file_grep`, `file_list`, `file_send`）均已完全适配 VFS  
✅ **文件发送工具**：支持将 VFS 文件作为真实附件发送给用户（如 `@personal/P_SOUL.md`）
✅ **Read-Before-Write 架构**：强制 AI 在修改文件前必须先读取，配合会话级状态管理和读取去重机制，彻底消灭盲目覆写和幻觉编辑，大幅节省 Token 消耗

### Web UI
✅ 8 个功能页面：系统概览、记忆管理、档案馆、知识库、配置中心等  
✅ Vue 3 + Vuetify + TypeScript  
✅ FastAPI 后端 + bcrypt 密码加密 + CSRF 保护

### 定时任务
✅ 个人/群组/全局三级任务体系  
✅ 主动问候：早安（8 点）、晚安总结（22 点）  
✅ 自动备份：每天凌晨 4 点自动备份数据  
✅ Heartbeat 定时任务：赋予 AI 主动巡逻能力  
✅ 闲时文件整理：自动整理 TODO 和 MEMORY  
✅ 上下文隔离：提醒和任务严格遵守"原路返回"原则

## 🏗️ 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    插件层 (Plugin Layer)                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ScriptorPlugin (main.py)                                 │   │
│  │  - Mixin 组合 (11 个功能模块)                                │   │
│  │  - AstrBot 框架对接                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                   Mixin 层 (业务模块层)                           │
│  ┌──────┬──────┬───────┬────────┬────────┬──────┬──────┬────┐ │
│  │Helpers│Identity│Memory │Learning│Knowledge│Events│Tools │...│ │
│  └──────┴──────┴───────┴────────┴────────┴──────┴──────┴────┘ │
├─────────────────────────────────────────────────────────────────┤
│                   核心层 (Core Layer)                            │
│  ┌──────────────┬──────────────┬──────────────┬────────────┐  │
│  │MemoryManager │SearchEngine  │PromptBuilder │GroupManager│  │
│  │IdentityMgr   │Compactor     │LearningMgr   │ArchiveMgr  │  │
│  │ActiveReplyMgr│SmartSender   │KnowledgeGraph│MediaMgr    │  │
│  └──────────────┴──────────────┴──────────────┴────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                 基础设施层 (Infrastructure)                       │
│  ┌──────────┬──────────┬──────────┬──────────┬────────────┐   │
│  │SQLite    │ChromaDB  │Tantivy   │FastAPI   │File System │   │
│  │(WAL 模式)  │(向量库)   │(BM25)     │(Web UI)   │(Markdown)  │   │
│  └──────────┴──────────┴──────────┴──────────┴────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 分层设计

#### 1. 插件层 (Plugin Layer)
- **职责**：AstrBot 框架对接，插件生命周期管理
- **核心组件**：`ScriptorPlugin` (main.py)
- **特点**：通过 Mixin 模式组合 11 个功能模块

#### 2. Mixin 层 (业务模块层)
- **职责**：业务逻辑封装，职责分离
- **核心 Mixins**：
  - `HelpersMixin`：内部辅助方法
  - `IdentityMixin`：身份与权限管理
  - `MemoryMixin`：记忆管理
  - `LearningMixin`：学习/授课模式
  - `KnowledgeMixin`：知识库管理
  - `EventsMixin`：事件拦截
  - `ToolsMixin`：LLM 工具（40+ 个）
  - `MediaToolsMixin`：媒体工具
  - `CommandsMixin`：普通命令
  - `AdminMixin`：管理员命令

#### 3. 核心层 (Core Layer)
- **职责**：核心业务逻辑实现
- **核心组件**：
  - `MemoryManager`：记忆管理核心
  - `SearchEngine`：混合检索引擎
  - `PromptBuilder`：系统提示词构建器
  - `GroupManager`：群体管理器
  - `IdentityManager`：跨平台身份管理
  - `KnowledgeGraph`：轻量级知识图谱
  - `ArchiveManager`：档案馆管理
  - `MediaManager`：媒体资源管理
  - `SmartSender`：智能分段发送器
  - `ActiveReplyManager`：主动回复管理

#### 4. 基础设施层 (Infrastructure)
- **职责**：数据存储与基础服务
- **核心组件**：
  - `SQLite` (WAL 模式)：对话总账、档案馆
  - `ChromaDB`：向量数据库（语义搜索）
  - `Tantivy`：BM25 全文检索
  - `FastAPI`：Web UI 后端
  - `File System` (Markdown)：文件存储

### Mixin 组合模式

**设计思想**：组合优于继承

```python
# main.py
class ScriptorPlugin(
    BaseMixin,
    HelpersMixin,
    IdentityMixin,
    MemoryMixin,
    LearningMixin,
    KnowledgeMixin,
    EventsMixin,
    ToolsMixin,
    MediaToolsMixin,
    CommandsMixin,
    AdminMixin,
):
    """Scriptor 插件主类 - 通过 Mixin 模式组合功能"""
    
    def __init__(self, context):
        super().__init__(context)
        # 初始化所有核心组件
        self.memory_manager = MemoryManager(...)
        self.identity_manager = IdentityManager(...)
        self.group_manager = GroupManager(...)
        self.search_engine = SearchEngine(...)
        self.prompt_builder = PromptBuilder(...)
        self.smart_sender = SmartSender(...)
        # ... 其他组件
```

**优势**：
- ✅ **职责分离**：每个 Mixin 负责一个业务领域
- ✅ **易于测试**：每个 Mixin 可独立测试
- ✅ **灵活扩展**：新增功能只需添加新 Mixin

## 🔧 核心功能模块

### 记忆系统

#### 多层次记忆体系

```
热记忆 (Hot Memory)
└─→ 当前会话的即时上下文 (对话总账 SQLite)
  
冷记忆 (Cold Memory)  
└─→ 基于日期的 Markdown 日记 (按天存储)
  
归档记忆 (Archived Memory)
└─→ 经过"睡眠巩固"提炼的核心事实 (MEMORY.md)
```

#### 记忆存储金字塔

```
┌──────────────────────────────────────────────────────────────┐
│                    记忆存储金字塔                               │
├──────────────────────────────────────────────────────────────┤
│  第一层：Markdown 文件（主记忆）                                │
│  ├─ 用户画像：profiles/{uid}/P_PROFILE.md                   │
│  ├─ 群体画像：groups/{group_id}/G_PROFILE.md                │
│  ├─ 灵魂文件：profiles/{uid}/P_SOUL.md                      │
│  ├─ 日记系统：profiles/{uid}/memory/{YYYY-MM-DD}.md         │
│  ├─ 长期记忆：profiles/{uid}/P_MEMORY.md                    │
│  ├─ 行为守则：profiles/{uid}/P_AGENTS.md                    │
│  ├─ 群组守则：groups/{group_id}/G_GROUP.md                  │
│  └─ Todo 清单：profiles/{uid}/P_TODO.md                     │
│                                                              │
│  第二层：向量数据库（辅助检索）                                  │
│  ├─ ChromaDB: global/chroma_db/                            │
│  ├─ 存储：个人记忆向量（独立隔离）                              │
│  └─ 用途：语义搜索、相似记忆召回                              │
│                                                              │
│  第三层：知识图谱（全局关联）                                   │
│  ├─ 文件：global/knowledge_graph.json                       │
│  ├─ 特点：多用户/群体共享                                     │
│  └─ 优势：跨用户涌现关联、全局知识网络                         │
│                                                              │
│  第四层：档案馆（外挂数据库）                                   │
│  ├─ 文件：global/archives.db / profiles/{uid}/archives.db   │
│  ├─ 用途：结构化数据存储（Excel/CSV 导入）                      │
│  └─ 查询：AI 通过 SQL 查询，附带原文对照                        │
└──────────────────────────────────────────────────────────────┘
```

#### 混合检索引擎

```python
# core/search_engine.py
class SearchEngine:
    """混合检索引擎 - 向量 +BM25+ 文件搜索"""
    
    async def search(self, query: str, uid: str, group_id: str, scope: str, limit: int):
        """
        检索策略：
        1. Tantivy BM25 - 关键词搜索
        2. ChromaDB - 向量语义搜索
        3. 结果融合与重排
        4. 智能降级 - 模型不可用时降级为纯文本搜索
        """
```

#### 睡眠巩固机制

会话闲置时触发记忆提炼流程：
1. 提取未处理消息
2. LLM 深度分析提取记忆
3. 更新知识图谱
4. 合并重复记忆
5. 衰减记忆强度

### 身份与群体系统

#### 跨平台身份管理

```python
# core/identity_manager.py
@dataclass
class IdentityMapping:
    """跨平台身份映射"""
    physical_id: str      # 物理 ID（平台原始 ID）
    logical_uid: str      # 逻辑 UID（统一身份 ID）
    platform: str         # 平台（QQ/微信/Telegram）
    aliases: List[str]    # 别名列表

class IdentityManager:
    """跨平台统一身份管理"""
    
    def resolve_identity(self, platform: str, physical_id: str) -> str:
        """解析身份，返回统一的 logical_uid"""
```

**示例**：
- QQ: `user_qq_123456` → logical_uid: `user_abc`
- 微信：`user_wx_789012` → logical_uid: `user_abc`

**结果**：同一用户在不同平台使用统一的 logical_uid

#### 群体画像构建

```python
# core/prompt_builder.py
def _build_group_context(self, group_id: str) -> str:
    """
    构建群体上下文
    
    注入内容：
    1. 群体工作流 (GROUP.md)
    2. 群体画像 (GROUP_PROFILE.md)
    3. 群体记忆 (MEMORY.md)
    4. 群成员列表
    """
```

#### 个性化回复流程

```
群成员 A 发送："我昨天感冒了"
    ↓
身份识别：uid = "user_A"
    ↓
PromptBuilder.build_system_prompt("user_A", "group_123", "我昨天感冒了")
    ↓
注入：
- user_A 的个人画像（过敏史、健康状况）
- group_123 的群体画像（群规、氛围）
- user_A 的热记忆（最近对话）
- user_A 的冷记忆（历史健康记录）
- 知识图谱（感冒相关建议）
    ↓
LLM 生成针对性回复：
"哎呀，感冒了要多休息呀！记得你之前说过对某些药过敏，
不要吃含 XX 成分的感冒药。群里大家也很关心你呢~"
```

### 消息优化

#### 智能分段发送

```python
# core/smart_sender.py
class SmartSender:
    """智能分段发送器"""
    
    def split_text(self, text: str) -> List[Segment]:
        """
        分段策略：
        1. 正则分段：r".*?[。？！~…\n]+|.+$"
        2. 保护@提及：不切断 "[@张三](UID:user_abc)"
        3. 表格保护：Markdown 表格不被拆分
        4. 长文本处理：超过 150 字符按空行分段
        """
        
    async def send_with_typing_delay(self, segments: List[Segment]):
        """
        拟人化发送：
        - 打字速度：0.08 秒/字符
        - 最小延迟：1.5 秒
        - 最大延迟：3.5 秒
        - 随机波动：±20%
        - 会话锁：防止消息穿插
        """
```

#### 多模式唤醒

```python
# core/active_reply_manager.py
async def should_reply(self, group_id, message, sender_id):
    """
    唤醒判定：
    
    1. 名称唤醒：
       - @机器人
       - 叫机器人名字（"小助手"、"管家"）
    
    2. 任务嗅探：
       - 检测到任务分配（"帮我查一下"、"记下来"）
    
    3. 连续对话判定：
       - 注意力窗口：2 分钟内
       - 消息条数：最多 10 条
       - 话题相关性：语义相似度 > 0.7
    
    4. 防抖处理：
       - 3 秒内不重复回复
    """
```

### 文件管理

#### 存储结构

```
{data_dir}/
├── profiles/                    # 个人文件目录
│   └── {uid}/
│       ├── media/
│       │   ├── images/          # 个人图片库
│       │   │   ├── 20260310_abc123.jpg
│       │   │   └── 20260311_def456.png
│       │   └── files/           # 个人文件库
│       │       ├── report.xlsx
│       │       └── notes.txt
│       └── media_index.json     # 个人媒体索引
│
├── groups/                      # 群体文件目录
│   └── {group_id}/
│       ├── media/
│       │   ├── images/          # 群体图片库
│       │   └── files/           # 群体文件库
│       └── media_index.json     # 群体媒体索引
│
└── global/                      # 全局配置
    └── chroma_db/              # 向量数据库
```

**隔离机制**：
- ✅ **物理隔离**：个人 (`profiles/`) 与群体 (`groups/`) 完全分离
- ✅ **索引隔离**：每个用户/群体有独立的 `media_index.json`
- ✅ **权限隔离**：群组成员只能访问群体媒体库

#### 三级隐私边界

| Scope | 群聊场景 | 私聊场景 | 需要理由 |
|-------|---------|---------|---------|
| **group** | 仅当前群聊 | ❌ 不可用 | ❌ |
| **personal** | 当前群聊 + 私聊 | ❌ 不可用 | ✅ 群聊需要 |
| **cross** | 当前群聊 + 私聊 + 所有群聊 | 默认使用 | ✅ 群聊需要 |

### 档案馆系统

#### 档案馆定位

**重要说明**：档案馆**不是**记忆系统的一部分，它是外挂数据库。重要决策、会议日志、文件导入等结构化数据应存入档案馆，**不应进入记忆系统**。

#### 核心功能

```python
# core/archives/manager.py
class ArchiveManager:
    """档案管理器 - 结构化数据存储"""
    
    存储路径：
    - 全局馆：global/archives.db
    - 个人馆：profiles/{uid}/archives.db
    - 群体馆：groups/{group_id}/archives.db
    
    核心功能：
    1. 档案表注册与管理
    2. CRUD 操作（只读安全检查）
    3. 元数据存储（表结构、列信息）
```

#### 文件导入流程

```python
# core/archives/ingestor.py
class DataIngestor:
    """数据采集器 - Excel/CSV/TXT导入"""
    
    def ingest_excel(self, file_path: str, display_name: str, description: str):
        """
        导入 Excel/CSV/TXT 文件到档案馆
        
        流程：
        1. 读取文件（支持多种编码检测）
        2. 自动检测分隔符（TXT）
        3. 创建 SQLite 表
        4. 注册到档案元数据表
        5. 返回表名和行数
        """
```

### 知识库与学习

#### 学习来源

- **CoPaw** - Agent 框架设计
- **ReMeLight** - 长期记忆架构
- **Angel Memory** - 情感记忆与人情味

#### 三态认知模型

| 状态 | 图标 | 特点 | 使用场景 |
|------|------|------|---------|
| **日常模式** | 🟢 | 正常工作，知识可读写 | 日常对话、任务处理 |
| **学习模式** | 🟡 | 积极提取，待确认机制 | 学习新知识、业务培训 |
| **授课模式** | 🔴 | 只读锁定，权威专家 | 教学、答疑、知识输出 |

#### 待确认知识机制

```python
@dataclass
class KnowledgeExtraction:
    """提取的知识条目"""
    title: str
    content: str
    knowledge_type: str  # fact/skill/preference/rule/experience
    tags: List[str]
    is_pending: bool = True  # 待确认状态
    created_at: str
    extracted_by: str
```

**工作流程**：
```
1. 管理员：/开始学习
   ↓
2. AI 切换到🟡学习模式
   ↓
3. 用户进行教学对话
   ↓
4. AI 积极提取知识，标记为 pending 状态
   ↓
5. 管理员：/学习状态 → 查看待确认知识列表
   ↓
6. 管理员：/确认知识 → 双轨写入（KB + KG）
   ↓
7. 管理员：/结束学习 → 切换回🟢日常模式
```

#### 知识图谱

```python
# core/knowledge_graph.py
class KnowledgeGraph:
    """轻量级知识图谱 - 全局共享"""
    
    存储路径：global/knowledge_graph.json
    
    核心特性：
    1. 双层解析器：
       - 正则快速解析 Markdown 语法
       - LLM 模糊解析与自修复
    
    2. 双向同步：
       - MD <-> JSON 双向同步
       - 阈值晋升机制（>=0.8 权重常驻 MD）
    
    3. 多用户涌现关联：
       - 跨用户知识关联
       - 群体智慧涌现
       - 全局知识网络
```

### Web UI

#### 技术栈

- **前端**：Vue 3.4.21 + TypeScript + Vuetify 3.5.9
- **后端**：FastAPI + Uvicorn + SlowAPI
- **安全**：bcrypt 密码加密 + CSRF 保护

#### 功能页面

| 路由 | 页面名称 | 功能描述 | 图标 |
|------|---------|---------|------|
| `/` | 系统概览 | 系统状态、活跃会话、快捷操作 | mdi-view-dashboard |
| `/memory` | 记忆管理 | 查看/编辑记忆文件、知识图谱可视化 | mdi-brain |
| `/archives` | 档案馆 | 档案馆数据库管理、SQL 查询、数据导入 | mdi-database |
| `/knowledge` | 知识库 | 知识搜索、知识添加、研究话题 | mdi-book-open-variant |
| `/config` | 配置中心 | 修改插件配置、密码设置、端口配置 | mdi-cog |
| `/performance` | 性能面板 | CPU/内存监控、Token 使用统计、响应时间 | mdi-chart-line |
| `/maintenance` | 维护工具 | 数据库清理、索引重建、备份恢复 | mdi-tools |
| `/debug` | 调试工具 | 日志查看、Prompt 调试、工具测试 | mdi-bug |

#### 安全机制

```python
def _hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希"""
    import bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def _verify_password(password: str, hashed: str) -> bool:
    """验证密码是否匹配哈希值"""
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
```

### 定时任务

#### 核心组件

```python
# core/scheduler.py
class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self, data_dir: Path):
        self.tasks_file = data_dir / "scheduled_tasks.json"
        self.state_file = data_dir / "scheduler_state.json"
        self.backup_dir = data_dir / "backups"
        self.tasks: List[ScheduledTask] = []
        self._running = False
        self._check_interval = 60  # 60 秒轮询一次
```

#### 三级任务体系

**1. 个人任务**：
- `uid` 设置为用户 ID
- `group_id` 为空或 "private"
- 触发场景：私聊或个人日程

**2. 群组任务**：
- `group_id` 设置为群组 ID
- `uid` 为空
- 触发场景：群组活动、群公告

**3. 全局任务**：
- `uid` 和 `group_id` 都为 "*"
- 触发场景：全局通知、节日祝福

#### 主动问候机制

```python
def _check_and_trigger_proactive_tasks(self):
    """检查并触发主动问候/提醒任务"""
    now = time.time()
    current_hour = datetime.fromtimestamp(now).hour
    today_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d")

    # 每天早上 8 点触发早安问候
    if current_hour == 8:
        if self._morning_greeted_today != today_str:
            self._trigger_proactive_event("morning_greeting")
            self._morning_greeted_today = today_str

    # 每天晚上 22 点触发晚安/总结提醒
    if current_hour == 22:
        if self._evening_greeted_today != today_str:
            self._trigger_proactive_event("evening_summary")
            self._evening_greeted_today = today_str
```

#### 自动备份机制

- **触发时间**：每天凌晨 4 点
- **备份内容**：数据目录（排除 backups 和 chroma_db）
- **备份格式**：tar.gz 压缩包
- **保留策略**：保留最近 7 天备份

#### Heartbeat 定时任务系统

Heartbeat 是一个定时触发的主动任务系统（学习自 CoPaw 设计），赋予 AI 真正的"主观能动性"。

**工作原理**：
- 系统每隔一定时间（默认 30 分钟，可通过 `heartbeat_interval` 配置）检查 `HEARTBEAT.md` 文件
- 如果文件有内容，就将其作为用户消息发送给 AI 执行
- 执行结果发送到对应的对话框

**三层架构**：
- **全局 HEARTBEAT.md**：对所有用户和群聊生效（`templates/global/HEARTBEAT.md`）
- **群组 G_HEARTBEAT.md**：只对该群聊生效（`groups/<gid>/G_HEARTBEAT.md`）
- **个人 P_HEARTBEAT.md**：只对该用户私聊生效（`profiles/<uid>/P_HEARTBEAT.md`）

**使用示例**：
```markdown
# 在 G_HEARTBEAT.md 中写入：
检查群里今天的聊天记录并总结热点话题
```

#### 闲时文件整理

当用户或群聊闲置超过一定时间（默认 1 小时）后，系统会自动执行文件整理任务：
- 检查 `NOTES.md` 和 `TODO.md`
- 将重要信息提炼到 `MEMORY.md`
- 清理已完成的 TODO 任务
- 整理过长的 NOTES 内容

#### 上下文隔离原则

**重要**：所有定时任务和提醒都严格遵守"原路返回"原则：
- 私聊发起的提醒 → 只发送到私聊
- 群聊 A 发起的提醒 → 只发送到群聊 A
- 个人 Heartbeat 任务 → 只在个人私聊执行
- 群组 Heartbeat 任务 → 只在该群组执行

系统已废弃跨群消息功能，彻底杜绝隐私泄露风险。

## 🛠️ 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.9+ | 主要编程语言 |
| AstrBot | 4.0+ | 聊天机器人框架 |
| SQLite | - | 对话总账、档案馆（WAL 模式） |
| ChromaDB | - | 向量数据库（语义搜索） |
| Tantivy | - | BM25 全文检索引擎 |
| jieba | 0.42.1+ | 中文分词（BM25 搜索优化） |
| FastAPI | - | Web UI 后端框架 |
| Uvicorn | - | ASGI 服务器 |
| SlowAPI | - | 限流中间件 |
| bcrypt | - | 密码加密 |
| psutil | - | 系统监控 |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.4.21 | 前端框架 |
| TypeScript | - | 类型安全 |
| Vuetify | 3.5.9 | Material Design UI 库 |
| Vue Router | 4.3.0 | 路由管理 |
| Pinia | 2.1.7 | 状态管理 |
| Axios | 1.6.8 | HTTP 客户端 |
| Vite | 5.2.0 | 构建工具 |
| md-editor-v3 | 4.12.1 | Markdown 编辑器 |
| @vueuse/core | 10.9.0 | 工具库 |

### 基础设施

| 组件 | 用途 |
|------|------|
| File System (Markdown) | 文件存储（日记、画像、记忆等） |
| SearXNG | 本地部署搜索引擎（联网搜索） |

## 💡 设计理念

### 1. 组合优于继承

采用 Mixin 组合模式，将 40+ 个核心模块组织为 11 个 Mixin，每个 Mixin 负责一个业务领域，实现职责分离、易于测试、灵活扩展。

### 2. 渐进式披露与常驻上下文 (Progressive Disclosure & Resident Context)

**核心思想**：
```
1. 核心常驻：PROFILE (画像)、AGENTS/GROUP (行为守则) 等决定 AI 基础认知和行为边界的文件，作为常驻上下文 (Resident Context) 完整加载，防止 AI "盲目行动"。
2. 渐进式披露：MEMORY (长期记忆)、SKILL (技能) 等大容量数据文件，采用目录索引模式。System Prompt 只包含精简的文件目录树。
3. 按需读取：AI 通过 file_read_tool 主动获取需要的节点内容。
4. 节约 Token：在保证 AI 核心认知不缺失的前提下，将基础 Prompt 从几千 Token 降至几百 Token。
```

**Token 优化效果**：

| 项目 | 旧模式 | 新模式 | 优化 |
|------|--------|--------|------|
| **基础 Prompt** | 5000+ Token | 1500-2000 Token | **60%+ 减少** |
| **PROFILE.md** | 全量加载 | 全量加载 (常驻) | **0% (保证认知)** |
| **MEMORY.md** | 全量加载 (3000 Token) | 目录索引 (80 Token) | **97% 减少** |
| **SOP.md** | 全量加载 (1500 Token) | 目录索引 (60 Token) | **96% 减少** |

### 2.1 Prompt Caching 极致优化 (缓存命中策略)

为了弥补核心文件常驻带来的 Token 增加，系统在 `PromptBuilder` 中实现了严格的**加载优先级策略**，以最大化利用 LLM 的 Prompt Caching 机制：

**加载顺序 (从前到后)**：
1. **[100] 全局核心 (Global)**：`SOUL.md` (所有用户/群聊共享，绝对静态)
2. **[99-97] 群组核心 (Group)**：`G_SOUL.md`, `G_PROFILE.md`, `G_GROUP.md` (同一群内所有用户共享，相对静态)
3. **[96-94] 个人核心 (Personal)**：`P_SOUL.md`, `P_PROFILE.md`, `P_AGENTS.md` (个人专属，动态变化)

**缓存原理**：
在多用户群聊场景中，当不同用户发言时，Prompt 的前 70% (Global + Group) 是完全一致的。LLM 能够完美命中这部分前缀缓存，从而大幅降低实际 Token 消耗和响应延迟。个人专属的动态文件被严格放置在 Prompt 尾部，防止破坏共享缓存。

### 3. 多层次记忆架构

**设计原则**：性能与容量平衡

```
热记忆 (Hot Memory) → 当前会话上下文 (SQLite 对话总账)
  ↓ 快速访问，低延迟
冷记忆 (Cold Memory) → Markdown 日记 (按天存储)
  ↓ 大容量，持久化
归档记忆 (Archived Memory) → 提炼的核心事实 (MEMORY.md)
  ↓ 睡眠巩固，去重合并
```

### 4. 混合检索策略

**设计原则**：高召回率、高可用性

1. **Tantivy BM25**：关键词匹配，精确查找
2. **ChromaDB 向量**：语义匹配，模糊查找
3. **结果融合重排**：综合排序，提升质量
4. **智能降级**：模型不可用时降级为纯文本搜索

### 5. 三级隐私边界与管家人设 (Privacy Boundaries & Butler Persona)

**设计原则**：隐私保护与跨场景检索平衡，结合"管家"人设化解冲突

| 级别 | 范围 | 场景 | 权限说明 |
|------|------|------|---------|
| **group** | 仅当前群聊 | 群聊默认，保护隐私 | 只能访问 `@group/` 目录，无法跨群访问 |
| **personal** | 当前群聊 + 私聊 | 群聊需理由，私聊不可用 | 只能访问当前用户的 `@personal/` 目录 |
| **cross** | 全量（所有群聊 + 私聊） | 群聊需理由，私聊默认 | 跨用户/跨群访问（受严格限制） |

**管家人设的隐私保护**：
在群聊中，AI 扮演"大家的管家"角色。当群成员 A 试图打听群成员 B 的隐私时，AI 不会生硬地拒绝（"我没有权限"），而是基于管家的职业素养，用高情商的方式化解（"B 先生的私人事务我不便透露，不过大家可以多在群里交流呀"）。这种基于 Prompt 的软性隐私保护，比硬编码的权限拦截更具人情味。

### 6. 档案馆与记忆系统分离

**设计原则**：结构化数据 vs 软性记忆

- **记忆系统**：存储对话、经历、情感等软性记忆
  - 日记、MEMORY.md、向量记忆
  
- **档案馆**：存储结构化、重要、需精确查询的数据
  - 会议记录、项目文档、Excel 数据、重要决策

### 7. 待确认知识机制

**设计原则**：防止错误污染

学习模式下提取的知识标记为 `pending` 状态，需管理员确认后才正式写入知识库和知识图谱，确保知识质量。

### 8. 拟人化交互

**设计原则**：更像真人

- 智能分段发送（保护@提及和表格）
- 拟人化打字延迟（0.08 秒/字符，±20% 波动）
- 免@唤醒（名称检测 + 注意力窗口）
- 引用回复（AI 决策 target_msg_id）
- 连续对话判定（话题相关性）

### 9. 虚拟文件系统 (VFS)

**设计原则**：认知减负与权限强化

- **向 AI 隐藏物理复杂性**：AI 不再需要处理包含哈希值的物理路径（如 `profiles/user_xxx/`），而是使用语义化的虚拟命名空间。
- **核心命名空间**：
  - `@personal/`：映射到当前用户的个人物理目录。
  - `@group/`：映射到当前群组的物理目录。
  - `@root/`：映射到系统全局根目录（受严格的 Sudo 权限保护）。
- **所见即所得的闭环**：通过“拦截-映射-反向格式化”机制，确保 AI 看到的路径、请求的路径以及工具返回的路径全部统一为虚拟路径。

### 10. Read-Before-Write 架构

**设计原则**：事前强制约束与 Token 极致优化

- **强制先读后写**：将“防缩水”从**事后惩罚**升级为**事前拦截**。AI 必须先在脑海中构建完整的上下文（读取文件），才能被允许修改文件。
- **会话级状态感知**：赋予工具“记忆”能力，系统在内存中维护 `_SESSION_READ_STATES`，记录 AI 在当前会话中是否已经读过某个文件。
- **读取去重 (Dedup)**：如果 AI 重复读取一个未发生变化的文件，系统直接拦截并提示其查阅历史记录，避免重复下发大量代码/文本，大幅节省 Token。
- **5 级模糊匹配容错**：配合 `file_edit` 工具，提供精确匹配、行尾空格容错、引号标准化、空白字符容错等 5 级降级匹配策略，彻底消灭幻觉编辑。

## 🚀 快速开始

### 🆕 最近更新 (v1.0.0 - 2026-04-11)

#### 新增功能
- ✨ **TODO 历史归档系统**：实现"热数据全量加载 + 冷数据工具检索"三级缓存架构
  - **按月切片归档**：超过 3 天的已完成任务自动归档到 `TODOed/P_TODO_YYYY-MM.md` 或 `TODOed/G_TODO_YYYY-MM.md`
  - **静默触发归档**：每次构建 Prompt 时自动触发归档，确保热数据绝对干净
  - **顶部提示注入**：在 TODO 文件开头注入引导提示，告知 AI 历史数据已归档
  - **历史检索工具**：新增 `search_historical_todos` 工具，支持按年月、关键词搜索历史待办
  - **防爆仓截断**：单次搜索最多返回 50 条记录，超出时提示用户缩小范围
- ✨ **文件发送工具 (`file_send_tool`)**：支持将 VFS 文件作为真实附件发送给用户，用户可直接下载查看（如 `@personal/P_SOUL.md`）
- ⚡ **知识图谱性能优化**：实现增量处理 + 并行化（`asyncio.Semaphore`），处理速度提升约 3 倍
- 🔄 **主动回复降级策略**：完善小模型 → 大模型的 Fallback 机制，提升意图判定可靠性

#### 重要修复
- 🐛 **修复斜杠命令失效问题**：回退到手动定义的命令代理方案，确保所有 26 个斜杠命令正常工作
- 🐛 **修复 VFS 导入路径错误**：修正 `file_ops.py` 中的相对导入路径，解决 `ModuleNotFoundError`
- 🐛 **修复配置同步问题**：实现 AstrBot WebUI 与插件配置的双向同步（UTF-8 BOM 处理 + 扁平/嵌套格式转换）

#### 架构改进
- 🏗️ **TODO 三级缓存架构**：
  | 数据层级 | 存储位置 | 加载方式 | Token 消耗 |
  |---------|---------|---------|-----------|
  | **热数据** | `P_TODO.md` / `G_TODO.md` | 全量加载 | 恒定（仅未完成 + 3天内已完成） |
  | **冷数据** | `TODOed/P_TODO_YYYY-MM.md` | 工具检索 (`search_historical_todos`) | 按需加载，50条截断 |
  | **目录树** | `context_indexer` | 不索引归档文件 | 零消耗 |
- 🏗️ **全工具 VFS 适配**：所有文件操作工具（`file_read`, `file_write`, `file_edit`, `file_append`, `file_delete`, `file_grep`, `file_list`, `file_send`）均已完全支持 VFS 虚拟路径
- 🔧 **API 规范化**：修复 32 处 API 导入，从 `astrbot.core` 迁移到 `astrbot.api`

### 环境要求

- Python 3.9+
- AstrBot 4.0+
- 操作系统：Windows / Linux / macOS

### 安装依赖

```bash
# 进入插件目录
cd AstrBot/data/plugins/astrbot_plugin_scriptor

# 安装后端依赖
pip install -r requirements.txt

# 安装 Web UI 依赖（可选）
pip install fastapi uvicorn slowapi psutil bcrypt
```

### 配置

编辑 `config.json` 配置文件：

```json
{
  "web_ui_enabled": true,
  "web_api_port": 18111,
  "admin_uids": ["your_uid"],
  "media_auto_save_enabled": true,
  "smart_split_group_reply": true,
  // ... 其他配置项（共 90+ 个）
}
```

### 启动

1. 重启 AstrBot
2. 访问 Web UI：`http://localhost:18111`
3. 首次访问需设置密码

### 基本使用

#### 个人使用

```
用户（私聊）："记住我明天下午 3 点开会"
AI: "好的，已记录你的日程安排。"

用户："帮我找一下去年做的那个项目报告"
AI: （检索记忆系统）"找到了，这是你去年做的 XX 项目报告..."
```

#### 群组使用

```
群成员 A："我昨天感冒了"
AI: "哎呀，感冒了要多休息呀！记得你之前说过对某些药过敏..."

群成员 B："找一下昨天发的那个图片"
AI: （搜索群体媒体库）"找到了，是这张吗？" [发送图片]
```

#### 学习模式

```bash
/开始学习
# AI 切换到🟡学习模式

用户："办理刑事案件的基本流程是：1. 立案 → 2. 侦查 → 3. 审查起诉 → 4. 审判"
AI: "好的，我已记录'刑事案件办理流程'知识点。"

/学习状态
# 查看待确认知识

/确认知识
# 双轨写入（KB + KG）

/结束学习
# 切换回🟢日常模式
```

#### 档案馆导入

```
用户发送文件：sales_report.xlsx
AI: "已自动保存到媒体库。"

用户："帮我把这个文件导入到档案馆"
AI: （调用 import_file_to_archive）
"✅ 文件导入成功！
   原始文件：sales_report.xlsx
   目标位置：群组档案馆
   表名：test_sales_report
   行数：150"
```

## 📊 项目统计

### 代码规模

- **代码行数**: ~18,000+ 行（后端） + ~3,000 行（前端）
- **核心模块**: 40+ 个
- **Mixin 模块**: 11 个
- **测试覆盖**: 342 个测试用例，98%+ 通过率

### 配置与模板

- **配置项**: 90+ 个（嵌套模型管理）
- **模板文件**: 17 个（个人 7 + 群组 7 + 全局 3）
- **Web UI 页面**: 8 个
- **API 接口**: 20+ 个

### 数据容量

- **记忆容量**: 10 万 + 条记录
- **档案馆容量**: 100+ 个档案表
- **媒体库容量**: 10 万 + 个文件（图片/文档）
- **知识图谱**: 全局共享，支持涌现关联

### 功能特性

- **支持平台**: QQ/微信/Telegram/Discord
- **搜索引擎**: 10+ 个聚合引擎（SearXNG）
- **隐私级别**: 3 级（group/personal/cross）
- **认知状态**: 3 态（日常/学习/授课）
- **定时任务**: 3 级（个人/群组/全局）

## 📚 文档

- [完整架构文档](chat.md) - 详细的架构演进与技术实现
- [Web UI 文档](web/README.md) - Web UI 使用指南
- [API 文档](docs/api.md) - API 接口文档
- [开发指南](docs/development.md) - 开发者指南

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

Copyright (C) 2026 ysf7762-dev

本项目采用 **GNU Affero General Public License v3.0 (AGPL-3.0)** 开源协议。

详细说明请参阅 [LICENSE](LICENSE) 文件或访问 <https://www.gnu.org/licenses/agpl-3.0.html>

## 🙏 致谢

- [AstrBot](https://github.com/Soulter/AstrBot) - 聊天机器人框架
- [CoPaw](https://github.com/CoPaw) - Agent 框架设计
- [ReMeLight](https://github.com/ReMeLight) - 长期记忆架构
- [Angel Memory](https://github.com/AngelMemory) - 情感记忆与人情味

---

**生成时间**: 2026-04-04  
**文档版本**: v1.0  
**项目版本**: Scriptor v1.0
