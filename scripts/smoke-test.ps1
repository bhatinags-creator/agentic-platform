param(
    [string]$ControlPlaneUrl = "http://localhost:8001",
    [string]$RuntimeUrl = "http://localhost:8002"
)

$ErrorActionPreference = "Stop"

$controlHealth = Invoke-RestMethod -Uri "$ControlPlaneUrl/health" -Method Get
$runtimeHealth = Invoke-RestMethod -Uri "$RuntimeUrl/health" -Method Get

Write-Host "Control Plane:" ($controlHealth | ConvertTo-Json -Compress)
Write-Host "Runtime:" ($runtimeHealth | ConvertTo-Json -Compress)

if ($controlHealth.status -ne "ok") { throw "Control Plane health check failed" }
if ($runtimeHealth.status -ne "ok") { throw "Runtime health check failed" }

Write-Host "Smoke test passed."
