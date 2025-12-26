<#
.SYNOPSIS
    IoT Client Provisioning & Startup Script
.DESCRIPTION
    Simulates the firmware upload and startup process for the IoT terminal.
    1. Checks for configuration file.
    2. Sets up a lightweight virtual environment.
    3. Installs client-specific libraries (rich, requests).
    4. Launches the IoT emulation.
#>

Write-Host "=== IOT TERMINAL PROVISIONING SYSTEM ===" -ForegroundColor Magenta

# --- 1. CONFIG CHECK ---
Write-Host "`n[1/4] Checking Configuration..."
if (Test-Path "config.json") {
    $config = Get-Content "config.json" | ConvertFrom-Json
    Write-Host " [OK] Config found." -ForegroundColor Green
    Write-Host "      Device ID: $($config.device_id)"
    Write-Host "      Room ID:   $($config.room_id)"
    Write-Host "      Server:    $($config.server_url)"
} else {
    Write-Host " [ERROR] config.json is missing! Please configure the device first." -ForegroundColor Red
    Exit 1
}

# --- 2. PYTHON CHECK ---
Write-Host "`n[2/4] Checking Runtime Environment..."
try {
    $pyVer = python --version 2>&1
    Write-Host " [OK] Runtime found: $pyVer" -ForegroundColor Green
} catch {
    Write-Host " [FATAL] Python runtime not found." -ForegroundColor Red
    Exit 1
}

# --- 3. PROVISIONING (LIBS) ---
Write-Host "`n[3/4] Provisioning Libraries..."

# Check if client venv exists, if not create it (Isolated from server)
if (-not (Test-Path "client_venv")) {
    Write-Host " [INIT] Creating isolated client environment..."
    python -m venv client_venv
}

# Install only necessary libs for client
Write-Host " [INSTALL] Installing drivers (requests, rich)..."
.\client_venv\Scripts\pip install requests rich --disable-pip-version-check

if ($LASTEXITCODE -eq 0) {
    Write-Host " [OK] Provisioning complete." -ForegroundColor Green
} else {
    Write-Host " [ERROR] Failed to install libraries." -ForegroundColor Red
    Exit 1
}

# --- 4. LAUNCH ---
Write-Host "`n[4/4] Booting Device..." -ForegroundColor Cyan
Start-Sleep -Seconds 1

Write-Host "------------------------------------------------"
Write-Host " Starting SmartPollingTerminal..."
Write-Host "------------------------------------------------"

.\client_venv\Scripts\python iot_client.py