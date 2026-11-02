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
#
# The copy mirrors the folder, so it overwrites changes made on an instance and deletes files
# added there. Each deploy leaves a record of what it copied (.deployed.json in the integration's
# folder). If an instance no longer matches its record, the script lists the differences and asks
# before touching that instance. Without a record yet, it compares with what is about to be copied.

param([string[]]$Targets)

$ErrorActionPreference = "Stop"
$source = Join-Path $PSScriptRoot "..\custom_components\plant_manager" | Resolve-Path
$repo = Join-Path $PSScriptRoot ".." | Resolve-Path
$targetsFile = Join-Path $PSScriptRoot "deploy.targets.local"
$recordName = ".deployed.json"

# Every file of a folder as relative path -> hash, without caches and the record.
function Get-Snapshot([string]$root) {
    $files = @{}
    if (-not (Test-Path $root)) { return $files }
    $prefix = (Get-Item $root).FullName.TrimEnd("\").Length + 1
    foreach ($file in Get-ChildItem $root -Recurse -File -Force) {
        $relative = $file.FullName.Substring($prefix).Replace("\", "/")
        if ($relative -eq $recordName -or $relative -match "(^|/)__pycache__/") { continue }
        $files[$relative] = (Get-FileHash $file.FullName -Algorithm SHA256).Hash
    }
    return $files
}

function Read-Record([string]$dest) {
    $path = Join-Path $dest $recordName
    if (-not (Test-Path $path)) { return $null }
    try {
        $record = Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
        $files = @{}
        foreach ($entry in $record.files.PSObject.Properties) { $files[$entry.Name] = $entry.Value }
        return @{ commit = $record.commit; files = $files }
    } catch {
        Write-Warning "Could not read $path; treating this instance as having no record."
        return $null
    }
}

# The commit being deployed, unless the integration has uncommitted changes.
function Get-CleanCommit {
    try {
        $status = git -C $repo status --porcelain -- custom_components/plant_manager
        if ($LASTEXITCODE -ne 0 -or $status) { return $null }
        $commit = git -C $repo rev-parse HEAD
        if ($LASTEXITCODE -eq 0) { return "$commit".Trim() }
    } catch {}
    return $null
}

# The record's commit as a temporary folder to diff against, or $null if git doesn't have it.
function Export-Commit([string]$commit) {
    if (-not $commit) { return $null }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        git -C $repo cat-file -e "$commit^{commit}" 2>$null
        if ($LASTEXITCODE -ne 0) { return $null }
        $folder = Join-Path ([IO.Path]::GetTempPath()) "plant-manager-deploy-$([guid]::NewGuid())"
        New-Item -ItemType Directory $folder | Out-Null
        $archive = Join-Path $folder "commit.tar"
        git -C $repo archive -o $archive $commit custom_components/plant_manager
        if ($LASTEXITCODE -ne 0) { return $null }
        tar -xf $archive -C $folder
        if ($LASTEXITCODE -ne 0) { return $null }
        return $folder
    } finally {
        $ErrorActionPreference = $previous
    }
}

# Returns $true if this instance may be overwritten.
function Confirm-Target([string]$share, [string]$dest, $current) {
    $record = Read-Record $dest
    $sourceFiles = Get-Snapshot $source
    if (-not (Test-Path $dest)) { return $true }  # a first install: nothing to lose
    $expected = if ($record) { $record.files } else { $sourceFiles }

    $changed = @($expected.Keys | Where-Object { $current.ContainsKey($_) -and $current[$_] -ne $expected[$_] } | Sort-Object)
    $added = @($current.Keys | Where-Object { -not $expected.ContainsKey($_) } | Sort-Object)
    $missing = @($expected.Keys | Where-Object { -not $current.ContainsKey($_) } | Sort-Object)
    if (-not ($changed.Count + $added.Count + $missing.Count)) { return $true }

    Write-Host ""
    if ($record) {
        Write-Warning "$share was changed since the last deploy."
    } else {
        Write-Warning "$share has no record of a deploy yet, and differs from what is about to be copied. This can also be an older version."
    }
    foreach ($path in $changed) { Write-Host "   changed: $path" }
    foreach ($path in $added) { Write-Host "   added:   $path (the deploy deletes it)" }
    foreach ($path in $missing) { Write-Host "   removed: $path (the deploy restores it)" }

    if ($changed.Count) {
        $export = if ($record) { Export-Commit $record.commit } else { $null }
        $baseline = if ($export) { Join-Path $export "custom_components\plant_manager" } else { "$source" }
        if ($record -and -not $export) {
            Write-Host "`nThe deployed commit isn't available, so this compares with what is about to be copied:"
        }
        foreach ($path in $changed) {
            Write-Host ""
            git -C $repo --no-pager diff --no-index --no-color -- (Join-Path $baseline $path) (Join-Path $dest $path) | Write-Host
        }
        if ($export) { Remove-Item $export -Recurse -Force -ErrorAction SilentlyContinue }
    }

    Write-Host ""
    try {
        $answer = Read-Host "Overwrite these on $share? Type yes to continue, anything else skips this instance"
    } catch {
        Write-Warning "Can't ask for confirmation here, so this instance is skipped."
        return $false
    }
    return $answer -eq "yes"
}

if (-not $Targets) {
    if (-not (Test-Path $targetsFile)) {
        Write-Error "No targets: pass them as arguments or list them in $targetsFile"
    }
    $Targets = Get-Content $targetsFile | ForEach-Object { $_.Trim() } |
        Where-Object { $_ -and -not $_.StartsWith("#") }
}

$version = (Get-Content (Join-Path $source "manifest.json") -Raw | ConvertFrom-Json).version
Write-Host "Plant Manager $version"

$commit = Get-CleanCommit
$failed = @()
foreach ($share in $Targets) {
    $dest = Join-Path $share "custom_components\plant_manager"
    Write-Host "`n-> $share"
    if (-not (Test-Path (Join-Path $share "custom_components"))) {
        Write-Warning "Not reachable, or no custom_components folder. Connect first: net use $share /user:<samba-user> *"
        $failed += $share
        continue
    }
    $before = Get-Snapshot $dest
    if (-not (Confirm-Target $share $dest $before)) {
        Write-Host "   skipped, nothing was changed"
        $failed += $share
        continue
    }
    robocopy $source $dest /MIR /XD __pycache__ /XF $recordName /NP /NDL /NFL /NJH /NJS | Out-Null
    # robocopy: 0-7 is success (1 = files copied), 8 and up is an error.
    if ($LASTEXITCODE -ge 8) {
        Write-Warning "Copy failed (robocopy exit code $LASTEXITCODE)"
        $failed += $share
        continue
    }
    # Not from robocopy's code: the record counts as an extra file there, on every deploy.
    $after = Get-Snapshot $dest
    $same = $before.Count -eq $after.Count -and -not ($after.Keys | Where-Object { $before[$_] -ne $after[$_] })
    if ($same) {
        Write-Host "   already up to date"
    } else {
        Write-Host "   updated, restart Home Assistant to load it"
    }
    try {
        @{ version = $version; commit = $commit; files = $after } | ConvertTo-Json -Depth 3 |
            Set-Content (Join-Path $dest $recordName) -Encoding UTF8
    } catch {
        Write-Warning "Copied, but could not save the record of this deploy: $_"
        $failed += $share
    }
}

if ($failed) {
    Write-Host "`nNot deployed: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
# Otherwise robocopy's last exit code (1 = files copied) would be the script's.
exit 0
