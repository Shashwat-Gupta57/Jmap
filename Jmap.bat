@echo off
setlocal
:: ============================================================
:: Jmap.bat  -  Java Project Context Mapper
::
:: Usage:
::   Jmap.bat <project_folder> [flags]
::
:: Flags:
::   --no-tree   Omit the file-tree section
::   --print     Also print the report to this console window
::   --help -h   Show full help and exit
::
:: Examples:
::   Jmap.bat "My Project"
::   Jmap.bat "My Project" --no-tree
::   Jmap.bat "My Project" --print
::   Jmap.bat "My Project" --no-tree --print
::   Jmap.bat --help
::
:: Output:
::   context.txt  placed inside the project folder
:: ============================================================

if "%~1"=="" (
    python "%~dp0Jmap.py" --help
    exit /b 0
)

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Download it from https://python.org
    exit /b 1
)

if not exist "%~dp0Jmap.py" (
    echo [ERROR] Cannot find Jmap.py
    echo Make sure Jmap.py is in the same folder as this .bat file.
    exit /b 1
)

python "%~dp0Jmap.py" %*
endlocal