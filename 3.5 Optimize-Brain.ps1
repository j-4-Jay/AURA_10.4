$ErrorActionPreference = "Stop"
$BasePath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $BasePath

# Activate Virtual Environment silently
if (Test-Path "$BasePath\.venv\Scripts\Activate.ps1") {
    . "$BasePath\.venv\Scripts\Activate.ps1"
} else {
    Write-Host "[!] CRITICAL ERROR: Virtual environment not found in .venv" -ForegroundColor Red
    Pause
    exit
}

# Launch the Python CustomTkinter App for Brain Tuning
Start-Process pythonw -ArgumentList "scripts\gui_brain_tuner.py"