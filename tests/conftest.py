# tests/conftest.py
"""
pytest 配置文件
用于设置测试环境，解决模块导入问题
"""

import os
import sys
from pathlib import Path

import pytest

# 项目根目录
project_root = Path(__file__).parent.parent
core_dir = project_root / "core"
tools_dir = project_root / "tools"

# 在 pytest 启动时设置 sys.path（优先级最高）
# 确保项目根目录在最前面，这样可以直接导入 core.xxx
sys.path.insert(0, str(project_root))

# 同时也添加 core 和 tools 目录，支持直接导入模块
if str(core_dir) not in sys.path:
    sys.path.insert(1, str(core_dir))
if str(tools_dir) not in sys.path:
    sys.path.insert(2, str(tools_dir))

# 设置环境变量
os.environ.setdefault("SCRIPT_OR_TEST_MODE", "1")


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: 单元测试（快速执行）")
    config.addinivalue_line("markers", "integration: 集成测试（较慢）")
    config.addinivalue_line("markers", "slow: 慢速测试")


def pytest_collection_modifyitems(items):
    """在收集测试后处理每个测试文件"""

    # 需要确保 core 模块能够正确导入
    # 清理可能导致问题的缓存模块
    modules_to_remove = [
        key
        for key in sys.modules.keys()
        if key.startswith("core.") or key == "core" or key == "astrbot_plugin_scriptor"
    ]
    for mod in modules_to_remove:
        if mod in sys.modules:
            del sys.modules[mod]


@pytest.fixture(scope="session", autouse=True)
def setup_syspath():
    """确保 sys.path 在所有测试前正确设置"""
    return sys.path[:]
