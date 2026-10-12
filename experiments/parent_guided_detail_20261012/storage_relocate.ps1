param([switch]$Execute)
$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath('C:\Users\USER\CHESHIRE').TrimEnd('\')
$dataRoot = [IO.Path]::GetFullPath('E:\CHESHIRE_DATA').TrimEnd('\')
$receiptRoot = Join-Path $dataRoot 'storage_migration_20261012_parent_guided'
$jobs = @(
    @('C:\Users\USER\CHESHIRE\worktrees\parent-guided-detail-20261012\output\parent_guided_detail_20261012_trial02', 'E:\CHESHIRE_DATA\experiments\parent_guided_detail_20261012\trial02'),
    @('C:\Users\USER\CHESHIRE\worktrees\fold-visible-gate-20261012\output\fold_visible_gate_20261012', 'E:\CHESHIRE_DATA\archives\fold_visible_gate_20261012_output'),
    @('C:\Users\USER\CHESHIRE\output\task14', 'E:\CHESHIRE_DATA\archives\cheshire_root_output_20261012\task14'),
    @('C:\Users\USER\CHESHIRE\output\task15', 'E:\CHESHIRE_DATA\archives\cheshire_root_output_20261012\task15'),
    @('C:\Users\USER\CHESHIRE\output\task16', 'E:\CHESHIRE_DATA\archives\cheshire_root_output_20261012\task16'),
    @('C:\Users\USER\CHESHIRE\output\task17', 'E:\CHESHIRE_DATA\archives\cheshire_root_output_20261012\task17'),
    @('C:\Users\USER\CHESHIRE\output\task18', 'E:\CHESHIRE_DATA\archives\cheshire_root_output_20261012\task18'),
    @('C:\Users\USER\CHESHIRE\output\task19', 'E:\CHESHIRE_DATA\archives\cheshire_root_output_20261012\task19'),
    @('C:\Users\USER\CHESHIRE\output\presentation_20261012_expanded', 'E:\CHESHIRE_DATA\archives\cheshire_root_output_20261012\presentation_20261012_expanded'),
    @('C:\Users\USER\CHESHIRE\output\presentation_20261012_revised', 'E:\CHESHIRE_DATA\archives\cheshire_root_output_20261012\presentation_20261012_revised'),
    @('C:\Users\USER\CHESHIRE\scratch\connected_tissue_20261010', 'E:\CHESHIRE_DATA\archives\scratch_connected_tissue_20261010'),
    @('C:\Users\USER\CHESHIRE\scratch\column_reference_20261010', 'E:\CHESHIRE_DATA\archives\scratch_column_reference_20261010')
)
function Check-Paths($source, $destination) {
    if (-not $source.StartsWith($workspace + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Source outside workspace.' }
    if (-not $destination.StartsWith($dataRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Destination outside CHESHIRE_DATA.' }
    foreach ($part in $source.Split('\')) {
        if ($part -in @('.git', '.venv', '.agents', '.codex')) { throw 'Protected source.' }
    }
}
foreach ($job in $jobs) {
    $source = [IO.Path]::GetFullPath($job[0]).TrimEnd('\')
    $destination = [IO.Path]::GetFullPath($job[1]).TrimEnd('\')
    Check-Paths $source $destination
    $item = Get-Item -LiteralPath $source -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Source already a link: $source" }
    if (Test-Path -LiteralPath $destination) { throw "Destination already exists: $destination" }
    $nestedLinks = @(Get-ChildItem -LiteralPath $source -Recurse -Force | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint })
    if ($nestedLinks.Count) { throw "Nested reparse point in $source" }
    Write-Output "PLAN $source -> $destination"
}
if (-not $Execute) { return }
if (Test-Path -LiteralPath $receiptRoot) { throw 'Migration receipt already exists; inspect before retrying.' }
New-Item -ItemType Directory -Path $receiptRoot | Out-Null
$summary = @()
$index = 0
foreach ($job in $jobs) {
    $index++
    $source = [IO.Path]::GetFullPath($job[0]).TrimEnd('\')
    $destination = [IO.Path]::GetFullPath($job[1]).TrimEnd('\')
    Check-Paths $source $destination
    Write-Output "HASH_SOURCE $index $source"
    $files = @(Get-ChildItem -LiteralPath $source -File -Recurse -Force)
    $records = @($files | ForEach-Object {
        [pscustomobject]@{Relative=$_.FullName.Substring($source.Length+1); Length=$_.Length; SHA256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash}
    })
    $manifest = Join-Path $receiptRoot ("{0:D2}_files.json" -f $index)
    ConvertTo-Json -InputObject $records -Depth 4 | Set-Content -LiteralPath $manifest -Encoding UTF8
    $parent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    Write-Output "COPY $index $($records.Count) files"
    Copy-Item -LiteralPath $source -Destination $destination -Recurse
    $copied = @(Get-ChildItem -LiteralPath $destination -File -Recurse -Force)
    if ($copied.Count -ne $records.Count) { throw 'Copied file count differs; source retained.' }
    foreach ($record in $records) {
        $targetFile = Join-Path $destination $record.Relative
        if ((Get-Item -LiteralPath $targetFile).Length -ne $record.Length -or (Get-FileHash -LiteralPath $targetFile -Algorithm SHA256).Hash -ne $record.SHA256) { throw "Copy mismatch; source retained: $targetFile" }
        # Recheck source immediately before retirement, after the copy.
        $sourceFile = Join-Path $source $record.Relative
        if ((Get-Item -LiteralPath $sourceFile).Length -ne $record.Length -or (Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash -ne $record.SHA256) { throw "Source changed; source retained: $sourceFile" }
    }
    if (@(Get-ChildItem -LiteralPath $source -File -Recurse -Force).Count -ne $records.Count) { throw 'Source inventory changed; source retained.' }
    Write-Output "VERIFIED $index"
    # The absolute paths above are fixed, bounded and checked again before deletion.
    Check-Paths $source $destination
    if ((Get-Item -LiteralPath $source -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Source became a link.' }
    Remove-Item -LiteralPath $source -Recurse -Force
    New-Item -ItemType Junction -Path $source -Value $destination | Out-Null
    $bytes = ($records | Measure-Object Length -Sum).Sum
    $summary += [pscustomobject]@{Source=$source;Destination=$destination;Files=$records.Count;Bytes=$bytes;SHA256Verified=$true;SourceReplacedByJunction=$true}
    ConvertTo-Json -InputObject $summary -Depth 5 | Set-Content -LiteralPath (Join-Path $receiptRoot 'SUMMARY.json') -Encoding UTF8
    Write-Output "MIGRATED $index $bytes bytes"
}
Write-Output "MIGRATION_COMPLETE $receiptRoot"
