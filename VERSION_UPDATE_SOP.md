# 版本号更新 SOP（标准操作流程）

> **适用范围**：AstrBot 插件版本发布
> **最后更新**：2026-04-29

---

## 一、更新版本号文件

### 1.1 必须修改的文件

| 文件 | 字段 | 示例 |
|------|------|------|
| `metadata.yaml` | `version` | `version: "1.0.2"` |
| `pyproject.toml` | `version` | `version = "1.0.2"` |
| `main.py` | `__version__` | `__version__ = "1.0.2"` |
| `CHANGELOG.md` | 新增版本章节 | `## [1.0.2] - 2026-04-29` |

### 1.2 注意事项
- **三个文件的版本号必须一致**
- 版本号格式：`主版本.次版本.修订号`（Semantic Versioning）
- `metadata.yaml` 是 AstrBot 插件市场读取的主要来源

---

## 二、编写 CHANGELOG.md 更新日志

### 2.1 文件格式

```markdown
## [版本号] - YYYY-MM-DD

### Added（新增功能）
- 功能描述

### Changed（变更/优化）
- 优化内容

### Fixed（修复问题）
- 修复内容

### Removed（移除内容）
- 移除内容
```

### 2.2 编写建议
- 按功能模块分类，而不是按提交记录
- 用用户视角描述变更，而非技术细节
- 重要变更标注 `**BREAKING**`
- 参考 `git log v上一个版本..HEAD` 获取变更记录

---

## 三、提交代码

```bash
git add .
git commit -m "chore: 更新版本号为 X.X.X"
git push origin main
```

---

## 四、创建并推送 Git Tag

### 4.1 创建 Tag

```bash
git tag -a vX.X.X -m "Release version X.X.X"
```

### 4.2 推送 Tag

```bash
git push origin vX.X.X
```

### 4.3 ⚠️ 踩坑记录

#### 坑 1：Tag 创建后插件市场不更新
**原因**：先创建了 Tag，后修改了 `metadata.yaml`，导致 Tag 指向的提交中版本号未更新。

**解决**：
1. 先修改所有版本号文件
2. 提交代码
3. **再**创建 Tag

#### 坑 2：需要重新创建 Tag
如果 Tag 已经推送到远程但有问题：

```bash
# 删除本地 Tag
git tag -d vX.X.X

# 删除远程 Tag
git push origin --delete vX.X.X

# 重新创建并推送
git tag -a vX.X.X -m "Release version X.X.X"
git push origin vX.X.X
```

#### 坑 3：Tag 名称格式
- **必须**以 `v` 开头：`v1.0.2`（不是 `1.0.2`）
- AstrBot 插件市场可能依赖此前缀

---

## 五、验证

### 5.1 本地验证

```bash
# 检查版本号
cat metadata.yaml | grep version
cat pyproject.toml | grep version

# 检查 Tag
git tag -l

# 检查远程同步
git status
```

### 5.2 插件市场验证
- 访问 AstrBot 插件商店
- 搜索插件名称
- 确认版本号显示正确
- **注意**：插件市场可能有缓存，更新后需要等待一段时间（通常几分钟到几小时）

---

## 六、完整流程示例

```bash
# 1. 修改版本号文件
# - metadata.yaml: version: "1.0.3"
# - pyproject.toml: version = "1.0.3"
# - main.py: __version__ = "1.0.3"
# - CHANGELOG.md: 添加新版本章节

# 2. 提交代码
git add .
git commit -m "chore: 更新版本号为 1.0.3"

# 3. 推送到远程
git push origin main

# 4. 创建 Tag
git tag -a v1.0.3 -m "Release version 1.0.3"

# 5. 推送 Tag
git push origin v1.0.3

# 6. 验证
git tag -l
git status
```

---

## 七、常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 插件市场版本号不更新 | metadata.yaml 未更新 | 检查 metadata.yaml 的 version 字段 |
| 插件市场版本号不更新 | Tag 未推送 | `git push origin vX.X.X` |
| 插件市场版本号不更新 | Tag 指向错误的提交 | 删除并重新创建 Tag |
| 依赖冲突 | 版本上限限制 | 移除上限，与 AstrBot 核心保持一致 |
| 指令冲突 | 多处注册命令 | 中心化命令注册，移除 mixin 中的装饰器 |

---

## 八、版本发布检查清单

- [ ] `metadata.yaml` 版本号已更新
- [ ] `pyproject.toml` 版本号已更新
- [ ] `main.py` 版本号已更新
- [ ] `CHANGELOG.md` 已添加新版本章节
- [ ] 代码已提交并推送到远程
- [ ] Git Tag 已创建（格式：`vX.X.X`）
- [ ] Git Tag 已推送到远程
- [ ] 插件市场版本号显示正确
- [ ] 依赖版本与 AstrBot 核心兼容
- [ ] 无指令冲突

---

*本文档由实际版本更新经验总结，持续更新中*
