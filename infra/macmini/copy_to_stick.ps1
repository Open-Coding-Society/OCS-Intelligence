# Copy the FIX stick contents (make_stick.py's output) onto the FIX USB stick, then eject it.
# Writes to one drive only, and only if Windows reports ALL of: label FIX, removable,
# USB, not a boot/system disk, disk size <= -MaxGB. Anything else: it stops, changing nothing.
#
# From WSL, in the repo, after make_stick.py (default output infra/macmini/build/stick):
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(wslpath -w infra/macmini/copy_to_stick.ps1)" \
#       -Source "$(wslpath -w infra/macmini/build/stick)" -Letter D [-DryRun]
# -Letter picks one stick (labelled FIX or unlabelled; it gets labelled FIX). Without it,
# the one stick already labelled FIX. -DryRun checks and lists, changing nothing.
# Guide: docs/operations/set-up-mac-minis.md
param(
    [Parameter(Mandatory)][string]$Source,   # make_stick.py's output; never on C:
    [int]$MaxGB = 10,
    [ValidatePattern('^[D-Zd-z]$')][string]$Letter = '',   # never A-C
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
function Stop-Here($msg) { Write-Host "STOP: $msg Nothing was changed."; exit 1 }

if ($Source -match '^(?i)c:') { Stop-Here "-Source is on C:, which is off limits; use the repo's build folder." }
if (-not (Test-Path "$Source\f") -or -not (Test-Path "$Source\ocs\SHA256SUMS")) {
    Stop-Here "$Source doesn't look like make_stick.py output (no f or ocs\SHA256SUMS)."
}

# The target: the one volume labelled FIX, or -Letter X (labelled FIX or unlabelled,
# and then labelled FIX once it passes the checks below). Two or more sticks: one -Letter at a time.
if ($Letter) {
    $vols = @(Get-Volume -DriveLetter $Letter -ErrorAction SilentlyContinue |
              Where-Object { $_.FileSystemLabel -in @('FIX', '') })
    if ($vols.Count -eq 0) { Stop-Here "drive ${Letter}: isn't there, or has a label other than FIX or none." }
} else {
    $vols = @(Get-Volume | Where-Object { $_.FileSystemLabel -eq 'FIX' -and $_.DriveLetter })
}
$found = @($vols | ForEach-Object {
    $disk = Get-Partition -DriveLetter $_.DriveLetter | Get-Disk
    [pscustomobject]@{
        Letter = [string]$_.DriveLetter; Type = [string]$_.DriveType; FS = $_.FileSystem
        Bus = [string]$disk.BusType; Boot = $disk.IsBoot; System = $disk.IsSystem
        DiskGB = [math]::Round($disk.Size / 1GB, 1); Model = $disk.FriendlyName
    }
})
if ($found.Count -eq 0) { Stop-Here "no drive labelled FIX is plugged in." }
if ($found.Count -gt 1) { Stop-Here "$($found.Count) drives are labelled FIX; plug in only one." }
$s = $found[0]
Write-Host ("Found {0}: {1}, {2}, bus {3}, disk {4} GB ({5}), boot={6} system={7}" -f `
    $s.Letter, $s.FS, $s.Type, $s.Bus, $s.DiskGB, $s.Model, $s.Boot, $s.System)
$why = @()
if ($s.Type -ne 'Removable') { $why += "not removable" }
if ($s.Bus -ne 'USB') { $why += "not on USB" }
if ($s.Boot -or $s.System) { $why += "a boot/system disk" }
if ($s.DiskGB -gt $MaxGB) { $why += "bigger than $MaxGB GB" }
if ($s.Letter -eq ($env:SystemDrive).Substring(0, 1)) { $why += "the Windows drive" }
if ($why) { Stop-Here ("{0}: is {1}." -f $s.Letter, ($why -join ', ')) }

$root = "$($s.Letter):\"
$label = (Get-Volume -DriveLetter $s.Letter).FileSystemLabel
if ($label -ne 'FIX') {
    if ($DryRun) {
        Write-Host "DRY RUN. Would label $($s.Letter): FIX (the FIX stick's f looks for that label)."
    } else {
        # Rename only (no format). Set-Volume can need admin; Explorer's rename doesn't.
        try { Set-Volume -DriveLetter $s.Letter -NewFileSystemLabel 'FIX' -ErrorAction Stop }
        catch { (New-Object -ComObject Shell.Application).NameSpace(17).ParseName("$($s.Letter):").Name = 'FIX' }
        Start-Sleep -Seconds 1
        if ((Get-Volume -DriveLetter $s.Letter).FileSystemLabel -ne 'FIX') { Stop-Here "couldn't label $($s.Letter): FIX." }
        Write-Host "Labelled $($s.Letter): FIX."
    }
}
$old =@(Get-ChildItem -LiteralPath $root -Force | Where-Object { $_.Name -ne 'System Volume Information' })
if ($DryRun) {
    Write-Host "DRY RUN. Would delete on ${root}: $(if ($old) { ($old.Name -join ', ') } else { '(nothing)' })"
    Write-Host "Then copy $Source -> $root, verify every file's SHA256, and eject."
    exit 0
}

Write-Host "Deleting $($old.Count) item(s) on $root ..."
$old | Remove-Item -Recurse -Force
Write-Host "Copying $Source -> $root ..."
Copy-Item -Path "$Source\*" -Destination $root -Recurse -Force

$bad = @()
$files = @(Get-ChildItem -LiteralPath $Source -Recurse -File)
foreach ($f in $files) {
    $rel = $f.FullName.Substring($Source.Length).TrimStart('\')
    $dst = Join-Path $root $rel
    if (-not (Test-Path -LiteralPath $dst) -or
        (Get-FileHash -LiteralPath $f.FullName).Hash -ne (Get-FileHash -LiteralPath $dst).Hash) { $bad += $rel }
}
if ($bad) { Write-Host "FAILED: $($bad.Count) file(s) differ on the stick: $($bad -join ', '). Rerun."; exit 1 }
Write-Host "Verified: all $($files.Count) files match."

# Eject, so Windows has finished writing before the stick is pulled (2026-11-17: a
# stick pulled early delivered a corrupted uv).
(New-Object -ComObject Shell.Application).Namespace(17).ParseName("$($s.Letter):").InvokeVerb("Eject")
# Once ejected, the letter can linger in Get-Volume, but the root is gone ("No Media").
# Mid-eject, the root can answer "access denied": count that as not gone yet.
function Test-Mounted { try { Test-Path -LiteralPath $root -ErrorAction Stop } catch { $true } }
for ($i = 0; $i -lt 20 -and (Test-Mounted); $i++) { Start-Sleep -Milliseconds 500 }
if (Test-Mounted) {
    Write-Host "Copied and verified, but Windows didn't eject it: eject $($s.Letter): yourself before pulling it."
} else {
    Write-Host "Ejected. Safe to pull the stick."
}
