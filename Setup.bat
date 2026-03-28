@echo off
setlocal enabledelayedexpansion

:: ============================================================
:: Setup.bat  -  JMAP Installer
:: Installs Jmap to %ProgramFiles%\Jmap and adds it to PATH
:: Must be run as Administrator
:: ============================================================

echo.
echo ================================================================
echo   JMAP - Java Project Context Mapper
echo   Installer
echo ================================================================
echo.

:: ── Check for Administrator privileges ───────────────────────────
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] This installer must be run as Administrator.
    echo.
    echo Right-click Setup.bat and choose "Run as administrator".
    echo.
    pause
    exit /b 1
)

:: ── Check Python is available ─────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please install Python from https://python.org
    echo Make sure to tick "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo   Python found : %PY_VER%

:: ── Locate source files ───────────────────────────────────────────
set "SRC_DIR=%~dp0"
:: Strip trailing backslash
if "%SRC_DIR:~-1%"=="\" set "SRC_DIR=%SRC_DIR:~0,-1%"

if not exist "%SRC_DIR%\Jmap.py" (
    echo [ERROR] Cannot find Jmap.py in: %SRC_DIR%
    echo Make sure Setup.bat is in the same folder as Jmap.py and Jmap.bat.
    pause
    exit /b 1
)
if not exist "%SRC_DIR%\Jmap.bat" (
    echo [ERROR] Cannot find Jmap.bat in: %SRC_DIR%
    pause
    exit /b 1
)

:: ── Set install destination ───────────────────────────────────────
set "INSTALL_DIR=%ProgramFiles%\Jmap"
echo   Install dir  : %INSTALL_DIR%
echo.

:: ── Ask user to confirm ───────────────────────────────────────────
set /p CONFIRM="   Proceed with installation? [Y/N]: "
if /i not "%CONFIRM%"=="Y" (
    echo Installation cancelled.
    pause
    exit /b 0
)
echo.

:: ── Create install directory ──────────────────────────────────────
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create directory: %INSTALL_DIR%
        pause
        exit /b 1
    )
)

:: ── Copy files ────────────────────────────────────────────────────
echo   Copying files...
copy /Y "%SRC_DIR%\Jmap.py"  "%INSTALL_DIR%\Jmap.py"  >nul
copy /Y "%SRC_DIR%\Jmap.bat" "%INSTALL_DIR%\Jmap.bat" >nul
if errorlevel 1 (
    echo [ERROR] File copy failed.
    pause
    exit /b 1
)
echo   Files copied successfully.

:: ── Add to System PATH (permanent, via registry) ─────────────────
echo   Updating System PATH...

:: Read current system PATH from registry
for /f "tokens=2,*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do (
    set "CURRENT_PATH=%%B"
)

:: Check if already in PATH
echo !CURRENT_PATH! | find /i "%INSTALL_DIR%" >nul
if not errorlevel 1 (
    echo   PATH already contains Jmap — skipping PATH update.
) else (
    :: Append to system PATH via registry
    setx /M PATH "!CURRENT_PATH!;%INSTALL_DIR%" >nul
    if errorlevel 1 (
        echo [WARN] Could not update system PATH automatically.
        echo        Please add the following folder to your PATH manually:
        echo        %INSTALL_DIR%
    ) else (
        echo   PATH updated successfully.
    )
)

:: ── Done ──────────────────────────────────────────────────────────
echo.
echo ================================================================
echo   Installation complete!
echo.
echo   Open a NEW command prompt and run:
echo     Jmap "C:\path\to\your\java\project"
echo.
echo   For help:
echo     Jmap --help
echo ================================================================
echo.
pause
endlocal