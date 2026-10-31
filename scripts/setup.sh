#!/bin/sh
# One-time setup: a small Python environment inside the skill with edge-tts,
# numpy and soundfile (about 60 MB). No AI model is downloaded: edge-tts is
# Microsoft's free online voice service. Safe to run again; it only adds what
# is missing.
set -e
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ ! -x "$SKILL_DIR/.venv/bin/python" ]; then
  uv venv --python 3.12 "$SKILL_DIR/.venv"
fi
uv pip install --python "$SKILL_DIR/.venv/bin/python" edge-tts numpy soundfile
"$SKILL_DIR/.venv/bin/edge-tts" --list-voices | grep km-KH
