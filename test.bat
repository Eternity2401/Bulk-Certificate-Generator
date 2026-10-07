@echo off
title Run Bulk Certificate Generator Tests
echo ========================================================
echo Running Automated Test Suite...
echo ========================================================
cd /d "%~dp0"
python -m pytest
pause
