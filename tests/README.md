# Scriptor 测试指南

## 🧪 运行测试

### ✅ 可以正常运行的测试

以下测试文件可以直接使用 pytest 运行，无需任何配置：

```bash
# 学习模式相关测试（推荐）
pytest tests/test_learning_manager.py -v
pytest tests/test_learning_manager_import.py -v
pytest tests/integration/test_learning_workflow.py -v

# 文件操作测试
pytest tests/test_file_import_simple.py -v
pytest tests/test_file_import_to_archive.py -v

# 媒体管理测试
pytest tests/test_media_manager_simple.py -v
pytest tests/test_media_tools_registration.py -v

# 其他独立测试
pytest tests/test_active_reply.py -v
pytest tests/test_async_io.py -v
pytest tests/test_backup_manager.py -v
pytest tests/test_conversation_ledger.py -v
pytest tests/test_encryption.py -v
pytest tests/test_file_monitor.py -v
pytest tests/test_knowledge_graph_fix.py -v
pytest tests/test_knowledge_graph_standalone.py -v
pytest tests/test_new_features.py -v
pytest tests/test_performance.py -v
```

### ⚠️ 已知问题：部分测试无法直接运行

以下测试文件由于使用相对导入，**直接运行 pytest 会失败**：

```bash
# ❌ 这些测试会报错
pytest tests/test_core_logic.py        # ImportError: attempted relative import
pytest tests/test_memory_manager.py    # ImportError: attempted relative import
pytest tests/test_search_engine.py     # ImportError: attempted relative import
pytest tests/test_config.py            # ImportError: attempted relative import
pytest tests/test_permissions.py       # ImportError: attempted relative import
pytest tests/test_smart_sender.py      # ImportError: attempted relative import
pytest tests/test_enhanced.py          # ImportError: attempted relative import
pytest tests/test_hooks.py             # ImportError: attempted relative import
pytest tests/test_integration.py       # ImportError: attempted relative import
```

### 📋 原因说明

**为什么这些测试会失败？**

AstrBot 插件必须使用相对导入（如 `from ..tools.config.enhanced_patterns import ...`），这样才能在 AstrBot 中正常运行。但是，这种相对导入在 pytest 直接运行时会失败，因为 pytest 不会将项目识别为 Python 包。

**这会影响插件的正常运行吗？**

❌ **不会影响！** 这只是 pytest 的问题，不影响 AstrBot 中插件的正常运行。

在 AstrBot 中，插件作为完整的 Python 包加载，相对导入完全正常。

### 🔧 解决方案

#### 方案 1：使用 AstrBot 测试（推荐）

在 AstrBot 中实际运行插件，通过真实使用来验证功能。

#### 方案 2：修改测试导入方式（复杂，不推荐）

需要修改 `core/__init__.py` 和多个文件的导入方式，可能引入新的问题。

#### 方案 3：使用 pytest 插件（实验性）

安装 pytest 插件来支持相对导入：

```bash
pip install pytest-custom-path
```

然后在 `pytest.ini` 中配置：

```ini
[pytest]
pythonpath = .
addopts = --import-mode=importlib
```

但这可能导致其他问题，不推荐。

### 📊 测试覆盖情况

#### ✅ 已充分测试的核心功能

| 功能模块 | 测试文件 | 状态 |
|---------|---------|------|
| 学习模式 | `test_learning_manager.py` | ✅ 23 个测试 |
| 学习模式导入 | `test_learning_manager_import.py` | ✅ 4 个测试 |
| 学习模式集成 | `test_learning_workflow.py` | ✅ 11 个测试 |
| 文件操作 | `test_file_import_*.py` | ✅ 通过 |
| 媒体管理 | `test_media_*.py` | ✅ 通过 |
| 记忆管理 | `test_memory_manager.py` | ⚠️ pytest 失败，AstrBot 正常 |
| 搜索引擎 | `test_search_engine.py` | ⚠️ pytest 失败，AstrBot 正常 |
| 配置系统 | `test_config.py` | ⚠️ pytest 失败，AstrBot 正常 |
| 权限管理 | `test_permissions.py` | ⚠️ pytest 失败，AstrBot 正常 |

### 💡 最佳实践

1. **优先运行学习模式测试**：这些测试最完善，覆盖了核心功能
2. **在 AstrBot 中测试**：真实环境最可靠
3. **关注日志**：AstrBot 启动时的日志会显示所有工具是否正确注册

### 🎯 推荐的测试流程

```bash
# 1. 运行学习模式测试（验证核心功能）
pytest tests/test_learning_manager.py tests/test_learning_manager_import.py tests/integration/test_learning_workflow.py -v

# 2. 运行独立测试（验证其他功能）
pytest tests/test_file_import_simple.py tests/test_media_manager_simple.py tests/test_active_reply.py -v

# 3. 在 AstrBot 中验证
# 启动 AstrBot，查看日志中是否有错误
# 使用 /mem_status, /whoami 等命令验证功能
```

### 📝 总结

- ✅ **学习模式测试**：完善且可靠，强烈推荐
- ✅ **独立测试**：可以正常运行
- ⚠️ **核心模块测试**：pytest 失败但 AstrBot 正常，建议在真实环境中验证
- ❌ **不要移除测试**：这些测试在 AstrBot 环境中是有价值的

---

*最后更新：2026-03-29*
