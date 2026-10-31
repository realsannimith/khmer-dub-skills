"""Dub a video into Khmer with Microsoft Edge TTS (free, online).

Usage:
  python khmer_dub.py <Movie>/Episode_NN/<Name>.mp4 [out.mp4]

Run it with the skill's own environment (scripts/setup.sh makes it):
  ~/.claude/skills/khmer-dub/.venv/bin/python khmer_dub.py ...

work/ beside the video holds background_music.wav (44.1 kHz, from
separate.sh) and khmer_script.json:
  { "lines": [ { start, end, speaker, km } ], "voices": { name: { voice, pitch } } }
The voices come from the movie's cast.json (<Movie>/cast.json, shared by every
episode); "voices" in the episode script is optional and adds or overrides.

Each line is voiced, fitted into its slot (the time until the next line
starts), placed at its start time, then mixed over the background with the
music ducked under speech. Speech rate is raised until a line fits, then a
little ffmpeg tempo if it still runs long. Writes <Name>_Khmer.mp4 (or
out.mp4) and a matching .srt beside it; the per-line audio lands in
work/khmer_lines/.
"""
import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44100
SKILL = Path(__file__).resolve().parent.parent
BASE_RATE = 10  # percent faster than the voice's default, drama pace
MAX_RATE = 60  # beyond this the voice starts to slur
MAX_STRETCH = 1.25  # extra ffmpeg tempo on top, if still too long
GAP = 0.08  # seconds kept free before the next line


def edge_tts_bin() -> str:
    for p in (os.environ.get("EDGE_TTS"), str(SKILL / ".venv" / "bin" / "edge-tts"), shutil.which("edge-tts")):
        if p and Path(p).exists():
            return p
    raise SystemExit("edge-tts not found: run scripts/setup.sh first")


EDGE_TTS = edge_tts_bin()


def run(*args: str) -> None:
    subprocess.run(args, check=True, capture_output=True)


def tts(text: str, voice: str, pitch: str, rate: int, mp3: Path) -> None:
    # `=` keeps a negative value ("-4Hz") from reading as a flag. The free
    # service drops a request now and then, more often under parallel load:
    # retry with a growing wait (3, 6, 12, 24, 30 s).
    for attempt in range(6):
        try:
            run(EDGE_TTS, f"--voice={voice}", f"--pitch={pitch}", f"--rate={rate:+d}%",
                f"--text={text}", f"--write-media={mp3}")
            return
        except subprocess.CalledProcessError:
            if attempt == 5:
                raise
            time.sleep(min(30, 3 * 2 ** attempt))


def load_trimmed(src: Path, tempo: float = 1.0) -> np.ndarray:
    """Decode to 44.1 kHz stereo float, trim leading/trailing silence."""
    wav = src.with_name(src.stem + ".fit.wav")
    chain = "silenceremove=start_periods=1:start_threshold=-45dB,areverse," \
            "silenceremove=start_periods=1:start_threshold=-45dB,areverse"
    if tempo != 1.0:
        chain += f",atempo={tempo:.4f}"
    run("ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", chain,
        "-ar", str(SR), "-ac", "2", str(wav))
    audio, _ = sf.read(wav, dtype="float32", always_2d=True)
    return audio


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def voice_line(i: int, line: dict, v: dict, slot: float, work: Path) -> tuple[np.ndarray, str]:
    mp3 = work / f"{i:02d}_{line['speaker']}.mp3"
    pitch = v.get("pitch", "+0Hz")
    rate = BASE_RATE
    tts(line["km"], v["voice"], pitch, rate, mp3)
    audio = load_trimmed(mp3)
    if len(audio) / SR > slot:
        # Speak faster first: ask edge-tts for the needed rate, capped.
        need = len(audio) / SR / slot
        rate = min(MAX_RATE, int(np.ceil((1 + BASE_RATE / 100) * need * 100 - 100)) + 2)
        tts(line["km"], v["voice"], pitch, rate, mp3)
        audio = load_trimmed(mp3)
    tempo = 1.0
    if len(audio) / SR > slot:
        tempo = min(MAX_STRETCH, len(audio) / SR / slot)
        audio = load_trimmed(mp3, tempo)
    return audio, f"rate {rate:+d}%  tempo {tempo:.2f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("out", type=Path, nargs="?")
    a = ap.parse_args()
    a.stems = a.video.parent / "work"
    a.out = a.out or a.video.with_name(a.video.stem + "_Khmer.mp4")

    script = json.loads((a.stems / "khmer_script.json").read_text())
    cast = next((p for p in (a.video.parent / "cast.json", a.video.parent.parent / "cast.json") if p.exists()), None)
    voices = {**(json.loads(cast.read_text())["voices"] if cast else {}), **script.get("voices", {})}
    missing = sorted({l["speaker"] for l in script["lines"]} - voices.keys())
    assert not missing, f"no voice for {missing}: add them to the movie's cast.json"
    script["voices"] = voices
    music, sr = sf.read(a.stems / "background_music.wav", dtype="float32", always_2d=True)
    assert sr == SR, f"background must be {SR} Hz"
    total = len(music) / SR

    work = a.stems / "khmer_lines"
    work.mkdir(exist_ok=True)
    voice_track = np.zeros_like(music)
    lines = script["lines"]
    srt = []

    for i, line in enumerate(lines):
        nxt = lines[i + 1]["start"] if i + 1 < len(lines) else total
        slot = max(line["end"], nxt - GAP) - line["start"]
        audio, how = voice_line(i, line, script["voices"][line["speaker"]], slot, work)
        dur = len(audio) / SR

        # Even level line to line: RMS of the speech to -20 dBFS.
        rms = float(np.sqrt(np.mean(audio**2))) or 1.0
        audio = audio * (10 ** (-20 / 20) / rms)

        at = int(line["start"] * SR)
        end = min(len(voice_track), at + len(audio))
        voice_track[at:end] += audio[: end - at]
        over = dur - slot
        print(f"{i:02d} {line['start']:6.2f}s {line['speaker']:8s} {dur:5.2f}s in {slot:5.2f}s slot  {how}"
              + (f"  OVER by {over:.2f}s" if over > 0.01 else ""), flush=True)
        srt.append(f"{i + 1}\n{srt_time(line['start'])} --> {srt_time(line['start'] + dur)}\n{line['km']}\n")

    # Duck the music by 6 dB under speech, with a smooth 120 ms envelope.
    env = np.abs(voice_track).max(axis=1)
    win = int(0.12 * SR)
    env = np.convolve((env > 0.01).astype(np.float32), np.ones(win) / win, mode="same")
    duck = 1.0 - 0.5 * np.clip(env * 3, 0, 1)
    mix = music * duck[:, None] + voice_track * 1.6

    # A temporary file only: kept, a mix costs ~45 MB per episode, and the script remakes it in seconds.
    mix_wav = a.stems / "khmer_mix.wav"
    sf.write(mix_wav, mix, SR, subtype="FLOAT")

    # Loudness for social video: -14 LUFS, peaks under -1.5 dBTP. One-pass
    # loudnorm can let a peak through, so a limiter at -2 dB follows it (AAC adds about half a dB). The
    # video stream is copied untouched; hvc1 lets QuickTime and iPhones play HEVC.
    vcodec = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                             "stream=codec_name", "-of", "csv=p=0", str(a.video)],
                            capture_output=True, text=True).stdout.strip()
    tag = ["-tag:v", "hvc1"] if vcodec == "hevc" else []
    run("ffmpeg", "-v", "error", "-y", "-i", str(a.video), "-i", str(mix_wav),
        "-map", "0:v", "-map", "1:a", "-c:v", "copy", *tag,
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.79:level=false", "-ar", str(SR),
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(a.out))
    mix_wav.unlink()
    a.out.with_suffix(".srt").write_text("\n".join(srt), encoding="utf-8")
    print(f"wrote {a.out} and {a.out.with_suffix('.srt')}")


if __name__ == "__main__":
    main()
