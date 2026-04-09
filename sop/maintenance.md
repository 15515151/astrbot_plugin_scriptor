# 记忆维护 SOP

## 1. 睡眠巩固 (Sleep Consolidation)
- **触发条件**：跨天且超过 60 分钟未活跃。
- **操作**：
  - 提取最近 3 天的日记。
  - 识别模式、发现目标、解决冲突。
  - 冷热分离：将低频、琐碎记忆标记为 `[ARCHIVE]`。

## 2. 半自动维护 (Semi-Auto Maintenance)
- **触发命令**：`/mem_report`。
- **分析内容**：
  - 过期低价值记忆 (Score < 3, > 30天)。
  - 重复记忆检测。
- **输出**：生成 Markdown 报告，由用户确认后手动清理。

## 3. 记忆强度更新
- 每次检索到记忆时，调用 `increase_memory_strength`。
- 增加 `useful_score`，影响后续检索权重。
