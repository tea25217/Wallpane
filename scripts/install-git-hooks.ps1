# Enable repo-local Git hooks (secret / personal-data scan).
# Run once after clone:  powershell -File scripts/install-git-hooks.ps1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (git rev-parse --show-toplevel).Trim()
if (-not $repoRoot) {
  throw "Run this from inside the Wallpane git repository."
}

Set-Location $repoRoot
git config core.hooksPath .githooks
Write-Host "Enabled local secret scan hooks (core.hooksPath=.githooks)."
Write-Host "Optional: install Betterleaks for the full rule set — https://github.com/betterleaks/betterleaks"
