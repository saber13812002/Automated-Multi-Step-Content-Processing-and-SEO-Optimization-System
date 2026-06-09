# Build Docker image offline on Windows (wheels/ must exist; base image cached locally).
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ImageName = if ($env:IMAGE_NAME) { $env:IMAGE_NAME } else { "ai-benchmark:latest" }
$TarOutput = if ($env:TAR_OUTPUT) { $env:TAR_OUTPUT } else { Join-Path $Root "ai-benchmark.tar" }
$WheelsDir = Join-Path $Root "wheels"

Set-Location $Root

$Wheels = Get-ChildItem -Path $WheelsDir -Filter "*.whl" -ErrorAction SilentlyContinue
if (-not $Wheels) {
  Write-Error "No wheels found in $WheelsDir. Run scripts/download-wheels.ps1 first."
}

docker image inspect python:3.12-slim 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Error @"
Base image python:3.12-slim is not available locally.
Run once with internet:
  docker pull python:3.12-slim
"@
}

Write-Host "==> Building $ImageName (offline, no network)..."
$env:DOCKER_BUILDKIT = "1"
docker build --network=none -t $ImageName .

Write-Host "==> Saving image to $TarOutput..."
docker save -o $TarOutput $ImageName

Write-Host ""
Write-Host "Build complete."
Write-Host "  Image : $ImageName"
Write-Host "  Tar   : $TarOutput"
Write-Host ""
Write-Host "Transfer ai-benchmark.tar to offline server, then:"
Write-Host "  docker load -i ai-benchmark.tar"
Write-Host "  docker run -d -p 8000:8000 -v ai_benchmarker_data:/data --name ai-benchmarker $ImageName"
