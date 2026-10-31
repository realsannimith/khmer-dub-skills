---
name: khmer-dub
description: Dub a short drama, movie series or any video into Khmer (ខ្មែរ) with free Microsoft Edge TTS, and make Khmer subtitles from Khmer speech — download the episode (TikTok short-drama pages, hongguoduanju.com, Facebook, YouTube, anything yt-dlp reads) into one folder per movie with every episode inside it, split the original voice from the background music with Demucs, translate the subtitles (Chinese, Vietnamese, English…) into natural spoken Khmer, give every character one voice for the whole series, fit each line into its slot, mix it over the ducked music at -14 LUFS and open the finished video with a Khmer .srt. For a video already spoken in Khmer it transcribes the speech on the GPU (Khmer Whisper), proofreads it and writes a timed .km.srt and a .km.txt transcript. Use it whenever someone asks to dub, voice over, "turn the voice into Khmer", make a Khmer version of a drama/episode/clip, separate voice and music, extract the text or subtitles from a video's audio, transcribe Khmer speech, or download a TikTok short-drama / 红果短剧 episode or a reel to work on — even if they only paste a link and say "start working on it". Edge TTS only: no local voice model.
---

# Khmer dub (Edge TTS) and Khmer subtitles

Two jobs, one project layout:

- **Dub**: turns an episode into `<Name>_Khmer.mp4` + `<Name>_Khmer.srt`. The original picture is untouched and the music
  and effects are kept; every spoken line is replaced by Khmer from Microsoft Edge TTS (free, online, no key). The voices are
  the two Khmer neural voices, `km-KH-SreymomNeural` (female) and `km-KH-PisethNeural` (male), and characters are told
  apart by pitch.
- **Subtitles from Khmer speech**: makes `<Name>.km.srt` + `<Name>.km.txt` for a video that is already spoken in Khmer.
  See section 7.

`SKILL_DIR` is the folder of this file. Scripts are in `SKILL_DIR/scripts`. Python scripts run through
`sh SKILL_DIR/scripts/run.sh <env> <script.py> …`, which picks the Python environment:

- `tts`: edge-tts, numpy, soundfile, Pillow (dubbing, covered subtitles)
- `ai`: torch, Demucs, librosa, transformers (voice/music split, pitch, Khmer Whisper)
- `mlx`: mlx-whisper (Chinese captions on Apple Silicon)

`combine_parts.py`, `file_episodes.py`, `receive.py` and `make_srt.py` need only the standard library: `python3` runs them.

**Edge TTS only.** Do not swap in a local voice model (VoxCPM, OmniVoice, …), even if one is installed. The only local
models are Demucs (voice/music split) and Whisper (transcription).

## Project layout: one folder per movie

Work in the folder the user names (default: the current project folder). **Each movie or series gets one folder, and every
episode of it goes inside that folder**, so a 60-episode drama stays together and every episode reuses the same voices:

```
<Movie_Title>/                         e.g. The_Emperors_Gossip_Girl/
  cast.json                            one voice per character, shared by every episode
  Episode_01/
    <Movie_Title>_Episode_01.mp4       the original, as downloaded
    <Movie_Title>_Episode_01.zh.vtt    its subtitles (language code in the name)
    <Movie_Title>_Episode_01_Khmer.mp4 the dub
    <Movie_Title>_Episode_01_Khmer.srt
    work/                              voice.wav, background_music.wav, khmer_script.json, khmer_lines/…
  Episode_02/ …
Clips/<Name>/                          a one-off video (a reel, a single clip): same inside, no cast.json
```

- Names are ASCII with underscores. Translate or romanise a Chinese title (`持械入宋 第十季` →
  `Chi_Xie_Ru_Song_Season_10`) and write the original title in `cast.json`'s `note`.
- Episode numbers have two digits (`Episode_03`, three digits past 99) so the folders sort in order.
- Before starting an episode, look in the movie folder: if `cast.json` already exists, use its voices and names as they are.
- `episodes.json` (TikTok dramas) lists every episode's id, length and subtitle languages.
- `work/` holds only what can be made again. To tidy a finished episode, move `work/khmer_lines/` to the Trash
  (`mv … ~/.Trash/`), never `rm` the user's files, and keep `voice.wav`, `background_music.wav` and `khmer_script.json` so
  a line can be fixed later.

## 0. Setup (once)

First look for `SKILL_DIR/config.env`. If it exists, it points the environments at engines already installed on this
machine: use them, and never run `setup.sh --ai` / `--mlx` or download those models again. Otherwise:

```bash
sh SKILL_DIR/scripts/setup.sh         # .venv: edge-tts, numpy, soundfile, Pillow + the Kantumruy Pro font (~60 MB)
sh SKILL_DIR/scripts/setup.sh --ai    # .venv-ai: torch, Demucs, librosa, transformers (~2 GB), for steps 2-3 and 7
sh SKILL_DIR/scripts/setup.sh --mlx   # .venv-mlx: mlx-whisper, only for episodes with no subtitles (Apple Silicon)
```

They need `uv` and `ffmpeg`. Run `--ai` and `--mlx` only when a step needs them, and tell the user the download size
first. Demucs (~320 MB) and the Whisper models (~1.6 GB each) download on first use. To reuse engines installed elsewhere,
copy `config.example.env` to `config.env` and fill it in.

## 1. Download the episode

Download into a fresh, empty temporary folder (the scratchpad, if your agent has one) and check it. Then move it to
`<Movie>/Episode_NN/<Movie>_Episode_NN.<ext>` (`mkdir -p` the folder first).

- **Anything yt-dlp reads** (YouTube, Facebook reels, ordinary TikTok videos…): run `yt-dlp -F <url>` to see the qualities,
  then `yt-dlp -f "bv*+ba/b" --write-subs --sub-langs all -o "<dir>/<Name>.%(ext)s" <url>`. A Facebook reel usually comes
  as AV1 video with no subtitles.
- **TikTok short drama** (`tiktok.com/shortdrama/episode/<dramaID>/<n>`; episode n is the last number, and one page
  lists every episode of the drama). yt-dlp says "Unsupported URL". Video links only work inside the browser's own
  session (curl gets 403, even with fresh cookies), and the page's security policy blocks sending data out with
  fetch, so the browser fetches the videos itself and hands them over in a form post:
  1. `python3 SKILL_DIR/scripts/receive.py <scratchpad>/inbox` in the background (listens on 127.0.0.1:8765).
  2. Open any episode page in a browser your agent can drive (the built-in browser in Claude Code). The drama's English title is in the page (the
     episode `desc`); name the movie folder after it.
  3. Run `scripts/tiktok_batch.js` in the page with the browser's JavaScript tool (`javascript_tool` in Claude Code), with `FIRST`, `LAST` (about 20 episodes, about 300 MB, per
     batch) and `NAME` set. It returns at once; the page fetches the batch (about a minute), posts it and reloads.
     Wait until the receiver's output says `saved … <NAME>_Episode_<LAST>.mp4`, then run the next range.
  4. After each batch: `python3 SKILL_DIR/scripts/file_episodes.py <scratchpad>/inbox <Movie>`. It moves each video into
     `<Movie>/Episode_NN/`, downloads its `.zh.vtt` (Chinese auto-captions) and `.en.vtt` (machine translation, often
     misaligned: hints only), and prints the length against the listed length.
  5. When all are in: `pkill -f receive.py`.

  Some episodes have no captions at all (`NO SUBTITLES`). Split them (step 2), then make Chinese captions with the
  multilingual Whisper (the `mlx` environment). This takes about 20 s per episode:
  ```bash
  sh SKILL_DIR/scripts/run.sh mlx transcribe_zh.py <Episode_dir>/<Name>.mp4 --prompt "<the drama's names, in Chinese>"
  ```
  Its captions are usually better than TikTok's auto-captions. In the script's `note`, say the lines came from Whisper.
  (The Khmer Whisper used in section 7 can't hear Chinese.)
- **hongguoduanju.com** (红果短剧). `/player/<seriesID>` alone gives yt-dlp only a 10 s preview; throw such a file away.
  1. Open the full episode at `/player/<seriesID>/<episodeID>` in a browser your agent can drive.
  2. Read `document.querySelector('video').currentSrc` (or the `performance.getEntriesByType('resource')` entries with
     `mime_type=video_mp4`).
  3. curl it with `-e "https://hongguoduanju.com/"`.

  The website tops out at 360p; HD is app-only, so tell the user.

Confirm with `ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of compact <file>`.

## 2. Split voice and music

```bash
sh SKILL_DIR/scripts/separate.sh <Movie>/Episode_NN/<Name>.mp4
```

Writes `work/voice.wav` and `work/background_music.wav` (44.1 kHz): a few seconds on a GPU (Apple or CUDA), longer on a
CPU. Under loud lines the
background keeps a faint trace of the original voice; ducking hides most of it.

## 3. Get the lines and who says them

Use the platform's subtitles when there are any (`.vtt`/`.srt`). Then run:

```bash
sh SKILL_DIR/scripts/run.sh ai cues.py <Episode_dir>/<Name>.<lang>.vtt <Episode_dir>/work/voice.wav
```

It prints each line with the pitch of the original voice, and any stretch of speech that has no subtitle. Use that and the
story to assign speakers:

- Pitch:
  - about 85–160 Hz: a man
  - 180–400 Hz: a woman or child
  - in between (about 200–250 Hz): a eunuch or a boy
- Pitch 0 means it couldn't be measured (a whisper, a shout, or a deep voice under music). Decide from who is on screen and
  what is said.
- Auto-captions (`ASR`) mishear names and run two speakers' lines together. Fix words from context, and split a cue where
  the speaker changes, splitting its time too (e.g. "Summon the physician! — Yes, Your Majesty").
- Speech with no subtitle: listen to `voice.wav` around that time. It is usually a gasp or a name. Leave it undubbed
  unless it is a real line, and tell the user.
- No subtitles at all: say so and ask the user for a script or a subtitle file. Do not invent dialogue.

## 4. Cast (once per movie) and the Khmer script (each episode)

**`<Movie>/cast.json`** holds every character's voice, kept the same all series. Write it with the first episode, and in
later episodes only add new characters. A full example from a real episode is in `references/example_cast.json`:

```json
{
  "note": "original title, where the names come from, how foreign names are written in Khmer",
  "names": { "Lin Shen": "លីនសិន" },
  "voices": {
    "heroine": { "voice": "km-KH-SreymomNeural", "pitch": "+8Hz", "f0": [250, 380] },
    "emperor": { "voice": "km-KH-PisethNeural",  "pitch": "-8Hz", "f0": [85, 145] }
  }
}
```

**`<Episode_dir>/work/khmer_script.json`** holds the episode's lines. Example: `references/example_script.json`.

```json
{ "note": "where the lines came from and anything changed",
  "lines": [ { "start": 0.28, "end": 2.32, "speaker": "heroine", "km": "ជួយផង! គេនឹងសម្លាប់ខ្ញុំហើយ!" } ] }
```

Translate into natural spoken Khmer, not word-for-word.

- **Timing.** `start`/`end` are in seconds, from the subtitles. A line may run past `end` into the silence before the next
  line (the script fits it into that slot), so keep it no longer than the original takes to say it.
- **Voices by pitch.**
  - Keep each character's pitch the same all series, and at least ~10 Hz apart from anyone else on the same voice.
  - Starting points: lead woman `Sreymom +6..+10Hz`; second woman `Sreymom -4..-8Hz`; older woman `Sreymom -12Hz`; lead man
    `Piseth -6..-10Hz`; young man or boy `Piseth +10Hz`; eunuch `Piseth +25Hz`; old man `Piseth -15Hz`.
  - Pitch beyond about ±30 Hz sounds robotic.
  - An episode script may carry its own `"voices"` to add a one-off character or override the cast.
- **Short and speakable.** Khmer runs longer than Chinese, so cut filler rather than let a line be sped up a lot. Keep
  punctuation (`។`, `?`, `!`): Edge reads it as pauses and tone.
- **Register.** Match who speaks to whom:
  - court dramas: palace and royal words (ព្រះករុណា, ព្រះអង្គ, ទូលបង្គំ, ខ្ញុំម្ចាស់)
  - rough equals: ឯង/អញ
  - couples and families: បង/អូន

  Keep names the same in every episode (`cast.json` `names`).
- Keep innuendo and insults as mild as the original. In your reply, say where a joke was hard to carry over.

## 5. Dub and build the video

```bash
sh SKILL_DIR/scripts/run.sh tts khmer_dub.py <Movie>/Episode_NN/<Name>.mp4
```

It writes `<Name>_Khmer.mp4` and `.srt` beside the original.

- **Per-line report.** For each line it prints the length, its slot, the rate and tempo used, and `OVER by` if the line
  still doesn't fit.
- **Fitting a line.** Rate starts at +10% (drama pace) and rises to at most +60%; after that, tempo goes up to 1.25×. If a
  line is OVER, or above about +45%, shorten its Khmer and run again. A whole episode takes a minute or two and needs
  internet. Edge occasionally drops a request; the script retries.
- **Missing voice.** If a speaker has no voice in `cast.json`, the script stops and names the speaker.

Output:

- The video stream copied untouched (HEVC tagged `hvc1` so QuickTime and iPhone play it).
- AAC 192k at -14 LUFS with peaks ≤ -1.5 dBTP, and the music ducked 6 dB under speech.
- `<Name>_Khmer.srt` with the Khmer lines.

### A whole series (dozens of episodes)

Done one by one, 80 episodes take days of tool calls. Instead:

1. **Download everything first** (step 1, batches of about 20).
2. **Split all in the background** while you work on the scripts. Each episode takes about a minute on the GPU:
   `sh SKILL_DIR/scripts/dub_series.sh <Movie> split`.
3. **Write `cast.json` and episode 1's script yourself**, and dub episode 1 to hear the voices.
4. **Write a translation guide**, then have helpers write the scripts in parallel. Put the guide in a temporary folder. It
   holds:
   - the output format and the cast keys
   - the register rules and the names
   - the ASR mishearings you have seen
   - a story summary of the episodes you read
   - a one-line check command

   Give each helper (a subagent, if your agent has them; otherwise write them yourself) about 10 episodes, with fewer than 10 helpers in all. Tell each one to skim the captions
   of the episodes before its range for the story. Helpers write only `work/khmer_script.json`: no `cast.json` edits, no
   dubbing. They report new recurring characters, and you add those to `cast.json`.
5. **Make the names consistent before dubbing.** Helpers spell new names differently (one series had three spellings
   of "the Turks"). Count each name's spellings across all scripts, pick one, replace the others, and add every
   name to `cast.json` `names`. A change to `cast.json` re-dubs every episode, so do this first.
6. **Dub all** in the background: `JOBS=4 sh SKILL_DIR/scripts/dub_series.sh <Movie> dub`.
   - It dubs four episodes at a time. Each takes about 3 minutes, mostly waiting on Edge.
   - It skips episodes already dubbed, unless the script or `cast.json` changed.
   - It prints `OVER` counts and moves `khmer_lines/` to the Trash.
   - Run it again for episodes whose script or split wasn't ready yet.
7. **Spot-check before handing over.** Read a few scripts against the captions (speaker keys, names, register) and check
   loudness on 3–4 episodes.
8. **Optional extras:**
   - Hide subtitles burned into the picture and draw the Khmer ones over them:
     `sh SKILL_DIR/scripts/run.sh tts cover_subs.py <Name>_Khmer.mp4 --band top:bottom`.
     It blurs that band and writes `<Name>_Khmer_sub.mp4`, about twice the size because the picture is re-encoded.
     Show the user one episode before doing them all.
   - Join episodes into longer videos: `python3 SKILL_DIR/scripts/combine_parts.py <Movie> --min 420 --max 480`.
     It writes `<Movie>/Parts/01.mp4, 02.mp4 …`, their subtitles in `<Movie>/Parts/Subtitles/01.srt …`, and
     `Parts/parts.txt` (which episodes each part holds). It doesn't re-encode
     and never cuts an episode. `--long-names` writes `<Movie>_Part_PP_EpAA-BB.mp4` with its `.srt` beside it instead.
     Add `--suffix _Khmer_sub` to join the covered versions. Each episode's first seconds repeat the end of the one
     before; they stay in.
     `--logo <transparent.png>` puts a channel logo in the top-right corner, at 90 % opacity and 154 px wide. The video is
     re-encoded with x265, about 1.5 minutes per part. To make a logo that sits on black transparent, set alpha to
     the brightest channel and un-premultiply, then add a soft shadow so white text still reads on bright scenes.
     Ask the user for their logo; the skill has none of its own.

## 6. Check and hand over

```bash
ffprobe -v error -show_entries format=duration:stream=codec_name,codec_tag_string,width,height -of compact <Name>_Khmer.mp4
ffmpeg -hide_banner -i <Name>_Khmer.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|Peak:)" | tail -2
open <Name>_Khmer.mp4; open -R <Name>_Khmer.mp4
```

Duration should match the original, and loudness should be about -14 LUFS. Then tell the user, briefly:

- where the files are and the quality downloaded
- how many lines, and who voices whom (a small table)
- any line that was sped up a lot, and any speech left undubbed
- that the Khmer should get a native speaker's read (auto-caption sources especially)

To change a line later: edit its `km` in `khmer_script.json` (or a voice's `pitch` in `cast.json`, which changes it for
every episode), then run step 5 again.

## 7. Khmer subtitles from Khmer speech

For a video already spoken in Khmer (a reel, a vlog, an explainer) the user wants the words as text or subtitles. No TTS is
involved; the Khmer Whisper runs locally (the `ai` environment).

1. **Check for existing subtitles.** Look for a subtitle track (`ffprobe -show_streams`, `yt-dlp --list-subs`) and for
   text burned into the picture: look at 3–4 frames, `ffmpeg -ss <t> -i <video> -frames:v 1 -update 1 f.jpg`. If there is
   one, use it rather than transcribing.
2. **Clean voice:** `sh SKILL_DIR/scripts/separate.sh <Episode_dir>/<Name>.mp4`. With music under the words, Whisper does
   much worse.
3. **Draft:** `sh SKILL_DIR/scripts/run.sh ai transcribe_km.py <Episode_dir>/<Name>.mp4`.
   - It writes `work/draft.json` (and `draft.srt`): one entry per phrase, up to 6 s each.
   - Phrases still garbled after a retry are marked `"check": true`.
   - About 7 minutes for a 5-minute video on an Apple GPU, so run it in the background.
4. **Proofread into `work/subtitles.json`** (same shape: `[{ "start", "end", "text" }]`). This step decides the quality, so
   do it by hand, line by line:
   - Join phrases into whole sentences (keep the first `start` and the last `end`).
   - Fix spelling the model mangles. Common ones: ក្រូតាស→ក្រដាស, a QR code written out phonetically → QR កូដ, stray
     letters at the ends of words. Write numbers as spoken, in Khmer digits (២៤).
   - Rebuild garbled `check` phrases from the sentences around them and from what the video shows (look at a frame).
     Re-listen with a higher `repetition_penalty` if needed.
   - Don't invent words. Note every guess so it can be listed for the user.
5. **Write the files:** `python3 SKILL_DIR/scripts/make_srt.py <Episode_dir>/<Name>.mp4`. It writes `<Name>.km.srt`
   (sentences over 52 characters split at a space, so each fits on a phone screen) and `<Name>.km.txt` (the transcript,
   one sentence per line) beside the video.
6. Check it with `ffprobe <Name>.km.srt` (it should say `subrip`), then `open -R` it. Tell the user:
   - where the two files are
   - that it was a GPU Whisper draft, proofread by hand
   - the lines you were unsure of, each with its time

   Offer to burn the subtitles into the video.

Other spoken languages (a Chinese drama with no subtitles) are not covered: ask the user for a subtitle file.
