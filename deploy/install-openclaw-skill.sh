#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
SOLUTION_DIR="$(cd -- "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd -P)"
SOURCE_DIR="$SOLUTION_DIR/openclaw-skill/stt-queue"

TARGETS=(
  "$HOME/.openclaw/workspace/skills/stt-queue"
  "$HOME/.openclaw/skills/stt-queue"
)

for target in "${TARGETS[@]}"; do
  mkdir -p "$(dirname "$target")"
  rm -rf "$target"
  rsync -a "$SOURCE_DIR/" "$target/"
done

chmod +x "$HOME/.openclaw/workspace/skills/stt-queue"/scripts/*.sh
chmod +x "$HOME/.openclaw/skills/stt-queue"/scripts/*.sh

echo "Installed stt-queue skill to:"
printf '  %s\n' "${TARGETS[@]}"

if command -v openclaw >/dev/null 2>&1; then
  openclaw skills info stt-queue --agent main || true
fi
