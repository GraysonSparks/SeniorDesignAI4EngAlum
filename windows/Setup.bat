@echo off
rem One-time install. Double-click, or run "Setup.bat -SkipEval" to skip the 56-case eval.
title AI4EngAlum setup
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
pause
