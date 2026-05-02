$ErrorActionPreference = "Stop"
$BasePath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $BasePath

Write-Host "==================================================" -ForegroundColor Green
Write-Host "          [BUTTON 5] AURA LIVE INFERENCE" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

Write-Host "`n[*] Waking up the factory..." -ForegroundColor Cyan
if (Test-Path "$BasePath\.venv\Scripts\Activate.ps1") {
    . "$BasePath\.venv\Scripts\Activate.ps1"
} else {
    Write-Host "[!] ERROR: Virtual environment missing!" -ForegroundColor Red; Pause; exit
}

Write-Host "[*] Waking up the Robot. He is now watching the live charts...`n" -ForegroundColor Green
python "rl\live_inference.py"

Write-Host "`n[*] The robot went to sleep." -ForegroundColor Green
Pause