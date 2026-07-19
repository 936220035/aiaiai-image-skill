#!/usr/bin/env bash
set -euo pipefail

TARGET="codex"
CODEX_SKILL_ROOT=""
CLAUDE_SKILL_ROOT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="${2:-codex}"; shift 2 ;;
    --codex-skill-root) CODEX_SKILL_ROOT="${2:-}"; shift 2 ;;
    --claude-skill-root) CLAUDE_SKILL_ROOT="${2:-}"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
case "$TARGET" in
  codex|claude|both) ;;
  *) echo "target must be codex, claude, or both" >&2; exit 2 ;;
esac

command -v python3 >/dev/null || { echo "Python 3 is required." >&2; exit 1; }
command -v curl >/dev/null || { echo "curl is required." >&2; exit 1; }
command -v unzip >/dev/null || { echo "unzip is required." >&2; exit 1; }

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
curl -fsSL "https://github.com/936220035/aiaiai-image-skill/archive/refs/heads/main.zip" -o "$TMP_DIR/repo.zip"
unzip -q "$TMP_DIR/repo.zip" -d "$TMP_DIR/extract"
REPO_ROOT="$(find "$TMP_DIR/extract" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
ARGS=("$REPO_ROOT/scripts/install_local.py" --target "$TARGET" --mode copy --force)
[[ -n "$CODEX_SKILL_ROOT" ]] && ARGS+=(--codex-skill-root "$CODEX_SKILL_ROOT")
[[ -n "$CLAUDE_SKILL_ROOT" ]] && ARGS+=(--claude-skill-root "$CLAUDE_SKILL_ROOT")
python3 "${ARGS[@]}"
echo "Installed. Restart Codex or Claude Code, then run configure to save your API key."
