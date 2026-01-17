# Create GitHub release with artifacts
#
# Usage: .\Create-Release.ps1 -Version <version> -ChangelogContent <content> [-ArtifactsDir <path>]
# Example: .\Create-Release.ps1 -Version v1.0.0 -ChangelogContent "Release notes here"
#
# Environment variables:
#   GITHUB_TOKEN or GH_TOKEN: GitHub token for authentication
#
# Expected artifact structure:
#   artifacts/
#   └── releases/
#       └── er-save-manager-<version>-windows.zip

param(
    [Parameter(Mandatory=$true)]
    [string]$Version,
    
    [Parameter(Mandatory=$true)]
    [string]$ChangelogContent,
    
    [Parameter(Mandatory=$false)]
    [string]$ArtifactsDir = "artifacts"
)

$ErrorActionPreference = "Stop"

# Strip 'v' prefix for file naming
$VersionNoV = $Version.TrimStart("v")

# Get commit SHA for tagging
$Commit = git rev-parse --verify HEAD
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to get commit SHA"
    exit 1
}

# Delete existing release if it exists (draft or otherwise)
Write-Host "Checking for existing release $Version..."
gh release view $Version 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Deleting existing release $Version..."
    gh release delete $Version --yes
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Failed to delete existing release, continuing anyway..."
    }
}

# Build artifact list
$Artifacts = @()

# Add Windows zip if exists
$WindowsZip = Join-Path $ArtifactsDir "releases" "er-save-manager-$VersionNoV-windows.zip"
if (Test-Path $WindowsZip) {
    $Artifacts += $WindowsZip
    Write-Host "✅ Found Windows artifact: $WindowsZip"
} else {
    Write-Warning "Windows artifact not found at $WindowsZip"
}

if ($Artifacts.Count -eq 0) {
    Write-Error "No artifacts found to upload"
    exit 1
}

# Save changelog to temp file (to avoid issues with special characters)
$TempChangelogFile = [System.IO.Path]::GetTempFileName()
Set-Content -Path $TempChangelogFile -Value $ChangelogContent -Encoding UTF8

try {
    # Create the draft release
    Write-Host "Creating draft release $Version with $($Artifacts.Count) artifact(s)..."
    
    $ghArgs = @(
        "release", "create",
        "--target", $Commit,
        "--title", $Version,
        "--notes-file", $TempChangelogFile,
        "--draft",
        $Version
    ) + $Artifacts
    
    & gh @ghArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create release"
        exit 1
    }
    
    Write-Host "✅ Release $Version created successfully!"
} finally {
    # Clean up temp file
    if (Test-Path $TempChangelogFile) {
        Remove-Item $TempChangelogFile -Force
    }
}
