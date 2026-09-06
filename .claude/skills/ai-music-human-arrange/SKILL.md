---
name: ai-music-human-arrange
description: Re-arrange an AI-generated song (Suno etc.) into a documented human+AI production - stem separation, A/B/C drum/bass/bridge proposals, structure edit, mix/master, technical QC, evidence package, tutorial report. Use when the user drops WAV/MP3 songs and asks to "편곡", "arrange", "QC", "prepare for distribution", "human contribution", or wants the ai-music pipeline re-run after editing human_decisions.json.
---

# AI-music → human+AI arrangement pipeline

Everything below is automated by `scripts/pipeline.py`; the human parts are deliberately **last**
(choose A/B/C, hum a melody, sing) and are recorded in `human_decisions.json` so that the
creative decisions have a paper trail. Never claim a file is "100% human" while AI audio remains.

## 0. Prerequisites (free stack)
- Python 3.10/3.11, ffmpeg on PATH, `pip install -r tools/requirements.txt` (torch CPU build is fine).
- Demucs weights: first run downloads `955717e8-8726e21a.th`; if the host is blocked use
  `tools/get_demucs_weights.sh` (S3 path-style URL) or copy the file to `~/.cache/torch/hub/checkpoints/`.
- Optional on the user's PC: REAPER + Reaper-MCP, MAutoPitch/Graillon 3 Free, Seed-VC (see docs/index.html §2).

## 1. Intake (agent)
1. Copy each song to `tracks/NN_name/00_original/original.wav` (never edit it). Hash it.
2. Ask/record provenance: generator, paid plan, song ID/URL, generation date, receipt → `07_evidence/` (unverified until the user supplies files).

## 2. Run the pipeline (agent)
```
python scripts/pipeline.py tracks/NN_name            # all stages
python scripts/pipeline.py tracks/NN_name --from arrange   # after human_decisions.json changes
python scripts/pipeline.py tracks/NN_name --only qc
```
Stages: hash → analyze (tempo/key/sections/chords, `02_analysis/`) → separate (Demucs htdemucs or
classical fallback, `01_stems/`) → midi (Basic Pitch reference MIDI, `02_midi/`) → proposals
(A/B/C drums, bass, bridge chord beds + MP3 previews, `03_proposals/`) → arrange (`04_edits/`,
`05_mix/premaster.wav`) → master (`06_master/`: 24-bit WAV, 16-bit FLAC, LISTEN mp3, A/B mp3) →
qc (`06_master/qc.json`) → evidence (`07_evidence/`: hashes, tool versions, AI_DISCLOSURE.txt).

Priority of what the automation applies (from the distribution brief):
1. stem separation → re-arrangement  2. structure re-edit (intro, breakdown, tail)
3. mix/master  4. synth/drum layers  — then the human items below.

## 3. Human steps (user) — do these last, in this order
1. **Choose**: listen to `03_proposals/*_preview.mp3`, write `tracks/NN_name/human_decisions.json`
   (schema: `schemas/human_decisions.schema.json`), include at least one note edit + a `notes` sentence.
   Re-run `--from arrange`.
2. **Hum a new melody** (bridge or hook) with headphones → `03_human_raw/bridge_hum.wav` →
   `python scripts/hum_to_midi.py 03_human_raw/bridge_hum.wav --key "<key>" --bpm <bpm>`.
3. **Sing** 2–3 takes (phone is fine: headphones, effects off, WAV, 15–25 cm) → `03_human_raw/TAKE_01.wav`…
   `python scripts/vocal_prep.py 03_human_raw/TAKE_01.wav --track tracks/NN_name --start <output_s> [--key "<key>" --tune]`
   then `python scripts/pipeline.py tracks/NN_name --from master`.
4. **Listen** to `06_master/LISTEN_arranged.mp3` and `AB_*.mp3` fully. Only then consider distribution.

## 4. Report (agent)
`python scripts/build_report.py` regenerates `docs/index.html` (tutorial + per-track results + links).
Commit: JSON, MIDI, MP3/FLAC, docs, scripts. Stems/float intermediates stay local (.gitignore).

## 5. Rules
- Original files and RAW human takes are never modified in place; every output has a hash.
- Automated MIDI is labelled as automated; only `human_decisions.json`, hummed melodies and recorded takes count as human contribution.
- Distributor/copyright policy changes fast: re-check the links in docs/index.html §9 on submission day.
