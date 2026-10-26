# -*- coding: utf-8 -*-
"""Turn the corrected draft into an orchestral score, and mix it like one.

No drum kit, no synth bass, no oom-pah pulse. The motion comes from the things an
orchestra actually uses for it: tremolo strings, pizzicato, a soft timpani roll, and a
glockenspiel for the bright ring on top. Every pitch is still one the composer played or
a chord tone of a chord they stated; the melody is theirs and stays untouched except for
straightening the ragged last block onto the beat.

The mix renders each instrument on its own, seats it across the stereo field the way an
orchestra sits, and sends it to a synthesized concert-hall reverb. That, not compression,
is what makes it sound full.
"""
from __future__ import annotations
import os, sys, subprocess, shutil
import numpy as np
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rebuild3 import BLOCK, PASS2, NBLK, CHORDS, SUB, nn   # noqa: E402

FLUID = shutil.which("fluidsynth")
SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"

# General MIDI, 0-based.
GM = {"violin": 40, "viola": 41, "cello": 42, "contrabass": 43, "tremolo": 44,
      "pizzicato": 45, "harp": 46, "timpani": 47, "strings1": 48, "strings2": 49,
      "choir": 52, "horn": 60, "glock": 9, "celesta": 8, "tubular": 14, "piano": 0}

# ---------------------------------------------------------------- the composer's own notes

# Block 4's string line is the one place the composer's playing drifts off the beat: the
# other three blocks sit exactly on the eighth-note grid, block 4 does not, and it holds
# 15 notes where the pattern wants 16. Their own four-note grouping is
#   [C#5 E5 G5 E5] [C#5 E5 G5 C#5] [A4 C#5 E5 C#5] [A#4 C#5 E5 _]
# so the missing sixteenth is the C#5 that makes the last group match the third. That is
# the only note added to their line, and it completes a figure they wrote themselves.
BLOCK4_CELL = [73, 76, 79, 76,  73, 76, 79, 73,  69, 73, 76, 73,  70, 73, 76, 73]


def straighten_block4(notes, gate=0.23):
    """Put block 4 of each pass back on the eighth-note grid, keeping the composer's own
    pitch order and completing their four-note grouping."""
    out, fixed = [], []
    for p in (0, 1):
        t0 = p * PASS2 + 3 * BLOCK
        inside = sorted([n for n in notes if t0 <= n["start"] < t0 + BLOCK],
                        key=lambda n: n["start"])
        if not inside:
            continue
        vel = [n["vel"] for n in inside]
        played = [n["pitch"] for n in inside]
        if played != BLOCK4_CELL[:len(played)]:
            # the take does not match the expected figure; leave it alone rather than guess
            out.extend(dict(n) for n in inside)
            continue
        step = BLOCK / 16.0
        for i, q in enumerate(BLOCK4_CELL):
            t = t0 + i * step
            out.append({"pitch": q, "start": t, "end": t + gate,
                        "vel": vel[i] if i < len(vel) else vel[-1]})
        fixed.append((p, len(inside), len(BLOCK4_CELL)))
    kept = [dict(n) for n in notes if not any(
        p * PASS2 + 3 * BLOCK <= n["start"] < p * PASS2 + 4 * BLOCK for p in (0, 1))]
    return sorted(kept + out, key=lambda n: (n["start"], n["pitch"])), fixed


def fill_blocks(notes, tail=0.05):
    """The composer's held notes stop early - the bass covers only 49% of block 1, and the
    chords leave a 0.44 s hole before every re-attack. Hold each to the end of its block.
    Duration only; no pitch and no onset moves."""
    out, grown = [], 0
    for n in notes:
        b = int(n["start"] // BLOCK) * BLOCK
        want = b + BLOCK - tail
        if n["end"] < want - 0.02:
            grown += 1
            out.append({**n, "end": want})
        else:
            out.append(dict(n))
    return out, grown


def horn_voicing_block4(piano):
    """Block 4 is A7: the composer's strings supply the seventh (G5) while their chord
    states a bare A triad, and their own A#4 then rings a minor ninth above the chord's
    root A3. Moving that one root to G3 - a pitch already in their block-4 material as G5 -
    makes the chord a proper A7 upper structure (G-C#-E) and leaves no root directly under
    the A#. One note, two semitones. Their A# stays exactly as they played it."""
    out, log = [], []
    for n in piano:
        blk = int(n["start"] // BLOCK) % NBLK
        if blk == 3 and n["pitch"] == 57:
            out.append({**n, "pitch": 55}); log.append("A3(57) -> G3(55)")
        else:
            out.append(dict(n))
    return out, log


# ---------------------------------------------------------------- orchestral colour

# Explicit voicings rather than "take the first three chord tones": block 4 deliberately
# omits the root A, because the composer's own A#4 (the b9) rings above it and a root
# underneath would turn their colour note into a minor-ninth collision.
TREM = [[50, 53, 57],   # Dm  D3 F3 A3
        [50, 53, 58],   # Bb  D3 F3 Bb3
        [53, 57, 60],   # F   F3 A3 C4
        [52, 55, 61]]   # A7  E3 G3 C#4   (no A)
PIZZ = [(50, 57),       # Dm  D3 -> A3
        (46, 53),       # Bb  Bb2 -> F3
        (53, 60),       # F   F3 -> C4
        (45, 52)]       # A7  A2 -> E3


def tremolo(voicings=None, passes=(1,), rate=16, vel=(26, 48)):
    """Tremolo strings: the orchestra's own way of making a fine, shimmering subdivision.
    Unlike a staccato pulse it has no accent pattern, so it drives without an oom-pah.
    Only chord tones the composer stated, in a register under their melody."""
    voicings = voicings or TREM
    out = []
    step = BLOCK / rate
    for p in passes:
        for b in range(NBLK):
            t0 = p * PASS2 + b * BLOCK
            tones = voicings[b]
            for k in range(rate):
                frac = k / (rate - 1)
                v = vel[0] + (vel[1] - vel[0]) * frac ** 1.4
                for q in tones:
                    out.append({"pitch": q, "start": t0 + k * step,
                                "end": t0 + k * step + step * 0.92,
                                "vel": int(np.clip(round(v), 1, 127))})
    return out


def pizzicato(pairs=None, passes=(1,), rate=8, vel=(34, 62)):
    """Pizzicato strings on the composer's own bass pitches: the fine, broken-up motion
    they asked for, plucked by a section instead of stamped out by a synth."""
    pairs = pairs or PIZZ
    out = []
    step = BLOCK / rate
    for p in passes:
        for b in range(NBLK):
            t0 = p * PASS2 + b * BLOCK
            root, alt = pairs[b]
            for k in range(rate):
                frac = k / (rate - 1)
                q = root if k % 4 != 3 else alt
                out.append({"pitch": q, "start": t0 + k * step, "end": t0 + k * step + 0.10,
                            "vel": int(np.clip(round(vel[0] + (vel[1] - vel[0]) * frac ** 1.4), 1, 127))})
    return out


def timpani(passes=(1,), vel=(30, 76), rolls=24):
    """A soft timpani roll on the roots the composer played, swelling into each block.
    Quiet enough to be felt rather than heard."""
    out = []
    for p in passes:
        for b in range(NBLK):
            t0 = p * PASS2 + b * BLOCK
            q = SUB[b] + 12                     # D3 Bb2 F3 A2 - timpani, not sub territory
            for k in range(rolls):
                frac = k / (rolls - 1)
                t = t0 + k * (BLOCK / rolls)
                out.append({"pitch": q, "start": t, "end": t + BLOCK / rolls,
                            "vel": int(np.clip(round(vel[0] + (vel[1] - vel[0]) * frac ** 2.2), 1, 127))})
    return out


def glock(passes=(0, 1), vel=58, lo=84, hi=96):
    """The bright ring on top - a glockenspiel, very quiet, only at the chord changes and
    the midpoint of each block. Chord tones only. This is the 'ping' with no drum in it."""
    out = []
    for p in passes:
        for b in range(NBLK):
            t0 = p * PASS2 + b * BLOCK
            tones = [q for q in range(lo, hi + 1) if q % 12 in CHORDS[b]["tones"]]
            if not tones:
                continue
            out.append({"pitch": tones[0], "start": t0 + 0.02, "end": t0 + 1.3, "vel": vel})
            if len(tones) > 1:
                out.append({"pitch": tones[1], "start": t0 + BLOCK / 2, "end": t0 + BLOCK / 2 + 1.0,
                            "vel": max(1, vel - 12)})
            if len(tones) > 2:
                out.append({"pitch": tones[2], "start": t0 + BLOCK * 0.75,
                            "end": t0 + BLOCK * 0.75 + 0.8, "vel": max(1, vel - 20)})
    return out


# ---------------------------------------------------------------- hall and seating

def hall_ir(sr=44100, rt_low=2.6, rt_mid=2.1, rt_high=1.0, predelay_ms=24.0, seed=7):
    """A concert hall, built rather than sampled: discrete early reflections, then three
    noise tails whose decay times shorten with frequency, which is how a real room behaves
    and why it sounds like space instead of a metallic ring."""
    n = int(max(rt_low, rt_mid, rt_high) * sr)
    t = np.arange(n) / sr
    rng = np.random.default_rng(seed)
    ir = np.zeros((n, 2))
    for lo, hi, rt, g in [(None, 400.0, rt_low, 0.9), (400.0, 3000.0, rt_mid, 1.0),
                          (3000.0, None, rt_high, 0.55)]:
        noise = rng.standard_normal((n, 2))
        if lo is None:
            sos = signal.butter(4, hi, btype="lowpass", fs=sr, output="sos")
        elif hi is None:
            sos = signal.butter(4, lo, btype="highpass", fs=sr, output="sos")
        else:
            sos = signal.butter(4, [lo, hi], btype="bandpass", fs=sr, output="sos")
        ir += signal.sosfilt(sos, noise, axis=0) * (10 ** (-3 * t / rt))[:, None] * g
    # early reflections, before the diffuse tail arrives
    for ms, g, pan in [(11, .46, -.7), (17, .38, .6), (23, .32, .25), (31, .26, -.4),
                       (43, .20, .5), (57, .15, -.2)]:
        i = int(ms / 1000 * sr)
        if i < n:
            ir[i, 0] += g * (1 - pan) / 2 * 2
            ir[i, 1] += g * (1 + pan) / 2 * 2
    pre = int(predelay_ms / 1000 * sr)
    ir = np.vstack([np.zeros((pre, 2)), ir])
    ir[:int(0.004 * sr)] *= np.linspace(0, 1, int(0.004 * sr))[:, None]
    # Unit total energy, so convolving does not change how loud the signal is; the hall's
    # level is then set once, on the wet bus, instead of drifting with the decay time.
    return ir / np.sqrt(np.sum(ir ** 2) / ir.shape[1])


def render_stem(track, tempo, wav, tmp_mid):
    """One instrument, rendered alone, dry (FluidSynth's own reverb and chorus off)."""
    from rebuild3 import write_midi
    write_midi(tmp_mid, tempo, [track])
    r = subprocess.run([FLUID, "-ni", "-g", "0.7", "-F", wav, "-r", "44100",
                        "-R", "0", "-C", "0", SF2, tmp_mid],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(wav):
        raise RuntimeError(f"fluidsynth failed for {track.get('name')}: {r.stderr[:200]}")
    x, sr = sf.read(wav, dtype="float64", always_2d=True)
    return x.mean(axis=1), sr                      # one instrument -> one mono stem


def seat(stem, pan, gain_db):
    """Constant-power pan, so moving an instrument across the stage does not change how
    loud it is."""
    g = 10 ** (gain_db / 20)
    a = (pan + 1) * np.pi / 4
    return np.stack([stem * np.cos(a) * g, stem * np.sin(a) * g], axis=1)


def mix(stems, ir, wet_bus_db=-7.0):
    """Sum the seated stems, and send each to the hall by its own amount: instruments at
    the back of the stage get more room than the melody at the front."""
    n = max(len(s["audio"]) for s in stems)
    dry = np.zeros((n, 2)); send = np.zeros((n, 2))
    for s in stems:
        y = seat(s["audio"], s["pan"], s["gain_db"])
        dry[:len(y)] += y
        send[:len(y)] += y * 10 ** (s["send_db"] / 20)
    wet = np.stack([signal.fftconvolve(send[:, c], ir[:, c])[:n] for c in (0, 1)], axis=1)
    return dry + wet * 10 ** (wet_bus_db / 20)
