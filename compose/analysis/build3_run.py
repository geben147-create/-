# -*- coding: utf-8 -*-
"""Build the three corrected versions and master each one.

python3 build3_run.py <folder holding 1안.mid> [out folder]
"""
import os, sys, json, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # compose/
import rebuild3 as R
import master_simple as M
from compose import render

SRC = sys.argv[1] if len(sys.argv) > 1 else HERE
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(SRC, "v3")
os.makedirs(OUT, exist_ok=True)

GM_STRINGS, GM_STRINGS2 = 48, 49
GM_PIANO, GM_BASS, GM_SUB, GM_PULSE, GM_CHOIR = 0, 33, 38, 38, 52

tracks, bpm = R.load(os.path.join(SRC, "1안.mid"))
pedal, bass, s1, s2, piano = tracks[0], tracks[1], tracks[2], tracks[3], tracks[4]
report = {"tempo": bpm, "source_notes": {"pedal": len(pedal), "bass": len(bass),
          "STRING": len(s1), "STRING 2": len(s2), "piano": len(piano)}, "edits": []}

# ---- 1. square the loop so every block is exactly 4.0 s
s1, d1 = R.square_loop(s1)
s2, d2 = R.square_loop(s2)
report["edits"].append({"id": "square-loop",
    "what": "두 STRING 트랙의 둘째 바퀴를 제자리로 밀어 블록을 모두 4.0초로 맞춤",
    "exact": f"STRING +{d1:.3f}s, STRING 2 +{d2:.3f}s (4번째 블록이 3.25초였음)"})

# ---- 2. pull notes that start just before a barline onto the barline
s1, m1 = R.snap_early(s1)
s2, m2 = R.snap_early(s2)
if m1 + m2:
    report["edits"].append({"id": "snap-early",
        "what": "다음 화음 음이 마디선보다 먼저 들어와 앞 화음과 부딪히던 것을 마디선에 맞춤",
        "exact": f"STRING {m1}개, STRING 2 {m2}개"})

# ---- 3. block 3: piano yields to the ostinato
piano, plog = R.fix_piano_block3(piano)
report["edits"].append({"id": "block3-c-to-f",
    "what": "3번째 블록에서 피아노가 C major, STRING이 F major를 동시에 쳐서 E와 F가 반음으로 부딪히던 것 수정. "
            "곡 전체를 끌고 가는 STRING을 살리고 피아노를 F/C로 바꿈",
    "exact": ", ".join(sorted(set(plog)))})

# ---- 3b. the piano stops doubling the bass at unison
piano, ulog = R.unmask_bass(piano, bass)
report["edits"].append({"id": "unmask-bass",
    "what": "당신 베이스가 피아노 맨 아래 음과 같은 옥타브·같은 타이밍의 완전 유니즌이어서 "
            "베이스 선이 전혀 들리지 않았음. 피아노의 중복된 맨 아래 음을 빼서 베이스에게 그 음역을 넘김. "
            "화음은 그대로 유지됨 (그 음은 베이스가 계속 치고 있음)",
    "exact": "피아노에서 제거: " + ", ".join(ulog)})

# ---- 4. the sustained C2 pedal becomes the root of each chord
pedal, pdlog = R.pedal_to_roots(pedal)
report["edits"].append({"id": "pedal-roots",
    "what": "제일 낮은 트랙이 네 화음 내내 C2 하나를 붙잡고 있어 A7의 C#과 반음으로 충돌. "
            "당신이 이미 연주한 각 화음의 루트로 바꿈",
    "exact": "; ".join(pdlog)})

# ---- 5. copy-paste the lower parts into the second statement
bass2  = bass  + R.shift(bass,  R.PASS2)
piano2 = piano + R.shift(piano, R.PASS2)
pedal2 = pedal + R.shift(pedal, R.PASS2)
report["edits"].append({"id": "copy-paste-pass2",
    "what": "둘째 바퀴에는 베이스·피아노·저음이 아예 없어서 STRING만 외롭게 돌고 있었음. 첫 바퀴를 그대로 복붙",
    "exact": f"+{R.PASS2:.1f}s 지점에 베이스 {len(bass)}, 피아노 {len(piano)}, 저음 {len(pedal)} 노트 복제"})

END = max(max(n["end"] for n in s1), max(n["end"] for n in s2),
          max(n["end"] for n in piano2), 32.0)
report["length_sec"] = round(END, 2)

# ---- 6. the voices that get added, same in all three versions
ch = R.choir(2)
report["added"] = {
    "choir": {"notes": len(ch),
              "what": "당신이 친 화음의 구성음만 길게. A3~F4 (당신 STRING은 D5~A5) 이므로 멜로디를 덮지 않음",
              "voicing": [[R.nn(q) for q in v] for v in R.CHOIR]},
}

MIX = {   # their own parts, pushed to the front
    "STRING 2 (당신)":  dict(notes=R.scale_vel(s2, 1.70), program=GM_STRINGS,  ascii="STRING 2 (yours)"),
    "STRING (당신)":    dict(notes=R.scale_vel(s1, 0.80), program=GM_STRINGS2, ascii="STRING (yours, soft double)"),
    "피아노 (당신)":     dict(notes=R.scale_vel(piano2, 1.18), program=GM_PIANO, ascii="Piano (yours)"),
    "베이스 (당신)":     dict(notes=R.scale_vel(bass2, 1.20), program=GM_BASS,  ascii="Bass (yours)"),
}

VERSIONS = {
    "A_깔린베이스": {
        "title": "A · 깔린 베이스",
        "blurb": "저음 루트를 처음부터 끝까지 길게 깔아 바닥만 받쳐줍니다. 가장 조용하고 "
                 "당신 멜로디가 제일 또렷하게 들립니다. 짜짜짜 펄스는 없습니다.",
        "sub": R.sustained_sub((0, 1), vel=100), "pulse": [],
    },
    "B_짜짜베이스": {
        "title": "B · 짜짜짜 베이스",
        "blurb": "첫 바퀴는 깔린 저음, 둘째 바퀴는 그 저음을 빼고 16분음표 스타카토 펄스로 "
                 "바꿔 버립니다. 바닥이 \u2018붙잡은 소리\u2019에서 \u2018잘게 부서지는 소리\u2019로 넘어가면서 고조됩니다.",
        "sub": R.sustained_sub((0,), vel=100), "pulse": R.pulse(R.PASS2),
    },
    "C_둘다": {
        "title": "C · 둘 다",
        "blurb": "깔린 저음을 끝까지 유지한 채로 둘째 바퀴에 짜짜짜 펄스를 겹칩니다. 가장 두껍습니다.",
        "sub": R.sustained_sub((0, 1), vel=96), "pulse": R.pulse(R.PASS2),
    },
}

report["versions"] = {}
for key, v in VERSIONS.items():
    T = []
    for name, d in MIX.items():
        T.append({"name": name, "midi_name": d["ascii"], "program": d["program"], "notes": d["notes"]})
    T.append({"name": "저음 루트 (당신 트랙 음고 교정)", "midi_name": "Sub root (your pitches, retuned)",
              "program": GM_SUB, "notes": v["sub"]})
    if v["pulse"]:
        T.append({"name": "짜짜짜 펄스 (당신 음고, 리듬만 새로)", "midi_name": "16th pulse (your pitches)",
                  "program": GM_PULSE, "notes": v["pulse"]})
    T.append({"name": "합창 (당신 화음 구성음)", "midi_name": "Choir (your chord tones)",
              "program": GM_CHOIR, "notes": ch})

    mid = R.write_midi(f"{OUT}/{key}.mid", bpm, T)
    raw = render(mid, f"{OUT}/{key}_raw.wav", gain=0.75)
    if not raw:
        print("render failed", key); sys.exit(1)
    rep = M.master(raw, f"{OUT}/{key}_master.wav", target_lufs=-14.0)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{OUT}/{key}_master.wav",
                    "-ac", "1", "-b:a", "112k", f"{OUT}/{key}.mp3"], check=True)
    os.remove(raw)
    counts = {t["name"]: len(t["notes"]) for t in T}
    report["versions"][key] = {"title": v["title"], "blurb": v["blurb"],
                               "tracks": counts, "total_notes": sum(counts.values()),
                               "master": rep}
    print(f"\n### {v['title']}  — {sum(counts.values())} notes")
    for n, c in counts.items():
        print(f"    {n:<34} {c:>5}")
    print(f"    master  {rep['before']['lufs']:+.2f} -> {rep['after']['lufs']:+.2f} LUFS, "
          f"TP {rep['after']['true_peak']:+.2f} dBTP, clipped {rep['after']['clipped']}")

json.dump(report, open(f"{OUT}/report.json", "w"), ensure_ascii=False, indent=1)
print("\n=== edits ===")
for e in report["edits"]:
    print(f"  [{e['id']}] {e['what']}\n      {e['exact']}")
print(f"\nwrote {OUT}/report.json   length {report['length_sec']}s")

# ---------------------------------------------------------------- the one note left to you
# Their ostinato plays A#4 in block 4 against the A7 chord. A# is Bb, the b9, and Bb is the
# sixth degree of D harmonic minor, so it is in key and defensible. It is also the one
# remaining semitone tension in the piece. Rather than silently rewrite their note, render
# the surrounding eight seconds both ways so they can choose.
AB = f"{OUT}/ab"
os.makedirs(AB, exist_ok=True)
CLIP0, CLIP1 = 24.0, 32.0

def clip(notes, lo=CLIP0, hi=CLIP1):
    return [{**n, "start": n["start"] - lo, "end": min(n["end"], hi) - lo}
            for n in notes if lo <= n["start"] < hi and n["end"] > lo]

def retune_bflat(notes):
    return [({**n, "pitch": 69} if n["pitch"] == 70 else dict(n)) for n in notes]

base = VERSIONS["C_둘다"]
ab_report = {}
for tag, tweak in [("as_played_Bb", lambda x: x), ("retuned_A", retune_bflat)]:
    T = [
        {"name": "STRING 2", "midi_name": "STRING 2", "program": GM_STRINGS,
         "notes": clip(tweak(MIX["STRING 2 (당신)"]["notes"]))},
        {"name": "STRING",   "midi_name": "STRING",   "program": GM_STRINGS2,
         "notes": clip(tweak(MIX["STRING (당신)"]["notes"]))},
        {"name": "Piano",    "midi_name": "Piano",    "program": GM_PIANO,
         "notes": clip(MIX["피아노 (당신)"]["notes"])},
        {"name": "Bass",     "midi_name": "Bass",     "program": GM_BASS,
         "notes": clip(MIX["베이스 (당신)"]["notes"])},
        {"name": "Sub",      "midi_name": "Sub",      "program": GM_SUB,
         "notes": clip(base["sub"])},
        {"name": "Pulse",    "midi_name": "Pulse",    "program": GM_PULSE,
         "notes": clip(base["pulse"])},
        {"name": "Choir",    "midi_name": "Choir",    "program": GM_CHOIR, "notes": clip(ch)},
    ]
    mid = R.write_midi(f"{AB}/{tag}.mid", bpm, T)
    raw = render(mid, f"{AB}/{tag}_raw.wav", gain=0.75)
    rep = M.master(raw, f"{AB}/{tag}_master.wav", target_lufs=-14.0)
    # trim the long GM string/choir reverb tail so the two clips can be A/B'd quickly
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{AB}/{tag}_master.wav",
                    "-t", "9.5", "-af", "afade=out:st=8.6:d=0.9",
                    "-ac", "1", "-b:a", "112k", f"{AB}/{tag}.mp3"], check=True)
    os.remove(raw); os.remove(f"{AB}/{tag}_master.wav")
    ab_report[tag] = rep["after"]
    print(f"  A/B {tag}: {sum(len(t['notes']) for t in T)} notes, {rep['after']['lufs']} LUFS")

report["ab_test"] = {"window": [CLIP0, CLIP1], "what": "당신 STRING의 A#4(B♭)를 그대로 둔 것 vs A4로 내린 것",
                     "masters": ab_report}
json.dump(report, open(f"{OUT}/report.json", "w"), ensure_ascii=False, indent=1)
print(f"wrote A/B clips to {AB}")
