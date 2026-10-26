# -*- coding: utf-8 -*-
"""Make an arrangement fuller WITHOUT writing any new melody.

Every added voice is derived from notes the composer already played:
  - octave doublings of their own lines (same pitch classes, different register)
  - a pad built only from the chord tones their piano already states
  - a sub-bass an octave or two below their own bass notes
  - voice-count thickening inside their own chords
The only genuinely new material is the drum pattern, which is accompaniment, and it is
labelled as such in the report. Nothing here invents a tune, so authorship of the music
stays with the person who played the chords and the ostinato.
"""
from __future__ import annotations
import os, sys, json
import numpy as np
import pretty_midi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from midi_theory import GM, NAMES

DRUM = {"kick": 36, "snare": 38, "hat": 42, "ohat": 46, "ride": 51, "crash": 49,
        "tom_lo": 45, "tom_hi": 50, "shaker": 70, "clap": 39}


def load(path):
    pm = pretty_midi.PrettyMIDI(path)
    out = []
    for inst in pm.instruments:
        out.append([{"pitch": n.pitch, "start": n.start, "end": n.end, "vel": n.velocity}
                    for n in sorted(inst.notes, key=lambda x: x.start)])
    tc, tt = pm.get_tempo_changes()
    return out, float(tt[0]) if len(tt) else 120.0


def octave(ns, shift, vel_scale=0.75, delay=0.0):
    """Same notes, different register. Not a new melody — the pitch classes are unchanged."""
    return [{"pitch": max(0, min(127, n["pitch"] + shift)), "start": n["start"] + delay,
             "end": n["end"] + delay, "vel": int(np.clip(n["vel"] * vel_scale, 1, 127))} for n in ns]


def chord_bed(chord_notes, bar_starts, bar_len, octaves=(0,), vel=52):
    """Hold the player's own chord tones across each bar. Adds no pitch they did not play."""
    out = []
    for i, t in enumerate(bar_starts):
        tones = chord_notes[i % len(chord_notes)]
        for o in octaves:
            for p in tones:
                q = p + 12 * o
                if 21 <= q <= 108:
                    out.append({"pitch": q, "start": t, "end": t + bar_len - 0.03, "vel": vel})
    return out


def drum_pattern(n_bars, bar_len, beat, style="steady", start=0.0):
    ev = []
    for b in range(n_bars):
        t = start + b * bar_len
        hard = (b % 8) in (6, 7)
        for p, inst, v in [(1, "kick", 104), (3, "kick", 96), (2, "snare", 98), (4, "snare", 102)]:
            ev.append({"pitch": DRUM[inst], "start": t + (p - 1) * beat, "end": t + (p - 1) * beat + 0.12,
                       "vel": v if not hard else min(127, v + 10)})
        if style == "steady":
            for k in range(8):
                ev.append({"pitch": DRUM["hat"], "start": t + k * beat / 2, "end": t + k * beat / 2 + 0.08,
                           "vel": 72 if k % 2 == 0 else 50})
        else:
            for k in range(16):
                ev.append({"pitch": DRUM["hat"], "start": t + k * beat / 4, "end": t + k * beat / 4 + 0.06,
                           "vel": 70 if k % 4 == 0 else (48 if k % 2 == 0 else 34)})
        if b % 8 == 0:
            ev.append({"pitch": DRUM["crash"], "start": t, "end": t + 0.6, "vel": 94})
        if b % 8 == 7:   # fill into the next phrase
            for k, p in enumerate([3, 3.5, 4, 4.5]):
                ev.append({"pitch": [DRUM["tom_hi"], DRUM["tom_hi"], DRUM["tom_lo"], DRUM["snare"]][k],
                           "start": t + (p - 1) * beat, "end": t + (p - 1) * beat + 0.1, "vel": 86 + k * 6})
    return ev


def write(path, tempo, tracks):
    pm = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    for t in tracks:
        inst = pretty_midi.Instrument(program=int(t.get("program", 0)),
                                      is_drum=bool(t.get("is_drum", False)), name=t.get("name", ""))
        for n in t["notes"]:
            inst.notes.append(pretty_midi.Note(velocity=int(np.clip(n.get("vel", 90), 1, 127)),
                                               pitch=int(n["pitch"]), start=float(n["start"]),
                                               end=float(max(n["end"], n["start"] + 0.03))))
        pm.instruments.append(inst)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    pm.write(path)
    return path
