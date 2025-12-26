<#
.SYNOPSIS
    Automated Deployment Script for Python FastAPI Server
.DESCRIPTION
    This script automates the setup of a Python environment:
    1. Checks prerequisites (Python).
    2. Configures Database connection interactively.
    3. Creates a Virtual Environment (venv).
    4. Installs dependencies from requirements.txt.
    5. Sets environment variables and starts the server.
#>

# --- CONFIGURATION DEFAULTS ---
$defaultHost = "localhost"
$defaultPort = "5432"
$defaultUser = "postgres"
$defaultPass = "password"
$defaultDB   = "poll_db"

# --- 1. PREREQUISITES CHECK ---
Write-Host "--- [1/6] Checking Prerequisites ---" -ForegroundColor Cyan

# Check for Python
try {
    $pyVersion = python --version 2>&1
    Write-Host " [OK] Python found: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host " [ERROR] Python is not installed or not in PATH." -ForegroundColor Red
    Exit 1
}

# --- 2. INTERACTIVE CONFIGURATION ---
Write-Host "`n--- [2/6] Database Configuration ---" -ForegroundColor Cyan
Write-Host "The script is configured to use the following defaults:"
Write-Host "  Host: $defaultHost"
Write-Host "  Port: $defaultPort"
Write-Host "  User: $defaultUser"
Write-Host "  DB:   $defaultDB"

$useDefaults = Read-Host -Prompt "Do you want to use these settings? (y/n)"

if ($useDefaults -eq 'n') {
    Write-Host "Please provide your PostgreSQL connection details:" -ForegroundColor Yellow
    $dbHost = Read-Host -Prompt "Host"
    $dbPort = Read-Host -Prompt "Port"
    $dbUser = Read-Host -Prompt "User"
    $dbPassword = Read-Host -Prompt "Password"
    $dbName = Read-Host -Prompt "Database Name"
} else {
    $dbHost = $defaultHost
    $dbPort = $defaultPort
    $dbUser = $defaultUser
    $dbPassword = $defaultPass
    $dbName = $defaultDB
}

# --- 3. ENVIRONMENT SETUP ---
Write-Host "`n--- [3/6] Setting up Environment Variables ---" -ForegroundColor Cyan

# Formulate SQLAlchemy Connection String
# Format: postgresql+asyncpg://user:password@host:port/dbname
$connectionString = "postgresql+asyncpg://$($dbUser):$($dbPassword)@$($dbHost):$($dbPort)/$($dbName)"

# Set Env Variable for the current session
$env:DATABASE_URL = $connectionString
Write-Host " [OK] DATABASE_URL environment variable set." -ForegroundColor Green

# Optional: Create .env file for persistence
Set-Content -Path ".env" -Value "DATABASE_URL=$connectionString"
Write-Host " [OK] .env file created for future use." -ForegroundColor Green

# --- 4. VIRTUAL ENVIRONMENT ---
Write-Host "`n--- [4/6] Managing Virtual Environment ---" -ForegroundColor Cyan

if (Test-Path "venv") {
    Write-Host " [INFO] Virtual environment 'venv' already exists." -ForegroundColor Yellow
} else {
    Write-Host " [INIT] Creating new virtual environment..."
    python -m venv venv
    if ($LASTEXITCODE -ne 0) { Write-Host " [ERROR] Failed to create venv." -ForegroundColor Red; Exit 1 }
    Write-Host " [OK] Virtual environment created." -ForegroundColor Green
}

# Activate Venv
Write-Host " [ACTIVATE] Activating virtual environment..."
try {
    . .\venv\Scripts\Activate.ps1
} catch {
    Write-Host " [WARNING] Could not run activation script directly. Using direct path for python." -ForegroundColor Yellow
}

# --- 5. DEPENDENCIES ---
Write-Host "`n--- [5/6] Installing Dependencies ---" -ForegroundColor Cyan
Write-Host "Installing requirements from requirements.txt..."

.\venv\Scripts\python -m pip install --upgrade pip | Out-Null
.\venv\Scripts\pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host " [ERROR] Failed to install dependencies." -ForegroundColor Red
    Exit 1
}
Write-Host " [OK] Dependencies installed successfully." -ForegroundColor Green

# --- 6. START SERVER ---
Write-Host "`n--- [6/6] Starting Application Server ---" -ForegroundColor Cyan
Write-Host "Server will start on 0.0.0.0:8000"
Write-Host "Press CTRL+C to stop." -ForegroundColor Yellow
Write-Host "------------------------------------------------"

# Launching main.py using the python inside venv
.\venv\Scripts\python main.py