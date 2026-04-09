# 开发者快速入门指南

欢迎加入 Scriptor 开发者社区！本指南将帮助你快速上手开发。

---

## 🚀 5 分钟快速开始

### 1. Fork 和克隆（2 分钟）

```bash
# 在 GitHub 上 Fork 项目，然后：
git clone https://github.com/YOUR_USERNAME/astrbot_plugin_scriptor.git
cd astrbot_plugin_scriptor
```

### 2. 安装依赖（2 分钟）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install -e .
```

### 3. 运行测试（1 分钟）

```bash
# 运行测试确保环境正常
cd tests
python run_tests.py
```

**恭喜！你现在可以开始开发了！** 🎉

---

## 📁 项目结构详解

```
astrbot_plugin_scriptor/
├── 📄 main.py                          # 主插件入口
├── 📄 pyproject.toml                   # Python 包配置
├── 📄 metadata.yaml                    # AstrBot 插件元数据
├── 📄 requirements.txt                 # Python 依赖
│
├── 📂 core/                            # 核心模块
│   ├── memory_manager.py               # 记忆管理器
│   ├── search_engine.py                # 搜索引擎
│   ├── identity_manager.py             # 身份管理器
│   ├── group_manager.py                # 群体管理器
│   ├── prompt_builder.py               # 提示词构建器
│   ├── knowledge_graph.py              # 知识图谱
│   └── config_pydantic.py              # 配置类
│
├── 📂 mixins/                          # Mixin 模块
│   ├── memory_ops.py                   # 记忆操作
│   ├── learning_mode.py                # 学习模式
│   ├── compact.py                      # 记忆压缩
│   └── ...
│
├── 📂 hooks/                           # Hook 系统
│   ├── event_hook.py                   # 事件钩子
│   └── prompt_hook.py                  # 提示词钩子
│
├── 📂 tools/                           # 工具类
│   ├── file_utils.py                   # 文件工具
│   ├── token_utils.py                  # Token 工具
│   └── ...
│
├── 📂 web/                             # Web UI
│   ├── src/                            # Vue 源码
│   ├── api.py                          # FastAPI 后端
│   └── package.json                    # Node 依赖
│
├── 📂 tests/                           # 测试
│   ├── test_learning_manager.py        # 学习模式测试
│   ├── test_file_import_simple.py      # 文件导入测试
│   └── ...
│
├── 📂 scripts/                         # 构建脚本
│   └── build_hook.py                   # 构建钩子
│
└── 📂 docs/                            # 文档
    ├── INDEX.md                        # 文档索引
    ├── Scriptor_User_Guide.md          # 用户指南
    └── ...
```

---

## 💻 开发工作流

### 1. 创建功能分支

```bash
# 确保基于最新的 main 分支
git checkout main
git pull upstream main

# 创建新分支
git checkout -b feature/your-feature
```

### 2. 开发和测试

```bash
# 修改代码...

# 运行相关测试
pytest tests/test_your_feature.py -v

# 代码格式化
black .
isort .

# 代码检查
flake8 .
```

### 3. 提交代码

```bash
# 添加修改
git add .

# 提交（遵循 Conventional Commits）
git commit -m "feat(core): 添加新功能"

# 推送
git push origin feature/your-feature
```

### 4. 创建 Pull Request

在 GitHub 上：
1. 点击 "New Pull Request"
2. 选择你的分支
3. 填写 PR 描述
4. 等待 Review

---

## 🔧 常用开发任务

### 添加新命令

```python
# 在 main.py 中添加
@self.bot.register_command("/your_command", "YOUR_COMMAND")
async def your_command(self, event: EventMessage) -> None:
    """你的命令处理函数"""
    # 你的代码
    pass
```

### 添加新的记忆操作

```python
# 在 mixins/memory_ops.py 中添加
class MemoryOps:
    async def your_operation(self, memory_id: str) -> bool:
        """你的记忆操作"""
        # 你的代码
        pass
```

### 添加新的 Hook

```python
# 在 hooks/event_hook.py 中添加
class EventHook:
    async def on_your_event(self, event: dict) -> None:
        """你的事件处理"""
        # 你的代码
        pass
```

### 添加 Web UI 页面

```vue
<!-- 在 web/src/views/ 中添加 YourPage.vue -->
<template>
  <v-container>
    <h1>你的页面</h1>
    <!-- 你的代码 -->
  </v-container>
</template>

<script lang="ts">
export default {
  name: 'YourPage',
  // 你的代码
}
</script>
```

---

## 🧪 测试指南

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_learning_manager.py -v

# 运行测试并生成覆盖率
pytest --cov=astrbot_plugin_scriptor tests/ --cov-report=html

# 查看覆盖率报告
# 打开 htmlcov/index.html
```

### 编写测试

```python
import pytest
from astrbot_plugin_scriptor.core.memory_manager import MemoryManager

class TestYourFeature:
    """测试你的功能"""
    
    @pytest.fixture
    def setup(self):
        """测试准备"""
        config = {"test_mode": True}
        manager = MemoryManager(config)
        yield manager
        # 清理代码
    
    def test_your_feature(self, setup):
        """测试你的功能"""
        result = setup.your_method()
        assert result is True
```

---

## 📚 调试技巧

### 启用调试模式

```yaml
# 配置文件中
scriptor:
  debug_mode: true
  log_level: DEBUG
```

### 查看日志

```bash
# 实时查看日志
tail -f data/logs/astrbot.log

# 筛选 Scriptor 日志
grep "Scriptor" data/logs/astrbot.log

# 查看错误日志
grep "ERROR" data/logs/astrbot.log
```

### 使用调试命令

```
/debug_memory        # 查看记忆调试信息
/memory_stats        # 查看统计信息
/verify_memory       # 验证记忆系统
```

---

## 🎯 代码规范

### Python 代码规范

```python
# ✅ 好的代码
from typing import Optional, List

class MemoryManager:
    """记忆管理器。"""
    
    def __init__(self, config: dict) -> None:
        self.config = config
        self.memories: List[str] = []
    
    def add_memory(self, content: str) -> bool:
        """添加记忆。
        
        Args:
            content: 记忆内容
            
        Returns:
            是否成功
        """
        if not content.strip():
            return False
        self.memories.append(content)
        return True

# ❌ 不好的代码
class MemoryManager:
    def __init__(self, config):
        self.config = config
        self.memories = []
    
    def add_memory(self, content):
        if content == "":
            return False
        self.memories.append(content)
        return True
```

### 提交信息规范

```bash
# ✅ 好的提交信息
git commit -m "feat(memory): 添加记忆压缩功能"
git commit -m "fix(search): 修复 BM25 检索 bug"
git commit -m "docs(readme): 更新安装说明"

# ❌ 不好的提交信息
git commit -m "update"
git commit -m "fix bug"
git commit -m "asdfasdf"
```

---

## 🛠️ 开发工具推荐

### 编辑器/IDE

- **VS Code** + Python 扩展
- **PyCharm** Professional
- **Vim** + coc.nvim

### 必备扩展

- Python (IntelliSense)
- Pylance (类型检查)
- Black Formatter (格式化)
- isort (导入排序)
- GitLens (Git 增强)

### 命令行工具

```bash
# 安装开发工具
pip install black isort flake8 pytest pytest-cov mypy

# 配置 pre-commit hooks
pip install pre-commit
pre-commit install
```

---

## 📖 学习资源

### 内部文档

- [API 参考](docs/Scriptor_API_Reference.md)
- [高级功能](docs/Scriptor_Advanced_Features.md)
- [系统设计哲学](docs/Scriptor_System_Design_Philosophy.md)

### 外部资源

- [AstrBot 插件开发文档](https://astrbot.app/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Vue 3 文档](https://vuejs.org/)
- [Python 最佳实践](https://docs.python-guide.org/)

---

## 🤝 获取帮助

### 遇到问题？

1. **查看文档**
   - [用户指南](docs/Scriptor_User_Guide.md)
   - [API 参考](docs/Scriptor_API_Reference.md)
   - [常见问题](docs/INDEX.md#常见问题)

2. **搜索 Issues**
   - [GitHub Issues](https://github.com/ysf7762-dev/astrbot_plugin_scriptor/issues)

3. **提问**
   - 在 GitHub 创建 Issue
   - 在 Discussions 中提问

---

## 🎉 开始贡献

现在你已经准备好了！

1. 找到一个感兴趣的 Issue
2. Fork 项目
3. 创建分支
4. 开发功能
5. 编写测试
6. 提交 PR

**期待你的贡献！** 🚀

---

## 📝 检查清单

开发新功能时的检查清单：

- [ ] 代码已编写
- [ ] 测试已通过
- [ ] 文档已更新
- [ ] 代码已格式化
- [ ] 类型注解已添加
- [ ] 提交信息规范
- [ ] CHANGELOG 已更新

---

*最后更新：2026-03-30*  
*版本：1.0.0*
