# -*- coding: utf-8 -*-
"""Turn the five measured gaps (reference vs current) into numeric targets.

Rule: close ALPHA of each gap, never all of it. With ALPHA = 0.6 a target always stays 40% of the way short of the
reference, so the result is shaped by the same principles (low-end weight, width, change over time) but cannot match
the reference's mix fingerprint. Only measurable mix properties are used; nothing here refers to the reference's notes,
rhythm figures, timbres or audio.
"""
import json, math
ALPHA = 0.6
d = json.load(open("/home/user/-/compose/analysis/orig_vs_current.json", encoding="utf-8"))
o, c = d["orig"], d["cur"]
def tgt(cur, ref): return cur + ALPHA * (ref - cur)
def db(x): return 20 * math.log10(x)
B = {x["name"]: x for x in o["bands"]}; Bc = {x["name"]: x for x in c["bands"]}
mids = lambda bb: bb["로우미드"]["pct"] + bb["미드"]["pct"]
rows = []

# 1. low end
t1 = tgt(10.7, o["sub120_pct"])      # 10.7 = share below 120 Hz of the current mix with its bass high-passed (sub sweep, no-sub row)
sweep = {None: 10.7, -15: 13.8, -12: 16.8, -9: 22.3, -6: 31.2, -3: 43.8}
slope = (sweep[-3] - sweep[-6]) / 3.0
need_rel = -3 + (t1 - sweep[-3]) / slope
rows.append(("1 저역 (120 Hz 아래 점유)", f"{sweep[None]}%", f"{o['sub120_pct']:.1f}%", f"{t1:.1f}%",
             f"서브 −3 dB 단계에서 {sweep[-3]}% (격차의 {100*(sweep[-3]-sweep[None])/(o['sub120_pct']-sweep[None]):.0f}% 해소). 목표까지는 서브를 약 {need_rel:+.1f} dB까지 올려야 하는데, 정하신 −3 dB 상한을 넘는다 → 상한을 지키는 쪽이 복제에서 멀다"))

# 2. width above 250 Hz
sm_o = sum(x for x in o["extra"]["sm_db_250_6k"]) / len(o["extra"]["sm_db_250_6k"])
sm_c = sum(x for x in c["extra"]["sm_db_250_6k"]) / len(c["extra"]["sm_db_250_6k"])
corr_t = tgt(c["extra"]["corr_250_6k"], o["extra"]["corr_250_6k"]); sm_t = tgt(sm_c, sm_o)
rows.append(("2 폭 (250 Hz–6 kHz 좌우 상관)", f"{c['extra']['corr_250_6k']:+.2f}", f"{o['extra']['corr_250_6k']:+.2f}", f"{corr_t:+.2f}",
             f"사이드/미드 {sm_c:+.1f} → 목표 {sm_t:+.1f} dB, 즉 250 Hz 위의 사이드를 {sm_t-sm_c:+.1f} dB (x{10**((sm_t-sm_c)/20):.2f}). 250 Hz 아래는 모노로 유지. 상관이 0 아래로 가면 모노 재생에서 소리가 빠지므로 {corr_t:+.2f}가 안전한 값"))

# 3. change over time
nov_t = tgt(c["novelty_peak"], o["novelty_peak"]); cen_t = tgt(c["extra"]["centroid_std_oct"], o["extra"]["centroid_std_oct"])
rows.append(("3 변화 (노벨티 최대 / 센트로이드 변동)", f"{c['novelty_peak']:.2f} / {c['extra']['centroid_std_oct']:.2f} oct", f"{o['novelty_peak']:.2f} / {o['extra']['centroid_std_oct']:.2f} oct",
             f"{nov_t:.2f} / {cen_t:.2f} oct",
             f"센트로이드가 중심(약 {c['cen_median']:.0f} Hz) 둘레를 ±{cen_t:.2f}옥타브(약 {c['cen_median']*2**-cen_t:.0f}–{c['cen_median']*2**cen_t:.0f} Hz) 오가야 한다. 음량 굴곡(오목한 곳)은 현재 1회 → 원본 5회의 60% 지점인 3회"))

# 4. mids and top
m_c, m_o = mids(Bc), mids(B); m_t = tgt(m_c, m_o)
air_c, air_o = Bc["에어"]["db_rel"], B["에어"]["db_rel"]; air_t = tgt(air_c, air_o)
# share after the sub at -3 dB: rest scaled by (1-.438)/(1-.107)
m_after_sub = m_c * (1 - 0.438) / (1 - 0.107)
k = (m_t / 100) * (100 - m_after_sub) / (m_after_sub * (1 - m_t / 100))
rows.append(("4 중음 점유 (250 Hz–1 kHz)", f"{m_c:.1f}%", f"{m_o:.1f}%", f"{m_t:.1f}%",
             f"서브를 넣으면 이미 {m_after_sub:.1f}%로 내려간다. 남은 만큼은 이 대역을 {db(k**0.5):+.1f} dB 깎으면 된다. 에어(6–16 kHz)는 {air_c:.1f} → {air_t:.1f} dB. 단 GM 음원에는 8 kHz 위 신호가 거의 없어서 EQ로 올리면 잡음만 커진다 → 소리 자체(글로켄슈필·활 소리)로 채워야 한다"))

# 5. crest
cr_t = tgt(c["crest_db"], o["crest_db"])
rows.append(("5 크레스트 (피크/평균)", f"{c['crest_db']:.1f} dB", f"{o['crest_db']:.1f} dB", f"{cr_t:.1f} dB",
             f"서브 −3 dB 단계에서 15.3 dB로 이미 {c['crest_db']-15.3:.1f} dB 내려옴. 나머지 {15.3-cr_t:.1f} dB는 타악(팀파니·타이코·글로켄슈필) 피크를 눌러서 줄인다"))

md = ["# 격차 5개 계산 (격차의 {}%만 줄이는 규칙)".format(int(ALPHA * 100)), "",
      "| 항목 | 현재 | 원본 | 목표 | 어떻게 |", "|---|---|---|---|---|"]
md += [f"| {a} | {b} | {c_} | **{d_}** | {e} |" for a, b, c_, d_, e in rows]
open("/home/user/-/compose/analysis/gap_plan.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
print("\n".join(md))
