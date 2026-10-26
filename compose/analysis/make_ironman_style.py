# -*- coding: utf-8 -*-
"""아이언맨 트랙의 '구조'만 가져와 새로 만든 예시.
가져온 것: 템포 148, D minor, i-VI-III-VII 진행, 서브베이스+중음선율이라는 역할 배치.
가져오지 않은 것: 원곡의 음 하나도 베끼지 않았습니다. 멜로디는 새로 썼습니다.
(템포·조성·코드진행·악기배치는 일반적으로 저작권 보호 대상이 아닙니다.)"""
import sys, os, pretty_midi
sys.path.insert(0,"/home/user/-/compose")
from midi_theory import GM
from compose import write_midi, render, to_mp3, drum_options, drum_notes, bar_grid

BPM=148; beat=60/BPM; bar=beat*4
OUT="/tmp/claude-0/-home-user--/4b2bd38e-8d7f-52a5-bb39-0e1615b1f404/scratchpad/style"
os.makedirs(OUT,exist_ok=True)
# D minor: i=D, VI=Bb, III=F, VII=C   (원곡 저음이 실제로 D 39% / A# 20% / F 16% / C 11% 였음)
ROOTS=[38,34,41,36]   # D2, Bb1, F2, C2
BARS=8

# 1) 베이스: 사람이 칠 법한 단순한 리듬 (1박, 2.5박, 4박)
bass=[]
for i in range(BARS):
    r=ROOTS[i%4]; t=i*bar
    for pos,vel,dur in [(1,112,0.9),(2.5,92,0.4),(4,100,0.9)]:
        s=t+(pos-1)*beat
        bass.append({"pitch":r,"start":s,"end":s+dur*beat,"vel":vel})
# 2) 새 멜로디 (원곡과 무관하게 새로 씀, D minor 스케일 안에서)
SC=[62,64,65,67,69,70,72,74]  # D dorian-ish / natural minor 위주
MEL=[[(74,1,1),(72,2,1),(70,3,2)],
     [(69,1,1.5),(67,2.5,1.5),(65,4,1)],
     [(65,1,1),(67,2,1),(69,3,1),(70,4,1)],
     [(72,1,2),(69,3,2)],
     [(74,1,1),(77,2,1),(74,3,2)],
     [(72,1,1.5),(70,2.5,1.5),(69,4,1)],
     [(67,1,1),(69,2,1),(72,3,2)],
     [(74,1,4)]]
mel=[]
for i in range(BARS):
    t=i*bar
    for (p,pos,dur) in MEL[i%len(MEL)]:
        s=t+(pos-1)*beat
        mel.append({"pitch":p,"start":s,"end":s+dur*beat*0.92,"vel":96})

bars=bar_grid(BPM, BARS*bar)
dr=drum_options(bars,BPM)["A"]

steps=[
 ("1_베이스만", [{"program":GM["synth_bass"][0],"notes":bass,"name":"Sub bass"}],
  "당신이 피아노로 치는 부분. D–B♭–F–C, 한 마디에 세 번만 누르면 됩니다."),
 ("2_베이스+선율", [{"program":GM["synth_bass"][0],"notes":bass,"name":"Sub bass"},
                 {"program":GM["square_lead"][0],"notes":mel,"name":"Lead"}],
  "그 위에 선율을 얹었습니다. 선율도 당신이 치시면 됩니다."),
 ("3_완성_드럼까지", [{"program":GM["synth_bass"][0],"notes":bass,"name":"Sub bass"},
                  {"program":GM["square_lead"][0],"notes":mel,"name":"Lead"},
                  {"program":GM["warm_pad"][0],"notes":[{"pitch":ROOTS[i%4]+24,"start":i*bar,"end":(i+1)*bar,"vel":48} for i in range(BARS)],"name":"Pad"},
                  {"is_drum":True,"notes":drum_notes(dr["events"]),"name":"Drums"}],
  "드럼과 패드는 제가 붙였습니다. 원곡에는 드럼이 거의 없어서 여기가 당신 곡의 차별점이 됩니다."),
]
for nm,tracks,desc in steps:
    m=write_midi(f"{OUT}/{nm}.mid",BPM,tracks)
    w=render(m,f"{OUT}/{nm}.wav"); p=to_mp3(w,f"{OUT}/{nm}.mp3","96k") if w else None
    print(f"{nm}: {os.path.getsize(p)//1024}KB" if p else f"{nm}: 렌더 실패")
