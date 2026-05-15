Dim shell
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "C:\Users\Breixo\Desktop\Escritorio\Proyectos\Linkedin Search"
shell.Run """C:\Users\Breixo\Desktop\Escritorio\Proyectos\Linkedin Search\.venv\Scripts\pythonw.exe"" main.py", 0, False
Set shell = Nothing
