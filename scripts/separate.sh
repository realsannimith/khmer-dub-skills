#!/bin/sh
# Split a video's sound into voice.wav + background_music.wav with Demucs (htdemucs_ft).
# Writes them into work/ beside the video.
#
# Usage: separate.sh <Movie>/Episode_NN/<Name>.mp4
#
# Runs scripts/separate.py in the 'ai' environment (run.sh ai; setup.sh --ai makes it).
set -e
VIDEO="$1"
[ -f "$VIDEO" ] || { echo "usage: separate.sh <Episode_dir>/<Name>.mp4"; exit 2; }
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(cd "$(dirname "$VIDEO")" && pwd)/work"
mkdir -p "$WORK"
ffmpeg -v error -y -i "$VIDEO" -vn -ar 44100 -ac 2 "$WORK/original_audio.wav"
sh "$SKILL_DIR/scripts/run.sh" ai separate.py "$WORK/original_audio.wav" "$WORK" 2>&1 | grep -E "^wrote|run.sh|Error" || true
rm -f "$WORK/original_audio.wav"  # a copy of the video's sound; ffmpeg remakes it in a second
ls -la "$WORK"
