#Requires -Version 5.1
param(
    [string]$Version = "0.1.0",
    [string[]]$OllamaModels = @()
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$OutputDir = Join-Path $Root "dist\helixguard-airgap-$Version"
$ImagesDir = Join-Path $OutputDir "images"
$ImageArchive = Join-Path $ImagesDir "helixguard-images.tar"
$ComposeBuild = "docker-compose.airgap.yml"
$BackendTag = "helixguard/backend:$Version"
$FrontendTag = "helixguard/frontend:$Version"

Write-Host "==> HelixGuard air-gap bundle v$Version"
if (Test-Path $OutputDir) { Remove-Item $OutputDir -Recurse -Force }
New-Item -ItemType Directory -Path $ImagesDir -Force | Out-Null

Push-Location $Root
try {
    Write-Host "==> Building and tagging application images..."
    docker compose -f $ComposeBuild build
    $projectName = (Split-Path $Root -Leaf).ToLower() -replace '\s',''
    $builtBackend = "${projectName}-backend:latest"
    $builtFrontend = "${projectName}-frontend:latest"
    if (-not (docker image inspect $builtBackend 2>$null)) {
        throw "Expected image $builtBackend after build. Check docker compose project name."
    }
    docker tag $builtBackend $BackendTag
    docker tag $builtFrontend $FrontendTag

    $thirdParty = @(
        "postgres:16-alpine",
        "redis:7-alpine",
        "hashicorp/vault:1.17",
        "openpolicyagent/opa:0.68.0",
        "ollama/ollama:0.5.4"
    )

    Write-Host "==> Pulling third-party images..."
    foreach ($image in $thirdParty) { docker pull $image }

    $saveImages = $thirdParty + @($BackendTag, $FrontendTag)
    Write-Host "==> Saving images to $ImageArchive..."
    docker save -o $ImageArchive @saveImages

    Write-Host "==> Copying deployment artifacts..."
    Copy-Item (Join-Path $PSScriptRoot "docker-compose.offline.yml") (Join-Path $OutputDir "docker-compose.airgap.yml")
    Copy-Item (Join-Path $Root "deploy\helm") (Join-Path $OutputDir "helm") -Recurse
    Copy-Item (Join-Path $Root "deploy\opa") (Join-Path $OutputDir "opa") -Recurse
    Copy-Item (Join-Path $PSScriptRoot "install.sh") $OutputDir
    Copy-Item (Join-Path $PSScriptRoot "install.ps1") $OutputDir
    Copy-Item (Join-Path $PSScriptRoot "import-ollama-models.sh") $OutputDir
    Copy-Item (Join-Path $PSScriptRoot "import-ollama-models.ps1") $OutputDir
    Copy-Item (Join-Path $PSScriptRoot "manifest.template.json") (Join-Path $OutputDir "manifest.json")

    if ($OllamaModels.Count -gt 0) {
        Write-Host "==> Bundling Ollama models: $($OllamaModels -join ', ')"
        $modelsDir = Join-Path $OutputDir "models"
        New-Item -ItemType Directory -Path $modelsDir -Force | Out-Null
        & (Join-Path $PSScriptRoot "export-ollama-models.ps1") -Models $OllamaModels -OutputPath (Join-Path $modelsDir "ollama-models.tar.gz")
    }

    @"
HELIXGUARD_BACKEND_IMAGE=$BackendTag
HELIXGUARD_FRONTEND_IMAGE=$FrontendTag
JWT_SECRET_KEY=airgap-change-me-before-production
POSTGRES_PASSWORD=helixguard-airgap
NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1
"@ | Set-Content (Join-Path $OutputDir ".env.airgap")

    $hash = Get-FileHash -Path $ImageArchive -Algorithm SHA256
    $manifest = Get-Content (Join-Path $OutputDir "manifest.json") -Raw | ConvertFrom-Json
    $manifest.version = $Version
    $manifest.created_at = (Get-Date).ToUniversalTime().ToString("o")
    $manifest.images_archive = "helixguard-images.tar"
    $manifest.sha256 = $hash.Hash.ToLower()
    $manifest | Add-Member -NotePropertyName images -NotePropertyValue @{
        backend = $BackendTag
        frontend = $FrontendTag
    } -Force
    if ($OllamaModels.Count -gt 0) {
        $modelManifest = Join-Path $OutputDir "models\ollama-models.manifest.json"
        if (Test-Path $modelManifest) {
            $manifest | Add-Member -NotePropertyName ollama_models -NotePropertyValue (Get-Content $modelManifest -Raw | ConvertFrom-Json) -Force
        }
    }
    $manifest | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $OutputDir "manifest.json")

    $archiveBase = Join-Path $Root "dist\helixguard-airgap-$Version"
    $tarPath = "$archiveBase.tar.gz"
    if (Test-Path $tarPath) { Remove-Item $tarPath -Force }
    Write-Host "==> Creating archive (tar.gz)..."
    tar -czf $tarPath -C (Join-Path $Root "dist") "helixguard-airgap-$Version"

    Write-Host ""
    Write-Host "Bundle ready:"
    Write-Host "  Directory: $OutputDir"
    Write-Host "  Archive:   $tarPath"
    Write-Host "  SHA256:    $($hash.Hash.ToLower())"
}
finally {
    Pop-Location
}
