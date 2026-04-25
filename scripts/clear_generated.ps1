<#
.SYNOPSIS
Deletes generated conversion-eval folders.

.DESCRIPTION
Removes the project-local intermediate, output, and reports folders.
The target folders are fixed intentionally so the script cannot be pointed at
an arbitrary path by accident. Use -WhatIf to preview the deletion.

.PARAMETER KeepDirectories
Recreates empty intermediate, output, and reports folders after deletion.

.EXAMPLE
.\scripts\clear_generated.ps1 -WhatIf

.EXAMPLE
.\scripts\clear_generated.ps1
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch]$KeepDirectories
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = if ($PSCommandPath) { $PSCommandPath } else { $MyInvocation.MyCommand.Path }
$scriptDir = Split-Path -Parent $scriptPath
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $scriptDir "..")).Path
$targetNames = @("intermediate", "output", "reports")

function Assert-ProjectChildPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,

        [Parameter(Mandatory = $true)]
        [string]$Candidate
    )

    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd("\", "/")
    $candidateFull = [System.IO.Path]::GetFullPath($Candidate).TrimEnd("\", "/")
    $rootWithSeparator = $rootFull + [System.IO.Path]::DirectorySeparatorChar

    if (-not $candidateFull.StartsWith($rootWithSeparator, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a path outside the project root: $candidateFull"
    }
}

foreach ($name in $targetNames) {
    $target = Join-Path $projectRoot $name
    if (-not (Test-Path -LiteralPath $target)) {
        Write-Host "Skip missing folder: $target"
        continue
    }

    $resolvedTarget = (Resolve-Path -LiteralPath $target).Path
    Assert-ProjectChildPath -Root $projectRoot -Candidate $resolvedTarget

    if ($PSCmdlet.ShouldProcess($resolvedTarget, "Remove generated folder")) {
        Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
        Write-Host "Removed: $resolvedTarget"

        if ($KeepDirectories) {
            New-Item -ItemType Directory -Path $resolvedTarget -Force | Out-Null
            Write-Host "Recreated: $resolvedTarget"
        }
    }
}
