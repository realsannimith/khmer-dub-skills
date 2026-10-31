"""Proofread Khmer lines -> <Name>.km.srt (timed subtitles) + <Name>.km.txt.

Usage (plain Python, no packages):
  python3 make_srt.py <Episode_dir>/<Name>.mp4

Reads <Episode_dir>/work/subtitles.json: the proofread copy of draft.json, a
list of { "start", "end", "text" }, one whole sentence per entry. Sentences
longer than MAX characters are split at the space nearest their middle (again
if still too long), the time shared by length, so each subtitle fits on a
phone screen. The .txt is the plain transcript, one sentence per line.
"""
import json
import sys
from pathlib import Path

MAX = 52  # characters per subtitle


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def split(s: float, e: float, t: str) -> list[tuple[float, float, str]]:
    if len(t) <= MAX or " " not in t:
        return [(s, e, t)]
    words = t.split(" ")
    a, b = min(((" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))),
               key=lambda p: abs(len(p[0]) - len(p[1])))
    m = s + (e - s) * len(a) / (len(a) + len(b))
    return split(s, m, a) + split(m, e, b)


def main() -> None:
    video = Path(sys.argv[1])
    lines = json.loads((video.parent / "work" / "subtitles.json").read_text(encoding="utf-8"))
    cues = [c for l in lines for c in split(l["start"], l["end"], " ".join(l["text"].split()))]
    srt = video.with_name(video.stem + ".km.srt")
    txt = video.with_name(video.stem + ".km.txt")
    srt.write_text("\n".join(f"{i + 1}\n{srt_time(s)} --> {srt_time(e)}\n{t}\n" for i, (s, e, t) in enumerate(cues)),
                   encoding="utf-8")
    txt.write_text("\n".join(l["text"] for l in lines) + "\n", encoding="utf-8")
    print(f"{len(lines)} sentences -> {len(cues)} subtitles (longest {max(len(t) for *_, t in cues)} chars)")
    print(f"wrote {srt} and {txt}")


if __name__ == "__main__":
    main()
