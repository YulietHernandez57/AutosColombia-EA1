@echo off
cd /d "%~dp0"
py app.py
if errorlevel 1 goto fallo
echo Abre http://127.0.0.1:8000 en tu navegador.
py web.py
:fallo
pause
