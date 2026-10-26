# -*- coding: utf-8 -*-
"""Does the composer's bass line actually contribute audible energy now?
Render the mix with and without the Bass track and measure the difference in the band
where its fundamentals live (A2=110 .. D3=147 Hz, so 95-190 Hz covers them with harmonic 1).
A bass buried in a unison changes almost nothing when removed; an audible one changes a lot.
"""
import sys, os, subprocess, numpy as np, pretty_midi, soundfile as sf
from scipy import signal
sys.path.insert(0,'/home/user/-/compose')
from compose import render
D=sys.argv[1]

def band_rms(x, sr, a, b):
    sos=signal.butter(4,[a,b],btype='bandpass',fs=sr,output='sos')
    y=signal.sosfiltfilt(sos,x)
    return 20*np.log10(np.sqrt(np.mean(y**2))+1e-12)

def strip(src, dst, drop):
    pm=pretty_midi.PrettyMIDI(src)
    pm.instruments=[i for i in pm.instruments if drop.lower() not in (i.name or "").lower()]
    pm.write(dst); return dst

for lab, src in [("NEW C_둘다", f"{D}/v3/C_둘다.mid"), ("OLD 풍성한버전", f"{D}/an1/풍성한버전.mid")]:
    if not os.path.exists(src): continue
    full=render(src, f"{D}/_full.wav", gain=0.75)
    nob =render(strip(src, f"{D}/_nobass.mid", "bass"), f"{D}/_nobass.wav", gain=0.75)
    # note: OLD has several tracks with 'bass' in the name; strip them all, which is the fair
    # comparison for "can I hear the bass line at all"
    xa,sr=sf.read(full,always_2d=True); xa=xa.mean(axis=1)
    xb,_ =sf.read(nob ,always_2d=True); xb=xb.mean(axis=1)
    n=min(len(xa),len(xb))
    pm=pretty_midi.PrettyMIDI(src)
    kept=[i.name for i in pm.instruments if 'bass' in (i.name or '').lower()]
    d_band = band_rms(xa[:n],sr,95,190) - band_rms(xb[:n],sr,95,190)
    print(f"\n{lab}")
    print(f"  bass-ish tracks removed for the test: {kept}")
    print(f"  95-190 Hz with bass  : {band_rms(xa[:n],sr,95,190):7.2f} dB")
    print(f"  95-190 Hz without    : {band_rms(xb[:n],sr,95,190):7.2f} dB")
    print(f"  the bass line is worth {d_band:+.2f} dB in its own band")
    for a,b in [(20,95),(190,400),(400,1000)]:
        print(f"     {a}-{b} Hz leak: {band_rms(xa[:n],sr,a,b)-band_rms(xb[:n],sr,a,b):+.2f} dB")
for f in ["_full.wav","_nobass.wav","_nobass.mid"]:
    p=f"{D}/{f}"
    if os.path.exists(p): os.remove(p)
