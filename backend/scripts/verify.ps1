[CmdletBinding()]
param(
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FrontendRoot = (Resolve-Path (Join-Path $BackendRoot "..\frontend")).Path
$Python = Join-Path $BackendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Backend Python executable not found at $Python"
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

Push-Location $BackendRoot
try {
    Invoke-Stage "Backend ruff" { & $Python -m ruff check . }
    Invoke-Stage "Backend black" { & $Python -m black --check . }
    Invoke-Stage "Backend isort" { & $Python -m isort --check-only . }
    Invoke-Stage "Backend mypy" { & $Python -m mypy app }
    Invoke-Stage "Backend tests" { & $Python -m pytest --cov=app --cov-fail-under=77 }
}
finally {
    Pop-Location
}

if (-not $SkipFrontend) {
    Push-Location $FrontendRoot
    try {
        Invoke-Stage "Frontend lint" { & npm.cmd run lint }
        Invoke-Stage "Frontend format" { & npm.cmd run format:check }
        Invoke-Stage "Frontend tests" { & npm.cmd run test }
        Invoke-Stage "Frontend coverage" { & npm.cmd run test:coverage }
        Invoke-Stage "Frontend build" { & npm.cmd run build }
    }
    finally {
        Pop-Location
    }
}

Write-Host "NFL Confidence verification completed."
