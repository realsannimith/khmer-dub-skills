#!/bin/sh
# One-time setup. Safe to run again; it only adds what is missing.
#
#   setup.sh          SKILL_DIR/.venv: edge-tts, numpy, soundfile, Pillow (about 60 MB, no AI model;
#                     edge-tts is Microsoft's free online voice service), and the Kantumruy Pro font
#                     (Google Fonts, OFL) in SKILL_DIR/fonts for covered subtitles.
#   setup.sh --ai     SKILL_DIR/.venv-ai: torch, Demucs, librosa, transformers (about 2 GB). Needed to
#                     split voice and music, measure pitch and transcribe Khmer speech.
#   setup.sh --mlx    SKILL_DIR/.venv-mlx: mlx-whisper (Apple Silicon only), for Chinese captions when
#                     an episode has none.
#
# Needs uv (https://docs.astral.sh/uv/) and ffmpeg. If SKILL_DIR/config.env already points at a
# Python for --ai or --mlx, that step does nothing.
set -e
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ -f "$SKILL_DIR/config.env" ]; then set -a; . "$SKILL_DIR/config.env"; set +a; fi
# Pillow shapes Khmer with libraqm, which loads libfribidi at run time; on macOS that is in Homebrew's
# lib folder, which the loader doesn't search by default.
if [ "$(uname -s)" = Darwin ]; then
  export DYLD_FALLBACK_LIBRARY_PATH="${DYLD_FALLBACK_LIBRARY_PATH:+$DYLD_FALLBACK_LIBRARY_PATH:}/opt/homebrew/lib:/usr/local/lib:/usr/lib"
fi
command -v uv >/dev/null || { echo "setup.sh: install uv first: https://docs.astral.sh/uv/"; exit 1; }
command -v ffmpeg >/dev/null || echo "setup.sh: ffmpeg is missing; install it (brew install ffmpeg / apt install ffmpeg)"

venv() {  # venv <dir> <packages…>
  dir="$1"; shift
  [ -x "$dir/bin/python" ] || uv venv --python 3.12 "$dir"
  uv pip install --python "$dir/bin/python" "$@"
}

case "${1:-}" in
  --ai)
    if [ -n "${KHMER_DUB_AI_PYTHON:-}" ]; then echo "config.env sets KHMER_DUB_AI_PYTHON; nothing to install."; exit 0; fi
    venv "$SKILL_DIR/.venv-ai" torch demucs librosa soundfile numpy transformers
    "$SKILL_DIR/.venv-ai/bin/python" -c "import torch, demucs, librosa, transformers; print('ai environment ready, GPU:', 'mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'none (CPU)')"
    ;;
  --mlx)
    if [ -n "${KHMER_DUB_MLX_PYTHON:-}" ]; then echo "config.env sets KHMER_DUB_MLX_PYTHON; nothing to install."; exit 0; fi
    [ "$(uname -s)-$(uname -m)" = Darwin-arm64 ] || { echo "mlx-whisper needs an Apple Silicon Mac."; exit 1; }
    venv "$SKILL_DIR/.venv-mlx" mlx-whisper
    ;;
  "")
    venv "$SKILL_DIR/.venv" edge-tts numpy soundfile pillow
    "$SKILL_DIR/.venv/bin/python" -c "from PIL import features; import sys; sys.exit(0 if features.check('raqm') else 1)" \
      || echo "setup.sh: Pillow can't shape Khmer text (covered subtitles need it): install fribidi (brew install fribidi / apt install libfribidi0) and run setup.sh again"
    if [ -z "${KHMER_DUB_FONT:-}" ] && [ ! -f "$SKILL_DIR/fonts/KantumruyPro.ttf" ]; then
      mkdir -p "$SKILL_DIR/fonts"
      curl -sSfL -o "$SKILL_DIR/fonts/KantumruyPro.ttf" \
        "https://github.com/google/fonts/raw/main/ofl/kantumruypro/KantumruyPro%5Bwght%5D.ttf"
    fi
    "$SKILL_DIR/.venv/bin/edge-tts" --list-voices | grep km-KH
    ;;
  *) echo "usage: setup.sh [--ai|--mlx]"; exit 2 ;;
esac
