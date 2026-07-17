#!/usr/bin/env bash
# Link every skill in this repo into the local agent harnesses.
#
#   repo/skills/<name>  <-  ~/.agents/skills/<name>  <-  ~/.claude/skills/<name>
#
# ~/.agents/skills is the cross-agent location (Claude Code, Codex, ...); ~/.claude/skills
# holds a relative symlink pointing at it, matching how installed skills already work here.
# Everything resolves back to this repo, so edits are live and every change is a real diff.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTS_DIR="$HOME/.agents/skills"
CLAUDE_DIR="$HOME/.claude/skills"

mkdir -p "$AGENTS_DIR" "$CLAUDE_DIR"

# Refuse to clobber a real directory: that would be someone's un-committed skill.
# `ln -sfn` would silently nest the link *inside* it rather than replace it.
check_free() {
  local path="$1"
  if [ -e "$path" ] && [ ! -L "$path" ]; then
    echo "error: $path exists and is not a symlink." >&2
    echo "       Move it into $REPO/skills/ or delete it, then re-run." >&2
    exit 1
  fi
}

linked=0
for skill_dir in "$REPO"/skills/*/; do
  name="$(basename "$skill_dir")"

  if [ ! -f "$skill_dir/SKILL.md" ]; then
    echo "skip $name (no SKILL.md)"
    continue
  fi

  check_free "$AGENTS_DIR/$name"
  check_free "$CLAUDE_DIR/$name"

  ln -sfn "$REPO/skills/$name" "$AGENTS_DIR/$name"
  # Relative, so it survives a different $HOME; mirrors the existing links here.
  ln -sfn "../../.agents/skills/$name" "$CLAUDE_DIR/$name"

  echo "link $name"
  linked=$((linked + 1))
done

echo "$linked skill(s) linked -> $REPO/skills"
