# Run on Windows WITH internet (PowerShell).
# Downloads all wheels into wheels/ for offline pip install and Docker build.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$WheelsDir = Join-Path $Root "wheels"
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }

New-Item -ItemType Directory -Force -Path $WheelsDir | Out-Null

Write-Host "==> Downloading build tools..."
& $Python -m pip download `
  -r (Join-Path $Root "requirements.build.txt") `
  -d $WheelsDir

Write-Host "==> Downloading runtime dependencies..."
& $Python -m pip download `
  -r (Join-Path $Root "requirements.docker.txt") `
  -d $WheelsDir

Write-Host "==> Downloading dev/test dependencies..."
& $Python -m pip download `
  -r (Join-Path $Root "requirements.txt") `
  -d $WheelsDir

Write-Host "==> Building project wheel..."
& $Python -m pip wheel `
  $Root `
  --no-deps `
  -w $WheelsDir

$Count = (Get-ChildItem -Path $WheelsDir -Filter "*.whl").Count
Write-Host ""
Write-Host "Done. $Count wheel file(s) in: $WheelsDir"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. git add wheels/ && git commit && git push"
Write-Host "  2. bash scripts/build-offline-docker.sh  (or build-offline-docker.ps1)"
Write-Host "  3. docker save -o ai-benchmark.tar ai-benchmark:latest"
