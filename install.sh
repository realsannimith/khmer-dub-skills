#!/bin/sh
# Install (or update) the khmer-dub skill for Claude Code in one command:
#
#   curl -fsSL https://raw.githubusercontent.com/realsannimith/khmer-dub-skill/main/install.sh | sh
#
# Clones the skill into ~/.claude/skills/khmer-dub (KHMER_DUB_DIR to change it), or updates it when
# it is already there, then runs scripts/setup.sh (edge-tts, Pillow and the Khmer font; no AI model).
set -e
DIR="${KHMER_DUB_DIR:-$HOME/.claude/skills/khmer-dub}"
REPO="https://github.com/realsannimith/khmer-dub-skill.git"
command -v git >/dev/null || { echo "install.sh: install git first"; exit 1; }
command -v uv >/dev/null || { echo "install.sh: install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
if [ -d "$DIR/.git" ]; then
  echo "Updating $DIR"
  git -C "$DIR" pull --ff-only -q
elif [ -e "$DIR" ]; then
  echo "install.sh: $DIR exists but is not a git checkout; move it away and run this again"; exit 1
else
  echo "Installing into $DIR"
  mkdir -p "$(dirname "$DIR")"
  git clone -q --depth 1 "$REPO" "$DIR"
fi
sh "$DIR/scripts/setup.sh"
echo
echo "khmer-dub is installed. In Claude Code, ask: \"dub this video into Khmer: <link or file>\""
