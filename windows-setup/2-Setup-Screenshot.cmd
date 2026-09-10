@echo off
REM ============================================================
REM  Ctrl+PrintScreen screenshot setup  (double-click to run)
REM  Deliberately does NOT elevate: the Screenshots folder must
REM  be relocated for the normal user account, not for an admin.
REM  All messages are shown in Korean by the PowerShell script.
REM ============================================================
title Ctrl+PrintScreen - screenshot setup

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0screenshot\Setup-ScreenshotHotkey.ps1"

echo.
echo   Press any key to close this window.
pause >nul
