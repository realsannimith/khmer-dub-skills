"""Hide subtitles burned into the picture and burn the Khmer ones in their place.

Usage (needs Pillow with Raqm for Khmer shaping: the kattor skill's environment has it):
  ~/.cache/khmer-video-editor/venv/bin/python cover_subs.py <Name>_Khmer.mp4 [--band 820:965] [--out file.mp4]

TikTok dramas often carry English (or Chinese) subtitles burned into the picture. This blurs a
full-width band where they sit (--band top:bottom in pixels of the video; find it on a frame, e.g.
ffmpeg -ss 98 -i video.mp4 -frames:v 1 -update 1 -vf "crop=iw:300:0:780,drawgrid=w=iw:h=20:c=red@0.4" band.png),
darkens it a little, and draws each line of <Name>_Khmer.srt centred in it: Kantumruy Pro, white
with a black outline, at most two lines. Writes <Name>_Khmer_sub.mp4 (or --out): video re-encoded
with the Mac's HEVC encoder, the Khmer audio copied.
"""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT = Path.home() / ".claude/skills/kattor/assets/fonts/KantumruyPro.ttf"


def srt_cues(path: Path) -> list[tuple[float, float, str]]:
    t = r"(\d+):(\d+):(\d+)[,.](\d+)"
    cues = []
    for m in re.finditer(t + r"\s*-->\s*" + t + r"\s*\n((?:.+\n?)+)", path.read_text(encoding="utf-8")):
        g = m.groups()
        s = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000
        e = int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000
        cues.append((s, e, " ".join(g[8].split())))
    return cues


def font(size: int) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT), size, layout_engine=ImageFont.Layout.RAQM)
    f.set_variation_by_axes([700])  # bold
    return f


def wrap(text: str, f: ImageFont.FreeTypeFont, width: int) -> list[str] | None:
    """Split at spaces into at most two lines that fit, balanced; None if it can't fit."""
    if f.getlength(text) <= width:
        return [text]
    words = text.split(" ")
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        if f.getlength(a) <= width and f.getlength(b) <= width:
            d = abs(f.getlength(a) - f.getlength(b))
            if best is None or d < best[0]:
                best = (d, [a, b])
    return best[1] if best else None


def render(text: str, w: int, h: int) -> Image.Image:
    for size in range(int(h * 0.30), int(h * 0.16), -2):
        f = font(size)
        lines = wrap(text, f, int(w * 0.92))
        if lines and size * 1.45 * len(lines) <= h:
            break
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    line_h = size * 1.45
    y = (h - line_h * len(lines)) / 2
    for line in lines:
        d.text((w / 2, y + line_h / 2), line, font=f, anchor="mm", fill="white",
               stroke_width=max(2, size // 12), stroke_fill="black")
        y += line_h
    return im


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--band", default="820:965")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    top, bottom = map(int, a.band.split(":"))
    bh = bottom - top
    w = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width",
                            "-of", "csv=p=0", str(a.video)], capture_output=True, text=True).stdout)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(a.video)], capture_output=True, text=True).stdout)
    out = a.out or a.video.with_name(a.video.stem + "_sub.mp4")
    cues = srt_cues(a.video.with_suffix(".srt"))
    # The .srt ends when the Khmer voice stops; keep each line up until the original line's end
    # too (khmer_script.json, same order), so short lines stay readable.
    script = a.video.parent / "work" / "khmer_script.json"
    if script.exists():
        import json
        lines = json.loads(script.read_text(encoding="utf-8"))["lines"]
        if len(lines) == len(cues):
            cues = [(s, max(e, l["end"]), t) for (s, e, t), l in zip(cues, lines)]

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        Image.new("RGBA", (w, bh), (0, 0, 0, 0)).save(tmp / "blank.png")
        # A timeline of images for the concat demuxer: blank in the gaps, one card per cue.
        listing, t = [], 0.0
        for i, (s, e, text) in enumerate(cues):
            e = min(max(e, s + 0.8), cues[i + 1][0] if i + 1 < len(cues) else dur)  # on screen at least 0.8 s
            if s > t:
                listing += ["file 'blank.png'", f"duration {s - t:.3f}"]
            render(text, w, bh).save(tmp / f"c{i:03d}.png")
            listing += [f"file 'c{i:03d}.png'", f"duration {e - s:.3f}"]
            t = e
        listing += ["file 'blank.png'", f"duration {max(dur - t, 0.1):.3f}", "file 'blank.png'"]
        (tmp / "cards.txt").write_text("\n".join(listing) + "\n")

        band = (f"[0:v]split[v][b];[b]crop=iw:{bh}:0:{top},boxblur=luma_radius=18:luma_power=3,"
                f"eq=brightness=-0.08[bl];[v][bl]overlay=0:{top}[vb];"
                f"[1:v]format=rgba[cards];[vb][cards]overlay=0:{top}:eof_action=pass,format=yuv420p[out]")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a.video),
                        "-f", "concat", "-safe", "0", "-i", str(tmp / "cards.txt"),
                        "-filter_complex", band, "-map", "[out]", "-map", "0:a",
                        "-c:v", "hevc_videotoolbox", "-b:v", "1600k", "-tag:v", "hvc1", "-c:a", "copy",
                        "-movflags", "+faststart", "-shortest", str(out)], check=True)
    print(f"wrote {out} ({len(cues)} subtitles, band {top}-{bottom})")


if __name__ == "__main__":
    main()
