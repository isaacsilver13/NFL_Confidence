[CmdletBinding()]
param(
    [string]$DatabaseUrl,
    [string]$ApiHost = "127.0.0.1",
    [int]$ApiPort = 8000,
    [switch]$NoSeed
)

$ErrorActionPreference = "Stop"
$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ComposeFile = (Resolve-Path (Join-Path $BackendRoot "..\docker-compose.yml")).Path
$Python = Join-Path $BackendRoot ".venv\Scripts\python.exe"

if (-not $DatabaseUrl) {
    $DatabaseUrl = $env:DATABASE_URL
}
if (-not $DatabaseUrl) {
    $DatabaseUrl = "postgresql+psycopg://nfl_confidence:nfl_confidence@localhost:5432/nfl_confidence"
}

if (-not (Test-Path $Python)) {
    throw "Backend Python executable not found at $Python"
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI was not found on PATH"
}

function Invoke-Stage {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host "[$Name]"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$listeners = Get-NetTCPConnection -LocalAddress $ApiHost -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
foreach ($ProcessId in $listeners) {
    Write-Host "Stopping API listener process $ProcessId on $ApiHost`:$ApiPort"
    Stop-Process -Id $ProcessId -Force -ErrorAction Stop
}

$env:DATABASE_URL = $DatabaseUrl

Invoke-Stage "Starting PostgreSQL" {
    & docker compose -f $ComposeFile up -d --wait db
}

Push-Location $BackendRoot
try {
    Invoke-Stage "Applying migrations" {
        & $Python -m alembic upgrade head
    }

    if (-not $NoSeed) {
        Invoke-Stage "Seeding deterministic test data" {
            & $Python -m scripts.seed_test_data
        }
    }
}
finally {
    Pop-Location
}

Write-Host "Local NFL Confidence preparation completed."
