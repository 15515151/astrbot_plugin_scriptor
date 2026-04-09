@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo   Scriptor v2.0 依赖安装脚本
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo [步骤 1/4] 检测 Python 版本...
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo   Python: %PYVER%
echo.

echo [步骤 2/4] 升级 pip...
python -m pip install --upgrade pip -q
echo.

echo [步骤 3/4] 安装纯 Python 依赖（快速）...
pip install -r requirements-core.txt --no-cache-dir
if errorlevel 1 (
    echo [警告] 部分核心依赖安装失败，请检查网络
)
echo.

echo [步骤 4/4] 处理 C++ 扩展依赖...
echo.

REM 检测是否使用 Conda
where conda >nul 2>&1
if not errorlevel 1 (
    echo   ✓ 检测到 Conda 环境
    echo   正在使用 Conda 安装 chromadb（推荐方式）...
    conda install -c conda-forge chroma-hnswlib -y
    if errorlevel 1 (
        echo   [警告] Conda 安装失败，尝试备用方案...
        goto :try_pip_fallback
    ) else (
        echo   ✓ chroma-hnswlib 安装成功！
    )
) else (
    :try_pip_fallback
    echo   ✗ 未检测到 Conda
    echo   尝试直接通过 pip 安装 chromadb...
    echo.
    echo   ⚠️  如果出现 "Microsoft Visual C++ 14.0" 错误，
    echo      请选择以下方案之一：
    echo.
    echo   方案 A（推荐）：安装 Miniconda 后运行本脚本
    echo     下载地址: https://docs.conda.io/en/latest/miniconda.html
    echo.
    echo   方案 B：安装 Visual C++ Build Tools
    echo     下载地址: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo     安装时勾选 "C++ 桌面开发"
    echo.
    
    REM 尝试安装，可能会失败但给用户明确提示
    pip install chromadb --no-cache-dir
    if errorlevel 1 (
        echo.
        echo   ❌ chromadb 安装失败
        echo   请参考上方提示安装编译环境后重试
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo   ✅ 所有依赖安装完成！
echo ========================================
echo.
echo 可选操作：
echo   • 运行测试: python tests/test_v2_integration.py
echo   • 启动插件: 在 AstrBot 中加载 Scriptor
echo.
pause
