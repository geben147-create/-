# -*- coding: utf-8 -*-
import sys, os, json, subprocess, numpy as np
sys.path.insert(0,'/home/user/-/compose')
from midi_theory import GM
from enrich import load, octave, chord_bed, drum_pattern, write, DRUM
from compose import render, to_mp3
import master_simple as M

# 작업 폴더: 1안.mid 가 들어있는 곳. 인자로 바꿀 수 있다.
D = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
tr,BPM_ORIG = load(f"{D}/1안.mid")
drum,bass,s1,s2,piano = tr[0],tr[1],tr[2],tr[3],tr[4]
BPM=140.0                      # .song 파일의 현재 템포
r=BPM_ORIG/BPM                 # 120 -> 140 로 시간 압축
def sc(ns): return [{**n,"start":n["start"]*r,"end":n["end"]*r} for n in ns]
bass,s1,s2,piano = sc(bass),sc(s1),sc(s2),sc(piano)
beat=60/BPM; bar=beat*4
BARS=16
bars=[i*bar for i in range(BARS)]
# 그들이 친 화음을 그대로 뽑는다 (2마디마다 하나)
CH=[]
for b in range(0,8,2):
    t0=b*bar
    tones=sorted({n["pitch"] for n in piano if abs(n["start"]-t0)<0.25})
    if tones: CH.append(tones)
print("당신이 친 화음:",[[f"{p}" for p in c] for c in CH])

# ---------- 레이어 구성 ----------
T=[]
# 1) 당신 음 그대로
T.append({"program":0,"notes":piano,"name":"Piano (yours)"})
T.append({"program":GM["strings"][0],"notes":s1,"name":"STRING (yours)"})
T.append({"program":GM["finger_bass"][0],"notes":bass,"name":"Bass (yours)"})
# 2) 당신 음에서 파생 — 새 음 아님
T.append({"program":GM["slow_strings"][0],"notes":octave(s2,-12,0.62,0.016),"name":"STRING -8ve (derived)"})
T.append({"program":GM["celesta"][0],"notes":octave(s1,+12,0.42,0.008),"name":"STRING +8ve sparkle (derived)"})
T.append({"program":GM["synth_bass"][0],"notes":octave(bass,-24,0.95),"name":"Sub bass -2oct (derived)"})
T.append({"program":GM["warm_pad"][0],"notes":chord_bed(CH,bars[:8],bar*2,octaves=(0,),vel=46)+
                                            chord_bed(CH,bars[8:],bar*2,octaves=(0,),vel=42),"name":"Pad from your chords (derived)"})
T.append({"program":GM["choir"][0],"notes":chord_bed(CH,bars[8:],bar*2,octaves=(1,),vel=38),"name":"Choir b9-16 (derived)"})
# 3) 새로 만든 반주 (멜로디 아님)
T.append({"is_drum":True,"notes":drum_pattern(8,bar,beat,"steady")+drum_pattern(8,bar,beat,"busy",start=8*bar),"name":"Drums (new accompaniment)"})
# 9~16마디 베이스·피아노 연장 (당신 화음 그대로 반복)
ext_bass=[{"pitch":CH[i%len(CH)][0]-24,"start":bars[8+i*2],"end":bars[8+i*2]+bar*2-0.04,"vel":88} for i in range(4)]
T.append({"program":GM["synth_bass"][0],"notes":ext_bass,"name":"Sub bass b9-16 (your chords)"})

mid=write(f"{D}/풍성한버전.mid",BPM,T)
w=render(mid,f"{D}/rich_raw.wav")
print("렌더:",bool(w))
rep=M.master(f"{D}/rich_raw.wav", f"{D}/풍성한버전_마스터.wav", target_lufs=-14.0)
print(json.dumps(rep,ensure_ascii=False,indent=1))
to_mp3(f"{D}/rich_raw.wav", f"{D}/d_풍성한버전_마스터전.mp3","96k")
subprocess.run(["ffmpeg","-y","-loglevel","error","-i",f"{D}/풍성한버전_마스터.wav","-ac","1","-b:a","96k",f"{D}/e_풍성한버전_마스터후.mp3"],check=True)
json.dump(rep,open(f"{D}/master_report.json","w"),ensure_ascii=False,indent=1)
print("노트 합계:",sum(len(t["notes"]) for t in T))
for t in T: print(f"   {t['name']:<36} {len(t['notes']):>5}")
