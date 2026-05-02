# [AURA-STRICT-PROTOCOL] Step 1.1 - The "Wormhole" Symlink Generator
$ErrorActionPreference = "Stop"
Clear-Host
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " [AURA] PHASE 1: DIRECTORY JUNCTION (THE WORMHOLE EXPERIMENT)" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

Write-Host "This script links your AURA project folder directly into MetaTrader 5."
Write-Host "You only need to run this ONCE." -ForegroundColor Yellow
Write-Host ""

# Hardcoded MT5 MQL5 path based on the terminal executable location
$MT5_Path = "C:\Users\JAY\AppData\Roaming\MetaQuotes\Terminal\53785E099C927DB68A545C249CDBCE06\MQL5"

if (-not (Test-Path $MT5_Path)) {
    Write-Host "[!] Error: The path '$MT5_Path' does not exist. Ensure MT5 is running or installed in portable mode." -ForegroundColor Red
    Pause
    exit
}

$AURA_Experts_Path = "$PSScriptRoot\..\ea\Experts"
$Target_Junction = "$MT5_Path\Experts\AURA_Experts"

if (Test-Path $Target_Junction) {
    Write-Host "[!] The wormhole already exists at $Target_Junction" -ForegroundColor Green
} else {
    New-Item -ItemType Junction -Path $Target_Junction -Target $AURA_Experts_Path | Out-Null
    Write-Host "[v] SUCCESS! MT5 can now see $AURA_Experts_Path instantly!" -ForegroundColor Green
}

Pause