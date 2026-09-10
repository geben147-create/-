@echo off
REM ============================================================
REM  Read-only diagnostics. Changes nothing.
REM  Run this and paste the output back if something is wrong.
REM ============================================================
title Setup status check

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Check-Status.ps1"

echo.
echo   Press any key to close this window.
pause >nul
