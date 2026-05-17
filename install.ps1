param(
    [switch]$AllUsers
)

$ErrorActionPreference = "Stop"

$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

if ($AllUsers) {
    $scope = "Machine"
    $scopeLabel = "all users"
    $requiresAdmin = $true
} else {
    $scope = "User"
    $scopeLabel = "current user"
    $requiresAdmin = $false
}

# Check admin if needed
if ($requiresAdmin) {
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Write-Host "✗ Administrator privileges required for -AllUsers. Run PowerShell as Administrator." -ForegroundColor Red
        exit 1
    }
}

Write-Host "  › Installing mmm for $scopeLabel..." -ForegroundColor Cyan

$oldPath = [Environment]::GetEnvironmentVariable("Path", $scope)
$newPath = if ($oldPath) { "$oldPath;$repoDir" } else { $repoDir }

# Avoid duplicates
if ($oldPath -split ";" -contains $repoDir) {
    Write-Host "  ✔ Already in PATH. Updating..." -ForegroundColor Green
}

[Environment]::SetEnvironmentVariable("Path", $newPath, $scope)

Write-Host "  ✔ Added $repoDir to PATH ($scopeLabel)" -ForegroundColor Green
Write-Host ""
Write-Host "  [1mNext steps:[0m"
Write-Host "  1. Restart your terminal (or run:  `$env:Path = [Environment]::GetEnvironmentVariable('Path','$scope')  + ';' + `$env:Path)"
Write-Host "  2. Try:  mmm --help"
Write-Host ""
