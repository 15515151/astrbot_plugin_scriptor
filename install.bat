@echo off
REM Scriptor v2.0 Dependency Installation Script
REM Compatible with Windows CMD (GBK/UTF-8)

echo ========================================
echo   Scriptor v2.0 - Install Dependencies
echo ========================================
echo.

REM Step 1: Detect Python (prefer venv)
echo [Step 1/4] Detecting Python environment...

REM Check for AstrBot venv first
set "PYTHON_CMD=python"
set "PIP_CMD=pip"

if exist "%~dp0..\..\..\.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0..\..\..\.venv\Scripts\python.exe"
    set "PIP_CMD=%~dp0..\..\..\.venv\Scripts\pip.exe"
    echo   Found AstrBot venv: %PYTHON_CMD%
) else if exist "%~dp0..\..\..\.venv\Scripts\pip.exe" (
    set "PIP_CMD=%~dp0..\..\..\.venv\Scripts\pip.exe"
    echo   Found AstrBot venv pip: %PIP_CMD%
) else (
    echo   Using system Python
)

%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('%PYTHON_CMD% --version 2^>^&1') do set PYVER=%%v
echo   Python: %PYVER%
echo.

REM Step 2: Upgrade pip
echo [Step 2/4] Upgrading pip...
%PYTHON_CMD% -m pip install --upgrade pip -q
echo.

REM Step 3: Install core dependencies
echo [Step 3/4] Installing core dependencies...
%PIP_CMD% install -r requirements-core.txt --no-cache-dir
if errorlevel 1 (
    echo   [WARNING] Some core dependencies failed to install. Check your network.
)
echo.

REM Step 4: Handle C++ extension dependencies
echo [Step 4/4] Installing C++ extension dependencies...
echo.

REM Check for Conda
where conda >nul 2>&1
if not errorlevel 1 (
    echo   Conda environment detected.
    echo   Installing chromadb via Conda (recommended)...
    conda install -c conda-forge chroma-hnswlib -y
    if errorlevel 1 (
        echo   [WARNING] Conda install failed, trying pip fallback...
        goto :try_pip_fallback
    ) else (
        echo   chroma-hnswlib installed successfully!
    )
) else (
    :try_pip_fallback
    echo   Conda not detected.
    echo   Trying pip install for chromadb...
    echo.
    echo   NOTE: If you see "Microsoft Visual C++ 14.0" error,
    echo   please choose one of the following solutions:
    echo.
    echo   Option A (recommended): Install Miniconda and re-run this script
    echo     Download: https://docs.conda.io/en/latest/miniconda.html
    echo.
    echo   Option B: Install Visual C++ Build Tools
    echo     Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo     Select "Desktop development with C++"
    echo.
    
    %PIP_CMD% install chromadb --no-cache-dir
    if errorlevel 1 (
        echo.
        echo   [ERROR] chromadb installation failed.
        echo   Please install build tools as described above and try again.
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo   All dependencies installed!
echo ========================================
echo.
echo Optional:
echo   Run tests: python tests/test_v2_integration.py
echo   Start plugin: Load Scriptor in AstrBot
echo.
pause
