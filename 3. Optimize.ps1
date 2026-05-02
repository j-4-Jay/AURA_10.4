# [AURA-STRICT-PROTOCOL] GUI Launcher (Optuna Tuner)
$ErrorActionPreference = "Stop"
$BasePath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $BasePath

# Activate Virtual Environment silently
if (Test-Path "$BasePath\.venv\Scripts\Activate.ps1") {
    . "$BasePath\.venv\Scripts\Activate.ps1"
} else {
    Write-Host "[!] CRITICAL ERROR: Virtual environment not found!" -ForegroundColor Red
    Pause
    exit
}

# Launch the Python CustomTkinter App
Start-Process pythonw -ArgumentList "scripts\gui_optuna_tuner.py"