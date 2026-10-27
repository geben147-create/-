# -*- coding: utf-8 -*-
"""Per-instrument tuning calibration for the General MIDI preview render.

A General MIDI soundfont is not tuned to concert pitch on every patch: a sampled choir or a timpani
can sit 20-40 cents off. Against horns and basses that are in tune, that mismatch is heard as a
dissonance even though every written note belongs to the chord. This renders each instrument
once on its own, measures where each pitch really lands, and returns the pitch-bend that puts it
back. The correction is applied to the preview render only; the MIDI files handed to Studio One
carry no bends, because there the player's own instruments are used.
"""
from __future__ import annotations
import os, shutil, subprocess
import numpy as np
import pretty_midi
import soundfile as sf

FLUID = shutil.which("fluidsynth")
SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
SR = 44100


def f0_cents(x, expected, search_cents=90):
    """Cents between the strongest partial near `expected` and `expected`."""
    seg = x * np.hanning(len(x)); n = 1 << 18
    sp = np.abs(np.fft.rfft(seg, n)); f = np.fft.rfftfreq(n, 1 / SR)
    k = (f >= expected * 2 ** (-search_cents / 1200)) & (f <= expected * 2 ** (search_cents / 1200))
    if not k.any() or sp[k].max() < 1e-7:
        return None
    i = int(np.argmax(np.where(k, sp, 0)))
    if i < 1 or i >= len(sp) - 1:
        return None
    a, b, c = np.log(sp[i - 1] + 1e-12), np.log(sp[i] + 1e-12), np.log(sp[i + 1] + 1e-12)
    d = 0.5 * (a - c) / (a - 2 * b + c)
    return 1200 * np.log2((f[i] + d * (f[1] - f[0])) / expected)


def calibrate(program, pitches, tmpdir, vels=(55, 85, 115), hold=1.4, gap=0.6, max_spread=25.0):
    """{pitch: cents the sample sounds above the written pitch}, measured one pitch at a time at
    three velocities. A pitch whose three readings disagree by more than `max_spread` cents is
    reported as 0 (the reading is not trustworthy, so it is left alone rather than 'corrected')."""
    os.makedirs(tmpdir, exist_ok=True)
    ps = sorted(set(int(p) for p in pitches))
    reads = {p: [] for p in ps}
    for vel in vels:
        pm = pretty_midi.PrettyMIDI(initial_tempo=120.0)
        inst = pretty_midi.Instrument(program=int(program))
        t = 0.2; spans = {}
        for p in ps:
            inst.notes.append(pretty_midi.Note(vel, p, t, t + hold)); spans[p] = t; t += hold + gap
        pm.instruments.append(inst)
        mid, wav = f"{tmpdir}/cal_{program}.mid", f"{tmpdir}/cal_{program}.wav"
        pm.write(mid)
        subprocess.run([FLUID, "-ni", "-g", "0.7", "-F", wav, "-r", str(SR), "-R", "0", "-C", "0", SF2, mid],
                       capture_output=True, text=True)
        x, _ = sf.read(wav, dtype="float64", always_2d=True); x = x.mean(axis=1)
        for p, t0 in spans.items():
            seg = x[int((t0 + 0.12) * SR): int((t0 + 0.9) * SR)]
            c = f0_cents(seg, 440.0 * 2 ** ((p - 69) / 12)) if len(seg) > 4000 else None
            if c is not None:
                reads[p].append(float(c))
        for f in (mid, wav):
            if os.path.exists(f): os.remove(f)
    out = {}
    for p, r in reads.items():
        if len(r) >= 2 and (max(r) - min(r)) <= max_spread:
            out[p] = float(np.median(r))
        else:
            out[p] = 0.0
    return out


def bend_value(cents):
    """MIDI pitch-bend (default range +-2 semitones) that moves a note by `cents`."""
    return int(np.clip(round(cents / 200.0 * 8192), -8191, 8191))
