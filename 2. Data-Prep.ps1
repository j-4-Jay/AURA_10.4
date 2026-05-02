# [AURA-STRICT-PROTOCOL] Data Preparation Ignition
$ErrorActionPreference = "Stop"

# Auto-detect the directory this script is located in
$BasePath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $BasePath

Write-Host "==================================================" -ForegroundColor Magenta
Write-Host "             AURA DATA PREP ENGINE" -ForegroundColor Magenta
Write-Host "==================================================" -ForegroundColor Magenta

Write-Host "`n[*] Activating Virtual Environment..." -ForegroundColor Cyan
if (Test-Path "$BasePath\.venv\Scripts\Activate.ps1") {
    . "$BasePath\.venv\Scripts\Activate.ps1"
} else {
    Write-Host "[!] CRITICAL ERROR: Virtual environment not found at $BasePath\.venv" -ForegroundColor Red
    Pause
    exit
}

Write-Host "`n[*] Launching Institutional Data Prep Dashboard..." -ForegroundColor Cyan
python "scripts\gui_data_prep.py"

Write-Host "`n[*] Dashboard offline." -ForegroundColor Green
Pause