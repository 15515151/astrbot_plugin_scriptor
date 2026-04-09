#!/bin/bash
# ========================================
#   Scriptor v2.0 依赖安装脚本 (Linux/Mac)
# ========================================

set -e

echo "========================================"
echo "  Scriptor v2.0 依赖安装脚本"
echo "========================================"
echo

if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3，请先安装 Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "[步骤 1/4] 检测到 Python: $PYTHON_VERSION"

echo
echo "[步骤 2/4] 升级 pip..."
python3 -m pip install --upgrade pip -q

echo
echo "[步骤 3/4] 安装纯 Python 依赖..."
pip3 install -r requirements-core.txt --no-cache-dir

echo
echo "[步骤 4/4] 处理 C++ 扩展依赖..."
echo

# 检测 Conda
if command -v conda &> /dev/null; then
    echo "✓ 检测到 Conda 环境"
    echo "正在使用 Conda 安装 chroma-hnswlib（推荐方式）..."
    conda install -c conda-forge chroma-hnswlib -y
    echo "✓ chroma-hnswlib 安装成功！"
else
    echo "✗ 未检测到 Conda，尝试直接通过 pip 安装..."
    echo
    
    # 检测操作系统
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macOS 系统：通常可以直接编译 C++ 扩展"
        echo "如果失败，请安装 Xcode Command Line Tools:"
        echo "  xcode-select --install"
        echo
    elif [[ "$OSTYPE" == "linux"* ]]; then
        echo "Linux 系统：需要 build-essential"
        echo "Ubuntu/Debian: sudo apt-get install build-essential"
        echo "CentOS/RHEL: sudo yum groupinstall 'Development Tools'"
        echo
    fi
    
    pip3 install chromadb --no-cache-dir || {
        echo
        echo "❌ chromadb 安装失败"
        echo
        echo "建议方案："
        echo "1. 安装 Miniconda: https://docs.conda.io/en/latest/miniconda.html"
        echo "2. 运行本脚本（会自动使用 Conda）"
        exit 1
    }
fi

echo
echo "========================================"
echo "  ✅ 所有依赖安装完成！"
echo "========================================"
echo
echo "可选操作："
echo "  • 运行测试: python3 tests/test_v2_integration.py"
echo "  • 启动插件: 在 AstrBot 中加载 Scriptor"
echo
