# Fly Intelligence Platform — remove local autostart (already run for Oracle migration)
# Run again if needed: powershell -ExecutionPolicy Bypass -File uninstall-local.ps1

Unregister-ScheduledTask -TaskName "FlyIntelligencePlatform" -Confirm:$false -ErrorAction SilentlyContinue
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Fly Intelligence Platform.lnk" -ErrorAction SilentlyContinue

$pid8787 = (netstat -ano 2>$null | Select-String ":8787.*LISTENING" | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -First 1)
if ($pid8787) { taskkill /PID $pid8787 /F 2>$null }

if (Test-Path "$PSScriptRoot\data\monitor.pid") {
    $mpid = Get-Content "$PSScriptRoot\data\monitor.pid"
    taskkill /PID $mpid /F 2>$null
    Remove-Item "$PSScriptRoot\data\monitor.pid" -Force -ErrorAction SilentlyContinue
}

Write-Host "Local Fly Intelligence Platform removed." -ForegroundColor Green
Write-Host "Deploy on Oracle Cloud: oracle-cloud\README.md"
