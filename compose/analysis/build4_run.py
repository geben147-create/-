# -*- coding: utf-8 -*-
"""Build three orchestral versions of the corrected draft.

python3 build4_run.py <folder holding 1안.mid> [out folder]
"""
import os, sys, json, subprocess, shutil
import numpy as np, soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import rebuild3 as R
import orchestra as O
import master_simple as M

SRC = sys.argv[1] if len(sys.argv) > 1 else HERE
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(SRC, "v4")
TMP = os.path.join(OUT, "_stems")
os.makedirs(TMP, exist_ok=True)

tracks, bpm = R.load(os.path.join(SRC, "1안.mid"))
pedal, bass, s1, s2, piano = tracks[0], tracks[1], tracks[2], tracks[3], tracks[4]
report = {"tempo": bpm, "edits": [], "removed": []}
def ed(i, w, x): report["edits"].append({"id": i, "what": w, "exact": x})

# ---- the composer's own material, corrected -------------------------------------------
s1, d1 = R.square_loop(s1)
s2, d2 = R.square_loop(s2)
ed("square-loop", "둘째 바퀴가 0.7초 일찍 들어와 4번째 블록이 3.25초였던 것을 4.0초로 맞춤",
   f"STRING +{d1:.3f}s, STRING 2 +{d2:.3f}s")

s1, m1 = R.snap_early(s1); s2, m2 = R.snap_early(s2)
if m1 + m2: ed("snap-early", "마디선보다 먼저 들어온 음을 마디선에 붙임", f"STRING {m1}개, STRING 2 {m2}개")

s1, f1 = O.straighten_block4(s1)
s2, f2 = O.straighten_block4(s2)
ed("straighten-block4",
   "마지막 블록만 박자가 어긋나 있었음 (1~3블록은 0.25초 격자에 정확히 맞는데 4블록만 "
   "0.125~0.25초로 들쭉날쭉, 음도 16개가 아니라 15개). 당신이 친 음 순서 그대로 8분음표 격자에 "
   "올리고, 당신이 만든 4음 묶음 패턴을 완성하는 C#5 한 개를 채움",
   f"[C#5 E5 G5 E5][C#5 E5 G5 C#5][A4 C#5 E5 C#5][A#4 C#5 E5 +C#5] — "
   f"STRING {f1}, STRING 2 {f2} (15음 → 16음)")

piano, plog = R.fix_piano_block3(piano)
ed("block3-c-to-f", "3블록에서 당신 화음(C major)과 당신 STRING(F major)이 동시에 울려 E와 F가 "
   "반음으로 4초 내내 부딪힘. 곡 전체를 끌고 가는 STRING을 살리고 화음을 F/C로",
   ", ".join(sorted(set(plog))))

piano, ulog = R.unmask_bass(piano, bass)
ed("unmask-bass", "당신 베이스가 화음 트랙 맨 아래 음과 완전 유니즌이라 베이스 선이 안 들렸음. "
   "중복된 맨 아래 음을 빼서 베이스에게 그 음역을 넘김", "제거: " + ", ".join(ulog))

piano, hlog = O.horn_voicing_block4(piano)
ed("block4-a7-voicing",
   "4블록에서 당신 STRING의 A#4(♭9)가 화음의 루트 A3 바로 위에 올라앉아 단9도로 부딪혔음. "
   "당신 A#4는 그대로 두고 — 조성 안의 음이고 당신이 의도한 반음 상승이므로 — 대신 화음의 루트를 "
   "G로 내려 A7의 7음을 만듦. 한 음만 움직임",
   ", ".join(hlog) + "  → 화음 G3-C#4-E4 + 베이스 A2 = 제대로 된 A7")

pedal, pdlog = R.pedal_to_roots(pedal)
ed("pedal-roots", "제일 낮은 트랙이 네 화음 내내 C2 하나를 붙잡아 A7의 C#과 충돌. "
   "당신이 친 각 화음의 루트로", "; ".join(pdlog))

piano, g1 = O.fill_blocks(piano); bass, g2 = O.fill_blocks(bass); pedal, g3 = O.fill_blocks(pedal)
ed("fill-blocks",
   "당신이 누른 긴 음들이 블록 끝까지 못 가고 일찍 끊겼음 (베이스는 1블록의 49%만 소리가 나고 "
   "2초가 비어 있었고, 화음은 매번 0.44초 구멍을 두고 다시 쳤음). 길이만 늘려 블록 끝까지 채움",
   f"화음 {g1}음, 베이스 {g2}음, 저음 {g3}음 — 음높이·시작점은 손대지 않음")

bass2 = bass + R.shift(bass, R.PASS2)
piano2 = piano + R.shift(piano, R.PASS2)
pedal2 = pedal + R.shift(pedal, R.PASS2)
ed("copy-paste-pass2", "둘째 바퀴에 베이스·화음·저음이 아예 없어 STRING만 혼자 돌고 있었음. 첫 바퀴를 복붙",
   f"+{R.PASS2:.0f}s 에 베이스 {len(bass)}, 화음 {len(piano)}, 저음 {len(pedal)}")

report["removed"] = ["드럼 킷 전체 (킥·스네어·하이햇·심벌·탐)", "신스 베이스 16분음표 펄스 (쿵짝거려서 제거)"]

ch = R.choir(2)
GM = O.GM

# ---- seating: pan -1 = hard left, +1 = hard right; send = how much hall -----------------
def T(name, mn, notes, prog, pan, gain, send, who):
    return dict(name=name, midi_name=mn, notes=notes, program=prog,
                pan=pan, gain_db=gain, send_db=send, who=who)

BASE = [
    T("제1바이올린 — 당신 멜로디", "Violin I (your melody)", R.scale_vel(s2, 1.75), GM["strings1"],
      -0.38, 0.0, -10.0, "당신"),
    T("제2바이올린 — 당신 멜로디 겹침", "Violin II (your melody, doubled)", R.scale_vel(s1, 0.78), GM["strings2"],
      -0.10, -5.0, -8.0, "당신"),
    T("호른 — 당신 화음", "Horns (your chords)", R.scale_vel(piano2, 0.92), GM["horn"],
      -0.30, -5.0, -4.0, "당신(교정)"),
    T("콘트라베이스 — 당신 베이스", "Contrabass (your bass)", R.scale_vel(bass2, 1.15), GM["contrabass"],
      0.40, -2.0, -9.0, "당신"),
    T("콘트라베이스 — 저음 루트", "Contrabass (root, retuned)", R.set_vel(pedal2, 92), GM["contrabass"],
      0.30, -4.0, -9.0, "당신(교정)"),
    T("합창", "Choir", ch, GM["choir"], 0.0, -9.0, -2.0, "제가 만든 반주"),
    T("글로켄슈필 — 쨍", "Glockenspiel", O.glock(), GM["glock"], 0.55, -15.0, -3.0, "제가 만든 반주"),
]

VERSIONS = {
    "orch1_tremolo": dict(
        title="1안 · 현악 트레몰로",
        blurb="둘째 바퀴에서 첼로·비올라가 트레몰로로 깔립니다. 활을 잘게 떠는 소리라 "
              "잘게 부서지면서도 박자를 때리지 않습니다. 가장 조용하고 클래식에 가깝습니다.",
        extra=[T("트레몰로 현악", "Tremolo strings", O.tremolo(), GM["tremolo"],
                 -0.05, -7.0, -5.0, "제가 만든 반주")]),
    "orch2_pizzicato": dict(
        title="2안 · 피치카토",
        blurb="둘째 바퀴에서 현을 손가락으로 뜯습니다. 당신이 말한 잘게 부서지는 느낌을 "
              "신스가 아니라 현악 섹션이 냅니다. 윤곽이 가장 또렷합니다.",
        extra=[T("피치카토 현악", "Pizzicato strings", O.pizzicato(), GM["pizzicato"],
                 0.22, -5.0, -6.0, "제가 만든 반주")]),
    "orch3_tremolo_timpani": dict(
        title="3안 · 트레몰로 + 팀파니",
        blurb="1안에 팀파니 롤을 아주 약하게 더했습니다. 들린다기보다 느껴지는 정도로, "
              "블록마다 조금씩 커지면서 밀어 올립니다. 가장 영화음악에 가깝습니다.",
        extra=[T("트레몰로 현악", "Tremolo strings", O.tremolo(), GM["tremolo"],
                 -0.05, -7.0, -5.0, "제가 만든 반주"),
               T("팀파니 롤", "Timpani roll", O.timpani(), GM["timpani"],
                 0.05, -5.0, -4.0, "제가 만든 반주")]),
}

IR = O.hall_ir()
report["hall"] = {"rt60_low_mid_high": [2.6, 2.1, 1.0], "predelay_ms": 24,
                  "what": "합성한 콘서트홀 — 초기 반사 6개 + 주파수별로 감쇠 시간이 다른 잔향"}
report["versions"] = {}

for key, v in VERSIONS.items():
    T_ALL = BASE + v["extra"]
    stems = []
    for i, t in enumerate(T_ALL):
        if not t["notes"]:
            continue
        audio, sr = O.render_stem(t, bpm, f"{TMP}/{key}_{i}.wav", f"{TMP}/{key}_{i}.mid")
        stems.append({**t, "audio": audio})
    y = O.mix(stems, IR, wet_bus_db=-6.0)
    # What is each added layer actually worth? Re-mix without it and compare. A layer that
    # is 30 dB under the programme is not "subtle", it is inaudible.
    full_rms = np.sqrt(np.mean(y ** 2))
    worth = {}
    W = int(0.2 * 44100)
    for s_ in stems:
        if s_["who"] != "제가 만든 반주":
            continue
        y2 = O.mix([q for q in stems if q is not s_], IR, wet_bus_db=-6.0)
        n2 = min(len(y), len(y2))
        diff = y[:n2] - y2[:n2]
        avg = np.sqrt(np.mean(diff ** 2))
        # A sparse bell can be plainly audible and still barely move the whole-file RMS,
        # so also take its loudest 200 ms against the music in that same 200 ms.
        nb = n2 // W
        dw = np.sqrt((diff[:nb * W] ** 2).reshape(nb, -1).mean(axis=1))
        mw = np.sqrt((y[:nb * W] ** 2).reshape(nb, -1).mean(axis=1))
        peak = float(np.max(20 * np.log10(dw / (mw + 1e-12) + 1e-12)))
        worth[s_["name"]] = {"avg_db": round(float(20 * np.log10(avg / full_rms + 1e-12)), 1),
                             "peak_db": round(peak, 1)}
    y = y / max(1.0, np.max(np.abs(y)) / 0.89)
    raw = f"{OUT}/{key}_raw.wav"
    sf.write(raw, y, 44100, subtype="PCM_24")
    rep = M.master(raw, f"{OUT}/{key}_master.wav", target_lufs=-14.0,
                   air_db=2.5, air_hz=7000.0)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{OUT}/{key}_master.wav",
                    "-ac", "2", "-b:a", "128k", f"{OUT}/{key}.mp3"], check=True)
    os.remove(raw)
    R.write_midi(f"{OUT}/{key}.mid", bpm, T_ALL)
    report["versions"][key] = {
        "title": v["title"], "blurb": v["blurb"], "master": rep,
        "length_sec": round(len(y) / 44100, 2),
        "layer_worth_db": worth,
        "stage": [{"name": t["name"], "who": t["who"], "notes": len(t["notes"]),
                   "pan": t["pan"], "gain_db": t["gain_db"], "send_db": t["send_db"]}
                  for t in T_ALL if t["notes"]],
    }
    tot = sum(len(t["notes"]) for t in T_ALL)
    mine = sum(len(t["notes"]) for t in T_ALL if t["who"] == "제가 만든 반주")
    report["versions"][key]["notes_total"] = tot
    report["versions"][key]["notes_mine"] = mine
    report["versions"][key]["notes_yours"] = tot - mine
    print(f"\n### {v['title']}  — {tot} notes ({tot-mine} 당신 / {mine} 제가)")
    for t in T_ALL:
        if t["notes"]:
            print(f"    {t['name']:<26} {len(t['notes']):>4}  pan{t['pan']:+.2f} {t['gain_db']:+5.1f}dB "
                  f"hall{t['send_db']:+5.1f}  [{t['who']}]")
    for k_, v_ in sorted(worth.items(), key=lambda kv: kv[1]["peak_db"], reverse=True):
        print(f"       레이어  {k_:<20} 평균 {v_['avg_db']:+6.1f} dB | 가장 크게 들리는 순간 {v_['peak_db']:+6.1f} dB")
    print(f"    master {rep['before']['lufs']:+.2f} -> {rep['after']['lufs']:+.2f} LUFS, "
          f"TP {rep['after']['true_peak']:+.2f}, clipped {rep['after']['clipped']}, "
          f"{report['versions'][key]['length_sec']}s")

shutil.rmtree(TMP, ignore_errors=True)
json.dump(report, open(f"{OUT}/report.json", "w"), ensure_ascii=False, indent=1)
print("\n=== 고친 것 ===")
for e in report["edits"]:
    print(f"  [{e['id']}] {e['what'][:95]}\n      {e['exact'][:150]}")
print(f"\nwrote {OUT}/report.json")
