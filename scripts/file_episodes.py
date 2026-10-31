"""Move downloaded episodes into <Movie>/Episode_NN/ and fetch their subtitles.

Usage (plain Python; needs curl and ffprobe):
  python3 file_episodes.py <inbox_dir> <Movie_folder>

<inbox_dir> is where receive.py saved <Movie>_Episode_NN.mp4 files and manifest.json (from
tiktok_batch.js). Each video goes to <Movie>/Episode_NN/, its subtitles are downloaded next to it
as .zh.vtt (Chinese auto-captions) and .en.vtt (machine translation) when TikTok has them (the
subtitle links work from curl with the path alone), and manifest.json is kept as
<Movie>/episodes.json. Prints one line per episode: length vs the listed length, which
subtitles came. Run it after each batch.
"""
import json
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36"
LANGS = {"cmn": "zh", "eng": "en"}  # TikTok LanguageCodeName prefix -> file suffix


def main() -> None:
    inbox, movie = Path(sys.argv[1]), Path(sys.argv[2])
    movie.mkdir(parents=True, exist_ok=True)
    shutil.copy(inbox / "manifest.json", movie / "episodes.json")
    manifest = {e["ep"]: e for e in json.loads((inbox / "manifest.json").read_text())}
    for mp4 in sorted(inbox.glob(f"{movie.name}_Episode_*.mp4")):
        num = mp4.stem.rsplit("_", 1)[1]
        e = manifest[int(num)]
        ep = movie / f"Episode_{num}"
        ep.mkdir(exist_ok=True)
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
                             capture_output=True, text=True).stdout.strip()
        dur = float(dur or 0)
        mp4.rename(ep / mp4.name)
        subs = []
        for s in e["subs"]:
            suffix = LANGS.get(s["lang"].split("-")[0])
            if not suffix:
                continue
            u = urllib.parse.urlsplit(s["url"])
            subprocess.run(["curl", "-sSL", "--fail", "--retry", "3", "-A", UA, "-o", str(ep / f"{mp4.stem}.{suffix}.vtt"),
                            f"{u.scheme}://{u.netloc}{u.path}"], check=True)
            subs.append(f"{suffix}({s['source']})")
        ok = abs(dur - e["duration"]) < 2
        print(f"{num} {dur:6.1f}s (listed {e['duration']}s) {' '.join(subs) or 'NO SUBTITLES'}"
              f"{'' if ok else '  LENGTH WRONG: download again'}")


if __name__ == "__main__":
    main()
