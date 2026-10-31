"""Khmer speech -> a draft of timed Khmer lines, phrase by phrase.

Usage (needs torch + transformers, the 'ai' environment):
  sh run.sh ai transcribe_km.py <Episode_dir>/<Name>.mp4

Reads <Episode_dir>/work/voice.wav when separate.sh made it (best: no music
under the words), else the video's own sound. Splits on silences into phrases
of at most 6 s, transcribes each with the Khmer fine-tune of
whisper-large-v3-turbo (forced language km, beam 5, fp32, on the GPU), and
writes work/draft.json + work/draft.srt.

Whisper sometimes loops on a phrase ("បិបិបិបិ…"): such phrases are run again
with a repetition penalty, and any still garbled get "check": true. The
draft always needs proofreading (make_srt.py turns the proofread copy into
the final .km.srt / .km.txt).

The model (about 1.6 GB) is downloaded into the Hugging Face cache on first
use; set HF_HUB_OFFLINE=1 (config.env) to never download it.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import librosa
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor
from transformers.utils import logging

logging.set_verbosity_error()  # else a max_length notice per phrase

MODEL = "metythorn/whisper-large-v3-turbo"
SR = 16000
MAX_PHRASE = 6.0  # seconds; longer phrases make the model loop
LOOP = re.compile(r"(.{1,6}?)\1{3,}")  # the same 1-6 characters four times in a row


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def garbled(text: str, dur: float) -> bool:
    return bool(LOOP.search(text.replace(" ", ""))) or len(text) / max(dur, 0.3) > 30


def main() -> None:
    video = Path(sys.argv[1])
    work = video.parent / "work"
    work.mkdir(exist_ok=True)
    voice = work / "voice.wav"
    wav16 = work / "asr_16k.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(voice if voice.exists() else video),
                    "-vn", "-ac", "1", "-ar", str(SR), str(wav16)], check=True)
    a, _ = librosa.load(wav16, sr=SR)
    dur = len(a) / SR

    err = subprocess.run(["ffmpeg", "-i", str(wav16), "-af", "highpass=f=100,silencedetect=noise=-40dB:d=0.3",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    wav16.unlink()
    ss = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    se = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    se += [dur] * (len(ss) - len(se))
    segs, cur = [], 0.0
    for s, e in zip(ss, se):
        if s - cur > 0.25:
            segs.append((max(0.0, cur - 0.1), s + 0.1))
        cur = e
    if dur - cur > 0.25:
        segs.append((max(0.0, cur - 0.1), dur))
    phrases = []
    for s, e in segs:
        n = int((e - s) // MAX_PHRASE) + 1
        phrases += [(s + (e - s) * i / n, s + (e - s) * (i + 1) / n) for i in range(n)]

    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    proc = WhisperProcessor.from_pretrained(MODEL)
    model = WhisperForConditionalGeneration.from_pretrained(MODEL, dtype=torch.float32).to(dev).eval()
    print(f"{len(phrases)} phrases, {dur:.1f}s, on {dev}", flush=True)

    def hear(s: float, e: float, **kw) -> str:
        feats = proc(a[int(s * SR):int(e * SR)], sampling_rate=SR, return_tensors="pt").input_features.to(dev)
        with torch.no_grad():
            ids = model.generate(feats, language="km", task="transcribe", num_beams=5, max_new_tokens=200, **kw)
        return proc.batch_decode(ids, skip_special_tokens=True)[0].strip()

    lines = []
    for s, e in phrases:
        text = hear(s, e)
        check = garbled(text, e - s)
        if check:
            text = hear(s, e, repetition_penalty=1.4)
            check = garbled(text, e - s)
        if text:
            lines.append({"start": round(s, 2), "end": round(e, 2), "text": text, **({"check": True} if check else {})})
            print(f"{s:7.2f}-{e:7.2f} {'?' if check else ' '} {text}", flush=True)

    (work / "draft.json").write_text(json.dumps(lines, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (work / "draft.srt").write_text("\n".join(
        f"{i + 1}\n{srt_time(l['start'])} --> {srt_time(l['end'])}\n{l['text']}\n" for i, l in enumerate(lines)),
        encoding="utf-8")
    print(f"wrote {work / 'draft.json'} ({len(lines)} phrases, {sum('check' in l for l in lines)} to check)")


if __name__ == "__main__":
    main()
