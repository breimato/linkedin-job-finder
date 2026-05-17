Dim shell
Set shell = CreateObject("WScript.Shell")
shell.Run "cmd /c cd /d ""C:\Users\Breixo\Desktop\Escritorio\Proyectos\Linkedin Search"" && "".venv\Scripts\pythonw.exe"" main.py >> logs\scheduler.log 2>&1", 0, True
Set shell = Nothing
