#Requires -Version 5.1
<#
.SYNOPSIS
  Import bundled Ollama models into a running air-gap compose stack.
#>
param(
    [string]$BundleDir = $PSScriptRoot,
    [string]$ComposeFile = "docker-compose.airgap.yml",
    [string]$Archive = "models/ollama-models.tar.gz",
    [string]$EnvFile = ".env.airgap"
)

$ErrorActionPreference = "Stop"
$archivePath = Join-Path $BundleDir $Archive
$manifestPath = Join-Path $BundleDir "models\ollama-models.manifest.json"

if (-not (Test-Path $archivePath)) {
    Write-Host "No bundled Ollama models at $archivePath — skip import."
    return
}

if (Test-Path $manifestPath) {
    $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
    $hash = Get-FileHash -Path $archivePath -Algorithm SHA256
    if ($manifest.sha256 -ne $hash.Hash.ToLower()) {
        throw "Ollama models SHA256 mismatch!"
    }
    Write-Host "Ollama models checksum verified."
}

Push-Location $BundleDir
try {
    $composeArgs = @("-f", $ComposeFile)
    if (Test-Path $EnvFile) { $composeArgs = @("--env-file", $EnvFile) + $composeArgs }

    Write-Host "==> Waiting for Ollama container..."
    $cid = $null
    for ($i = 0; $i -lt 30; $i++) {
        $cid = docker compose @composeArgs ps -q ollama 2>$null
        if ($cid) { break }
        Start-Sleep -Seconds 2
    }
    if (-not $cid) { throw "Ollama container not found. Start the stack first." }

    Write-Host "==> Importing models into Ollama volume..."
    docker cp $archivePath "${cid}:/tmp/ollama-models.tar.gz"
    docker exec $cid sh -c "tar xzf /tmp/ollama-models.tar.gz -C /root/.ollama && rm -f /tmp/ollama-models.tar.gz"

    Write-Host "==> Installed models:"
    docker exec $cid ollama list
    Write-Host "Ollama model import complete."
}
finally {
    Pop-Location
}
