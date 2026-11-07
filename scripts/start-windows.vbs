' Starts the server in a hidden window (Windows; Hermes runs in WSL).
' Auto-start: put a shortcut to this file in shell:startup.
dir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName))
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = dir
sh.Run """" & dir & "\.venv\Scripts\python.exe"" """ & dir & "\server\main.py""", 0, False
