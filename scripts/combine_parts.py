"""Join a series' dubbed episodes into longer parts (e.g. 7–8 minutes each).

Usage (plain Python; needs ffmpeg/ffprobe):
  python3 combine_parts.py <Movie_folder> [--min 420] [--max 480] [--suffix _Khmer]

Takes <Movie>_Episode_NN<suffix>.mp4 from every Episode_NN/ in order (suffix _Khmer = the dub,
_Khmer_sub = the dub with covered subtitles), groups whole consecutive episodes so every part
lasts between --min and --max seconds (as close to the middle as the episode lengths allow;
an episode is never cut), and joins each group without re-encoding. Writes <Movie>/Parts/PP.mp4,
<Movie>/Parts/Subtitles/PP.srt (the episodes' Khmer subtitles, shifted to the part's timeline) and
<Movie>/Parts/parts.txt (which episodes each part holds), and prints each part's episodes and length.
--long-names writes <Movie>/Parts/<Movie>_Part_PP_EpAA-BB.mp4 with its .srt beside it instead.

--logo channel_logo.png puts a transparent PNG (with its shadow, if it has one) in the top-right
corner at 90 % opacity; the video is then re-encoded with x265 (about 1.5 min per 7-minute part).
"""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path


def duration(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                capture_output=True, text=True).stdout)


def group(durs: list[float], lo: float, hi: float) -> list[list[int]]:
    """Split indexes 0..n-1 into consecutive runs, each as close to [lo, hi] as whole episodes allow.

    A run outside the range costs the square of the seconds it misses by, so several small misses
    (6:50, 8:10) win over one big one (4:44 or 9:49); inside the range, nearer the middle is better.
    """
    n, mid = len(durs), (lo + hi) / 2
    pre = [0.0]
    for d in durs:
        pre.append(pre[-1] + d)
    best = [0.0] + [float("inf")] * n  # cost of the best split of the first i episodes
    back = [0] * (n + 1)
    for i in range(1, n + 1):
        for j in range(i):
            length = pre[i] - pre[j]
            miss = 0 if lo <= length <= hi else (lo - length if length < lo else length - hi)
            c = best[j] + miss ** 2 + abs(length - mid) / 60
            if c < best[i]:
                best[i], back[i] = c, j
    runs, i = [], n
    while i > 0:
        runs.append(list(range(back[i], i)))
        i = back[i]
    return runs[::-1]


def srt_cues(path: Path):
    t = r"(\d+):(\d+):(\d+)[,.](\d+)"
    for m in re.finditer(t + r"\s*-->\s*" + t + r"\s*\n((?:.+\n?)+)", path.read_text(encoding="utf-8")):
        g = m.groups()
        yield (int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000,
               int(g[4]) * 3600 + int(g[5]) * 60 + int(g[6]) + int(g[7]) / 1000, g[8].strip())


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("movie", type=Path)
    ap.add_argument("--min", type=float, default=420)
    ap.add_argument("--max", type=float, default=480)
    ap.add_argument("--suffix", default="_Khmer")
    ap.add_argument("--logo", type=Path, help="transparent PNG put in the top-right corner (re-encodes the video)")
    ap.add_argument("--logo-width", type=int, default=154, help="width of the PNG on screen, in video pixels (shadow margin included)")
    ap.add_argument("--logo-margin", type=int, default=17)
    ap.add_argument("--long-names", action="store_true", help="<Movie>_Part_PP_EpAA-BB.mp4 + .srt beside it")
    a = ap.parse_args()
    name = a.movie.resolve().name
    eps = sorted(a.movie.glob("Episode_*/"))
    videos = [ep / f"{name}_{ep.name}{a.suffix}.mp4" for ep in eps]
    missing = [v.name for v in videos if not v.exists()]
    assert not missing, f"missing: {missing}"
    durs = [duration(v) for v in videos]
    out_dir = a.movie / "Parts"
    out_dir.mkdir(exist_ok=True)
    if not a.long_names:
        (out_dir / "Subtitles").mkdir(exist_ok=True)
    index = []
    num = lambda v: v.parent.name.split("_")[1]
    hevc = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name",
                           "-of", "csv=p=0", str(videos[0])], capture_output=True, text=True).stdout.strip() == "hevc"
    for p, run in enumerate(group(durs, a.min, a.max), 1):
        vs = [videos[i] for i in run]
        if a.long_names:
            out = out_dir / f"{name}_Part_{p:02d}_Ep{num(vs[0])}-{num(vs[-1])}.mp4"
            out_srt = out.with_suffix(".srt")
        else:
            out = out_dir / f"{p:02d}.mp4"
            out_srt = out_dir / "Subtitles" / f"{p:02d}.srt"
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("".join(f"file '{v.resolve()}'\n" for v in vs))
        if a.logo:  # the picture changes, so it is re-encoded (x265, about the episodes' own size)
            logo = f"[1:v]scale={a.logo_width}:-1,format=rgba,colorchannelmixer=aa=0.9[l];" \
                   f"[0:v][l]overlay=W-w-{a.logo_margin}:{a.logo_margin}"
            video = ["-i", str(a.logo), "-filter_complex", logo, "-c:v", "libx265", "-crf", "26", "-preset", "faster",
                     "-x265-params", "log-level=error", "-tag:v", "hvc1", "-c:a", "copy"]
        else:
            video = ["-c", "copy", *(["-tag:v", "hvc1"] if hevc else [])]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f.name, *video,
                        "-movflags", "+faststart", str(out)], check=True)
        Path(f.name).unlink()
        cues, offset = [], 0.0
        for i in run:
            srt = videos[i].with_suffix(".srt")
            if not srt.exists():
                srt = videos[i].with_name(f"{name}_{eps[i].name}_Khmer.srt")
            if srt.exists():
                cues += [(s + offset, e + offset, t) for s, e, t in srt_cues(srt)]
            offset += durs[i]
        out_srt.write_text("\n".join(
            f"{k + 1}\n{srt_time(s)} --> {srt_time(e)}\n{t}\n" for k, (s, e, t) in enumerate(cues)), encoding="utf-8")
        total = sum(durs[i] for i in run)
        line = f"{out.name}  Ep{num(vs[0])}-{num(vs[-1])}  {len(run)} episodes  {int(total // 60)}:{int(total % 60):02d}"
        index.append(line)
        print(f"{line}{'' if a.min <= total <= a.max else '  (outside the range)'}", flush=True)
    (out_dir / "parts.txt").write_text("\n".join(index) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
