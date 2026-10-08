param(
    [int]$ControlPlanePort = 8001,
    [int]$RuntimePort = 8002
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".\.venv")) {
    python -m venv .venv
}

. .\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]

New-Item -ItemType Directory -Path "data" -Force | Out-Null
$env:AGENTIC_PLATFORM_DB_PATH = "data/agentic_platform.db"
$env:AGENTIC_PLATFORM_RUNTIME_DB_PATH = "data/agentic_platform_runtime.db"

Write-Host "Starting Control Plane API on port $ControlPlanePort"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$ProjectRoot'; . .\.venv\Scripts\Activate.ps1; uvicorn apps.control_plane_api.main:app --reload --port $ControlPlanePort"
)

Write-Host "Starting Runtime API on port $RuntimePort"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$ProjectRoot'; . .\.venv\Scripts\Activate.ps1; uvicorn apps.runtime_api.main:app --reload --port $RuntimePort"
)

Write-Host "Local platform startup requested. Use scripts/smoke-test.ps1 to verify health."
