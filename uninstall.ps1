param(
    [switch]$AllUsers
)

$ErrorActionPreference = "Stop"

$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

if ($AllUsers) {
    $scope = "Machine"
    $scopeLabel = "all users"
} else {
    $scope = "User"
    $scopeLabel = "current user"
}

Write-Host "  › Uninstalling mmm for $scopeLabel..." -ForegroundColor Cyan

$oldPath = [Environment]::GetEnvironmentVariable("Path", $scope)
if (-not $oldPath) {
    Write-Host "  ⊘ mmm not found in PATH" -ForegroundColor Yellow
    exit 0
}

$entries = $oldPath -split ";"
$newEntries = $entries | Where-Object { $_ -ne $repoDir }
$newPath = $newEntries -join ";"

if ($newPath -eq $oldPath) {
    Write-Host "  ⊘ mmm not found in PATH" -ForegroundColor Yellow
    exit 0
}

[Environment]::SetEnvironmentVariable("Path", $newPath, $scope)
Write-Host "  ✔ Removed $repoDir from PATH ($scopeLabel)" -ForegroundColor Green
Write-Host ""
Write-Host "  Restart your terminal to apply changes."
Write-Host ""
