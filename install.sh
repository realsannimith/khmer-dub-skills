#!/bin/sh
# Install (or update) the khmer-dub skill in one command, for one or more coding agents:
#
#   curl -fsSL https://raw.githubusercontent.com/realsannimith/khmer-dub-skill/main/install.sh | sh                    # Claude Code
#   curl -fsSL https://raw.githubusercontent.com/realsannimith/khmer-dub-skill/main/install.sh | sh -s -- codex       # Codex
#   curl -fsSL https://raw.githubusercontent.com/realsannimith/khmer-dub-skill/main/install.sh | sh -s -- claude codex
#
# Agents and the skills folder each one reads:
#   claude                    ~/.claude/skills
#   codex, cline, warp, zed   ~/.agents/skills   (also: agents)
#   cursor                    ~/.cursor/skills
#   gemini                    ~/.gemini/skills
#   copilot                   ~/.copilot/skills
#   opencode                  ~/.config/opencode/skills
#   windsurf                  ~/.codeium/windsurf/skills
#
# The first agent gets a git checkout (updated when it is already there); the others get a link to it.
# Then scripts/setup.sh runs (edge-tts, Pillow and the Khmer font; no AI model).
# KHMER_DUB_DIR=<folder> installs the checkout there instead, for a single agent.
set -e
REPO="https://github.com/realsannimith/khmer-dub-skill.git"
[ $# -gt 0 ] || set -- claude

skills_dir() {
  case "$1" in
    claude|claude-code) echo "$HOME/.claude/skills" ;;
    codex|agents|cline|warp|zed) echo "$HOME/.agents/skills" ;;
    cursor) echo "$HOME/.cursor/skills" ;;
    gemini|gemini-cli) echo "$HOME/.gemini/skills" ;;
    copilot|github-copilot) echo "$HOME/.copilot/skills" ;;
    opencode) echo "$HOME/.config/opencode/skills" ;;
    windsurf) echo "$HOME/.codeium/windsurf/skills" ;;
    *) echo "install.sh: unknown agent '$1' (claude, codex, cursor, gemini, copilot, opencode, windsurf, agents)" >&2; return 1 ;;
  esac
}

command -v git >/dev/null || { echo "install.sh: install git first"; exit 1; }
command -v uv >/dev/null || { echo "install.sh: install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }

MAIN=""
for agent in "$@"; do
  if [ -z "$MAIN" ] && [ -n "${KHMER_DUB_DIR:-}" ]; then
    dir="$KHMER_DUB_DIR"
  else
    dir="$(skills_dir "$agent")/khmer-dub"
  fi
  if [ -z "$MAIN" ]; then
    # The first agent holds the checkout. An existing link (e.g. made by another installer) is followed.
    if [ -d "$dir/.git" ]; then
      echo "Updating $dir ($agent)"
      git -C "$dir" pull --ff-only -q
    elif [ -e "$dir" ]; then
      echo "install.sh: $dir exists but is not a git checkout; move it away and run this again"; exit 1
    else
      echo "Installing into $dir ($agent)"
      mkdir -p "$(dirname "$dir")"
      git clone -q --depth 1 "$REPO" "$dir"
    fi
    MAIN="$(cd "$dir" && pwd -P)"
  elif [ -e "$dir" ] || [ -L "$dir" ]; then
    if [ "$(cd "$dir" 2>/dev/null && pwd -P)" = "$MAIN" ]; then
      echo "Already linked: $dir ($agent)"
    else
      echo "install.sh: $dir already exists ($agent); left as it is"
    fi
  else
    mkdir -p "$(dirname "$dir")"
    ln -s "$MAIN" "$dir"
    echo "Linked $dir -> $MAIN ($agent)"
  fi
done

sh "$MAIN/scripts/setup.sh"
echo
echo "khmer-dub is installed. Ask your agent: \"dub this video into Khmer: <link or file>\""
