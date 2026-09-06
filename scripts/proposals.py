"""A/B/C proposal generators for drums, bass and a bridge chord bed.
The proposals are deliberately *different from each other* (rhythm, octave, note length,
rest placement) so that a human choice between them is a real musical decision.
Nothing here is 'final': the arrangement stage uses whatever human_decisions.json says,
and defaults to variant A only so that a preview exists before the human has chosen."""
from __future__ import annotations
import numpy as np
from analysis import KEY_NAMES, chord_to_midi_root

# ---------------------------------------------------------------- timing helpers

def beat_grid(beat_times: list[float], phase: int) -> list[dict]:
    """Return bars: each with 4 beat times (interpolated if the track ends mid-bar)."""
    bt = list(beat_times)
    bars = []
    i = phase
    while i + 1 < len(bt):
        beats = bt[i:i + 4]
        if len(beats) < 4:
            step = bt[i] - bt[i - 1] if i > 0 else 0.5
            while len(beats) < 4:
                beats.append(beats[-1] + step)
        bars.append({"bar": len(bars), "beats": beats, "end": bt[i + 4] if i + 4 < len(bt) else beats[-1] + (beats[-1] - beats[-2])})
        i += 4
    return bars


def sub(bar: dict, pos: float) -> float:
    """Time at beat position pos (1.0 = first beat, 2.5 = the 'and' of 2...)."""
    b = bar["beats"]; e = bar["end"]
    k = int(np.floor(pos - 1)); frac = pos - 1 - k
    k = max(0, min(3, k))
    nxt = b[k + 1] if k + 1 < 4 else e
    return b[k] + frac * (nxt - b[k])


def human_offset(rng, ms_range=(-9, 12)):
    return rng.uniform(ms_range[0], ms_range[1]) / 1000.0


# ---------------------------------------------------------------- drums

def drums_variant(variant: str, bars: list[dict], section_ends: set[int], seed: int = 11) -> list[dict]:
    rng = np.random.default_rng(seed + ord(variant))
    ev = []
    def add(t, inst, vel):
        ev.append({"time": float(t), "inst": inst, "vel": float(np.clip(vel, 0.05, 1.0))})
    for bar in bars:
        last = bar["bar"] in section_ends
        if variant == "A":  # straight pop/rock: kick 1 & 3, snare 2 & 4, 8th hats
            add(sub(bar, 1), "kick", 0.95); add(sub(bar, 3), "kick", 0.9)
            add(sub(bar, 2), "snare", 0.85); add(sub(bar, 4), "snare", 0.9)
            for p in np.arange(1, 5, 0.5):
                add(sub(bar, p) + human_offset(rng, (-4, 4)), "hat", 0.55 if p % 1 == 0 else 0.35)
            if last:
                for p in [4, 4.25, 4.5, 4.75]:
                    add(sub(bar, p), "snare", 0.5 + 0.12 * (p - 4) * 4 / 3)
        elif variant == "B":  # syncopated: kick 1, 2.5, 3.5 ; clap+snare 2 & 4 ; 16th hats accents ; open hat 4.5
            add(sub(bar, 1), "kick", 0.95); add(sub(bar, 2.5), "kick", 0.8); add(sub(bar, 3.5), "kick", 0.85)
            for p in (2, 4):
                add(sub(bar, p), "snare", 0.8); add(sub(bar, p) + 0.004, "clap", 0.7)
            for p in np.arange(1, 5, 0.25):
                acc = 0.6 if p % 1 == 0 else (0.42 if (p * 4) % 2 == 0 else 0.28)
                add(sub(bar, p) + human_offset(rng, (-5, 5)), "hat", acc)
            add(sub(bar, 4.5), "ohat", 0.5)
            if last:
                add(sub(bar, 4.5), "kick", 0.9); add(sub(bar, 4.75), "snare", 0.7); add(bar["end"], "crash", 0.6)
        else:  # C: half-time: kick 1 (+ghost 2.75), snare 3, 8th hats, shaker 16ths
            add(sub(bar, 1), "kick", 0.95); add(sub(bar, 2.75), "kick", 0.55)
            add(sub(bar, 3), "snare", 0.9)
            add(sub(bar, 4.5), "rim", 0.4)
            for p in np.arange(1, 5, 0.5):
                add(sub(bar, p) + human_offset(rng, (-4, 4)), "hat", 0.5 if p % 1 == 0 else 0.3)
            for p in np.arange(1, 5, 0.25):
                add(sub(bar, p) + human_offset(rng), "shaker", 0.25 + 0.15 * ((p * 4) % 2 == 0))
            if last:
                for p in [3.5, 3.75, 4, 4.5]:
                    add(sub(bar, p), "snare", 0.45 + 0.1 * p / 4)
                add(bar["end"], "crash", 0.5)
    return ev


DRUM_DESCRIPTIONS = {
    "A": "Straight pop/rock groove: kick on 1 & 3, snare on 2 & 4, 8th-note hats, snare-roll fill at section ends.",
    "B": "Syncopated: kicks on 1, 2.5, 3.5, clap layered on the snare, 16th-note hats with accents, open hat on 4.5.",
    "C": "Half-time: kick on 1 with a ghost kick, snare on 3, rim on 4.5, 8th hats plus a humanised 16th shaker.",
}

# ---------------------------------------------------------------- bass

def bass_variant(variant: str, bars: list[dict], bar_chords: list[str], octave: int = 2, seed: int = 21) -> list[dict]:
    rng = np.random.default_rng(seed + ord(variant))
    notes = []
    def note(s, e, midi, vel):
        notes.append({"start": float(s), "end": float(max(e, s + 0.05)), "midi": int(midi), "vel": float(np.clip(vel, 0.1, 1.0))})
    for i, bar in enumerate(bars):
        ch = bar_chords[i] if i < len(bar_chords) else bar_chords[-1]
        nxt = bar_chords[i + 1] if i + 1 < len(bar_chords) else ch
        root = chord_to_midi_root(ch, octave)
        fifth = root + 7
        nroot = chord_to_midi_root(nxt, octave)
        if variant == "A":  # long roots: whole note / half note, octave drop on bar 4 of a phrase
            if i % 4 == 3:
                note(sub(bar, 1), sub(bar, 3), root, 0.85); note(sub(bar, 3), bar["end"], root - 12 if root - 12 >= 24 else root, 0.8)
            else:
                note(sub(bar, 1), bar["end"] - 0.03, root, 0.85)
        elif variant == "B":  # 8th-note pulse, octave jump on 4.5, rest on 2.5 for air
            for p in np.arange(1, 5, 0.5):
                if p == 2.5:
                    continue
                m = root + 12 if p == 4.5 else root
                note(sub(bar, p), sub(bar, p) + 0.9 * (sub(bar, p + 0.5) - sub(bar, p)) if p < 4.5 else bar["end"], m, 0.7 + 0.2 * (p % 1 == 0) + rng.uniform(-0.05, 0.05))
        else:  # C: syncopated root / fifth / approach note into the next chord
            note(sub(bar, 1), sub(bar, 2), root, 0.9)
            note(sub(bar, 2.5), sub(bar, 3), fifth if fifth < root + 12 else root, 0.7)
            note(sub(bar, 3), sub(bar, 4), root, 0.85)
            approach = nroot - 1 if nroot > root else nroot + 1
            if nroot == root:
                approach = root + 7 if rng.random() < 0.5 else root - 5
            note(sub(bar, 4.5), bar["end"], approach, 0.65)
    return notes


BASS_DESCRIPTIONS = {
    "A": "Long root notes (whole/half), octave drop every 4th bar — warm, leaves room for the vocal.",
    "B": "Driving 8th-note pulse with a rest on the '2-and' and an octave jump on '4-and'.",
    "C": "Syncopated root–fifth pattern with a chromatic approach note into the next chord.",
}

# ---------------------------------------------------------------- bridge chord beds

def bridge_progressions(key: dict) -> dict:
    tonic = KEY_NAMES.index(key["tonic"])
    def n(semi, q=""):
        return KEY_NAMES[(tonic + semi) % 12] + q
    if key["mode"] == "major":
        return {
            "A": {"chords": [n(9, "m"), n(5), n(0), n(7)], "roman": "vi – IV – I – V", "mood": "familiar lift, resolves home"},
            "B": {"chords": [n(5), n(7), n(9, "m"), n(4, "m")], "roman": "IV – V – vi – iii", "mood": "suspended, bittersweet"},
            "C": {"chords": [n(2, "m"), n(7), n(0), n(9, "m")], "roman": "ii – V – I – vi", "mood": "jazzy turnaround"},
        }
    return {
        "A": {"chords": [n(0, "m"), n(8), n(3), n(10)], "roman": "i – VI – III – VII", "mood": "epic minor loop"},
        "B": {"chords": [n(5, "m"), n(10), n(3), n(0, "m")], "roman": "iv – VII – III – i", "mood": "descending, reflective"},
        "C": {"chords": [n(8), n(10), n(0, "m"), n(0, "m")], "roman": "VI – VII – i – i", "mood": "rock/anime drive"},
    }


def chord_freqs(name: str, octave: int = 3) -> list[float]:
    root = chord_to_midi_root(name, octave)
    third = root + (3 if name.endswith("m") else 4)
    return [440.0 * 2 ** ((m - 69) / 12) for m in (root, third, root + 7, root + 12)]
