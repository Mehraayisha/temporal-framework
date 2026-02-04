<#
Integrate a Team B package (zip or folder) into the Privacy Firewall repo on Windows.

Usage:
  .\integrate_team_b.ps1 -Path "C:\path\to\team_b_org_chart.zip" -StartDocker
  .\integrate_team_b.ps1 -Path "C:\path\to\team_b_org_chart_folder"

What it does:
 - Accepts a zip file or folder containing Team B integration files.
 - Extracts (when zip) into `data/team_b_org_chart` and looks for `org_data.json`.
 - Copies `org_data.json` to `data/org_data.json` (backing up existing file).
 - Runs `python data/ingestion.py` if present.
 - Starts the API (background) with uvicorn on port 8000.
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Path,
    [switch]$StartDocker
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..') | Select-Object -ExpandProperty Path
Set-Location $repoRoot

if (-not (Test-Path $Path)) {
    Write-Error "Provided path '$Path' does not exist. Provide a zip file or folder."
    exit 1
}

$targetDir = Join-Path $repoRoot "data\team_b_org_chart"
if (Test-Path $targetDir) { Remove-Item $targetDir -Recurse -Force }
New-Item -ItemType Directory -Path $targetDir | Out-Null

if ($Path.ToLower().EndsWith('.zip')) {
    Write-Host "Extracting zip to $targetDir..."
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($Path, $targetDir)
} else {
    Write-Host "Copying folder contents to $targetDir..."
    Copy-Item -Path (Join-Path $Path '*') -Destination $targetDir -Recurse
}

$found = Get-ChildItem -Path $targetDir -Filter 'org_data.json' -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $found) {
    Write-Warning "org_data.json not found in the Team B package. Looked under: $targetDir"
} else {
    $orgDataSrc = $found.FullName
    $orgDataDst = Join-Path $repoRoot 'data\org_data.json'
    if (Test-Path $orgDataDst) {
        $bak = "$orgDataDst.bak.$((Get-Date).ToString('yyyyMMddHHmmss'))"
        Copy-Item $orgDataDst $bak
        Write-Host "Backed up existing org_data.json to $bak"
    }
    Copy-Item $orgDataSrc $orgDataDst -Force
    Write-Host "Copied Team B org_data.json to data/org_data.json"

    # Prefer package's ingestion script if present, otherwise look for repo-level ingestion
    $packageIngest = Join-Path $targetDir 'data\ingestion.py'
    $repoIngest = Join-Path $repoRoot 'data\ingestion.py'
    if (Test-Path $packageIngest) {
        Write-Host "Running package ingestion script: $packageIngest"
        python $packageIngest
    } elseif (Test-Path $repoIngest) {
        Write-Host "Running repo ingestion script: $repoIngest"
        python $repoIngest
    } else {
        Write-Warning "No ingestion script found (checked $packageIngest and $repoIngest). Please load data manually if needed."
    }
}

if ($StartDocker) {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Host "Starting docker-compose services..."
        docker-compose up -d
    } else {
        Write-Warning "Docker not found. Skipping docker-compose."
    }
}

if (Test-Path "api/rest_api.py") {
    Write-Host "Starting API on port 8000 (background)..."
    Start-Process -NoNewWindow -FilePath "python" -ArgumentList "-m","uvicorn","api.rest_api:app","--port","8000"
    Write-Host "API started (background). Use curl http://localhost:8000/api/v1/health to verify."
} else {
    Write-Warning "api/rest_api.py not found. Start the API manually when ready."
}

Write-Host "Team B integration script finished."
