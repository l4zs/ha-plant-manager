# Copy the integration to one or more Home Assistant instances over Samba.
#
# Targets are the instances' config shares, one per line in scripts/deploy.targets.local
# (ignored by git), e.g.:
#   \\homeassistant\config
#   \\homeassistant.example.ts.net\config
# or passed directly: ./scripts/deploy.ps1 \\homeassistant\config
#
# Connect to a share that needs a login first:
#   net use \\host\config /user:<samba-user> *
# Restart Home Assistant afterwards to load the new version.

param([string[]]$Targets)

$ErrorActionPreference = "Stop"
$source = Join-Path $PSScriptRoot "..\custom_components\plant_manager" | Resolve-Path
$targetsFile = Join-Path $PSScriptRoot "deploy.targets.local"

if (-not $Targets) {
    if (-not (Test-Path $targetsFile)) {
        Write-Error "No targets: pass them as arguments or list them in $targetsFile"
    }
    $Targets = Get-Content $targetsFile | ForEach-Object { $_.Trim() } |
        Where-Object { $_ -and -not $_.StartsWith("#") }
}

$version = (Get-Content (Join-Path $source "manifest.json") -Raw | ConvertFrom-Json).version
Write-Host "Plant Manager $version"

$failed = @()
foreach ($share in $Targets) {
    $dest = Join-Path $share "custom_components\plant_manager"
    Write-Host "`n-> $share"
    if (-not (Test-Path (Join-Path $share "custom_components"))) {
        Write-Warning "Not reachable, or no custom_components folder. Connect first: net use $share /user:<samba-user> *"
        $failed += $share
        continue
    }
    robocopy $source $dest /MIR /XD __pycache__ /NP /NDL /NFL /NJH /NJS | Out-Null
    # robocopy: 0-7 is success (1 = files copied), 8 and up is an error.
    if ($LASTEXITCODE -ge 8) {
        Write-Warning "Copy failed (robocopy exit code $LASTEXITCODE)"
        $failed += $share
    } elseif ($LASTEXITCODE -eq 0) {
        Write-Host "   already up to date"
    } else {
        Write-Host "   updated, restart Home Assistant to load it"
    }
}

if ($failed) {
    Write-Host "`nFailed: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
