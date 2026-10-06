@echo off
title Critical Heart Patient Cyber Security System
echo =========================================================================
echo    CRITICAL HEART PATIENT CYBER SECURITY SYSTEM
echo    Starting Flask Cyber-Defense Server...
echo =========================================================================

REM Use workspace Python wrapper or default python
if exist "%~dp0python.bat" (
    call "%~dp0python.bat" "%~dp0app.py"
) else (
    python "%~dp0app.py"
)

pause
