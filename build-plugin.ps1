<#
.SYNOPSIS
    Builds the GGU QGIS Plugin ZIP package.

.DESCRIPTION
    Creates a ZIP file from the ggu-qgis-plugin folder that can be installed
    in QGIS via "Install from ZIP". Optionally copies the ZIP to the
    ggu-connect-app misc folder for inclusion in the installer.

.PARAMETER OutputPath
    Output path for the ZIP file. Defaults to .\ggu-qgis-plugin.zip

.PARAMETER CopyToConnectApp
    If specified, copies the ZIP to the ggu-connect-app misc folder
    for inclusion in the GGU-CONNECT installer.

.EXAMPLE
    .\build-plugin.ps1

.EXAMPLE
    .\build-plugin.ps1 -CopyToConnectApp
#>

param(
    [string]$OutputPath = "",
    [switch]$CopyToConnectApp
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PluginDir = Join-Path $ScriptDir "ggu-qgis-plugin"

if (-not (Test-Path $PluginDir)) {
    Write-Error "Plugin directory not found: $PluginDir"
    exit 1
}

# Default output path
if (-not $OutputPath) {
    $OutputPath = Join-Path $ScriptDir "ggu-qgis-plugin.zip"
}

# Remove existing ZIP
if (Test-Path $OutputPath) {
    Remove-Item $OutputPath -Force
}

# QGIS requires the ZIP to contain the plugin folder as root entry.
# Compress-Archive -Path "folder\*" would zip contents without the folder.
# We must zip from the parent directory with the folder name as the path.
Push-Location $ScriptDir
try {
    Compress-Archive -Path "ggu-qgis-plugin" -DestinationPath $OutputPath -CompressionLevel Optimal
} finally {
    Pop-Location
}

if (-not (Test-Path $OutputPath)) {
    Write-Error "Failed to create ZIP: $OutputPath"
    exit 1
}

$zipInfo = Get-Item $OutputPath
Write-Host "Created: $($zipInfo.FullName) ($([math]::Round($zipInfo.Length / 1KB, 1)) KB)"

# Verify ZIP structure - root entry must be ggu-qgis-plugin/
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($OutputPath)
$firstEntry = $zip.Entries[0].FullName
$zip.Dispose()

if (-not $firstEntry.StartsWith("ggu-qgis-plugin/")) {
    Write-Error "Invalid ZIP structure: root entry is '$firstEntry' (expected 'ggu-qgis-plugin/...')"
    exit 1
}
Write-Host "ZIP structure verified: root folder is 'ggu-qgis-plugin/'"

# Copy to ggu-connect-app misc folder if requested
if ($CopyToConnectApp) {
    $reposBase = $env:GGUReposBaseDir
    if (-not $reposBase) {
        $reposBase = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $ScriptDir))
    }

    $connectAppMisc = Join-Path $reposBase "apps-desktop\ggu-connect-app\misc"

    if (-not (Test-Path $connectAppMisc)) {
        New-Item -ItemType Directory -Path $connectAppMisc -Force | Out-Null
    }

    $targetPath = Join-Path $connectAppMisc "GGU-QGIS-Plugin.zip"
    Copy-Item $OutputPath $targetPath -Force
    Write-Host "Copied to: $targetPath"
}
