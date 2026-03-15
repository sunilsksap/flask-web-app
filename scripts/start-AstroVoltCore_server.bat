@echo off
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"
start "" http://192.168.140.153:8765
python "%PROJECT_ROOT%\backend\AstroVoltCore_server.py"
pause
