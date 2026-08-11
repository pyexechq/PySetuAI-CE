#Requires -Version 5.1
<#
.SYNOPSIS
  Export Ollama model blobs for offline air-gap bundles (internet-connected host).
.PARAMETER Models
  Comma-separated model tags to pull and bundle (default: llama3.2).
.PARAMETER OutputPath
  Output tar.gz path (default: models/ollama-models.tar.gz).
#>
param(
    [string[]]$Models = @("llama3.2"),
    [string]$OutputPath = "models/ollama-models.tar.gz",
    [string]$OllamaImage = "ollama/ollama:0.5.4"
)

$ErrorActionPreference = "Stop"
$outputDir = Split-Path -Parent $OutputPath
if ($outputDir -and -not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}
$outputAbs = (Resolve-Path $outputDir).Path + "\" + (Split-Path -Leaf $OutputPath)

$vol = "helixguard-ollama-export-$(Get-Random)"
$container = "helixguard-ollama-export-$(Get-Random)"

function Cleanup {
    docker rm -f $container 2>$null | Out-Null
    docker volume rm $vol 2>$null | Out-Null
}

try {
    Write-Host "==> Exporting Ollama models: $($Models -join ', ')"
    docker volume create $vol | Out-Null
    docker run -d --name $container -v "${vol}:/root/.ollama" $OllamaImage | Out-Null
    Start-Sleep -Seconds 5

    foreach ($model in $Models) {
        if ([string]::IsNullOrWhiteSpace($model)) { continue }
        Write-Host "    pulling $model..."
        docker exec $container ollama pull $model
    }

    docker exec $container sh -c "tar czf /tmp/ollama-models.tar.gz -C /root/.ollama ."
    docker cp "${container}:/tmp/ollama-models.tar.gz" $outputAbs

    $hash = Get-FileHash -Path $outputAbs -Algorithm SHA256
    $manifest = @{
        models = @($Models | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        archive = Split-Path -Leaf $outputAbs
        sha256 = $hash.Hash.ToLower()
        ollama_image = $OllamaImage
    }
    $manifestPath = Join-Path $outputDir "ollama-models.manifest.json"
    $manifest | ConvertTo-Json -Depth 4 | Set-Content $manifestPath

    Write-Host "==> Export complete:"
    Write-Host "  Archive:  $outputAbs"
    Write-Host "  SHA256:   $($hash.Hash.ToLower())"
    Write-Host "  Manifest: $manifestPath"
}
finally {
    Cleanup
}
