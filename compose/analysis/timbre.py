# -*- coding: utf-8 -*-
"""원곡 중음역이 무슨 악기인지 음색으로 판별.
악기를 가르는 특징: 어택 시간, 지속 여부(감쇠하나 유지되나), 비브라토, 배음 구조, 비조화도."""
import numpy as np, librosa, json
from scipy import signal as sg
P="tracks/01_IronManBGM_Remix/00_original/original.wav"
y,sr=librosa.load(P,sr=44100,mono=True)

def bp(x,lo,hi):
    sos=sg.butter(6,[lo,min(hi,sr/2-100)],btype="band",fs=sr,output="sos"); return sg.sosfiltfilt(sos,x)

mid=bp(y,200,4000)
mid=mid/ (np.max(np.abs(mid))+1e-9)

# 중음역 온셋
oenv=librosa.onset.onset_strength(y=mid,sr=sr,hop_length=256)
on=librosa.onset.onset_detect(onset_envelope=oenv,sr=sr,hop_length=256,units="time",backtrack=True,delta=0.2,wait=5)
print(f"중음역 온셋 {len(on)}회 / {len(y)/sr:.1f}초")

def attack_decay(t):
    i=int(t*sr); seg=mid[i:i+int(1.2*sr)]
    if len(seg)<sr//2: return None
    env=np.abs(sg.hilbert(seg)); env=sg.savgol_filter(env,601,2); env=np.maximum(env,0)
    if env.max()<1e-4: return None
    e=env/env.max()
    pk=int(np.argmax(e))
    # 어택: 10%->90%
    pre=e[:pk+1]
    try:
        a10=np.where(pre>=0.1)[0][0]; a90=np.where(pre>=0.9)[0][0]
        atk=(a90-a10)/sr
    except Exception: atk=np.nan
    # 피크 후 300ms 지점 레벨 (피아노면 뚝 떨어지고 현/관이면 유지)
    i300=min(pk+int(0.30*sr),len(e)-1); i600=min(pk+int(0.60*sr),len(e)-1)
    return {"t":round(float(t),2),"attack_ms":round(float(atk*1000),1) if atk==atk else None,
            "lvl_300ms":round(float(e[i300]),3),"lvl_600ms":round(float(e[i600]),3)}

strength=oenv[np.clip(librosa.time_to_frames(on,sr=sr,hop_length=256),0,len(oenv)-1)] if len(on) else []
sel=[on[i] for i in np.argsort(-strength)[:25]] if len(on) else []
rows=[r for r in (attack_decay(t) for t in sel) if r]
atks=[r["attack_ms"] for r in rows if r["attack_ms"] is not None]
s300=[r["lvl_300ms"] for r in rows]; s600=[r["lvl_600ms"] for r in rows]
print(f"\n어택 시간 중앙값 : {np.median(atks):.1f} ms   (피아노·타건 5~20ms / 현악 활 60~200ms / 패드 300ms+)")
print(f"피크 후 300ms 잔존: {np.median(s300):.2f}   (피아노 0.2~0.4 / 지속악기 0.7~1.0)")
print(f"피크 후 600ms 잔존: {np.median(s600):.2f}")

# 비브라토: f0의 4~8Hz 흔들림
f0,vf,_=librosa.pyin(mid,fmin=150,fmax=1200,sr=sr,frame_length=4096,hop_length=256)
hop_t=256/sr
vib=[]
idx=np.where(~np.isnan(f0))[0]
runs=np.split(idx,np.where(np.diff(idx)>1)[0]+1)
for r in runs:
    if len(r)<int(0.45/hop_t): continue
    c=1200*np.log2(f0[r]/np.nanmean(f0[r]))
    c=c-np.mean(c)
    sp=np.abs(np.fft.rfft(c*np.hanning(len(c))))
    fr=np.fft.rfftfreq(len(c),hop_t)
    band=(fr>3.5)&(fr<9)
    if band.any():
        vib.append({"rate":float(fr[band][np.argmax(sp[band])]),
                    "depth":float(np.std(c)),"frac":float(np.max(sp[band])/(np.sum(sp)+1e-9))})
if vib:
    print(f"\n지속음 구간 {len(vib)}개")
    print(f"  4~9Hz 흔들림 비율 중앙값: {np.median([v['frac'] for v in vib]):.3f}  (비브라토 뚜렷하면 0.15+)")
    print(f"  음정 흔들림 폭 중앙값   : {np.median([v['depth'] for v in vib]):.1f} cents  (현악 비브라토 20~60)")

# 배음 구조 + 비조화도 (피아노는 배음이 살짝 위로 틀어짐)
def harm_profile(t):
    i=int(t*sr); seg=mid[i+int(0.05*sr):i+int(0.45*sr)]
    if len(seg)<4096: return None
    w=seg*np.hanning(len(seg)); sp=np.abs(np.fft.rfft(w,65536)); fr=np.fft.rfftfreq(65536,1/sr)
    b=(fr>180)&(fr<1500); f1=fr[b][np.argmax(sp[b])]
    out=[]
    for n in range(1,9):
        f=f1*n
        if f>12000: break
        k=(fr>f*0.96)&(fr<f*1.04)
        out.append(float(np.max(sp[k])) if k.any() else 0.0)
    out=np.array(out); out=out/(out[0]+1e-12)
    return f1,out
hp=[h for h in (harm_profile(t) for t in sel[:12]) if h]
if hp:
    prof=np.median(np.array([h[1] for h in hp if len(h[1])>=6])[:, :6],axis=0)
    print(f"\n배음 세기 (기음=1.00): " + "  ".join(f"{i+1}차 {v:.2f}" for i,v in enumerate(prof)))
    cen=librosa.feature.spectral_centroid(y=mid,sr=sr)[0]
    print(f"스펙트럼 중심 중앙값: {np.median(cen):.0f} Hz")
    print(f"고차배음 합(2~6차)/기음: {np.sum(prof[1:]):.2f}")

json.dump({"attack_ms":float(np.median(atks)),"lvl300":float(np.median(s300)),"lvl600":float(np.median(s600)),
           "vib_frac":float(np.median([v['frac'] for v in vib])) if vib else None,
           "vib_depth":float(np.median([v['depth'] for v in vib])) if vib else None,
           "harm":[float(x) for x in prof] if hp else None,
           "centroid":float(np.median(librosa.feature.spectral_centroid(y=mid,sr=sr)[0]))},
          open("/tmp/claude-0/-home-user--/4b2bd38e-8d7f-52a5-bb39-0e1615b1f404/scratchpad/timbre.json","w"),indent=1)
