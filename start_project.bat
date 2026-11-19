@echo off
:: Delegate to deploy/start_project.bat
cd /d "%~dp0"
call deploy\start_project.bat
