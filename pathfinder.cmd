@echo off
setlocal
pushd "%~dp0" >nul

if "%~1"=="" (
    call "%~dp0dev.cmd" --login
) else (
    call "%~dp0dev.cmd" %*
)

set "EXIT_CODE=%ERRORLEVEL%"
popd >nul
exit /b %EXIT_CODE%
