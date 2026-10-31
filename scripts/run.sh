#!/bin/sh
# Run one of the skill's Python scripts with the right Python environment.
#
# Usage: run.sh <tts|ai|mlx> <script.py> [args…]
#
#   tts  edge-tts, numpy, soundfile, Pillow   SKILL_DIR/.venv       (setup.sh)
#   ai   torch, Demucs, librosa, transformers SKILL_DIR/.venv-ai    (setup.sh --ai)
#   mlx  mlx-whisper (Apple Silicon only)     SKILL_DIR/.venv-mlx   (setup.sh --mlx)
#
# SKILL_DIR/config.env, if it exists, can point each one at a Python that is already
# installed elsewhere (KHMER_DUB_TTS_PYTHON, KHMER_DUB_AI_PYTHON, KHMER_DUB_MLX_PYTHON) and set
# anything else the scripts read (TORCH_HOME, HF_HUB_OFFLINE, KHMER_DUB_FONT). See config.example.env.
set -e
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
KIND="${1:?usage: run.sh <tts|ai|mlx> <script.py> [args…]}"
SCRIPT="${2:?usage: run.sh <tts|ai|mlx> <script.py> [args…]}"
shift 2
if [ -f "$SKILL_DIR/config.env" ]; then
  set -a; . "$SKILL_DIR/config.env"; set +a
fi
# Pillow shapes Khmer with libraqm, which loads libfribidi at run time; on macOS that is in Homebrew's
# lib folder, which the loader doesn't search by default.
if [ "$(uname -s)" = Darwin ]; then
  export DYLD_FALLBACK_LIBRARY_PATH="${DYLD_FALLBACK_LIBRARY_PATH:+$DYLD_FALLBACK_LIBRARY_PATH:}/opt/homebrew/lib:/usr/local/lib:/usr/lib"
fi
case "$KIND" in
  tts) PY="${KHMER_DUB_TTS_PYTHON:-$SKILL_DIR/.venv/bin/python}"; HOW="sh $SKILL_DIR/scripts/setup.sh" ;;
  ai)  PY="${KHMER_DUB_AI_PYTHON:-$SKILL_DIR/.venv-ai/bin/python}"; HOW="sh $SKILL_DIR/scripts/setup.sh --ai" ;;
  mlx) PY="${KHMER_DUB_MLX_PYTHON:-$SKILL_DIR/.venv-mlx/bin/python}"; HOW="sh $SKILL_DIR/scripts/setup.sh --mlx" ;;
  *) echo "run.sh: unknown environment '$KIND' (tts, ai or mlx)" >&2; exit 2 ;;
esac
[ -x "$PY" ] || { echo "run.sh: no '$KIND' Python at $PY. Run: $HOW (or set it in $SKILL_DIR/config.env)" >&2; exit 1; }
case "$SCRIPT" in /*) ;; *) SCRIPT="$SKILL_DIR/scripts/$SCRIPT" ;; esac
exec "$PY" -I "$SCRIPT" "$@"
