# [AURA-STRICT-PROTOCOL] Ignition Script
$ErrorActionPreference = "Stop"

# Auto-detect the directory this script is located in
$BasePath = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $BasePath

Write-Host "==================================================" -ForegroundColor Magenta
Write-Host "             AURA IGNITION SEQUENCE" -ForegroundColor Magenta
Write-Host "==================================================" -ForegroundColor Magenta

Write-Host "`n[*] Running Pre-Flight Port Sweep (Ghost Buster)..." -ForegroundColor Cyan

# Define the ports AURA needs (8000 for Backend, 3000 for Frontend)
$PortsToClear = @(8000, 3000)

foreach ($port in $PortsToClear) {
    # Find any process using this port (handles both IPv4 and IPv6 overlaps safely)
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($connections) {
        $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($pidToKill in $pids) {
            if ($pidToKill -ne 0 -and $pidToKill -ne 4) { # Safely ignore core Windows system processes
                Write-Host "    [!] Port $port is locked by Ghost Process (PID: $pidToKill). Terminating..." -ForegroundColor Yellow
                Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            }
        }
        Write-Host "    [OK] Port $port is now clear." -ForegroundColor Green
    } else {
        Write-Host "    [OK] Port $port is already clear." -ForegroundColor Green
    }
}

Write-Host "`n[*] Activating Virtual Environment..." -ForegroundColor Cyan
if (Test-Path "$BasePath\.venv\Scripts\Activate.ps1") {
    . "$BasePath\.venv\Scripts\Activate.ps1"
} else {
    Write-Host "[!] CRITICAL ERROR: Virtual environment not found at $BasePath\.venv" -ForegroundColor Red
    Pause
    exit
}

Write-Host "`n[*] Checking MT5 Terminal Status..." -ForegroundColor Cyan
$mt5Process = Get-Process -Name "terminal64", "terminal" -ErrorAction SilentlyContinue
if (-not $mt5Process) {
    Write-Host "    MT5 is not running. Starting MT5..." -ForegroundColor Yellow
    $mt5Path = "C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
    if (Test-Path $mt5Path) {
        Start-Process -FilePath $mt5Path
        Write-Host "    MT5 startup initiated." -ForegroundColor Green
        Start-Sleep -Seconds 3
    } else {
        Write-Host "    [!] Could not find MT5 at $mt5Path. Please start it manually." -ForegroundColor Red
    }
} else {
    Write-Host "    MT5 is already running." -ForegroundColor Green
}

Write-Host "`n[*] Creating Symlink (Wormhole) to MT5...`n" -ForegroundColor Cyan

# Dynamically find MT5 MQL5 Scripts folder
$MT5TerminalBase = "C:\Users\JAY\AppData\Roaming\MetaQuotes\Terminal"
$MT5MQL5Path = $null

if (Test-Path $MT5TerminalBase) {
    # Find the first terminal instance (not "Common" or "Community")
    $TerminalDirs = Get-ChildItem $MT5TerminalBase -Directory | Where-Object { $_.Name -notmatch "^(Common|Community)$" }
    if ($TerminalDirs) {
        $TerminalPath = $TerminalDirs[0].FullName
        $MT5MQL5Path = "$TerminalPath\MQL5\Scripts"
        Write-Host "    [OK] Found MT5 Terminal at: $TerminalPath" -ForegroundColor Green
    }
}

$AuraEAPath = "$BasePath\ea\Experts"

# Ensure the source directory exists before linking
if (-not (Test-Path $AuraEAPath)) {
    Write-Host "    [*] Creating missing target directory: $AuraEAPath" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $AuraEAPath -Force | Out-Null
}

if (Test-Path $MT5MQL5Path) {
    $LinkPath = "$MT5MQL5Path\AURA_Workspace"
    
    # Remove existing symlink/junction if it exists
    if (Test-Path $LinkPath) {
        Write-Host "    [*] Removing existing wormhole..." -ForegroundColor Yellow
        cmd /c rmdir "`"$LinkPath`"" /s /q 2>$null
    }
    
    Write-Host "    [*] Attempting to create wormhole (Junction)..." -ForegroundColor Yellow
    
    # [CRITICAL FIX] Using /J (Junction) instead of /D (Symlink) bypasses the need for Administrator Privileges
    $output = & cmd /c mklink /J "`"$LinkPath`"" "`"$AuraEAPath`"" 2>&1
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host "    [OK] Wormhole created successfully!" -ForegroundColor Green
        Write-Host "    [INFO] MT5 can now access: $LinkPath" -ForegroundColor Green
    } else {
        Write-Host "    [!] CRITICAL ERROR: Wormhole creation failed (exit code: $exitCode)" -ForegroundColor Red
        Write-Host "    [!] Reason: $output" -ForegroundColor Red
        Write-Host "    [!] SYMLINK IS MANDATORY. Aborting boot sequence." -ForegroundColor Red
        Pause
        exit
    }
} else {
    Write-Host "    [!] CRITICAL ERROR: MT5 MQL5 Scripts path not found. Check MT5 installation." -ForegroundColor Red
    Write-Host "    [!] SYMLINK IS MANDATORY. Aborting boot sequence." -ForegroundColor Red
    Pause
    exit
}

Write-Host "`n[*] Starting MT5 Sync Daemon..." -ForegroundColor Cyan
Start-Process pythonw -ArgumentList "scripts\mt5_sync_daemon.py" -WorkingDirectory $BasePath

Write-Host "`n[*] Engaging Boot Commander...`n" -ForegroundColor Cyan
python "scripts\1. Start-AURA.py"