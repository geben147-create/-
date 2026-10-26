# -*- coding: utf-8 -*-
"""아이언맨 트랙에 무슨 악기가 들어있는지, 특히 저음 '빰빰'의 정체를 밝힙니다.
모델 없이 신호처리만으로: HPSS, 대역 에너지, 저역 온셋의 하모닉 구조 분석."""
import numpy as np, librosa, json, soundfile as sf
from scipy import signal as sg

P = "tracks/01_IronManBGM_Remix/00_original/original.wav"
y, sr = librosa.load(P, sr=44100, mono=True)
dur = len(y)/sr
print(f"길이 {dur:.2f}s  sr {sr}")

tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
tempo = float(np.atleast_1d(tempo)[0])
print(f"템포 {tempo:.1f} BPM, 비트 {len(beats)}개")

# 하모닉(음정 있는 소리) vs 퍼커시브(타악) 분리
yh, yp = librosa.effects.hpss(y, margin=(2.0, 2.0))
eh, ep = float(np.mean(yh**2)), float(np.mean(yp**2))
print(f"하모닉 에너지 {100*eh/(eh+ep):.1f}% / 퍼커시브 {100*ep/(eh+ep):.1f}%")

# 대역별 에너지
BANDS = [("서브 20-60Hz",20,60),("저음 60-120Hz",60,120),("베이스 120-250Hz",120,250),
         ("로우미드 250-500Hz",250,500),("미드 500-2kHz",500,2000),
         ("하이미드 2k-6kHz",2000,6000),("고음 6k-16kHz",6000,16000)]
S = np.abs(librosa.stft(y, n_fft=8192, hop_length=1024))
freqs = librosa.fft_frequencies(sr=sr, n_fft=8192)
tot = float(np.sum(S**2))
bandinfo=[]
for nm, lo, hi in BANDS:
    m = (freqs>=lo)&(freqs<hi)
    e = float(np.sum(S[m]**2))
    bandinfo.append({"band":nm,"pct":round(100*e/tot,1)})
    print(f"  {nm:<20} {100*e/tot:5.1f}%")

# 저역 온셋 = '빰빰' 찾기
sos = sg.butter(4, [35, 180], btype="band", fs=sr, output="sos")
low = sg.sosfiltfilt(sos, y)
oenv = librosa.onset.onset_strength(y=low, sr=sr, hop_length=512)
on = librosa.onset.onset_detect(onset_envelope=oenv, sr=sr, hop_length=512, units="time",
                                backtrack=True, delta=0.25, wait=8)
print(f"\n저역 타격(빰) {len(on)}회, 평균 간격 {np.mean(np.diff(on)):.3f}s" if len(on)>2 else f"\n저역 타격 {len(on)}회")
beat_s = 60/tempo
if len(on)>2:
    gaps=np.diff(on); print(f"  간격을 박으로 환산: {np.median(gaps)/beat_s:.2f}박")

# 가장 센 저역 타격 몇 개를 뽑아 '음정이 있는가'를 본다
def analyze_hit(t):
    i0 = int(t*sr); seg = y[i0:i0+int(0.45*sr)]
    if len(seg) < 2048: return None
    w = seg*np.hanning(len(seg))
    sp = np.abs(np.fft.rfft(w, 65536)); fr = np.fft.rfftfreq(65536, 1/sr)
    band = (fr>=30)&(fr<=600)
    pk = fr[band][np.argmax(sp[band])]
    # 기본주파수의 배음이 실제로 있는지 확인 -> 있으면 음정 악기, 없으면 북
    harm=[]
    for n in range(1,7):
        f=pk*n
        if f>sr/2-50: break
        k=(fr>f*0.97)&(fr<f*1.03)
        harm.append(float(np.max(sp[k])) if k.any() else 0.0)
    harm=np.array(harm); harm=harm/ (harm[0]+1e-12)
    # 감쇠 시간
    env=np.abs(sg.hilbert(seg)); env/=env.max()+1e-12
    below=np.where(env<0.1)[0]
    decay = below[0]/sr if len(below) else 0.45
    # 노이즈성: 스펙트럼 평탄도
    flat=float(np.mean(librosa.feature.spectral_flatness(y=seg)))
    return {"t":round(float(t),2),"f0":round(float(pk),1),
            "midi":librosa.hz_to_note(pk) if pk>25 else "-",
            "harmonics":[round(float(h),2) for h in harm],
            "harmonic_strength":round(float(np.mean(harm[1:4])),3),
            "decay_s":round(float(decay),3),"flatness":round(flat,4)}

strength = oenv[librosa.time_to_frames(on, sr=sr, hop_length=512).clip(0,len(oenv)-1)] if len(on) else []
order = np.argsort(-strength)[:8] if len(on) else []
hits=[h for h in (analyze_hit(on[i]) for i in order) if h]
print("\n가장 센 저역 타격 분석:")
for h in hits:
    print(f"  {h['t']:>6.2f}s  f0={h['f0']:>6.1f}Hz ({h['midi']})  배음강도={h['harmonic_strength']:.2f}  감쇠={h['decay_s']:.3f}s  평탄도={h['flatness']:.4f}")

hs=np.median([h["harmonic_strength"] for h in hits]) if hits else 0
fl=np.median([h["flatness"] for h in hits]) if hits else 0
dc=np.median([h["decay_s"] for h in hits]) if hits else 0
f0=np.median([h["f0"] for h in hits]) if hits else 0
print(f"\n중앙값: f0={f0:.1f}Hz 배음강도={hs:.2f} 평탄도={fl:.4f} 감쇠={dc:.3f}s")

# 멜로디 음역
yh2=librosa.effects.harmonic(y, margin=3.0)
f0t,vf,_=librosa.pyin(yh2, fmin=80, fmax=1200, sr=sr, frame_length=4096)
vals=f0t[~np.isnan(f0t)]
mel={"note_low":librosa.hz_to_note(np.percentile(vals,5)),"note_high":librosa.hz_to_note(np.percentile(vals,95)),
     "median":librosa.hz_to_note(np.median(vals))} if len(vals)>50 else {}
print(f"\n선율 음역: {mel}")

json.dump({"duration":round(dur,2),"tempo":round(tempo,1),"harmonic_pct":round(100*eh/(eh+ep),1),
           "bands":bandinfo,"low_hits":len(on),"hit_analysis":hits,
           "median":{"f0":round(float(f0),1),"harm":round(float(hs),2),"flat":round(float(fl),4),"decay":round(float(dc),3)},
           "melody_range":mel},
          open("/tmp/claude-0/-home-user--/4b2bd38e-8d7f-52a5-bb39-0e1615b1f404/scratchpad/ironman_analysis.json","w"),
          ensure_ascii=False, indent=1)
