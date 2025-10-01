# PowerShell script to run temporal framework with environment variables
$env:NEO4J_PASSWORD = "your_password_here"
$env:OPENAI_API_KEY = "your_api_key_here"

Write-Host "Starting Temporal Framework..." -ForegroundColor Green
uv run python main.py