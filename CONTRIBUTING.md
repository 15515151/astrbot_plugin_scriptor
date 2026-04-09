# 贡献指南 (Contributing)

欢迎为 Scriptor (灵笔司书) 做出贡献！本指南将帮助你了解如何参与项目。

---

## 📖 目录

1. [行为准则](#行为准则)
2. [我能贡献什么？](#我能贡献什么)
3. [开发环境设置](#开发环境设置)
4. [提交代码](#提交代码)
5. [代码规范](#代码规范)
6. [测试](#测试)
7. [文档](#文档)
8. [发布流程](#发布流程)

---

## 🎯 行为准则

本项目采用 [Contributor Covenant](https://www.contributor-covenant.org/) 行为准则。

**我们的承诺**：
- 营造开放、友善、包容的社区
- 尊重不同观点和经验
- 优雅地接受建设性批评
- 关注对社区最有利的事情
- 对其他社区成员表示同理心

**不可接受的行为**：
- 使用性化的语言或图像
- 人身攻击或侮辱性评论
- 公开或私下骚扰
- 未经许可发布他人信息
- 其他不道德或不专业的行为

---

## 💡 我能贡献什么？

### 1. 报告 Bug
如果你发现 Bug，请：
1. 检查是否已有相同的 [Issue](https://github.com/ysf7762-dev/astrbot_plugin_scriptor/issues)
2. 如果没有，创建一个新的 Issue
3. 提供详细信息：
   - 重现步骤
   - 预期行为
   - 实际行为
   - 环境信息（Python 版本、操作系统等）
   - 日志文件

### 2. 提出新功能
如果你想添加新功能：
1. 先创建 Issue 讨论
2. 说明新功能的用途和优势
3. 等待社区反馈
4. 获得认可后开始开发

### 3. 修复 Bug
如果你修复了 Bug：
1. 确保有对应的 Issue
2. 在 Issue 中说明你要修复
3. 提交 Pull Request

### 4. 改进文档
文档永远需要改进：
- 修正错别字和语法错误
- 补充缺失的说明
- 添加示例
- 改进翻译

### 5. 分享经验
- 写教程文章
- 制作视频教程
- 在社区回答问题
- 分享给更多人

---

## 🛠️ 开发环境设置

### 1. Fork 和克隆

```bash
# 1. 在 GitHub 上 Fork 项目
# 2. 克隆你的 Fork
git clone https://github.com/YOUR_USERNAME/astrbot_plugin_scriptor.git
cd astrbot_plugin_scriptor

# 3. 添加上游仓库
git remote add upstream https://github.com/ysf7762-dev/astrbot_plugin_scriptor.git
```

### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -r requirements.txt
pip install -e .

# 安装开发工具
pip install pytest pytest-asyncio flake8 black isort
```

### 3. 构建 Web UI（可选）

```bash
cd web
npm install
npm run dev  # 开发模式
# 或
npm run build  # 生产构建
```

### 4. 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_learning_manager.py -v

# 运行测试并生成覆盖率报告
pytest --cov=astrbot_plugin_scriptor tests/
```

---

## 📝 提交代码

### 1. 创建分支

```bash
# 从 main 分支创建新分支
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/issue-123
```

**分支命名规范**：
- `feature/xxx` - 新功能
- `fix/xxx` - Bug 修复
- `docs/xxx` - 文档更新
- `refactor/xxx` - 代码重构
- `test/xxx` - 测试相关
- `chore/xxx` - 构建/工具相关

### 2. 进行修改

- 保持代码简洁
- 添加必要的注释
- 更新相关文档
- 编写测试用例

### 3. 提交变更

```bash
# 添加修改的文件
git add .

# 提交（遵循提交信息规范）
git commit -m "type: description"

# 推送到远程
git push origin feature/your-feature-name
```

### 4. 提交信息规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Type 类型**：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

**示例**：
```
feat(memory): 添加记忆压缩功能

- 实现基于阈值的自动压缩
- 添加手动压缩命令
- 更新相关文档

Closes #123
```

### 5. 创建 Pull Request

1. 在 GitHub 上创建 PR
2. 填写 PR 描述：
   - 变更说明
   - 关联的 Issue
   - 测试方法
   - 截图（如有）
3. 等待 Code Review
4. 根据反馈修改
5. 合并到 main 分支

---

## 📏 代码规范

### Python 代码

遵循 [PEP 8](https://pep8.org/)：

```bash
# 代码格式化
black .
isort .

# 代码检查
flake8 .
```

**关键规则**：
- 使用 4 个空格缩进
- 最大行宽 127 字符
- 使用有意义的变量名
- 添加类型注解
- 编写文档字符串

**示例**：
```python
from typing import Optional, List

class MemoryManager:
    """记忆管理器，负责记忆的存储、检索和管理。"""
    
    def __init__(self, config: dict) -> None:
        """初始化记忆管理器。
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.memories: List[str] = []
    
    def add_memory(self, content: str) -> bool:
        """添加一条记忆。
        
        Args:
            content: 记忆内容
            
        Returns:
            是否添加成功
        """
        if not content.strip():
            return False
        
        self.memories.append(content)
        return True
```

### TypeScript/Vue 代码

```bash
# 安装 lint 工具
npm install --save-dev eslint @typescript-eslint/parser

# 运行 lint
npm run lint
```

**关键规则**：
- 使用 2 个空格缩进
- 使用有意义的变量名
- 添加类型注解
- 遵循 Vue 3 最佳实践

---

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_learning_manager.py -v

# 运行测试并生成覆盖率报告
pytest --cov=astrbot_plugin_scriptor tests/ --cov-report=html
```

### 编写测试

```python
import pytest
from astrbot_plugin_scriptor.core.memory_manager import MemoryManager

class TestMemoryManager:
    """测试记忆管理器。"""
    
    @pytest.fixture
    def manager(self):
        """创建测试用的记忆管理器。"""
        config = {"memory_compact_threshold": 8000}
        return MemoryManager(config)
    
    def test_add_memory(self, manager):
        """测试添加记忆功能。"""
        result = manager.add_memory("测试记忆")
        assert result is True
        assert len(manager.memories) == 1
    
    def test_add_empty_memory(self, manager):
        """测试添加空记忆。"""
        result = manager.add_memory("")
        assert result is False
        assert len(manager.memories) == 0
```

### 测试要求

- 新功能必须包含测试
- Bug 修复应包含回归测试
- 测试覆盖率应保持在合理水平
- 测试应该独立、可重复

---

## 📚 文档

### 文档结构

```
docs/
├── INDEX.md                          # 文档索引
├── Scriptor_User_Guide.md            # 用户指南
├── LEARNING_MODE_GUIDE.md            # 学习模式指南
├── Scriptor_API_Reference.md         # API 参考
├── Scriptor_Advanced_Features.md     # 高级功能
├── Scriptor_System_Design_Philosophy.md  # 设计理念
├── BUILD.md                          # 构建指南
└── ...
```

### 文档规范

- 使用清晰的标题
- 提供充分的示例
- 使用代码块标注语言
- 保持格式一致
- 使用 Emoji 增强可读性（适度）

### 更新文档

如果你修改了代码：
1. 更新相关文档
2. 更新 CHANGELOG.md
3. 如有必要，更新 README.md

---

## 🚀 发布流程

### 发布新版本

1. **更新版本号**
   - 修改 `pyproject.toml` 中的 `version`
   - 修改 `metadata.yaml` 中的 `version`
   - 更新 `CHANGELOG.md`

2. **运行测试**
   ```bash
   pytest tests/ -v
   ```

3. **构建**
   ```bash
   $env:ASTRBOT_BUILD_WEB="1"
   python -m build
   ```

4. **提交并打标签**
   ```bash
   git add .
   git commit -m "release: v1.0.0"
   git tag v1.0.0
   git push origin main --tags
   ```

5. **CI/CD 自动发布**
   - GitHub Actions 自动运行
   - 自动发布到 PyPI
   - 自动创建 GitHub Release

---

## 🎯 Code Review

### Reviewer 职责

- 检查代码质量
- 确保遵循规范
- 提出建设性意见
- 测试功能是否正常

### 被 Review 者职责

- 保持开放心态
- 解释设计决策
- 及时响应反馈
- 修改代码以符合建议

### Review 清单

- [ ] 代码是否清晰易读？
- [ ] 是否遵循代码规范？
- [ ] 是否有充分的测试？
- [ ] 文档是否更新？
- [ ] 是否有性能问题？
- [ ] 是否有安全隐患？
- [ ] 是否有重复代码？
- [ ] 是否有不必要的依赖？

---

## 🤝 社区

### 沟通渠道

- **GitHub Issues**: Bug 报告和功能请求
- **GitHub Discussions**: 讨论和问答
- **Email**: ysf7762-dev@example.com（示例）

### 获得帮助

- 查阅 [文档](docs/INDEX.md)
- 搜索 [Issues](https://github.com/ysf7762-dev/astrbot_plugin_scriptor/issues)
- 在 Discussions 中提问

---

## 📄 许可证

本项目采用 **AGPL-3.0 License**。

通过贡献代码，你同意你的贡献遵循此许可证。

---

## 🙏 致谢

感谢所有为 Scriptor 做出贡献的开发者！

你的每一份贡献都让这个项目变得更好！💖

---

*最后更新：2026-03-30*
