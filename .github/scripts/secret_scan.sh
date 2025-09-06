#!/usr/bin/env bash
set -euo pipefail

violations=0

echo "::group::Secret scan"

# Fail if tracked .env or .venv exist
while IFS= read -r f; do
  if [[ "$f" =~ (^|/)[.]env($|[./]) ]]; then
    echo "Secret scan: tracked .env file found: $f" >&2
    violations=1
  fi
  if [[ "$f" =~ (^|/)[.]venv(/|$) ]]; then
    echo "Secret scan: tracked .venv content found: $f" >&2
    violations=1
  fi
done < <(git ls-files)

# File patterns to scan (skip docs and hooks and CI files won't be skipped here)
should_scan() {
  local p="$1"
  case "$p" in
    .githooks/*) return 1 ;;
    *.md|*.rst|*.txt|LICENSE|LICENSE.*) return 1 ;;
  esac
  case "$p" in
    *.py|*.js|*.jsx|*.ts|*.tsx|*.json|*.yml|*.yaml|*.env|*.ini|*.toml|*.cfg|*.conf|*.properties|*.sh|*.bash|*.zsh) return 0 ;;
    *) return 1 ;;
  esac
}

scan_file() {
  local file="$1"
  # Ignore binary
  local content
  content=$(grep -I -n -H "^" "$file" || true)
  [[ -z "$content" ]] && return 0

  if grep -I -E -n 'sk-[A-Za-z0-9]{20,}' "$file" >/dev/null; then
    echo "Secret scan: $file: possible OpenAI secret detected (sk-...)." >&2
    violations=1
  fi
  if grep -I -E -n 'AIza[0-9A-Za-z\-_]{35}' "$file" >/dev/null; then
    echo "Secret scan: $file: possible Google API key detected." >&2
    violations=1
  fi
  if grep -I -E -n 'xox[baprs]-[A-Za-z0-9-]{10,}' "$file" >/dev/null; then
    echo "Secret scan: $file: possible Slack token detected." >&2
    violations=1
  fi
  if grep -I -E -n 'OPENAI_API_KEY\s*[:=]' "$file" >/dev/null; then
    echo "Secret scan: $file: OPENAI_API_KEY appears assigned; do not commit secrets." >&2
    violations=1
  fi
  if grep -I -E -in '(^|[^A-Za-z])(api[_-]?key|secret|token)[^\n]{0,40}[:=][^\n]{0,128}' "$file" >/dev/null; then
    echo "Secret scan: $file: possible credential assignment detected (api key/secret/token)." >&2
    violations=1
  fi
}

while IFS= read -r f; do
  if should_scan "$f"; then
    scan_file "$f"
  fi
done < <(git ls-files)

echo "::endgroup::"

if [[ "$violations" -ne 0 ]]; then
  echo "Secret scan: violations found. Failing CI." >&2
  exit 1
fi
echo "Secret scan: no violations found."

