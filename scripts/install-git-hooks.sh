#!/usr/bin/env bash
# Enable repo-local Git hooks (secret / personal-data scan).
# Run once after clone:  bash scripts/install-git-hooks.sh
set -euo pipefail
repo_root="$(git rev-parse --show-toplevel)"
git -C "$repo_root" config core.hooksPath .githooks
echo "Enabled local secret scan hooks (core.hooksPath=.githooks)."
echo "Optional: install Betterleaks for the full rule set — https://github.com/betterleaks/betterleaks"
