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
curl -fsSL https://raw.githubusercontent.com/realsannimith/khmer-dub-skill/main/install.sh | sh
```

It clones the skill into `~/.claude/skills/khmer-dub` (or updates it) and runs `scripts/setup.sh`. Run it again
later to update.

Then ask Claude Code something like "dub this episode into Khmer: <link or file>".

Needs [uv](https://docs.astral.sh/uv/) and ffmpeg, on macOS or Linux. `setup.sh` makes a small Python environment
inside the skill (edge-tts, numpy, soundfile, Pillow) and downloads the Kantumruy Pro font from Google Fonts. That is
enough to dub.

The other steps need local AI engines. Claude installs them the first time a step needs them, after asking:

| Command | Installs | Used for |
|---|---|---|
| `setup.sh --ai` | torch, Demucs, librosa, transformers (about 2 GB) | splitting voice and music, telling speakers apart by pitch, transcribing Khmer speech |
| `setup.sh --mlx` | mlx-whisper (Apple Silicon only) | Chinese captions for episodes that have no subtitles |

The models download on first use: Demucs `htdemucs_ft` (about 320 MB), the Khmer Whisper
`metythorn/whisper-large-v3-turbo`, and `mlx-community/whisper-large-v3-turbo`. A GPU (Apple Silicon or CUDA) makes
them much faster.

### Already have these engines?

Copy `config.example.env` to `config.env` and point it at your Python environments, model folders and font. The
skill then uses them and never installs or downloads its own. `config.env` is not committed.

## Voices

The two Khmer neural voices: `km-KH-SreymomNeural` (female) and `km-KH-PisethNeural` (male). Characters are told apart by
pitch, set once per series in `cast.json`.

## License

[MIT](LICENSE)
