#!/usr/bin/env bash
# Scan commits or the working tree for secrets and obvious personal data.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="$ROOT/.betterleaks.toml"
ZERO="0000000000000000000000000000000000000000"
PATTERN='-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}'
FORBIDDEN_PATH='(^|/)\.env($|\.)|(^|/)(credentials|secrets)\.json$|\.(pem|p12|pfx)$|(^|/)id_(rsa|ed25519)$'

scan_diff() {
  local hit=0
  local files

  files="$(git -C "$ROOT" diff --name-only --diff-filter=ACMR "${@}" || true)"
  if echo "$files" | grep -E "$FORBIDDEN_PATH" >/dev/null; then
    echo "Refusing credential or key files:" >&2
    echo "$files" | grep -E "$FORBIDDEN_PATH" >&2
    hit=1
  fi

  if git -C "$ROOT" diff --no-color -U0 "${@}" | grep -E "$PATTERN" >/dev/null; then
    echo "High-signal secret pattern found in diff:" >&2
    git -C "$ROOT" diff --no-color -U0 "${@}" | grep -E "$PATTERN" >&2 || true
    hit=1
  fi

  return "$hit"
}

scan_tree() {
  local hit=0
  if git -C "$ROOT" ls-files | grep -E "$FORBIDDEN_PATH" >/dev/null; then
    echo "Refusing credential or key files:" >&2
    git -C "$ROOT" ls-files | grep -E "$FORBIDDEN_PATH" >&2
    hit=1
  fi
  if git -C "$ROOT" grep -nE -I -e "$PATTERN" >/dev/null; then
    echo "High-signal secret pattern found:" >&2
    git -C "$ROOT" grep -nE -I -e "$PATTERN" >&2 || true
    hit=1
  fi
  return "$hit"
}

fallback_notice() {
  echo "betterleaks is not installed; running the built-in high-signal fallback." >&2
  echo "Install from https://github.com/betterleaks/betterleaks for the full rule set." >&2
}

run_betterleaks() {
  betterleaks git "$ROOT" -v --redact --config "$CONFIG" --exit-code 1 "$@"
}

mode="${1:-all}"

case "$mode" in
  --ci|all)
    if command -v betterleaks >/dev/null 2>&1; then
      run_betterleaks
    else
      fallback_notice
      scan_tree
    fi
    ;;
  --staged)
    if command -v betterleaks >/dev/null 2>&1; then
      run_betterleaks --pre-commit --staged
    else
      fallback_notice
      scan_diff --cached
    fi
    ;;
  --push)
    failed=0
    while read -r _local_ref local_sha _remote_ref remote_sha; do
      [[ -z "${local_sha:-}" ]] && continue
      if [[ "$local_sha" == "$ZERO" ]]; then
        continue
      fi
      if command -v betterleaks >/dev/null 2>&1; then
        if [[ "$remote_sha" == "$ZERO" ]]; then
          if ! run_betterleaks --log-opts="$local_sha"; then
            failed=1
          fi
        else
          if ! run_betterleaks --log-opts="$remote_sha..$local_sha"; then
            failed=1
          fi
        fi
      else
        fallback_notice
        if [[ "$remote_sha" == "$ZERO" ]]; then
          if ! scan_tree; then
            failed=1
          fi
        else
          if ! scan_diff "$remote_sha..$local_sha"; then
            failed=1
          fi
        fi
      fi
    done
    exit "$failed"
    ;;
  *)
    echo "Usage: $0 [--ci|--staged|--push]" >&2
    exit 2
    ;;
esac
