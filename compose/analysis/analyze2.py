# -*- coding: utf-8 -*-
"""대역별로 나눠서 각 대역 안에 '음정 있는 소리'와 '타악'이 각각 얼마나 있는지 본다.
저음이 에너지의 90%라 전체 HPSS만 보면 중음역 드럼이 묻혀서 안 보인다."""
import numpy as np, librosa, json
from scipy import signal as sg
P="tracks/01_IronManBGM_Remix/00_original/original.wav"
y,sr=librosa.load(P,sr=44100,mono=True)
res={}

def band(lo,hi):
    sos=sg.butter(4,[lo,min(hi,sr/2-100)],btype="band",fs=sr,output="sos")
    return sg.sosfiltfilt(sos,y)

print("대역 안에서 음정 vs 타악 비율 (에너지가 아니라 대역 내부 비율)")
rows=[]
for nm,lo,hi in [("저음 35-150Hz",35,150),("중저음 150-500Hz",150,500),
                 ("중음 500-2000Hz",500,2000),("고음 2k-10kHz",2000,10000)]:
    b=band(lo,hi)
    if np.max(np.abs(b))<1e-5: 
        rows.append({"band":nm,"harm":0,"perc":0,"rel_db":-99}); continue
    h,p=librosa.effects.hpss(b,margin=(2.0,2.0))
    eh,ep=float(np.mean(h**2)),float(np.mean(p**2))
    tot=eh+ep+1e-20
    rel=20*np.log10(np.sqrt(np.mean(b**2))/ (np.sqrt(np.mean(y**2))+1e-12))
    rows.append({"band":nm,"harm":round(100*eh/tot,1),"perc":round(100*ep/tot,1),"rel_db":round(float(rel),1)})
    print(f"  {nm:<18} 음정 {100*eh/tot:5.1f}%  타악 {100*ep/tot:5.1f}%   전체대비 {rel:+6.1f}dB")
res["bands"]=rows

# 중음역(멜로디)만 따로 음정 추적
mid=band(200,2000)
f0,vf,_=librosa.pyin(mid,fmin=110,fmax=1000,sr=sr,frame_length=4096)
v=f0[~np.isnan(f0)]
if len(v)>50:
    notes=[librosa.hz_to_note(x) for x in v]
    from collections import Counter
    pc=Counter(n.rstrip("0123456789") for n in notes)
    print(f"\n중음역 선율: {librosa.hz_to_note(np.percentile(v,5))} ~ {librosa.hz_to_note(np.percentile(v,95))}"
          f"  (중앙 {librosa.hz_to_note(np.median(v))})  유성 프레임 {len(v)}")
    print("  많이 쓰인 음:", ", ".join(f"{k} {100*c/len(notes):.0f}%" for k,c in pc.most_common(7)))
    res["mid_melody"]={"low":librosa.hz_to_note(np.percentile(v,5)),"high":librosa.hz_to_note(np.percentile(v,95)),
                       "median":librosa.hz_to_note(np.median(v)),"frames":int(len(v)),
                       "top_pitches":[[k,round(100*c/len(notes),1)] for k,c in pc.most_common(7)]}

# 저음 라인의 음정 추적 (빰빰이 어떤 음을 치는가)
lowb=band(35,160)
f0l,_,_=librosa.pyin(lowb,fmin=32,fmax=170,sr=sr,frame_length=8192)
vl=f0l[~np.isnan(f0l)]
if len(vl)>30:
    from collections import Counter
    nl=[librosa.hz_to_note(x) for x in vl]
    pcl=Counter(n.rstrip("0123456789") for n in nl)
    print(f"\n저음 라인: {librosa.hz_to_note(np.percentile(vl,5))} ~ {librosa.hz_to_note(np.percentile(vl,95))}"
          f"  (중앙 {librosa.hz_to_note(np.median(vl))})")
    print("  저음이 치는 음:", ", ".join(f"{k} {100*c/len(nl):.0f}%" for k,c in pcl.most_common(6)))
    res["bass_line"]={"low":librosa.hz_to_note(np.percentile(vl,5)),"high":librosa.hz_to_note(np.percentile(vl,95)),
                      "median":librosa.hz_to_note(np.median(vl)),
                      "top_pitches":[[k,round(100*c/len(nl),1)] for k,c in pcl.most_common(6)]}

# 하이햇/심벌 같은 고역 타격이 있는가
hi=band(6000,16000)
rms_hi=float(np.sqrt(np.mean(hi**2))); rms_all=float(np.sqrt(np.mean(y**2)))
oh=librosa.onset.onset_detect(y=hi,sr=sr,units="time",delta=0.3)
print(f"\n고역(6k+) 레벨: 전체 대비 {20*np.log10(rms_hi/rms_all+1e-12):+.1f}dB, 고역 타격 {len(oh)}회")
res["high_band"]={"rel_db":round(20*np.log10(rms_hi/rms_all+1e-12),1),"onsets":int(len(oh))}

# 스테레오
import soundfile as sf
st,_=sf.read(P,always_2d=True)
corr=float(np.corrcoef(st[:,0],st[:,1])[0,1])
print(f"스테레오 상관 {corr:.3f} ({'거의 모노' if corr>0.95 else '넓음' if corr<0.6 else '보통'})")
res["stereo_corr"]=round(corr,3)
json.dump(res,open("/tmp/claude-0/-home-user--/4b2bd38e-8d7f-52a5-bb39-0e1615b1f404/scratchpad/ironman2.json","w"),ensure_ascii=False,indent=1)
