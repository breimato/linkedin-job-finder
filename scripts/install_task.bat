@echo off
echo Registrando tareas en el Programador de tareas de Windows...

schtasks /Create /TN "JobHunter\Monitor" /TR "\"C:\Users\Breixo\Desktop\Escritorio\Proyectos\Linkedin Search\scripts\run_monitor.bat\"" /SC MINUTE /MO 20 /RL HIGHEST /F

schtasks /Create /TN "JobHunter\ApprovalBot" /TR "\"C:\Users\Breixo\Desktop\Escritorio\Proyectos\Linkedin Search\scripts\run_approval_bot.bat\"" /SC ONLOGON /RL HIGHEST /F

echo.
echo Tareas registradas. Verificando...
schtasks /Query /TN "JobHunter\Monitor" /FO LIST
pause
