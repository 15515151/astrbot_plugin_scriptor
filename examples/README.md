# Examples 目录结构说明

本目录展示了 Scriptor 插件初始化后的标准文件结构，供开发者参考。

## 目录结构

```
examples/
├── standard_user_profile/       # 标准个人用户目录样例
│   ├── P_PROFILE.md             # 个人画像（P_ 前缀）
│   ├── P_SOUL.md                # 个人人格定义（P_ 前缀）
│   ├── P_MEMORY.md              # 个人长期记忆（P_ 前缀）
│   ├── P_HEARTBEAT.md           # 个人心跳指令（P_ 前缀）
│   ├── P_TODO.md                # 个人待办事项（P_ 前缀）
│   ├── P_AGENTS.md              # 个人代理设定（P_ 前缀）
│   ├── SOP.md                   # 自定义工作流程（用户创建）
│   └── memory/                  # 日记目录
│       └── 2026-04-03.md
│
├── standard_group_profile/      # 标准群组目录样例
│   ├── G_PROFILE.md             # 群组画像（G_ 前缀）
│   ├── G_SOUL.md                # 群组人格定义（G_ 前缀）
│   ├── G_MEMORY.md              # 群组记忆（G_ 前缀）
│   ├── G_HEARTBEAT.md           # 群组心跳指令（G_ 前缀）
│   ├── G_TODO.md                # 群组待办事项（G_ 前缀）
│   └── G_GROUP.md               # 群组工作流（G_ 前缀）
│
└── global_data/                 # 全局数据目录样例
    ├── SOUL.md                  # 全局核心人格基座（无前缀）
    ├── MEMORY.md                # 全局共享记忆（无前缀）
    └── HEARTBEAT.md             # 全局临时指令（无前缀）
```

## 命名规范说明

### 文件名前缀规则
- **P_** (Personal): 个人用户专属文件
- **G_** (Group): 群组专属文件
- **无前缀** (Global): 全局共享文件

### 为什么需要前缀？
1. **避免命名冲突**：当个人和群组文件同时加载到上下文时，防止同名文件混淆
2. **快速识别**：通过文件名即可判断文件归属
3. **Token 节约**：相比 `Personal_`、`Group_`、`Global_` 长前缀，短前缀更节省 Token

### 目录结构优势
- **按类型分组**：`personal/`、`group/`、`global/` 目录清晰分离
- **渐进式披露**：AI 通过目录路径即可理解文件用途
- **权限控制**：不同目录可应用不同的访问权限

## 初始化流程

### 新用户首次对话
1. 系统检测到新 UID
2. 从 `templates/personal/` 复制模板文件到 `profiles/{uid}/`
3. 创建 `BOOTSTRAP.md` 引导文件
4. AI 开始引导式对话，收集用户信息
5. 用户信息写入 `P_PROFILE.md`
6. 完成后删除 `BOOTSTRAP.md`

### 新群组首次激活
1. 系统检测到新 group_id
2. 从 `templates/group/` 复制模板文件到 `groups/{group_id}/`
3. 创建 `G_BOOTSTRAP.md` 引导文件
4. AI 开始引导式对话，收集群组信息
5. 群组信息写入 `G_PROFILE.md`
6. 完成后删除 `G_BOOTSTRAP.md`

### 全局数据初始化
1. 插件启动时自动执行
2. 从 `templates/global/` 复制模板文件到 `global/`
3. 仅管理员可在 Sudo 模式下修改

## 技能目录 (Skills)

技能文件位于插件根目录下的 `skills/` 文件夹（全局共享）：

```
astrbot_plugin_scriptor/
├── skills/                      # 全局技能目录（只读）
│   ├── scriptor-todo-schedule/
│   │   └── SKILL.md
│   └── [其他技能]/
├── templates/                   # 模板文件（只读）
├── profiles/                    # 用户数据（可读写）
├── groups/                      # 群组数据（可读写）
└── global/                      # 全局数据（仅 Sudo 可写）
```

## 注意事项

1. **不要手动修改 templates/ 目录**：这是官方模板，应该保持原样
2. **skills/ 是只读的**：AI 可以读取但不能修改技能文件
3. **用户可以自由编辑 profiles/ 和 groups/ 下的文件**
4. **global/ 目录需要 Sudo 权限**：普通用户无法修改
