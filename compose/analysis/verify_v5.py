# -*- coding: utf-8 -*-
"""Checks on the shipped files.  python3 verify_v5.py <their upload .mid> <out folder>"""
import sys, os, itertools
import numpy as np, pretty_midi, soundfile as sf
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from compose import render
NM = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
def nn(p): return f"{NM[p%12]}{p//12-1}"
UP, D = sys.argv[1], sys.argv[2]
PFX = sys.argv[3] if len(sys.argv) > 3 else "finale"
FULL = f"{D}/{PFX}_FULL_140bpm.mid"
B = lambda pm: float(pm.get_tempo_changes()[1][0]) / 60.0

# 1. harmony: semitone / minor-9th between different tracks
pm = pretty_midi.PrettyMIDI(FULL)
ev = [(n.start, n.end, n.pitch, i, inst.name) for i, inst in enumerate(pm.instruments) for n in inst.notes]
seen = {}
for t in np.arange(0, pm.get_end_time(), 0.02):
    on = [(p, i, nm) for s, e, p, i, nm in ev if s <= t < e]
    for (p1, i1, n1), (p2, i2, n2) in itertools.combinations(on, 2):
        if i1 != i2 and abs(p1 - p2) in (1, 13):
            lo, hi = sorted([(p1, n1), (p2, n2)])
            seen.setdefault((nn(lo[0]), nn(hi[0]), lo[1], hi[1]), [0, t])[0] += 1
print(f"1. cross-track semitone / minor-9th pairs: {len(seen)}  (20 ms samples: {sum(v[0] for v in seen.values())})")
for (a, b, x, y), (c, t0) in sorted(seen.items(), key=lambda kv: -kv[1][0])[:8]:
    print(f"     {a} vs {b}  x{c:3d}  first t={t0:5.2f}s  [{x}] x [{y}]")

# 2. their notes: untouched in blocks 1-8?
up = pretty_midi.PrettyMIDI(UP); bu, bn = B(up), B(pm)
def key(n, b): return (n.pitch, round(n.start * b, 2))
keep = {"Violin I (your melody)": "Violin I (yours)", "Violin II (your melody, doubled)": "Violin II (yours)",
        "Contrabass (your bass)": "Contrabass (yours)"}
for old, new in keep.items():
    a = {key(n, bu) for i in up.instruments if i.name == old for n in i.notes if n.start * bu < 64}
    b = {key(n, bn) for i in pm.instruments if i.name == new for n in i.notes if n.start * bn < 64}
    print(f"2. {old:<34} blocks 1-8: {len(a)} notes in upload, {len(a & b)} identical in output, {len(a - b)} changed/missing")

# 3. retrigger density in blocks 1-8 for everything that is not the composer's
print("3. fastest repeated-note rate on one track, blocks 1-8 (beats between onsets):")
for inst in pm.instruments:
    st = sorted(n.start * bn for n in inst.notes if n.start * bn < 64)
    if len(st) < 3: continue
    d = np.diff(st); d = d[d > 0.01]
    print(f"     {inst.name:<24} min gap {d.min():5.2f}   median {np.median(d):5.2f}   notes {len(st)}")

# 4/5. low-end and melody presence in the mastered file
def band(x, sr, a, b):
    s = signal.butter(4, [a, b], btype="bandpass", fs=sr, output="sos"); return 20*np.log10(np.sqrt(np.mean(signal.sosfiltfilt(s, x)**2))+1e-12)
mid = f"{D}/_nb.mid"
pm2 = pretty_midi.PrettyMIDI(initial_tempo=140.0); pm2.instruments = [i for i in pm.instruments if i.name != "Contrabass (yours)"]; pm2.write(mid)
wa = render(FULL, f"{D}/_a.wav", 0.7); wb = render(mid, f"{D}/_b.wav", 0.7)
xa, sr = sf.read(wa, always_2d=True); xb, _ = sf.read(wb, always_2d=True); xa, xb = xa.mean(1), xb.mean(1); n = min(len(xa), len(xb))
print(f"4. your bass line is worth {band(xa[:n], sr, 95, 190) - band(xb[:n], sr, 95, 190):+.2f} dB in 95-190 Hz")
for f in (mid, wa, wb): os.remove(f)
x, sr = sf.read(f"{D}/{PFX}_master.wav", always_2d=True); m = x.mean(1)
f, P = signal.welch(m, sr, nperseg=16384); tot = np.trapezoid(P, f)
sh = lambda a, b: round(100*np.trapezoid(P[(f>=a)&(f<b)], f[(f>=a)&(f<b)])/tot, 1)
print(f"5. energy share  <120Hz {sh(20,120)}%   120-350 {sh(120,350)}%   MELODY 500-1k {sh(500,1000)}%   1-3k {sh(1000,3000)}%   >3k {sh(3000,12000)}%")
print(f"   crest {20*np.log10(np.max(np.abs(m))/(np.sqrt(np.mean(m**2))+1e-12)):.1f} dB, clipped {int(np.sum(np.abs(x)>=0.99997))} samples, length {len(m)/sr:.1f}s")
