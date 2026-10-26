# -*- coding: utf-8 -*-
"""1안을 (a) 있는 그대로 (b) 고친 버전으로 렌더."""
import sys, os, pretty_midi, numpy as np
sys.path.insert(0,"/home/user/-/compose")
from midi_theory import GM
from compose import write_midi, render, to_mp3
D="/tmp/claude-0/-home-user--/4b2bd38e-8d7f-52a5-bb39-0e1615b1f404/scratchpad/an1"
pm=pretty_midi.PrettyMIDI(f"{D}/1안.mid")
BPM=120; beat=60/BPM; bar=beat*4
def notes(i):
    return [{"pitch":n.pitch,"start":n.start,"end":n.end,"vel":n.velocity} for n in pm.instruments[i].notes]
drum,bass,s1,s2,piano = notes(0),notes(1),notes(2),notes(3),notes(4)

# ---------- (a) 있는 그대로: 트랙 이름대로 악기만 배정 ----------
asis=[
 {"program":GM["strings"][0],"notes":s1,"name":"STRING"},
 {"program":GM["strings"][0],"notes":s2,"name":"STRING 2"},
 {"program":0,"notes":piano,"name":"Piano"},
 {"program":GM["finger_bass"][0],"notes":bass,"name":"Bass"},
 {"is_drum":True,"notes":drum,"name":"Drum as-is"},
]
m=write_midi(f"{D}/a_있는그대로.mid",BPM,asis)
w=render(m,f"{D}/a.wav"); to_mp3(w,f"{D}/a_있는그대로.mp3","96k")
print("a 있는그대로 완료")

# ---------- (b) 고친 버전 ----------
# 1) 베이스를 2옥타브 내려 서브베이스 음역으로 (아이언맨 D1~C2 대역)
bass_lo=[{**n,"pitch":n["pitch"]-24} for n in bass]
# 2) 드럼: C2 롱노트 4개 -> 실제 킥/스네어/하이햇 패턴 (8마디)
DR={"kick":36,"snare":38,"hat":42,"crash":49}
dr=[]
for b in range(8):
    t=b*bar
    for p,inst,v in [(1,"kick",104),(3,"kick",96),(2,"snare",98),(4,"snare",102)]:
        dr.append({"pitch":DR[inst],"start":t+(p-1)*beat,"end":t+(p-1)*beat+0.12,"vel":v})
    for k in range(8):
        dr.append({"pitch":DR["hat"],"start":t+k*beat/2,"end":t+k*beat/2+0.08,"vel":72 if k%2==0 else 50})
    if b%4==0:
        dr.append({"pitch":DR["crash"],"start":t,"end":t+0.5,"vel":92})
# 3) STRING 2를 그대로 겹치지 말고 한 옥타브 아래 + 18ms 지연 (폭이 생김)
s2w=[{**n,"pitch":n["pitch"]-12,"start":n["start"]+0.018,"end":n["end"]+0.018,"vel":max(40,n["vel"]-18)} for n in s2]
# 4) 9~16마디: 피아노/베이스/드럼이 비어 있어 스트링만 남음 -> 코드 진행을 한 번 더 깔아줌
CH=[[50,57,62,65],[46,53,58,62],[48,55,60,64],[45,57,61,64]]  # Dm, Bb, C, A
pad=[];bass2=[];dr2=[]
for k in range(4):
    t=(8+k*2)*bar
    for p in CH[k]:
        pad.append({"pitch":p,"start":t,"end":t+2*bar-0.05,"vel":58})
    root=CH[k][0]-24
    bass2.append({"pitch":root,"start":t,"end":t+2*bar-0.05,"vel":88})
for b in range(8,16):
    t=b*bar
    for p,inst,v in [(1,"kick",100),(3,"kick",92),(2,"snare",94),(4,"snare",98)]:
        dr2.append({"pitch":DR[inst],"start":t+(p-1)*beat,"end":t+(p-1)*beat+0.12,"vel":v})
    for k in range(8):
        dr2.append({"pitch":DR["hat"],"start":t+k*beat/2,"end":t+k*beat/2+0.08,"vel":68 if k%2==0 else 46})

fixed=[
 {"program":GM["strings"][0],"notes":s1,"name":"STRING"},
 {"program":GM["slow_strings"][0],"notes":s2w,"name":"STRING low"},
 {"program":0,"notes":piano,"name":"Piano"},
 {"program":GM["warm_pad"][0],"notes":pad,"name":"Pad fill b9-16"},
 {"program":GM["synth_bass"][0],"notes":bass_lo+bass2,"name":"Sub bass"},
 {"is_drum":True,"notes":dr+dr2,"name":"Drums"},
]
m=write_midi(f"{D}/b_고친버전.mid",BPM,fixed)
w=render(m,f"{D}/b.wav"); to_mp3(w,f"{D}/b_고친버전.mp3","96k")
print("b 고친버전 완료")

# ---------- (c) 아이언맨처럼: 템포 148 + 서브베이스 강조 ----------
r=148/120
def sc(ns,sh=0):
    return [{**n,"pitch":n["pitch"]+sh,"start":n["start"]/r,"end":n["end"]/r} for n in ns]
beat2=60/148; bar2=beat2*4
dr3=[]
for b in range(16):
    t=b*bar2
    for p,inst,v in [(1,"kick",104),(3,"kick",96),(2,"snare",98),(4,"snare",102)]:
        dr3.append({"pitch":DR[inst],"start":t+(p-1)*beat2,"end":t+(p-1)*beat2+0.1,"vel":v})
    for k in range(8):
        dr3.append({"pitch":DR["hat"],"start":t+k*beat2/2,"end":t+k*beat2/2+0.07,"vel":70 if k%2==0 else 48})
fast=[
 {"program":GM["strings"][0],"notes":sc(s1),"name":"STRING"},
 {"program":GM["slow_strings"][0],"notes":sc(s2,-12),"name":"STRING low"},
 {"program":0,"notes":sc(piano),"name":"Piano"},
 {"program":GM["warm_pad"][0],"notes":sc(pad),"name":"Pad"},
 {"program":GM["synth_bass"][0],"notes":sc(bass_lo+bass2),"name":"Sub bass"},
 {"is_drum":True,"notes":dr3,"name":"Drums"},
]
m=write_midi(f"{D}/c_148bpm.mid",148,fast)
w=render(m,f"{D}/c.wav"); to_mp3(w,f"{D}/c_148bpm.mp3","96k")
print("c 148bpm 완료")
for f in ("a_있는그대로","b_고친버전","c_148bpm"):
    print(f, os.path.getsize(f"{D}/{f}.mp3")//1024,"KB")
