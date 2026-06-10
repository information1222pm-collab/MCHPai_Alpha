@echo off
:: ===================================================================
::  MCHP Boxing Services - ISBoxer Multibox Command Center
::  One-click installer launcher (double-click this file)
:: ===================================================================
title MCHP Boxing - Installer
cd /d "%~dp0"

echo.
echo   Starting the MCHP Boxing installer...
echo.

:: Run the PowerShell installer with execution policy bypassed for this run only.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-MCHP-Boxing.ps1"

if %ERRORLEVEL% NEQ 0 (
  echo.
  echo   The installer reported a problem. See the messages above.
)

echo.
echo   You can close this window.
pause >nul
