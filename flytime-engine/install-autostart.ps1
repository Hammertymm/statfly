# Fly Intelligence Platform - zero-account local autostart installer
# Run: powershell -ExecutionPolicy Bypass -File install-autostart.ps1

$ErrorActionPreference = "Stop"
$EngineDir = $PSScriptRoot
$TaskName = "FlyIntelligencePlatform"
$VbsLauncher = Join-Path $EngineDir "launch-platform-hidden.vbs"
$Wscript = "$env:SystemRoot\System32\wscript.exe"

Write-Host ""
Write-Host "  Fly Intelligence Platform - Autostart Installer" -ForegroundColor Cyan
Write-Host "  ==============================================" -ForegroundColor Cyan
Write-Host ""

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "  ERROR: Python not found on PATH." -ForegroundColor Red
    exit 1
}
Write-Host "  Python: $($python.Source)" -ForegroundColor Green

Push-Location $EngineDir
python main.py init | Out-Null
Pop-Location
Write-Host "  Database: OK" -ForegroundColor Green

try {
    powercfg /change standby-timeout-ac 0 | Out-Null
    powercfg /change hibernate-timeout-ac 0 | Out-Null
    powercfg /change monitor-timeout-ac 30 | Out-Null
    powercfg /change standby-timeout-dc 90 | Out-Null
    Write-Host "  Power plan: no sleep on AC, 90 min on battery" -ForegroundColor Green
} catch {
    Write-Host "  Power plan: skipped" -ForegroundColor Yellow
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute $Wscript -Argument "`"$VbsLauncher`"" -WorkingDirectory $EngineDir

$logonTrigger = New-ScheduledTaskTrigger -AtLogon -User $env:USERNAME
$heartbeatTrigger = New-ScheduledTaskTrigger -Once -At "00:05" `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger @($logonTrigger, $heartbeatTrigger) `
    -Settings $settings `
    -Principal $principal `
    -Description "ScoreFly Fly Intelligence Platform on port 8787" | Out-Null

Write-Host "  Scheduled task: $TaskName" -ForegroundColor Green
Write-Host "    - At Windows logon" -ForegroundColor DarkGray
Write-Host "    - Every 30 min (restart if stopped)" -ForegroundColor DarkGray
Write-Host "    - Startup folder shortcut (backup)" -ForegroundColor DarkGray

$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "Fly Intelligence Platform.lnk"
$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut($shortcutPath)
$sc.TargetPath = $Wscript
$sc.Arguments = "`"$VbsLauncher`""
$sc.WorkingDirectory = $EngineDir
$sc.Description = "Fly Intelligence Platform"
$sc.Save()
Write-Host "  Startup shortcut: OK" -ForegroundColor Green

Start-Process -FilePath $Wscript -ArgumentList "`"$VbsLauncher`"" -WorkingDirectory $EngineDir -WindowStyle Hidden
Start-Sleep -Seconds 5

$listening = netstat -ano 2>$null | Select-String ":8787.*LISTENING"
if ($listening) {
    Write-Host "  Platform: running at http://127.0.0.1:8787/" -ForegroundColor Green
} else {
    Write-Host "  Platform: starting... open http://127.0.0.1:8787/ shortly" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  DONE - no accounts, no credit card required." -ForegroundColor Cyan
Write-Host ""
Write-Host "  Dashboard:     http://127.0.0.1:8787/"
Write-Host "  Plug in laptop: stays on indefinitely on AC power"
Write-Host "  Trade-off: pauses when laptop sleeps or is powered off (about 8 pct)"
Write-Host "  Uninstall task: Unregister-ScheduledTask -TaskName FlyIntelligencePlatform"
Write-Host ""
