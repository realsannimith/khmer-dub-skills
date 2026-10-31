#!/bin/sh
# Split a video's sound into voice.wav + background_music.wav (Demucs
# htdemucs_ft, already installed once in ~/ai-engines/demucs; never download it
# again). Writes them into work/ beside the video.
#
# Usage: separate.sh <Movie>/Episode_NN/<Name>.mp4
#
# Demucs needs torch; it borrows the Python environment in ~/ai-engines
# (~/ai-engines/voxcpm/.venv). Only its packages are used, no voice model.
set -e
VIDEO="$1"
[ -f "$VIDEO" ] || { echo "usage: separate.sh <Episode_dir>/<Name>.mp4"; exit 2; }
PY="$HOME/ai-engines/voxcpm/.venv/bin/python"
[ -x "$PY" ] || { echo "missing $PY (see ~/ai-engines/README.md)"; exit 1; }
WORK="$(cd "$(dirname "$VIDEO")" && pwd)/work"
mkdir -p "$WORK"
ffmpeg -v error -y -i "$VIDEO" -vn -ar 44100 -ac 2 "$WORK/original_audio.wav"
cd "$WORK"
TORCH_HOME="$HOME/ai-engines/demucs/models" "$PY" -I "$HOME/ai-engines/demucs/separate.py" original_audio.wav . 2>&1 \
  | grep -E "^wrote" || true
rm -f original_audio.wav  # a copy of the video's sound; ffmpeg remakes it in a second
ls -la .
