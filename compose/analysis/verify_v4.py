# -*- coding: utf-8 -*-
"""Checks run on the files that actually ship."""
import sys, os, itertools, subprocess
import numpy as np, pretty_midi, soundfile as sf
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from compose import render
NM = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
def nn(p): return f"{NM[p%12]}{p//12-1}"
D = sys.argv[1]
KEYS = sys.argv[2].split(",")

def collisions(path):
    pm = pretty_midi.PrettyMIDI(path)
    ev = [(n.start, n.end, n.pitch, i, inst.name)
          for i, inst in enumerate(pm.instruments) for n in inst.notes]
    seen = {}
    for t in np.arange(0, pm.get_end_time(), 0.02):
        on = [(p, i, nm) for s, e, p, i, nm in ev if s <= t < e]
        for (p1, i1, n1), (p2, i2, n2) in itertools.combinations(on, 2):
            if i1 == i2: continue
            if abs(p1 - p2) in (1, 13):
                lo = (p1, n1) if p1 < p2 else (p2, n2)
                hi = (p2, n2) if p1 < p2 else (p1, n1)
                seen.setdefault((nn(lo[0]), nn(hi[0]), lo[1], hi[1]), [0, t])[0] += 1
    return sorted(seen.items(), key=lambda kv: -kv[1][0])

def spectrum(path):
    x, sr = sf.read(path, always_2d=True)
    m = x.mean(axis=1)
    f, P = signal.welch(m, sr, nperseg=16384); tot = np.trapezoid(P, f)
    def sh(a, b):
        k = (f >= a) & (f < b); return round(100*np.trapezoid(P[k], f[k])/tot, 1)
    mid = (x[:,0]+x[:,1])/2; side = (x[:,0]-x[:,1])/2
    w = 20*np.log10(np.sqrt(np.mean(side**2))/(np.sqrt(np.mean(mid**2))+1e-12)+1e-12)
    pk = 20*np.log10(np.max(np.abs(m))+1e-12); rms = 20*np.log10(np.sqrt(np.mean(m**2))+1e-12)
    return {"sub<120": sh(20,120), "low 120-350": sh(120,350), "MELODY 500-1000": sh(500,1000),
            "1-3k": sh(1000,3000), ">3k": sh(3000,12000),
            "side/mid dB": round(w,1), "crest dB": round(pk-rms,1)}

def bass_worth(mid_path):
    """Re-render flat with and without the two contrabass tracks."""
    pm = pretty_midi.PrettyMIDI(mid_path)
    keep = [i for i in pm.instruments if "contrabass" not in (i.name or "").lower()]
    pm2 = pretty_midi.PrettyMIDI(initial_tempo=120.0); pm2.instruments = keep
    pm2.write(f"{D}/_nb.mid")
    a = render(mid_path, f"{D}/_a.wav", 0.7); b = render(f"{D}/_nb.mid", f"{D}/_b.wav", 0.7)
    xa, sr = sf.read(a, always_2d=True); xb, _ = sf.read(b, always_2d=True)
    xa = xa.mean(axis=1); xb = xb.mean(axis=1); n = min(len(xa), len(xb))
    def bd(x):
        sos = signal.butter(4, [95,190], btype="bandpass", fs=sr, output="sos")
        return 20*np.log10(np.sqrt(np.mean(signal.sosfiltfilt(sos, x)**2))+1e-12)
    out = round(bd(xa[:n]) - bd(xb[:n]), 2)
    for f_ in ["_nb.mid","_a.wav","_b.wav"]:
        p = f"{D}/{f_}"
        if os.path.exists(p): os.remove(p)
    return out

for k in KEYS:
    mid, wav = f"{D}/{k}.mid", f"{D}/{k}_master.wav"
    print(f"\n=== {k}")
    c = collisions(mid)
    print(f"  반음/단9도 충돌 쌍 {len(c)}  (20ms 구간 합 {sum(v[0] for _,v in c)})")
    for (a,b,t1,t2),(cnt,t0) in c[:6]:
        print(f"     {a} vs {b}  x{cnt}  t={t0:.2f}  [{t1}] x [{t2}]")
    if os.path.exists(wav): print("  ", spectrum(wav))
    print(f"   콘트라베이스 기여도 {bass_worth(mid):+.2f} dB (95-190 Hz)")

print("\n=== 세 버전이 실제로 다른가 (둘째 바퀴 16-32s) ===")
sig = {}
for k in KEYS:
    p = f"{D}/{k}_master.wav"
    if os.path.exists(p):
        x, sr = sf.read(p, always_2d=True); sig[k] = (x.mean(axis=1), sr)
for a, b in itertools.combinations([k for k in KEYS if k in sig], 2):
    xa, sr = sig[a]; xb, _ = sig[b]; n = min(len(xa), len(xb)); s = int(16*sr)
    d = xa[s:n]-xb[s:n]
    print(f"  {a:18s} vs {b:18s} 차이 RMS {20*np.log10(np.sqrt(np.mean(d**2))+1e-12):7.2f} dBFS "
          f"(음악 {20*np.log10(np.sqrt(np.mean(xa[s:n]**2))):.2f})")
