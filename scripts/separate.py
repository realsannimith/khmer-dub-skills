"""Split a WAV into vocals and background (everything else) with Demucs.

Usage: run.sh ai separate.py <input.wav> <out_dir> [model]   (model default htdemucs_ft)

Writes <out_dir>/voice.wav and <out_dir>/background_music.wav. Reads and writes audio with
soundfile, so torchaudio's file I/O is not needed. Runs on the Apple GPU (mps) or CUDA when there
is one, else the CPU. Demucs downloads the model (about 320 MB) into TORCH_HOME on first use.
KHMER_DUB_EXTRA_SITE (folders, ':'-separated) is searched for packages first, for a Demucs
installed outside the Python environment.
"""
import os
import sys
from pathlib import Path

for p in reversed(os.environ.get("KHMER_DUB_EXTRA_SITE", "").split(os.pathsep)):
    if p:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
import torch  # noqa: E402
from demucs.apply import apply_model  # noqa: E402
from demucs.pretrained import get_model  # noqa: E402

src, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
model_name = sys.argv[3] if len(sys.argv) > 3 else "htdemucs_ft"

device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
model = get_model(model_name)
model.eval()

audio, sr = sf.read(src, dtype="float32", always_2d=True)
assert sr == model.samplerate, f"expected {model.samplerate} Hz, got {sr}"
wav = torch.from_numpy(audio.T.copy())
if wav.shape[0] == 1:
    wav = wav.repeat(2, 1)

# Normalise like demucs' own CLI, then undo it on the outputs.
ref = wav.mean(0)
mean, std = ref.mean(), ref.std()
mix = ((wav - mean) / std)[None]

with torch.no_grad():
    stems = apply_model(model, mix, device=device, shifts=1, split=True, overlap=0.25, progress=True)[0]
stems = stems * std + mean

names = model.sources
vocals = stems[names.index("vocals")]
background = sum(stems[i] for i, n in enumerate(names) if n != "vocals")

out_dir.mkdir(parents=True, exist_ok=True)
for name, track in (("voice", vocals), ("background_music", background)):
    data = track.cpu().numpy().T
    peak = float(np.abs(data).max())
    if peak > 1.0:
        data = data / peak
    sf.write(out_dir / f"{name}.wav", data, sr, subtype="PCM_16")
    print(f"wrote {out_dir / f'{name}.wav'} (peak {peak:.2f})")
