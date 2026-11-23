@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Publish portfolio
set GH_CONFIG_DIR=E:\tools\gh-config
git add -A
git diff --cached --quiet && (echo ไม่มีอะไรเปลี่ยนแปลง & pause & exit /b)
git commit -m "Update portfolio content"
git push
echo.
echo เผยแพร่แล้ว! เว็บจะอัปเดตภายใน 1-2 นาที: https://tncnon.github.io/
pause
