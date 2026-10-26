# -*- coding: utf-8 -*-
import sys, os, itertools
import numpy as np, pretty_midi, soundfile as sf
from scipy import signal
NM=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
def nn(p): return f"{NM[p%12]}{p//12-1}"

def distinct_collisions(path):
    pm=pretty_midi.PrettyMIDI(path)
    ev=[(n.start,n.end,n.pitch,i,inst.name) for i,inst in enumerate(pm.instruments) for n in inst.notes]
    seen={}
    for t in np.arange(0,pm.get_end_time(),0.02):
        on=[(p,i,nm) for s,e,p,i,nm in ev if s<=t<e]
        for (p1,i1,n1),(p2,i2,n2) in itertools.combinations(on,2):
            if i1==i2: continue
            if abs(p1-p2) in (1,13):
                lo,hi=(p1,n1) if p1<p2 else (p2,n2); other=(p2,n2) if p1<p2 else (p1,n1)
                k=(lo,other[0],lo and hi, other[1])
                k=(nn(lo),nn(other[0]),hi,other[1])
                seen.setdefault(k,[0,t]); seen[k][0]+=1
    return sorted(seen.items(), key=lambda kv:-kv[1][0])

def melody_presence(path):
    """Share of energy in 500-1000 Hz, where the composer's D5/F5/A4/A5 ostinato
    fundamentals live. Higher = their line is more in front."""
    x,sr=sf.read(path,always_2d=True); x=x.mean(axis=1)
    f,P=signal.welch(x,sr,nperseg=16384)
    tot=np.trapezoid(P,f)
    def sh(a,b):
        m=(f>=a)&(f<b); return 100*np.trapezoid(P[m],f[m])/tot
    return {"sub<120":round(sh(20,120),1),"low 120-350":round(sh(120,350),1),
            "OSTINATO 500-1000":round(sh(500,1000),1),"1-3k":round(sh(1000,3000),1),
            ">3k":round(sh(3000,10000),1)}

for lab,p in [("ORIGINAL 1안 (their draft)", sys.argv[1]+"/an1/1안.mid")]+[
        (k, f"{sys.argv[1]}/v3/{k}.mid") for k in ["A_깔린베이스","B_짜짜베이스","C_둘다"]]:
    print(f"\n=== {lab}")
    c=distinct_collisions(p)
    print(f"  distinct cross-track semitone/m9 pairs: {len(c)}   (total 20ms samples flagged: {sum(v[0] for _,v in c)})")
    for (a,b,t1,t2),(cnt,t0) in c[:10]:
        print(f"     {a} vs {b}  x{cnt:4d}  first t={t0:.2f}   [{t1}] x [{t2}]")

print("\n=== melody presence (energy share of their ostinato band) ===")
for lab,p in [("OLD 풍성한버전 (the one you disliked)", sys.argv[1]+"/an1/풍성한버전_마스터.wav")]+[
        (k, f"{sys.argv[1]}/v3/{k}_master.wav") for k in ["A_깔린베이스","B_짜짜베이스","C_둘다"]]:
    if os.path.exists(p): print(f"  {lab:<40}", melody_presence(p))
