# 🌿 사람+AI 편곡 튜토리얼 · AI-music → human+AI arrangement pipeline

**Read the tutorial:** [`docs/index.html`](docs/index.html) (deep-green tutorial with per-track results, priorities, install ranking, human steps, distributor comparison, fact-check, all links).

What this repo does, in one command per song:

```
pip install -r tools/requirements.txt        # or tools/install_windows.ps1 / tools/install_linux_mac.sh
python scripts/pipeline.py tracks/01_IronManBGM_Remix
python scripts/build_report.py               # regenerates docs/index.html
```

Stages: hash → analyze (tempo/key/sections/chords) → separate (Demucs htdemucs) → midi (Basic Pitch reference) →
proposals (drums/bass/bridge **A/B/C** previews) → arrange (new intro, new parts on the beat grid, breakdown) →
master (−14 LUFS, −1 dBTP, 16-bit FLAC + MP3 + A/B) → qc → evidence (hashes, tool versions, AI disclosure).

The **human steps come last** and are the only ones that create human contribution: choose A/B/C and edit notes
(`human_decisions.json`, schema in `.claude/skills/ai-music-human-arrange/schemas/`), hum a new melody
(`scripts/hum_to_midi.py`), record vocals (`scripts/vocal_prep.py`), listen to everything.

| folder | content |
|---|---|
| `tracks/NN_name/` | one song: original + hash, analysis, proposals, edits, master, QC, evidence (stems and float intermediates are git-ignored; regenerate with the pipeline) |
| `scripts/` | the pipeline (pure Python + ffmpeg, all free/open-source) |
| `tools/` | installers, requirements, Demucs weight fetcher |
| `.claude/skills/ai-music-human-arrange/` | reusable skill: SKILL.md + JSON schemas so the same run can be repeated on the next songs |
| `docs/` | `index.html` tutorial + `content.json` (editable text) |

Not legal advice. Nothing here certifies copyright ownership, distributor approval or Content ID eligibility.
Do not describe a track as "100% human" while AI-generated audio remains in it.
