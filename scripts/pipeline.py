"""One command per track:  python scripts/pipeline.py tracks/01_xxx [--from STAGE] [--only STAGE]
Stages in order: hash, analyze, separate, midi, proposals, arrange, master, qc, evidence.
Each stage writes its own JSON so the run is inspectable and resumable; pipeline_log.json
records timings and errors. Re-run from 'arrange' after editing human_decisions.json."""
from __future__ import annotations
import os, sys, json, time, csv, argparse, traceback, shutil
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audiolib import load_audio, save_wav, sha256, measure, write_json, tool_versions
from analysis import analyze, bar_chords
from separate import separate
from proposals import (beat_grid, drums_variant, bass_variant, bridge_progressions, chord_freqs,
                       DRUM_DESCRIPTIONS, BASS_DESCRIPTIONS)
from synth import render_drums, render_notes, pad_chord, write_drum_midi, write_note_midi
from arrange import arrange, DEFAULT_DECISIONS
from master import master, qc

STAGES = ["hash", "analyze", "separate", "midi", "proposals", "arrange", "master", "qc", "evidence"]


def j(path):
    return json.load(open(path, encoding="utf-8"))


def stage_hash(td):
    src = os.path.join(td, "00_original", "original.wav")
    h = sha256(src)
    with open(os.path.join(td, "00_original", "sha256.txt"), "w") as f:
        f.write(f"{h}  original.wav\n")
    return {"sha256": h}


def stage_analyze(td):
    x, sr = load_audio(os.path.join(td, "00_original", "original.wav"))
    an = analyze(x, sr)
    an["bar_chords"] = [{"bar": b["bar"], "start": round(b["start"], 3), "chord": b["chord"]} for b in bar_chords(an)]
    write_json(os.path.join(td, "02_analysis", "analysis.json"), an)
    write_json(os.path.join(td, "02_analysis", "technical_original.json"), measure(os.path.join(td, "00_original", "original.wav")))
    return {"tempo": an["tempo_bpm"], "key": an["key"]["key"], "sections": len(an["sections"]), "bars": len(an["bar_chords"])}


def stage_separate(td):
    return separate(td)


def stage_midi(td):
    """Basic Pitch transcription of the separated stems -> reference MIDI (transcription aid only)."""
    from basic_pitch.inference import predict
    from basic_pitch import ICASSP_2022_MODEL_PATH
    sep = j(os.path.join(td, "01_stems", "separation.json"))
    out = os.path.join(td, "02_midi", "reference_from_stems")
    os.makedirs(out, exist_ok=True)
    res = {}
    for stem, kw in (("bass", dict(minimum_frequency=30, maximum_frequency=400)),
                     ("other", dict(minimum_frequency=60, maximum_frequency=2500)),
                     ("vocals", dict(minimum_frequency=80, maximum_frequency=1500, onset_threshold=0.6))):
        p = os.path.join(td, sep["stems_dir"], f"{stem}.wav")
        _, midi, notes = predict(p, ICASSP_2022_MODEL_PATH, **kw)
        mp = os.path.join(out, f"{stem}_basicpitch.mid")
        midi.write(mp)
        res[stem] = {"notes": len(notes), "midi": os.path.relpath(mp, td)}
    write_json(os.path.join(out, "transcription.json"), {"tool": "basic-pitch (Spotify), ICASSP 2022 model",
               "purpose": "reference/transcription only — not a human composition claim", "stems": res})
    return res


def stage_proposals(td):
    an = j(os.path.join(td, "02_analysis", "analysis.json"))
    x, sr = load_audio(os.path.join(td, "00_original", "original.wav"))
    bars = beat_grid(an["beat_times"], an["downbeat_phase"])
    bch = [b["chord"] for b in an["bar_chords"]]
    while len(bch) < len(bars):
        bch.append(bch[-1])
    # preview window: 8 bars starting at the first 'hook' section (or bar 8)
    hooks = [s for s in an["sections"] if s["label"] == "hook"]
    start_t = hooks[0]["start"] if hooks else (bars[8]["beats"][0] if len(bars) > 8 else 0.0)
    sb = [b for b in bars if b["beats"][0] >= start_t - 0.05][:8]
    t0 = sb[0]["beats"][0]; t1 = sb[-1]["end"]
    L = t1 - t0
    out = os.path.join(td, "03_proposals")
    os.makedirs(out, exist_ok=True)
    bed = x[int(t0 * sr):int(t1 * sr)]
    bed = bed * (10 ** ((-20 - 20 * np.log10(np.sqrt(np.mean(bed ** 2)) + 1e-9)) / 20))  # bed at -20 dB RMS under the proposal
    listing = {"preview_window_orig_s": [round(t0, 3), round(t1, 3)], "bars": [b["bar"] for b in sb], "drums": {}, "bass": {}, "bridge": {}}
    ends = {sb[-1]["bar"], sb[3]["bar"]}
    for v in "ABC":
        ev = drums_variant(v, sb, ends)
        for e in ev:
            e["time"] -= t0
        d = render_drums(ev, sr, L)[: len(bed)]
        nt = bass_variant(v, sb, [bch[b["bar"]] for b in sb])
        for nn in nt:
            nn["start"] -= t0; nn["end"] -= t0
        bs = render_notes(nt, sr, L)[: len(bed)]
        for name, sig, mid_fn in (("drums", d, lambda p: write_drum_midi(p, ev, an["tempo_bpm"])),
                                  ("bass", bs, lambda p: write_note_midi(p, nt, an["tempo_bpm"]))):
            mix = sig / (np.max(np.abs(sig)) + 1e-9) * 0.7 + bed * 0.5
            save_wav(os.path.join(out, f"{name}_{v}_preview.wav"), mix, sr, subtype="PCM_16", dither=True)
            mid_fn(os.path.join(out, f"{name}_{v}.mid"))
        write_json(os.path.join(out, f"bass_{v}_notes.json"), [dict(n, index=i) for i, n in enumerate(nt)])
        write_json(os.path.join(out, f"drums_{v}_events.json"), [dict(e, index=i) for i, e in enumerate(ev)])
        listing["drums"][v] = {"description": DRUM_DESCRIPTIONS[v], "events": len(ev), "preview": f"drums_{v}_preview.wav"}
        listing["bass"][v] = {"description": BASS_DESCRIPTIONS[v], "notes": len(nt), "preview": f"bass_{v}_preview.wav"}
    bp = bridge_progressions(an["key"])
    bar_len = 60 / an["tempo_bpm"] * 4
    for v, info in bp.items():
        pad = np.concatenate([pad_chord(chord_freqs(c, 3), bar_len, sr, vel=0.7, attack=0.1, release=0.3) for c in info["chords"] * 2])
        save_wav(os.path.join(out, f"bridge_{v}_chords_preview.wav"), pad / (np.max(np.abs(pad)) + 1e-9) * 0.7, sr, subtype="PCM_16", dither=True)
        notes = []
        t = 0.0
        for c in info["chords"] * 2:
            from analysis import chord_to_midi_root
            r = chord_to_midi_root(c, 3)
            for m in (r, r + (3 if c.endswith("m") else 4), r + 7):
                notes.append({"start": t, "end": t + bar_len, "midi": m, "vel": 0.7})
            t += bar_len
        write_note_midi(os.path.join(out, f"bridge_{v}_chords.mid"), notes, an["tempo_bpm"], program=88, name=f"Bridge {v} pad")
        listing["bridge"][v] = {**info, "bars": 8, "preview": f"bridge_{v}_chords_preview.wav",
                                "melody": "none yet — the human hums/sings the bridge melody over this bed (scripts/hum_to_midi.py)"}
    # small MP3 copies of every preview for the report / repo (WAVs stay local)
    import subprocess
    from audiolib import FFMPEG
    for f in sorted(os.listdir(out)):
        if f.endswith("_preview.wav"):
            subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", os.path.join(out, f), "-codec:a", "libmp3lame", "-b:a", "192k",
                            os.path.join(out, f.replace(".wav", ".mp3"))], check=True)
    listing["how_to_choose"] = ("Listen to *_preview.mp3, then write human_decisions.json (see skill schema) with drums.choice, "
                                "bass.choice and bridge.choice, and re-run: pipeline.py <track> --from arrange. "
                                "For NOTE EDITS use the index fields in 04_edits/midi/new_notes.json (written by that run) — "
                                "the indices in this folder belong to the 8-bar audition only. Drum edits can also be addressed "
                                "by bar+beat+inst via action 'remove_at', which survives re-renders.")
    write_json(os.path.join(out, "proposals.json"), listing)
    return {"window": listing["preview_window_orig_s"], "variants": 3}


def stage_arrange(td):
    an = j(os.path.join(td, "02_analysis", "analysis.json"))
    sep = j(os.path.join(td, "01_stems", "separation.json"))
    m = arrange(td, an, sep["stems_dir"])
    return {"intro_s": m["intro"]["len_s"], "changed": [c["output_range"] for c in m["changed_sections"]],
            "counts": m["new_midi_counts"], "duration_out": m["duration_out_s"]}


def stage_master(td):
    m = j(os.path.join(td, "04_edits", "arrangement_manifest.json"))
    return master(td, m)


def stage_qc(td):
    q = qc(td)
    return {"pass": q["all_technical_checks_pass"], "lufs": q["distributor_flac"]["lufs_integrated"], "tp": q["distributor_flac"]["true_peak_dbtp_4x"]}


def stage_evidence(td):
    ev = os.path.join(td, "07_evidence")
    os.makedirs(ev, exist_ok=True)
    rows = []
    for root, _, files in os.walk(td):
        for f in files:
            p = os.path.join(root, f)
            if p.startswith(ev) or f.endswith(".part"):
                continue
            rows.append({"path": os.path.relpath(p, td), "bytes": os.path.getsize(p), "sha256": sha256(p)})
    with open(os.path.join(ev, "file_hashes.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "bytes", "sha256"]); w.writeheader(); w.writerows(sorted(rows, key=lambda r: r["path"]))
    write_json(os.path.join(ev, "tool_versions.json"), tool_versions())
    if not os.path.exists(os.path.join(td, "human_decisions.json")):
        tmpl = {**DEFAULT_DECISIONS, "_status": "TEMPLATE — no human decision recorded yet",
                "decided_by": "", "decided_at": "", "notes": "",
                "_help": "Set drums.choice / bass.choice / bridge.choice to A, B or C after listening to 03_proposals/*_preview.mp3. "
                         "Then run the pipeline once with --from arrange and read 04_edits/midi/new_notes.json: "
                         "edits reference the 'index' fields THERE (the 8-bar audition lists in 03_proposals/ are a shorter, "
                         "different list). Position-based drum edits (action 'remove_at' with bar+beat+inst) are stable across re-renders."}
        write_json(os.path.join(ev, "human_decisions.TEMPLATE.json"), tmpl)
    sep = j(os.path.join(td, "01_stems", "separation.json"))
    man = j(os.path.join(td, "04_edits", "arrangement_manifest.json"))
    disc = f"""AI DISCLOSURE — {os.path.basename(td)}
Source audio: user-supplied file (stated by the user to be generated with Suno under a paid plan; receipt / song ID / URL / generation date NOT verified in this session).
This session (automated, local, no human performance):
  - stem estimation: {sep['backend']}  (sum correlation {sep.get('sum_correlation')})
  - transcription aid: Basic Pitch (reference MIDI only, not claimed as human composition)
  - new programmed parts: drums variant {man['decisions_used']['drums']['choice']}, bass variant {man['decisions_used']['bass']['choice']}, pad, intro, riser
    ({man['new_midi_counts']['drum_events']} drum events / {man['new_midi_counts']['bass_notes']} bass notes / {man['new_midi_counts']['pad_chords']} pad chords) — auto-generated data, not a human performance
  - structure: new {man['intro']['bars']}-bar intro, breakdown {'yes' if man['breakdown'] else 'no'}, tail trimmed {man['tail_trimmed_s']} s
  - mix/master: gain automation, 20 Hz HPF, M/S width, loudness normalisation, oversampled limiter
NOT done: main melody rewrite, re-harmonisation of the whole song, new human vocal or instrument performance, manual spectral repair, full human listening.
Decisions used: {man['decisions_used']['_source']}
Do not describe this file as "100% human" while AI-generated audio remains in it.
"""
    with open(os.path.join(ev, "AI_DISCLOSURE.txt"), "w", encoding="utf-8") as f:
        f.write(disc)
    return {"files_hashed": len(rows)}


def run(td: str, start: str = "hash", only: str | None = None):
    td = td.rstrip("/")
    logp = os.path.join(td, "pipeline_log.json")
    log = j(logp) if os.path.exists(logp) else {"track": os.path.basename(td), "stages": {}}
    todo = [only] if only else STAGES[STAGES.index(start):]
    for st in todo:
        t0 = time.time()
        try:
            r = globals()[f"stage_{st}"](td)
            log["stages"][st] = {"ok": True, "seconds": round(time.time() - t0, 1), "result": r}
            print(f"[{os.path.basename(td)}] {st}: ok {round(time.time()-t0,1)}s {json.dumps(r, ensure_ascii=False)[:300]}", flush=True)
        except Exception as e:
            log["stages"][st] = {"ok": False, "seconds": round(time.time() - t0, 1), "error": repr(e), "trace": traceback.format_exc()[-2000:]}
            print(f"[{os.path.basename(td)}] {st}: FAILED {e!r}", flush=True)
            write_json(logp, log)
            raise
        write_json(logp, log)
    return log


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("track_dir")
    ap.add_argument("--from", dest="start", default="hash", choices=STAGES)
    ap.add_argument("--only", default=None, choices=STAGES)
    a = ap.parse_args()
    run(a.track_dir, a.start, a.only)
