# -*- coding: utf-8 -*-
"""피아노냐 신스냐를 가르는 결정적 지표: 비조화도(inharmonicity).
피아노 줄은 뻣뻣해서 n차 배음이 n*f0보다 '살짝 위'로 틀어집니다(B>0).
신스/샘플러는 정확히 정수배라 B≈0 입니다."""
import numpy as np, librosa, soundfile as sf, json
from scipy import signal as sg
P="tracks/01_IronManBGM_Remix/00_original/original.wav"
y,sr=librosa.load(P,sr=44100,mono=True)
sos=sg.butter(6,[200,5000],btype="band",fs=sr,output="sos"); mid=sg.sosfiltfilt(sos,y)
mid=mid/(np.max(np.abs(mid))+1e-9)
oenv=librosa.onset.onset_strength(y=mid,sr=sr,hop_length=256)
on=librosa.onset.onset_detect(onset_envelope=oenv,sr=sr,hop_length=256,units="time",backtrack=True,delta=0.25,wait=6)
st=oenv[np.clip(librosa.time_to_frames(on,sr=sr,hop_length=256),0,len(oenv)-1)]
sel=[on[i] for i in np.argsort(-st)[:18]]

def dev(t):
    i=int(t*sr); seg=mid[i+int(0.04*sr):i+int(0.50*sr)]
    if len(seg)<8192: return None
    w=seg*np.hanning(len(seg)); N=1<<18
    sp=np.abs(np.fft.rfft(w,N)); fr=np.fft.rfftfreq(N,1/sr)
    b=(fr>180)&(fr<900)
    if not b.any(): return None
    f1=fr[b][np.argmax(sp[b])]
    if f1<150: return None
    devs=[]
    for n in range(2,7):
        tgt=f1*n
        if tgt>sr/2-200: break
        k=(fr>tgt*0.93)&(fr<tgt*1.07)
        if not k.any(): continue
        fp=fr[k][np.argmax(sp[k])]
        if np.max(sp[k])<0.02*np.max(sp[b]): continue
        devs.append(1200*np.log2(fp/tgt))   # cents, +면 배음이 위로 틀어짐
    return (f1,devs) if len(devs)>=3 else None

rows=[r for r in (dev(t) for t in sel) if r]
alld=[d for _,ds in rows for d in ds]
print(f"분석한 음 {len(rows)}개, 배음 편차 샘플 {len(alld)}개")
print(f"배음 편차 중앙값: {np.median(alld):+.1f} cents  (평균 {np.mean(alld):+.1f})")
print(f"  해석: 피아노면 2~6차에서 +3~+25 cents 위로 틀어짐 / 신스·샘플러는 0 근처")
for f1,ds in rows[:6]:
    print(f"   f0={f1:6.1f}Hz ({librosa.hz_to_note(f1)})  배음편차 " + " ".join(f"{d:+5.1f}" for d in ds))

# 들어볼 수 있게 선율 구간만 뽑기 (베이스 완전히 제거)
S="/tmp/claude-0/-home-user--/4b2bd38e-8d7f-52a5-bb39-0e1615b1f404/scratchpad/band"
hp=sg.butter(8,260,btype="high",fs=sr,output="sos")
melody=sg.sosfiltfilt(hp,y)
for nm,(a,b) in {"10_선율만_저음완전제거_1분10초":(70,88),"11_선율만_저음완전제거_도입부":(2,20)}.items():
    seg=melody[int(a*sr):int(b*sr)]
    seg=seg/(np.max(np.abs(seg))+1e-9)*0.9
    sf.write(f"{S}/{nm}.wav",seg.astype(np.float32),sr)
    print("저장:",nm)
json.dump({"median_dev_cents":float(np.median(alld)),"mean_dev_cents":float(np.mean(alld)),"n":len(alld)},
          open("/tmp/claude-0/-home-user--/4b2bd38e-8d7f-52a5-bb39-0e1615b1f404/scratchpad/inharm.json","w"),indent=1)
