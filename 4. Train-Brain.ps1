$ErrorActionPreference = "Stop"
$BasePath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $BasePath

Clear-Host
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " [AURA-STRICT-PROTOCOL] PHASE 4: DEEP RL GYM TRAINING ENGINE" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[*] Validating Institutional Environment..." -ForegroundColor DarkGray
if (Test-Path "$BasePath\.venv\Scripts\Activate.ps1") {
    . "$BasePath\.venv\Scripts\Activate.ps1"
    Write-Host "    [v] Virtual Environment (AURA-ENV) Activated." -ForegroundColor Green
} else {
    Write-Host "    [!] FATAL ERROR: Virtual environment not found in $BasePath\.venv" -ForegroundColor Red
    Write-Host "    [!] Halting pipeline progression. Lock & Move protocol engaged." -ForegroundColor Red
    Pause
    exit
}

Write-Host "`n[*] Initiating Neural Training Sequence (Hardware Auto-Detect)..." -ForegroundColor Yellow

# AURA Routing: Check the scripts folder for the UI file
$gui_path = "$BasePath\scripts\gui_rl_trainer.py"
$headless_path = "$BasePath\rl\training\train_multicore.py"

if (Test-Path $gui_path) {
    Write-Host "    [v] Visual Gym Environment Detected. Booting UI..." -ForegroundColor Green
    python $gui_path
} elseif (Test-Path $headless_path) {
    Write-Host "    [v] Headless Multi-Core Engine Detected. Booting CLI..." -ForegroundColor Yellow
    Write-Host "    [!] WARNING: CTKinter UI not found in 'scripts\'. Falling back to headless mode." -ForegroundColor DarkYellow
    python $headless_path
} else {
    Write-Host "    [!] ERROR: No Phase 4 training modules found." -ForegroundColor Red
    Pause
    exit
}

Write-Host "`n==================================================================" -ForegroundColor Cyan
Write-Host " [✅] PHASE 4 PIPELINE EXITED." -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Cyan
Pause