# Download Linux (manylinux) wheels for Python 3.12 from Windows — NO Docker required.
# Use this when building the Docker image for an offline Linux server.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$WheelsDir = Join-Path $Root "wheels"
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python" }
$Platform = "manylinux2014_x86_64"
$PyVersion = "3.12"

New-Item -ItemType Directory -Force -Path $WheelsDir | Out-Null

function Download-Wheels {
    param([string]$RequirementsFile)
    Write-Host "==> $RequirementsFile (linux/$PyVersion)"
    & $Python -m pip download `
        -r (Join-Path $Root $RequirementsFile) `
        -d $WheelsDir `
        --platform $Platform `
        --python-version $PyVersion `
        --implementation cp `
        --abi cp312 `
        --only-binary ":all:"
}

Download-Wheels "requirements.build.txt"
Download-Wheels "requirements.docker.txt"
Download-Wheels "requirements.txt"

Write-Host "==> Building project wheel (platform-independent)..."
& $Python -m pip wheel $Root --no-deps -w $WheelsDir

$Count = (Get-ChildItem -Path $WheelsDir -Filter "*.whl").Count
Write-Host ""
Write-Host "Done. $Count wheel(s) in $WheelsDir"
Write-Host "IMPORTANT: These are LINUX wheels for Docker/offline Linux server."
Write-Host "Commit and push: git add wheels/ && git commit -m 'Linux wheels' && git push"
