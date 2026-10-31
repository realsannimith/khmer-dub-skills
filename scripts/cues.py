"""List a subtitle file's lines with the original voice's pitch, and find
speech the subtitles miss. Use it to decide who says each line (pitch: men
roughly 85-160 Hz, women 180-400 Hz) and whether a line is missing.

Usage (needs librosa: run with the ~/ai-engines Python):
  ~/ai-engines/voxcpm/.venv/bin/python -I cues.py <subs.vtt|.srt> <stems_dir>/voice.wav

Pitch 0 means the line had too little clear voice to measure (whisper,
shouting over music, or a deep voice under noise): judge it from the story.
"""
import re
import sys

import librosa
import numpy as np
import soundfile as sf

sub, wav = sys.argv[1], sys.argv[2]
stamp = r"(?:(\d+):)?(\d+):(\d+)[.,](\d+)"
cues = []
for m in re.finditer(stamp + r"\s*-->\s*" + stamp + r"[^\n]*\n((?:.+\n?)+)", open(sub, encoding="utf-8").read()):
    g = m.groups()
    s = int(g[0] or 0) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 10 ** len(g[3])
    e = int(g[4] or 0) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 10 ** len(g[7])
    cues.append((s, e, " ".join(g[8].split())))

y, sr = sf.read(wav, dtype="float32", always_2d=True)
y16 = librosa.resample(y.mean(1), orig_sr=sr, target_sr=16000)
hop = 160
db = 20 * np.log10(librosa.feature.rms(y=y16, frame_length=800, hop_length=hop)[0] + 1e-9)
t = np.arange(len(db)) * hop / 16000
covered = np.zeros(len(db), bool)
for s, e, _ in cues:
    covered |= (t >= s - 0.2) & (t <= e + 0.2)
missed, run_start = [], None
for k, flag in enumerate((db > -38) & ~covered):
    if flag and run_start is None:
        run_start = k
    if not flag and run_start is not None:
        if (k - run_start) * hop / 16000 > 0.3:
            missed.append((round(t[run_start], 2), round(t[k - 1], 2)))
        run_start = None
print(f"total {len(y) / sr:.2f}s, {len(cues)} lines; speech with no subtitle: {missed or 'none'}")
for k, (s, e, text) in enumerate(cues):
    seg = y16[int(s * 16000):int(e * 16000)]
    f, voiced, prob = librosa.pyin(seg, fmin=65, fmax=500, sr=16000, frame_length=1024)
    f = f[voiced & (prob > 0.5)]
    print(f"{k:02d} {s:6.2f}-{e:6.2f}  f0 {np.median(f) if len(f) else 0:4.0f}  {text}")
