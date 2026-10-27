# -*- coding: utf-8 -*-
"""Progressive orchestral build-up on top of the composer's own parts.

Everything is computed in BEATS, because that is the unit the Studio One project uses (the
song's tempo map is 0.4286 s/beat = 140 BPM and the .musicx note starts are beat positions).
A block is 8 beats. The composer's material is blocks 1-8 (two passes of Dm | Bb | F/C | A7).

Added here, all derived from their chords and bass notes:
  low strings bed, cello ostinato, low French horns, trombones, timpani and taiko,
  brass swells (MIDI expression, CC11), a reverse-cymbal swell, and two extra blocks:
  block 9  the driving cinematic-rock bar, on the tonic the A7 resolves to
  block 10 the final chorus, ending on a held Dm
Blocks 9 and 10 repeat the composer's own block-1 figures; no new melody is written.
"""
from __future__ import annotations
import os, subprocess, shutil
import numpy as np
import pretty_midi
import soundfile as sf

TEMPO = 140.0
BLK = 8.0
SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
FLUID = shutil.which("fluidsynth")
GM = {"strings1": 48, "strings2": 49, "cello": 42, "contrabass": 43, "horn": 60, "trombone": 57,
      "timpani": 47, "taiko": 116, "revcym": 119}
NM = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
def nn(p): return f"{NM[p % 12]}{p // 12 - 1}"
def sec(b): return b * 60.0 / TEMPO


# ---------------------------------------------------------------- reading their file
def load_beats(path):
    pm = pretty_midi.PrettyMIDI(path)
    t = float(pm.get_tempo_changes()[1][0])
    out = {}
    for i in pm.instruments:
        out[i.name] = [{"pitch": n.pitch, "start": n.start * t / 60.0, "end": n.end * t / 60.0,
                        "vel": n.velocity} for n in sorted(i.notes, key=lambda x: (x.start, x.pitch))]
    return out


def shift(ns, db): return [{**n, "start": n["start"] + db, "end": n["end"] + db} for n in ns]
def scale_vel(ns, g): return [{**n, "vel": int(np.clip(round(n["vel"] * g), 1, 127))} for n in ns]
def in_block(ns, b): return [n for n in ns if b * BLK - 1e-6 <= n["start"] < (b + 1) * BLK - 1e-6]


# ---------------------------------------------------------------- the harmony, one entry per block
# Chord of each block (0-based): Dm | Bb | F/C | A7 | Dm | Bb | F/C | A7 | Dm (new) | Dm (new)
N_BLOCKS = 22
# Five passes of the composer's four chords, then two blocks on the tonic the A7 resolves to.
CH = [0, 1, 2, 3] * 5 + [0, 0]
# Low strings bed: open fifths/thirds under the composer's own bass note.
# An octave above the composer's bass, so the bed never sits in the 95-190 Hz band their bass line lives in.
PAD   = [[57, 65], [53, 62], [57, 65], [52, 64]]            # A3 F4 | F3 D4 | A3 F4 | E3 E4
# Cello ostinato: root and a second chord tone, an octave and a half under their melody.
# Block 3 is F over THEIR C bass, so the cello stays on C (C2/C3): alternating C and F under a held C
# made the low end swing between two roots.
OST   = [(38, 45), (34, 41), (36, 48), (33, 40)]            # D A | Bb F | C C8 | A E
# Low French horns: their own bass note plus the fifth/fourth above it.
# Also above the bass register (it used to double their bass notes and bury them).
# Block 4 leaves out the root A: their own A#4 (the b9) rings above it and a root underneath turns it into a minor 9th.
LHORN = [[57, 62], [58, 65], [60, 65], [55, 64]]             # A3 D4 | Bb3 F4 | C4 F4 | G3 E4
# Trombones: root and fifth in the bottom octave, only for the closing blocks (tonic).
TBONE = [38, 45, 50]                                        # D2 A2 D3


def sustained(voicing, b, vel, length=BLK - 0.12, start=None):
    t0 = b * BLK if start is None else start
    return [{"pitch": p, "start": t0 + 0.02, "end": t0 + length, "vel": vel} for p in voicing]


def ramp(b0, b1, v0, v1, step=0.25, curve=1.6):
    """Expression (CC11) ramp across [b0, b1) beats - the swell."""
    n = max(2, int((b1 - b0) / step))
    return [(b0 + (b1 - b0) * k / (n - 1), v0 + (v1 - v0) * (k / (n - 1)) ** curve) for k in range(n)]


def cello_ostinato(blocks, vel_base=54, drive=False):
    """The low cello ostinato: a root/second-tone figure, eighth notes, one accent per beat.
    Repeating but pitched low and bowed short, which is the difference from the high
    tremolo it replaces."""
    out = []
    for b in blocks:
        root, alt = OST[CH[b]]
        for k in range(16):
            t = b * BLK + k * 0.5
            p = alt if k % 4 == 3 else root
            v = vel_base + (14 if k % 4 == 0 else 0) + (7 if k % 2 == 0 and not (k % 4 == 0) else 0)
            if drive and k % 4 == 0: v += 8
            out.append({"pitch": p, "start": t, "end": t + 0.42, "vel": int(np.clip(v, 1, 127))})
    return out


def timpani_pass2(b_first=4, b_last=7):
    """Soft, sparse: one hit on each block's downbeat, a quieter one on beat 5, and a short
    rising fill into the driving block."""
    out = []
    for b in range(b_first, b_last + 1):
        root = OST[CH[b]][0] + 12 if CH[b] != 3 else 45
        root = max(38, min(57, root))
        out.append({"pitch": root, "start": b * BLK, "end": b * BLK + 1.5, "vel": 60 + (b - b_first) * 8})
        out.append({"pitch": root, "start": b * BLK + 4, "end": b * BLK + 5.2, "vel": 46 + (b - b_first) * 8})
    b = b_last
    for k, (t, v) in enumerate([(6.0, 60), (6.5, 66), (7.0, 74), (7.5, 86)]):
        out.append({"pitch": 45, "start": b * BLK + t, "end": b * BLK + t + 0.4, "vel": v})
    return out


# The rock figure runs through all four chords in the long build, so its pitches follow the chord:
# timpani (the "kick") on a root, taiko (the "backbeat") on another chord tone.
KICK  = {0: 38, 1: 46, 2: 48, 3: 45}      # D2  Bb2  C3  A2
SNARE = {0: 45, 1: 53, 2: 45, 3: 52}      # A2  F3   A2  E3
TBONE_V = {0: [45, 53], 1: [41, 50], 2: [45, 53], 3: [40, 52]}   # trombones: A2 F3 | F2 D3 | A2 F3 | E2 E3


def rock_bar(b):
    """The driving cinematic-rock bar, with orchestral percussion instead of a kit: timpani
    where a kick would be, taiko where the backbeat would be, the low strings carrying the
    eighth-note drive."""
    timp, taiko = [], []
    c = CH[b]
    for half in range(2):
        t0 = b * BLK + half * 4
        for t in (0.0, 2.0, 2.5):                                  # kick figure
            timp.append({"pitch": KICK[c], "start": t0 + t, "end": t0 + t + 0.5, "vel": 104 if t == 0 else 92})
        for t in (1.0, 3.0):                                       # backbeat
            taiko.append({"pitch": SNARE[c], "start": t0 + t, "end": t0 + t + 0.5, "vel": 100})
    return timp, taiko


def finale_roll(t0, t1, v0=70, v1=118, step=0.125):
    """One timpani roll, a crescendo into the last chord. Used once, at the very end."""
    out, t, k = [], t0, 0
    n = int((t1 - t0) / step)
    while t < t1 - 1e-6:
        out.append({"pitch": 38, "start": t, "end": t + step * 0.95,
                    "vel": int(v0 + (v1 - v0) * (k / max(1, n - 1)) ** 1.8)})
        t += step; k += 1
    return out
