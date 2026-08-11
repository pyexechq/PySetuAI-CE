#Requires -Version 5.1
<#
.SYNOPSIS
  Install HelixGuard AI from an offline bundle (run inside extracted bundle directory).
#>
$ErrorActionPreference = "Stop"
$BundleDir = $PSScriptRoot
$ImageArchive = Join-Path $BundleDir "images\helixguard-images.tar"
$ComposeFile = Join-Path $BundleDir "docker-compose.airgap.yml"
$Manifest = Join-Path $BundleDir "manifest.json"

if (-not (Test-Path $ImageArchive)) {
    throw "Missing $ImageArchive. Run bundle.ps1 on a connected machine first."
}

if (Test-Path $Manifest) {
    $manifest = Get-Content $Manifest -Raw | ConvertFrom-Json
    $hash = Get-FileHash -Path $ImageArchive -Algorithm SHA256
    if ($manifest.sha256 -ne $hash.Hash.ToLower()) {
        throw "SHA256 mismatch! Expected $($manifest.sha256), got $($hash.Hash.ToLower())"
    }
    Write-Host "Checksum verified."
}

Write-Host "==> Loading container images (offline)..."
docker load -i $ImageArchive

Write-Host "==> Starting air-gapped stack..."
Push-Location $BundleDir
try {
    docker compose --env-file (Join-Path $BundleDir ".env.airgap") -f $ComposeFile up -d
}
finally {
    Pop-Location
}

$importScript = Join-Path $BundleDir "import-ollama-models.ps1"
if (Test-Path $importScript) {
    Write-Host "==> Importing bundled Ollama models (if present)..."
    & $importScript -BundleDir $BundleDir -ComposeFile "docker-compose.airgap.yml"
}

Write-Host ""
Write-Host "HelixGuard air-gap stack is starting."
Write-Host "  UI:      http://localhost:3000"
Write-Host "  API:     http://localhost:8001"
Write-Host "  Health:  http://localhost:8001/health"
Write-Host ""
if (-not (Test-Path (Join-Path $BundleDir "models\ollama-models.tar.gz"))) {
    Write-Host "Load a local LLM model manually:"
    Write-Host "  docker compose -f $ComposeFile exec ollama ollama pull llama3.2"
}
