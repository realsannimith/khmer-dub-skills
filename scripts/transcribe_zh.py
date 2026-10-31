"""Chinese captions (<Name>.zh.vtt) for episodes that came without subtitles.

Usage (the 'mlx' environment: mlx-whisper on the Apple GPU):
  sh run.sh mlx transcribe_zh.py <Episode_dir>/<Name>.mp4 [more.mp4 …] [--prompt "names…"]

Transcribes work/voice.wav (from separate.sh; the video's own sound if it isn't there) with
whisper-large-v3-turbo (mlx-community weights, downloaded into the Hugging Face cache on first use;
HF_HUB_OFFLINE=1 in config.env stops any download) and writes <Name>.zh.vtt beside the video, one cue per
phrase. About 20 s per 2-minute episode. --prompt gives Whisper the drama's names and
words (e.g. "李承乾、李世民、太子殿下、陛下") so it spells them right.
"""
import sys
from pathlib import Path

import mlx_whisper

MODEL = "mlx-community/whisper-large-v3-turbo"


def vtt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def main() -> None:
    args = sys.argv[1:]
    prompt = None
    if "--prompt" in args:
        i = args.index("--prompt")
        prompt = "以下是短剧的对白。" + args[i + 1]
        del args[i:i + 2]
    for video in map(Path, args):
        voice = video.parent / "work" / "voice.wav"
        r = mlx_whisper.transcribe(str(voice if voice.exists() else video), path_or_hf_repo=MODEL, language="zh",
                                   initial_prompt=prompt, condition_on_previous_text=False, no_speech_threshold=0.5)
        cues = [s for s in r["segments"] if s["text"].strip()]
        out = video.with_name(video.stem + ".zh.vtt")
        out.write_text("WEBVTT\n\n" + "\n".join(
            f"{vtt_time(s['start'])} --> {vtt_time(s['end'])}\n{s['text'].strip()}\n" for s in cues), encoding="utf-8")
        print(f"{video.name}: {len(cues)} cues -> {out.name}", flush=True)


if __name__ == "__main__":
    main()
