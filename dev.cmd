@echo off
setlocal
pushd "%~dp0" >nul

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    call :create_venv
    if errorlevel 1 goto :cleanup
)

".venv\Scripts\python.exe" -c "import rich, textual" >nul 2>nul
if errorlevel 1 (
    echo Installing package and dependencies...
    ".venv\Scripts\python.exe" -m pip install -e .
    if errorlevel 1 goto :cleanup
)

if "%~1"=="" (
    ".venv\Scripts\python.exe" -m pathfinder_cli --login
) else (
    ".venv\Scripts\python.exe" -m pathfinder_cli %*
)

:cleanup
set "EXIT_CODE=%ERRORLEVEL%"
popd >nul
exit /b %EXIT_CODE%

:create_venv
where py >nul 2>nul
if not errorlevel 1 (
    py -3.11 -m venv .venv
    exit /b %ERRORLEVEL%
)

python -m venv .venv
exit /b %ERRORLEVEL%
