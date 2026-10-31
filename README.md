# khmer-dub skill

A Claude Code skill that dubs short dramas, movie series and clips into Khmer (ខ្មែរ) with free Microsoft Edge TTS, and
makes Khmer subtitles from Khmer speech.

What it does:

- Downloads episodes (TikTok short dramas, hongguoduanju.com, Facebook, YouTube, anything yt-dlp reads) into one folder
  per movie.
- Splits the original voice from the background music with Demucs.
- Translates the subtitles into natural spoken Khmer, with one voice per character for the whole series.
- Fits each line into its slot, mixes it over the ducked music at -14 LUFS, and writes `<Name>_Khmer.mp4` + `.srt`.
- Dubs a whole series in parallel, covers burned-in subtitles, and joins episodes into 7–8 minute parts with a channel
  logo.
- Transcribes Khmer speech (Khmer Whisper on the GPU) into a proofread `.km.srt` and `.km.txt`.

The full instructions Claude follows are in [SKILL.md](SKILL.md).

## Install

```bash
git clone https://github.com/realsannimith/khmer-dub-skill.git ~/.claude/skills/khmer-dub
sh ~/.claude/skills/khmer-dub/scripts/setup.sh
```

`setup.sh` makes a small Python environment inside the skill with edge-tts, numpy and soundfile. It needs
[uv](https://docs.astral.sh/uv/) and ffmpeg.

## Requirements

The dub itself needs only Edge TTS (online, free, no key) and ffmpeg. The other steps expect engines that are already
installed on the author's Mac, and the scripts look for them in these places:

| Step | Engine | Expected at |
|---|---|---|
| Voice/music split | Demucs `htdemucs_ft` | `~/ai-engines/demucs`, run with the torch environment `~/ai-engines/voxcpm/.venv` |
| Khmer transcription | `metythorn/whisper-large-v3-turbo` | Hugging Face cache, same torch environment |
| Chinese captions when an episode has none | `mlx-community/whisper-large-v3-turbo` | `~/ai-engines/mlx-whisper/.venv` (Apple Silicon) |
| Covering burned-in subtitles | Pillow with Raqm (Khmer text shaping) | `~/.cache/khmer-video-editor/venv` |

On another machine, install these yourself and change the paths at the top of the scripts.

## Voices

The two Khmer neural voices: `km-KH-SreymomNeural` (female) and `km-KH-PisethNeural` (male). Characters are told apart by
pitch, set once per series in `cast.json`.
