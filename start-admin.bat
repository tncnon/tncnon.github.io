@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Portfolio Admin
python server.py --open
pause
