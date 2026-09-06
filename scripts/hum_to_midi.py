"""Human step helper: turn a hummed/sung melody (phone recording) into MIDI + a note list.
   python scripts/hum_to_midi.py 03_human_raw/bridge_hum.wav --key "D minor" --bpm 148 --out 03_human_raw/bridge_hum
Uses Basic Pitch for the transcription and then (optionally) snaps notes to the song key and to a
16th-note grid, keeping the *raw* transcription next to the snapped one so the human origin
of the melody is documented (raw = what you sang; snapped = tidied for the arrangement)."""
from __future__ import annotations
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audiolib import write_json, sha256
from analysis import KEY_NAMES

SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}


def snap_pitch(m, tonic, mode):
    pcs = [(tonic + s) % 12 for s in SCALES[mode]]
    best = min(range(m - 2, m + 3), key=lambda k: (0 if k % 12 in pcs else 1, abs(k - m)))
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--key", default=None, help='e.g. "D minor" (from 02_analysis/analysis.json)')
    ap.add_argument("--bpm", type=float, default=None)
    ap.add_argument("--grid", type=int, default=4, help="subdivisions per beat to snap to (4 = 16th notes)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    from basic_pitch.inference import predict
    from basic_pitch import ICASSP_2022_MODEL_PATH
    out = a.out or os.path.splitext(a.audio)[0]
    _, midi, notes = predict(a.audio, ICASSP_2022_MODEL_PATH, minimum_frequency=70, maximum_frequency=1200, onset_threshold=0.5, minimum_note_length=90)
    midi.write(out + "_raw.mid")
    # basic-pitch amplitudes are already 0..1 (it writes MIDI velocity = round(127*amplitude))
    raw = [{"start": float(s), "end": float(e), "midi": int(p), "vel": float(np.clip(v, 0.05, 1.0))} for (s, e, p, v, *_rest) in notes]
    raw.sort(key=lambda n: n["start"])
    snapped = []
    tonic = mode = None
    if a.key:
        t, m = a.key.split(); tonic, mode = KEY_NAMES.index(t), m
    for n in raw:
        s, e, p = n["start"], n["end"], n["midi"]
        if a.bpm:
            step = 60 / a.bpm / a.grid
            s = round(s / step) * step; e = max(s + step, round(e / step) * step)
        if tonic is not None:
            p = snap_pitch(p, tonic, mode)
        snapped.append({"start": round(s, 4), "end": round(e, 4), "midi": p, "vel": n["vel"]})
    import pretty_midi
    pm = pretty_midi.PrettyMIDI(initial_tempo=a.bpm or 120)
    inst = pretty_midi.Instrument(program=73, name="Hummed melody (snapped)")
    for n in snapped:
        inst.notes.append(pretty_midi.Note(velocity=int(max(1, min(127, n["vel"] * 127))), pitch=n["midi"], start=n["start"], end=n["end"]))
    pm.instruments.append(inst)
    pm.write(out + "_snapped.mid")
    write_json(out + "_notes.json", {"source_audio": os.path.basename(a.audio), "source_sha256": sha256(a.audio),
               "origin": "HUMAN — hummed/sung by the user; Basic Pitch only transcribed it",
               "key": a.key, "bpm": a.bpm, "raw_notes": raw, "snapped_notes": snapped})
    print(f"{len(raw)} notes -> {out}_raw.mid / {out}_snapped.mid / {out}_notes.json")


if __name__ == "__main__":
    main()
