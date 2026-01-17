# Extract changelog section for a specific version from CHANGELOG.md
#
# Usage: .\Extract-Changelog.ps1 -Version <version> [-ChangelogFile <path>]
# Example: .\Extract-Changelog.ps1 -Version v1.0.0
#          .\Extract-Changelog.ps1 -Version v1.0.0 -ChangelogFile .\CHANGELOG.md

param(
    [Parameter(Mandatory=$true)]
    [string]$Version,
    
    [Parameter(Mandatory=$false)]
    [string]$ChangelogFile = "CHANGELOG.md"
)

$ErrorActionPreference = "Stop"

# Validate changelog file exists
if (-not (Test-Path $ChangelogFile)) {
    Write-Error "Changelog file not found: $ChangelogFile"
    exit 1
}

# Read the entire changelog
$content = Get-Content $ChangelogFile -Raw

# Try to extract the section for this version
# Pattern: from "## 📦 Release X.Y.Z" to next "---"
# Using text pattern to avoid encoding issues with emoji
$pattern = "(?ms)^## .+ Release $([regex]::Escape($Version)).*?(?=^---)"
$match = [regex]::Match($content, $pattern)

if ($match.Success) {
    $changelog = $match.Value.TrimEnd()
} else {
    # Fallback: Try to get the first release section
    $fallbackPattern = "(?ms)^## .+ Release.*?(?=^---)"
    $fallbackMatch = [regex]::Match($content, $fallbackPattern)
    
    if ($fallbackMatch.Success) {
        $changelog = $fallbackMatch.Value.TrimEnd()
        Write-Warning "Could not find version $Version, using first release section"
    } else {
        Write-Warning "Could not extract changelog for version $Version"
        $changelog = "No changelog available for this version."
    }
}

# Output to stdout
Write-Output $changelog
