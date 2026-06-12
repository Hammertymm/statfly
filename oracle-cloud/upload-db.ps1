# Fly Intelligence Platform — upload local database to Oracle VM
# Usage: .\upload-db.ps1 -VmIp 123.45.67.89 -KeyPath C:\path\to\key.key

param(
    [Parameter(Mandatory = $true)]
    [string]$VmIp,
    [string]$User = "ubuntu",
    [string]$KeyPath = ""
)

$ErrorActionPreference = "Stop"
$DbPath = Join-Path $PSScriptRoot "..\flytime-engine\data\flytime_engine.db"
$RemotePath = "/data/flytime/flytime_engine.db"

if (-not (Test-Path $DbPath)) {
    Write-Host "ERROR: Database not found at $DbPath" -ForegroundColor Red
    exit 1
}

$sizeMb = [math]::Round((Get-Item $DbPath).Length / 1MB, 1)
Write-Host "Uploading flytime_engine.db (${sizeMb} MB) to ${User}@${VmIp}:${RemotePath}..."

$scpArgs = @()
if ($KeyPath) { $scpArgs += @("-i", $KeyPath) }
$scpArgs += @($DbPath, "${User}@${VmIp}:${RemotePath}")

& scp @scpArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "SCP failed. Enable OpenSSH Client in Windows Settings, or use WinSCP." -ForegroundColor Red
    exit 1
}

$sshArgs = @()
if ($KeyPath) { $sshArgs += @("-i", $KeyPath) }
$remote = "cd ~/scorefly && docker compose -f docker-compose.oracle.yml restart && echo Platform restarted."
$sshArgs += "${User}@${VmIp}", $remote

& ssh @sshArgs
Write-Host ""
Write-Host "Done. Dashboard: http://${VmIp}:8787/" -ForegroundColor Green
