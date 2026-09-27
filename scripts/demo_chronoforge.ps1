$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Demo = Join-Path $Root "examples\chronoforge-demo"

Write-Host "==> Running current demo tests"
Push-Location $Demo
try {
    pytest
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "==> Starting ChronoForge on the demo workspace"
$env:LR_AGENT_WORKSPACE = $Demo

lr-agent chrono `
    "Keep current client configuration behavior stable while allowing future configuration evolution" `
    --generations 3 `
    --trajectories 3
