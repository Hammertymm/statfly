' Launch Fly Intelligence Platform (skip if already running on port 8787).
Set sh = CreateObject("Wscript.Shell")
engineDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = engineDir
sh.Run "cmd /c python ensure_running.py", 0, False
