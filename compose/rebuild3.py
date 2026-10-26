# -*- coding: utf-8 -*-
"""Rebuild the draft in three versions, correcting its harmony and bringing the
composer's own parts to the front.

What this does NOT do: write a melody, write a counter-line, or add a drum kit.
Every pitch that sounds is either a note the composer played, that same note moved
to fix a collision, or the root of a chord they themselves stated. The only new
thing is rhythm applied to their own pitches.

Three versions differ only in the low end:
  1  sustained sub-bass under the whole piece
  2  a sixteenth-note staccato pulse on their own bass pitches, entering in pass 2
  3  both at once
"""
from __future__ import annotations
import os, sys, json
import numpy as np
import pretty_midi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

NM = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
def nn(p): return f"{NM[p % 12]}{p // 12 - 1}"

# ---------------------------------------------------------------- the draft's own layout
BLOCK = 4.0          # one harmonic block, as the composer counts a "bar"
PASS2 = 16.0         # where the second statement should begin once the loop is squared
NBLK = 4

# Each block, after the harmony correction below.
#   root   : the chord root, for the low end
#   tones  : pitch classes the chord is allowed to use, for the choir
CHORDS = [
    {"name": "Dm",  "root": 2,  "tones": [2, 5, 9]},            # D  F  A
    {"name": "Bb",  "root": 10, "tones": [10, 2, 5]},           # Bb D  F
    {"name": "F",   "root": 5,  "tones": [5, 9, 0]},            # F  A  C
    {"name": "A7",  "root": 9,  "tones": [9, 1, 4, 7, 10]},     # A  C# E  G  (Bb = b9)
]
# Sub-bass roots, one per block, in the sub octave.
SUB = [38, 34, 41, 33]                   # D2  Bb1  F2  A1
# Pulse pitches: each one is a pitch the composer plays somewhere in the draft.
PULSE_ROOT = [50, 46, 53, 45]            # D3  Bb2  F3  A2
PULSE_ALT  = [57, 53, 48, 52]            # A3  F3   C3  E3
# Choir voicing per block, chord tones only, in a register under the ostinato.
# Block 4 deliberately omits the root A: the composer's ostinato plays A#4 (the b9 of A7,
# which is the sixth degree of D harmonic minor and therefore in key). Doubling the root
# underneath it would turn a spice into a minor-ninth collision, so the choir takes 3-5-7.
CHOIR = [[57, 62, 65],                   # A3  D4  F4
         [58, 62, 65],                   # Bb3 D4  F4
         [57, 60, 65],                   # A3  C4  F4
         [61, 64, 67]]                   # C#4 E4  G4


def load(path):
    pm = pretty_midi.PrettyMIDI(path)
    tracks = [[{"pitch": n.pitch, "start": float(n.start), "end": float(n.end), "vel": n.velocity}
               for n in sorted(i.notes, key=lambda x: (x.start, x.pitch))] for i in pm.instruments]
    tc, tt = pm.get_tempo_changes()
    return tracks, (float(tt[0]) if len(tt) else 120.0)


def shift(ns, dt):
    return [{**n, "start": n["start"] + dt, "end": n["end"] + dt} for n in ns]


def scale_vel(ns, g, lo=1, hi=127):
    return [{**n, "vel": int(np.clip(round(n["vel"] * g), lo, hi))} for n in ns]


def set_vel(ns, v):
    return [{**n, "vel": int(v)} for n in ns]


# ---------------------------------------------------------------- corrections
def square_loop(strings, first_pass_end=15.24):
    """The composer's second statement comes in 0.7-0.75 s early, which makes block 4 of the
    first pass 3.25 s instead of 4.0 s. Nudge the whole second statement so every block is
    4.0 s and a copy-paste of the lower parts lands on the right chord."""
    if not strings:
        return strings, 0.0
    tail = [n for n in strings if n["start"] >= first_pass_end]
    if not tail:
        return strings, 0.0
    dt = PASS2 - min(n["start"] for n in tail)
    head = [n for n in strings if n["start"] < first_pass_end]
    return head + shift(tail, dt), dt


def snap_early(ns, tol=0.16):
    """A note that belongs to the next chord but starts just before the barline is sounding
    against the old chord. Pull it onto the barline."""
    out, moved = [], 0
    for n in ns:
        t = n["start"]
        b = round(t / BLOCK) * BLOCK
        if 0 < b - t <= tol:
            out.append({**n, "start": b, "end": max(n["end"], b + 0.05)})
            moved += 1
        else:
            out.append(dict(n))
    return out, moved


def fix_piano_block3(piano):
    """Block 3: the piano states C major (C-G-C-E) while the string ostinato states F major
    (F-C-A) over it. E against F is a minor ninth. The ostinato runs through the whole piece,
    so the piano yields. Keeping C in the bass, two voices move one and two semitones:
    G3 -> A3 and E4 -> F4, giving F major over C."""
    out, log = [], []
    for n in piano:
        blk = int(n["start"] // BLOCK) % NBLK
        p = n["pitch"]
        if blk == 2 and p == 55:      # G3 -> A3
            out.append({**n, "pitch": 57}); log.append("G3(55) -> A3(57)")
        elif blk == 2 and p == 64:    # E4 -> F4
            out.append({**n, "pitch": 65}); log.append("E4(64) -> F4(65)")
        else:
            out.append(dict(n))
    return out, log


def unmask_bass(piano, bass):
    """The composer's Bass plays the same pitch in the same octave as the piano's bottom note,
    with the same onset, in every block: D3/D3, Bb2/Bb2, C3/C3, A2/A2. Three sources then sit
    in one narrow band and the bass line contributes nothing you can pick out - which is
    exactly the complaint. Drop the piano's doubled bottom note so the bass owns that register.
    Nothing is lost harmonically: the bass still states that pitch, and the sub states its root.
    """
    bass_at = {}
    for n in bass:
        bass_at.setdefault(round(n["start"] / BLOCK) * BLOCK, set()).add(n["pitch"])
    out, log = [], []
    for n in piano:
        b = round(n["start"] / BLOCK) * BLOCK
        low = min((q["pitch"] for q in piano if round(q["start"] / BLOCK) * BLOCK == b), default=None)
        if n["pitch"] == low and n["pitch"] in bass_at.get(b, ()):
            log.append(f"{nn(n['pitch'])}({n['pitch']}) @{b:.0f}s")
            continue
        out.append(dict(n))
    return out, log


def pedal_to_roots(pedal):
    """The composer's lowest track holds a single C2 under all four chords. It is in tune under
    block 3 only; under A7 the C natural sits a semitone under the chord's C#, which is the
    muddiest collision in the draft. Give it the root of each chord they already played."""
    out, log = [], []
    for n in pedal:
        blk = int(round(n["start"] / BLOCK)) % NBLK
        q = SUB[blk]
        out.append({**n, "pitch": q})
        log.append(f"{nn(n['pitch'])}({n['pitch']}) -> {nn(q)}({q})  block {blk+1} {CHORDS[blk]['name']}")
    return out, log


# ---------------------------------------------------------------- added low end and voices
def sustained_sub(passes=(0, 1), vel=96):
    """One root per block, held. Pitches are the roots of the composer's own chords.
    `passes` selects which statements get it, so a version can hand the low end over to
    the sixteenth pulse halfway through."""
    out = []
    for p in passes:
        for b in range(NBLK):
            t = p * PASS2 + b * BLOCK
            out.append({"pitch": SUB[b], "start": t, "end": t + BLOCK - 0.05,
                        "vel": vel if p == 0 else min(127, vel + 6)})
    return out


def pulse(t0, n_blocks=NBLK, gate=0.075, lo=26, hi=62):
    """The fine sixteenth-note pulse: short, quiet, and rising through each block.
    Only the composer's own pitches are used, so this adds rhythm, not melody."""
    out = []
    step = BLOCK / 32.0                      # sixteenths at 120 BPM
    for b in range(n_blocks):
        base = t0 + b * BLOCK
        for k in range(32):
            frac = k / 31.0
            v = lo + (hi - lo) * frac ** 1.6                 # crescendo across the block
            if k % 4 == 0: v += 6                            # light accent on each beat
            if k >= 24 and k % 2 == 1:
                p = PULSE_ALT[b]                             # lift into the next block
            else:
                p = PULSE_ROOT[b]
            t = base + k * step
            out.append({"pitch": p, "start": t, "end": t + gate,
                        "vel": int(np.clip(round(v), 1, 127))})
    return out


def choir(n_pass=2, vel_pass=(30, 46)):
    """Sustained chord tones only, in A3-F4, which is below the composer's D5-A5 ostinato
    so it fills the middle without covering their line."""
    out = []
    for p in range(n_pass):
        for b in range(NBLK):
            t = p * PASS2 + b * BLOCK
            for q in CHOIR[b]:
                out.append({"pitch": q, "start": t + 0.04, "end": t + BLOCK - 0.10,
                            "vel": vel_pass[min(p, len(vel_pass) - 1)]})
    return out


def write_midi(path, tempo, tracks):
    pm = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    for t in tracks:
        # mido writes track names as latin-1, so the file carries an ASCII label and the
        # Korean name lives in the report instead.
        label = t.get("midi_name") or t.get("name", "")
        label = label.encode("ascii", "ignore").decode("ascii").strip() or "track"
        inst = pretty_midi.Instrument(program=int(t.get("program", 0)),
                                      is_drum=False, name=label)
        for n in t["notes"]:
            inst.notes.append(pretty_midi.Note(
                velocity=int(np.clip(n.get("vel", 90), 1, 127)), pitch=int(n["pitch"]),
                start=float(n["start"]), end=float(max(n["end"], n["start"] + 0.04))))
        pm.instruments.append(inst)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    pm.write(path)
    return path
