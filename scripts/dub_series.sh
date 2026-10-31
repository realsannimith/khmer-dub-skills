#!/bin/sh
# Split and dub every episode of a movie folder, skipping work already done.
#
# Usage: [JOBS=4] dub_series.sh <Movie_folder> [split|dub|all]   (default all, JOBS=1)
#
# split: separate.sh for each Episode_*/ that has no work/background_music.wav yet (GPU, ~1 min each).
# dub:   khmer_dub.py for each episode that has work/khmer_script.json and whose _Khmer.mp4 is
#        missing or older than its script or the movie's cast.json (online Edge TTS, ~3 min each:
#        mostly waiting on the service, so JOBS=4 dubs four episodes at once), then moves its
#        per-line audio (work/khmer_lines/) to the Trash.
# Each episode is claimed with a lock folder (work/.busy), so several copies can run side by side.
# Prints one line per episode and a summary. Run it again after fixing a script; if a run was
# killed, delete the leftover work/.busy folders first (rmdir <Movie>/Episode_*/work/.busy).
set -u
MOVIE="${1:?usage: dub_series.sh <Movie_folder> [split|dub|all]}"; WHAT="${2:-all}"
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
SELF="$SKILL/scripts/dub_series.sh"
if [ "${JOBS:-1}" -gt 1 ]; then
  i=0; while [ $i -lt "$JOBS" ]; do JOBS=1 sh "$SELF" "$MOVIE" "$WHAT" & i=$((i + 1)); sleep 2; done
  wait; exit 0
fi
PY="$SKILL/.venv/bin/python"
cd "$MOVIE" || exit 1
NAME="$(basename "$(pwd)")"
TRASH="$HOME/.Trash/${NAME}_khmer_lines"
done=0; failed=""
for d in Episode_*/; do
  ep="${d%/}"; video="$ep/${NAME}_$ep.mp4"
  [ -f "$video" ] || continue
  mkdir -p "$ep/work"
  mkdir "$ep/work/.busy" 2>/dev/null || continue   # another copy has this episode
  if [ "$WHAT" != dub ] && [ ! -f "$ep/work/background_music.wav" ]; then
    if sh "$SKILL/scripts/separate.sh" "$video" >/dev/null 2>&1; then echo "$ep split"; else echo "$ep SPLIT FAILED"; failed="$failed $ep"; fi
  fi
  if [ "$WHAT" != split ] && [ -f "$ep/work/khmer_script.json" ] && [ -f "$ep/work/background_music.wav" ]; then
    out="$ep/${NAME}_${ep}_Khmer.mp4"
    if [ ! -f "$out" ] || [ "$ep/work/khmer_script.json" -nt "$out" ] || { [ -f cast.json ] && [ cast.json -nt "$out" ]; }; then
      if log=$("$PY" "$SKILL/scripts/khmer_dub.py" "$video" 2>&1); then
        over=$(printf '%s\n' "$log" | grep -c "OVER by")
        if [ "$over" -gt 0 ]; then echo "$ep dubbed ($over lines OVER: shorten them)"; else echo "$ep dubbed"; fi
        mkdir -p "$TRASH" && mv "$ep/work/khmer_lines" "$TRASH/$ep.$(date +%s)" 2>/dev/null
        done=$((done + 1))
      else
        rm -f "$out"; echo "$ep DUB FAILED: $(printf '%s\n' "$log" | tail -1)"; failed="$failed $ep"
      fi
    fi
  fi
  rmdir "$ep/work/.busy"
done
echo "finished: $done dubbed${failed:+; failed:$failed}"
