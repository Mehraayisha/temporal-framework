<#
Setup Integration for Privacy Firewall (Windows PowerShell)
Creates virtual environment, installs requirements, optionally starts docker-compose,
runs sample ingestion if present, and starts the demo API (best-effort).
#>

param(
    [switch]$StartDocker
)

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$venvPath = ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at $venvPath..."
    python -m venv $venvPath
}

$activate = "$venvPath\Scripts\Activate.ps1"
if (Test-Path $activate) {
    Write-Host "Activating virtual environment..."
    & $activate
} else {
    Write-Warning "Activation script not found at $activate. Activate the venv manually: .\$venvPath\Scripts\Activate.ps1"
}

Write-Host "Installing Python dependencies from requirements.txt..."
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt
} else {
    Write-Warning "requirements.txt not found. Please install dependencies manually."
}

if ($StartDocker) {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Host "Starting docker-compose services..."
        docker-compose up -d
    } else {
        Write-Warning "Docker not found. Skipping docker-compose."
    }
}

# Run ingestion script if present
if (Test-Path "data/ingestion.py") {
    Write-Host "Running data/ingestion.py to load sample data..."
    python data/ingestion.py
} else {
    Write-Host "No data/ingestion.py found; skipping ingestion."
}

# Start API if available
if (Test-Path "api/rest_api.py") {
    Write-Host "Starting API on port 8000 (background)..."
    Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m","uvicorn","api.rest_api:app","--port","8000"
    Write-Host "API started (background). Use curl http://localhost:8000/api/v1/health to verify."
} else {
    Write-Warning "api/rest_api.py not found. Start the API manually when ready."
}

Write-Host "Integration setup complete."
