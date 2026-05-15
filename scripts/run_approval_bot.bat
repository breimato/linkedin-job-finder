@echo off
cd /d "C:\Users\Breixo\Desktop\Escritorio\Proyectos\Linkedin Search"

REM Evitar instancias duplicadas comprobando el título de ventana
tasklist /FI "WINDOWTITLE eq JobHunterBot" 2>nul | find "python.exe" >nul
if %ERRORLEVEL% == 0 (
    echo Bot ya en ejecucion >> logs\bot.log
    exit /b 0
)

title JobHunterBot
"C:\Users\Breixo\Desktop\Escritorio\Proyectos\Linkedin Search\.venv\Scripts\python.exe" -m src.approval_bot.bot >> logs\bot.log 2>&1
