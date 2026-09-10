@echo off
REM ============================================================
REM  RustDesk unattended access setup  (double-click to run)
REM  Requires administrator rights - it elevates itself via UAC.
REM  All messages are shown in Korean by the PowerShell script.
REM ============================================================
title RustDesk - unattended access setup

REM --- admin check -------------------------------------------
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   Administrator rights are required.
    echo   Please click [Yes] on the UAC prompt.
    echo.
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0rustdesk\Setup-RustDeskUnattended.ps1"

echo.
echo   Press any key to close this window.
pause >nul
