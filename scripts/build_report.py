"""Builds docs/index.html — the step-by-step tutorial + per-track results + links — from the JSON the
pipeline wrote. Re-run after every pipeline run:  python scripts/build_report.py
Static content (priorities, install ranking, distributor table, fact-check) lives in docs/content.json
so it can be edited without touching code."""
from __future__ import annotations
import os, sys, json, glob, html
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/geben147-create/-"
BRANCH = "claude/stay-with-fade-qc-qq268d"
BLOB = f"{REPO}/blob/{BRANCH}/"
RAW = f"{REPO}/raw/{BRANCH}/"


def j(p, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def esc(s):
    return html.escape(str(s), quote=True)


def mmss(t):
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def envelope(path, step=0.25):
    try:
        x, sr = sf.read(path, dtype="float32", always_2d=True)
    except Exception:
        return []
    y = np.mean(x, axis=1); n = int(step * sr)
    return [float(np.sqrt(np.mean(y[i:i + n] ** 2))) for i in range(0, len(y), n)]


# ------------------------------------------------------------------ SVG helpers

def svg_timeline(man, an):
    dur = man["duration_out_s"]; W, H = 1000, 74
    off = man["original_offset_in_output_s"]
    parts = [f'<svg class="tl" viewBox="0 0 {W} {H}" role="img" aria-label="구간 타임라인">']
    parts.append(f'<rect x="0" y="22" width="{W}" height="26" rx="4" fill="var(--panel2)"/>')
    colors = {"intro": "var(--mute)", "verse": "#3f7a5c", "hook": "#5db67f", "low": "#2c5c45", "outro": "var(--mute)"}
    for s in man["sections_output_time"]:
        x0 = s["start"] / dur * W; w = max(2, (s["end"] - s["start"]) / dur * W - 2)
        parts.append(f'<rect x="{x0:.1f}" y="22" width="{w:.1f}" height="26" rx="3" fill="{colors.get(s["label"], "#3f7a5c")}" opacity="0.85">'
                     f'<title>{esc(s["label"])} · {mmss(s["start"])}–{mmss(s["end"])} · {s["bars"]}마디 · {s["rms_db"]} dB RMS</title></rect>')
        if w > 40:
            parts.append(f'<text x="{x0 + 6:.1f}" y="40" class="tl-lbl">{esc(s["label"])}</text>')
    # intro (new)
    iw = off / dur * W
    parts.append(f'<rect x="0" y="22" width="{iw:.1f}" height="26" rx="3" fill="var(--gold)" opacity="0.9"><title>새 인트로 {man["intro"]["bars"]}마디 ({man["intro"]["len_s"]}s)</title></rect>')
    parts.append(f'<text x="{iw/2:.1f}" y="16" class="tl-tag gold" text-anchor="middle">NEW</text>')
    for c in man["changed_sections"]:
        a, b = c["output_range"]; x0 = a / dur * W; w = (b - a) / dur * W
        parts.append(f'<rect x="{x0:.1f}" y="19" width="{w:.1f}" height="32" rx="4" fill="none" stroke="var(--lime)" stroke-width="2.5"><title>새 드럼/베이스/패드 · {mmss(a)}–{mmss(b)}</title></rect>')
        parts.append(f'<text x="{x0 + w/2:.1f}" y="66" class="tl-tag lime" text-anchor="middle">🥁🎸 {mmss(a)}–{mmss(b)}</text>')
    if man.get("breakdown"):
        a, b = man["breakdown"]["output_range"]; x0 = a / dur * W; w = max(3, (b - a) / dur * W)
        parts.append(f'<rect x="{x0:.1f}" y="19" width="{w:.1f}" height="32" fill="var(--red)" opacity="0.75"><title>브레이크다운 (드럼 -14 dB, 베이스 -8 dB) {mmss(a)}–{mmss(b)}</title></rect>')
        parts.append(f'<text x="{x0 + w/2:.1f}" y="16" class="tl-tag red" text-anchor="middle">⚡</text>')
    for t in range(0, int(dur) + 1, 30):
        x = t / dur * W
        parts.append(f'<line x1="{x:.1f}" y1="48" x2="{x:.1f}" y2="53" stroke="var(--mute)" stroke-width="1"/>')
        parts.append(f'<text x="{x:.1f}" y="{H-2}" class="tl-tick" text-anchor="{"start" if t == 0 else "middle"}">{t//60}:{t%60:02d}</text>')
    parts.append("</svg>")
    return "".join(parts)


def svg_envelope(env_a, env_b, off_s, step=0.25):
    W, H = 1000, 120
    n = max(len(env_a) + int(off_s / step), len(env_b))
    mx = max(max(env_a or [1e-6]), max(env_b or [1e-6]), 1e-6)
    def poly(env, shift):
        pts = []
        for i, v in enumerate(env):
            x = (i + shift) / n * W; y = H - 6 - (v / mx) * (H - 14)
            pts.append(f"{x:.1f},{y:.1f}")
        return " ".join(pts)
    return (f'<svg class="env" viewBox="0 0 {W} {H}" role="img" aria-label="RMS 엔벌로프 전후">'
            f'<rect x="0" y="0" width="{W}" height="{H}" fill="var(--panel2)" rx="4"/>'
            f'<polyline points="{poly(env_a, off_s / step)}" fill="none" stroke="var(--mute)" stroke-width="1.6" opacity="0.9"/>'
            f'<polyline points="{poly(env_b, 0)}" fill="none" stroke="var(--lime)" stroke-width="1.6" opacity="0.95"/>'
            f'<text x="10" y="16" class="tl-tag" fill="var(--mute)">— 원본 (인트로만큼 밀어서 정렬)</text>'
            f'<text x="10" y="32" class="tl-tag lime">— 편곡 마스터</text></svg>')


# ------------------------------------------------------------------ per-track panel

def metric_rows(q):
    o, m = q["original"], q["distributor_flac"]
    rows = [
        ("길이", o["duration_mmss"], m["duration_mmss"]),
        ("샘플레이트 / 비트", f'{o["sample_rate"]} Hz / {o["subtype"]}', f'{m["sample_rate"]} Hz / {m["subtype"]}'),
        ("LUFS-I", o["lufs_integrated"], m["lufs_integrated"]),
        ("LRA (LU)", o["lra_lu"], m["lra_lu"]),
        ("True peak (dBTP, 4×)", o["true_peak_dbtp_4x"], m["true_peak_dbtp_4x"]),
        ("Sample peak (dBFS)", o["sample_peak_dbfs"], m["sample_peak_dbfs"]),
        ("Crest factor (dB)", o["crest_factor_db"], m["crest_factor_db"]),
        ("Stereo correlation", round(o["correlation"], 3), round(m["correlation"], 3)),
        ("1초 구간 음의 상관 비율", f'{o["neg_corr_ratio_1s"]*100:.2f}%', f'{m["neg_corr_ratio_1s"]*100:.2f}%'),
        ("최대 DC 절댓값", f'{o["dc_offset_max_abs"]:.7f}', f'{m["dc_offset_max_abs"]:.7f}'),
        ("0 dBFS 이상 샘플", o["clipped_samples_ge_0dbfs"], m["clipped_samples_ge_0dbfs"]),
        ("앞/뒤 무음 (s)", f'{o["head_silence_s"]} / {o["tail_silence_s"]}', f'{m["head_silence_s"]} / {m["tail_silence_s"]}'),
    ]
    return "".join(f"<tr><th>{esc(a)}</th><td>{esc(b)}</td><td class='after'>{esc(c)}</td></tr>" for a, b, c in rows)


def track_panel(td, idx):
    name = os.path.basename(td)
    an = j(f"{td}/02_analysis/analysis.json"); man = j(f"{td}/04_edits/arrangement_manifest.json")
    q = j(f"{td}/06_master/qc.json"); pr = j(f"{td}/03_proposals/proposals.json"); sep = j(f"{td}/01_stems/separation.json")
    ms = j(f"{td}/06_master/master_settings.json"); log = j(f"{td}/pipeline_log.json", {"stages": {}})
    midi = j(f"{td}/02_midi/reference_from_stems/transcription.json", {"stems": {}})
    if not (an and man and q):
        return f'<section class="track" id="{esc(name)}"><h3>{esc(name)}</h3><p class="warn">⚠️ 파이프라인 미완료 — pipeline_log.json 확인</p></section>'
    env_a = an["rms_envelope_0p25s"]; env_b = envelope(f"{td}/06_master/arranged_master_44k1_24bit.wav")
    rel = f"tracks/{name}/"
    def link(p, label, raw=False):
        return f'<a href="{(RAW if raw else BLOB) + rel + p}" target="_blank" rel="noopener">{esc(label)}</a>'
    checks = q["checks"]
    chk = "".join(f'<li class="{"ok" if v else "bad"}">{"✅" if v else "❌"} {esc(k)}</li>' for k, v in checks.items())
    cs = man["changed_sections"]
    dv, bv = man["decisions_used"]["drums"]["choice"], man["decisions_used"]["bass"]["choice"]
    props = "".join(
        f'<tr><th>{k}</th>' + "".join(f'<td><b class="lime">{v}</b> · {esc(pr[k][v]["description"])}<br>{link(f"03_proposals/{k}_{v}_preview.mp3", "▶ 미리듣기 MP3", raw=True)} · {link(f"03_proposals/{k}_{v}.mid", "MIDI")}</td>' for v in "ABC") + "</tr>"
        for k in ("drums", "bass")) + "<tr><th>bridge</th>" + "".join(
        f'<td><b class="lime">{v}</b> · {esc(pr["bridge"][v]["roman"])} ({esc(", ".join(pr["bridge"][v]["chords"]))})<br>{esc(pr["bridge"][v]["mood"])} · {link(f"03_proposals/bridge_{v}_chords_preview.mp3", "▶ 코드 베드", raw=True)}</td>' for v in "ABC") + "</tr>"
    stage_secs = ", ".join(f'{k} {v.get("seconds", "?")}s' for k, v in log["stages"].items())
    return f'''
<section class="track" id="{esc(name)}">
  <header class="track-h"><span class="tnum">TRACK {idx}</span><h3>{esc(name)}</h3>
    <div class="chips"><span class="chip">🎼 {an["tempo_bpm"]} BPM</span><span class="chip">🔑 {esc(an["key"]["key"])} <small>(신뢰도 {an["key"]["confidence"]})</small></span>
    <span class="chip">📏 {man["bars_total"]}마디 · {len(an["sections"])}구간</span><span class="chip">🧩 분리: {esc(sep["backend"])} (합산 상관 {sep.get("sum_correlation")})</span>
    <span class="chip {"ok" if q["all_technical_checks_pass"] else "bad"}">{"✅ 기술 QC 통과" if q["all_technical_checks_pass"] else "❌ 기술 QC 항목 실패"}</span></div></header>
  <div class="grid2">
    <div>
      <h4>🎧 먼저 들어볼 파일</h4>
      <ul class="files">
        <li>🎵 {link("06_master/LISTEN_arranged.mp3", "LISTEN_arranged.mp3 — 편곡 결과 (청취용)", raw=True)}</li>
        <li>🆚 {link("06_master/AB_original24s_silence1s_arranged24s.mp3", "A/B 비교 — 원본 24초 → 무음 1초 → 편곡 24초", raw=True)} <small>(원본 {ms["ab_compare"]["orig_start_s"]}s ↔ 편곡 {ms["ab_compare"]["arranged_start_s"]}s, {ms["ab_compare"]["matched_lufs"]} LUFS로 음량 맞춤)</small></li>
        <li>📦 {link("06_master/distributor_candidate_44k1_16bit.flac", "distributor_candidate_44k1_16bit.flac — 제출 후보 (청취·권리 확인 전 제출 금지)", raw=True)}</li>
        <li>🧾 {link("06_master/qc.json", "qc.json")} · {link("04_edits/arrangement_manifest.json", "arrangement_manifest.json")} · {link("02_analysis/analysis.json", "analysis.json")} · {link("07_evidence/AI_DISCLOSURE.txt", "AI_DISCLOSURE.txt")} · {link("07_evidence/file_hashes.csv", "file_hashes.csv")}</li>
      </ul>
      <h4>✂️ 실제로 바뀐 곳 (출력 타임코드)</h4>
      <ul class="changes">
        <li><b class="gold">00:00.00–{mmss(man["intro"]["len_s"])}</b> 새 신스 인트로 {man["intro"]["bars"]}마디 (패드 {esc(man["intro"]["chord"])} + 라이저 + 하이햇 픽업). 원곡은 <b>{mmss(man["original_offset_in_output_s"])}</b>부터 시작.</li>
        {"".join(f'<li><b class="lime">{mmss(c["output_range"][0])}–{mmss(c["output_range"][1])}</b> ({esc(c["label"])}, {c["bars"]}마디) 새 드럼 <b>{dv}</b> + 베이스 <b>{bv}</b> + 패드. 기존 추정 드럼 {man["decisions_used"]["original_drums_db"]} dB, 베이스 {man["decisions_used"]["original_bass_db"]} dB 감산, 경계 180 ms 전환.</li>' for c in cs)}
        {f'<li><b class="red">{mmss(man["breakdown"]["output_range"][0])}–{mmss(man["breakdown"]["output_range"][1])}</b> 브레이크다운 1마디 (드럼 −14 dB, 베이스 −8 dB) + 라이저.</li>' if man.get("breakdown") else ""}
        {f'<li>끝 무음 {man["tail_trimmed_s"]}s 제거.</li>' if man["tail_trimmed_s"] else "<li>끝 무음: 3초 미만이라 제거 없음.</li>"}
        <li>새 MIDI: 리듬 <b>{man["new_midi_counts"]["drum_events"]}</b>개 / 베이스 <b>{man["new_midi_counts"]["bass_notes"]}</b>개 / 패드 코드 <b>{man["new_midi_counts"]["pad_chords"]}</b>개 — <b class="red">자동 생성 데이터, 인간 실연 아님</b>. 결정 출처: {esc(man["decisions_used"]["_source"])}</li>
        <li>레벨 매칭: {esc(json.dumps(man.get("levels", {}), ensure_ascii=False))}</li>
        {f'<li>🩹 비트 추적 보정 <b>{len(man.get("beat_corrections", []))}</b>개 (최대 {max([abs(c["shift_ms"]) for c in man.get("beat_corrections", [])], default=0)} ms) — 드럼 브레이크에서 비트가 싱코페이션 히트로 끌려간 곳을 지역 중앙값 그리드로 되돌렸습니다. 원본 목록은 analysis.json의 beat_times_raw.</li>' if man.get("beat_corrections") else "<li>🩹 비트 추적 보정: 없음 (전 구간 그리드 일치)</li>"}
        <li class="small">노트 편집 index 출처: <code>04_edits/midi/new_notes.json</code> (03_proposals의 index는 8마디 미리듣기 전용).</li>
      </ul>
    </div>
    <div>
      <h4>📊 전후 측정 (원본 → 제출 후보 FLAC)</h4>
      <div class="tbl"><table class="metrics"><thead><tr><th>측정</th><th>원본</th><th>편곡</th></tr></thead><tbody>{metric_rows(q)}</tbody></table></div>
      <ul class="checks">{chk}</ul>
      <p class="small">마스터 설정: 20 Hz HPF · side gain {ms["side_gain"]} · 목표 {ms["target_lufs"]} LUFS · 4× 오버샘플 리미터 −1.0 dBTP · TPDF 디더 16-bit. <b>−14 LUFS는 이번 세션 설정이지 유통사 합격선이 아닙니다.</b></p>
    </div>
  </div>
  <h4>🗺️ 구조 타임라인 (출력 기준) — <span class="gold">■ 새 인트로</span> · <span class="lime">▭ 새 파트 구간</span> · <span class="red">■ 브레이크다운</span></h4>
  {svg_timeline(man, an)}
  <h4>📈 RMS 엔벌로프 전후 (0.25 s)</h4>
  {svg_envelope(env_a, env_b, man["original_offset_in_output_s"])}
  <h4>🎛️ A/B/C 제안 — <b class="red">여기서부터 사람이 고릅니다</b> (미리듣기 8마디, 원곡 {pr["preview_window_orig_s"][0]}–{pr["preview_window_orig_s"][1]}s 위에 얹음)</h4>
  <div class="tbl"><table class="props"><thead><tr><th></th><th>A</th><th>B</th><th>C</th></tr></thead><tbody>{props}</tbody></table></div>
  <p class="small">참고 MIDI (Basic Pitch 추출, 사람 작곡 아님): bass {midi["stems"].get("bass", {}).get("notes", "?")}음 · other {midi["stems"].get("other", {}).get("notes", "?")}음 · vocals {midi["stems"].get("vocals", {}).get("notes", "?")}음 → {link("02_midi/reference_from_stems/", "02_midi/")}. 단계별 소요: {esc(stage_secs)}.</p>
  <details><summary>🔎 분석 상세: 구간·코드 추정 (자동, 오인식 가능)</summary>
    <p class="small">구간: {esc("; ".join(f'{s["label"]} {mmss(s["start"])}–{mmss(s["end"])} ({s["bars"]}마디, {s["rms_db"]} dB)' for s in an["sections"]))}</p>
    <p class="small">마디별 코드: {esc(" ".join(b["chord"] for b in an["bar_chords"]))}</p>
  </details>
</section>'''


# ------------------------------------------------------------------ page

CSS = r"""
:root{--bg:#06110c;--bg2:#08150f;--panel:#0d2118;--panel2:#12291e;--line:#1e3d2c;--ink:#e9f2ec;--mute:#9cb6a7;
--red:#ff2d55;--lime:#c6ff3d;--gold:#cbb06a;--ok:#5ee58a;--bad:#ff6b6b;
--fd:"Noto Serif KR",Georgia,"Apple SD Gothic Neo",serif;--fb:"Noto Sans KR","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;--fm:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace}
html{color-scheme:dark}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--fb);font-size:15.5px;line-height:1.65;-webkit-font-smoothing:antialiased}
a{color:var(--lime);text-decoration:none;border-bottom:1px solid rgba(198,255,61,.35)}a:hover{border-bottom-color:var(--lime)}
.wrap{display:grid;grid-template-columns:250px minmax(0,1fr);gap:40px;max-width:1280px;margin:0 auto;padding:0 28px 80px}
nav.toc{position:sticky;top:0;align-self:start;height:100vh;overflow:auto;padding:28px 0;border-right:1px solid var(--line)}
nav.toc ol{list-style:none;margin:0;padding:0;counter-reset:s}
nav.toc li a{display:block;padding:7px 14px 7px 10px;color:var(--mute);border:0;font-size:13.5px;border-left:2px solid transparent}
nav.toc li a:hover{color:var(--ink);border-left-color:var(--lime)}
nav.toc .brand{font-family:var(--fd);font-weight:700;font-size:20px;color:var(--ink);padding:0 10px 18px;letter-spacing:-.01em}
main{max-width:920px;padding-top:28px}
.hero{padding:26px 0 18px;border-bottom:1px solid var(--line)}
.eyebrow{font-family:var(--fm);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--gold)}
h1{font-family:var(--fd);font-weight:700;font-size:clamp(30px,4.2vw,44px);line-height:1.15;margin:8px 0 12px;text-wrap:balance}
h2{font-family:var(--fd);font-weight:700;font-size:26px;margin:52px 0 12px;padding-top:18px;border-top:1px solid var(--line);text-wrap:balance}
h2 .step{font-family:var(--fm);font-size:13px;color:var(--gold);letter-spacing:.12em;display:block;margin-bottom:6px}
h3{font-family:var(--fd);font-size:21px;margin:0}h4{font-size:15px;margin:22px 0 8px;color:var(--ink)}
p,li{max-width:72ch}.lead{font-size:17px;color:var(--ink)}
b.red,.red{color:var(--red);text-shadow:0 0 12px rgba(255,45,85,.55)}b.lime,.lime{color:var(--lime);text-shadow:0 0 10px rgba(198,255,61,.45)}.gold{color:var(--gold)}
mark{background:transparent;color:var(--lime);font-weight:600;text-shadow:0 0 10px rgba(198,255,61,.45)}
mark.r{color:var(--red);text-shadow:0 0 12px rgba(255,45,85,.55)}
.callout{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--red);padding:14px 18px;border-radius:6px;margin:16px 0}
.callout.g{border-left-color:var(--lime)}.callout.y{border-left-color:var(--gold)}
.tbl{overflow-x:auto;margin:10px 0 6px}table{border-collapse:collapse;width:100%;min-width:640px;font-size:14px;font-variant-numeric:tabular-nums}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}thead th{color:var(--mute);font-weight:500;font-size:12.5px;letter-spacing:.06em;text-transform:uppercase;white-space:nowrap}
tbody th{color:var(--ink);font-weight:500;white-space:nowrap}td.after{color:var(--lime)}
.metrics td{font-family:var(--fm);font-size:13px}.props td{font-size:13.5px}
code,pre{font-family:var(--fm);font-size:13px}pre{background:var(--bg2);border:1px solid var(--line);border-radius:6px;padding:14px 16px;overflow-x:auto;line-height:1.5}
code{background:var(--panel2);padding:1px 6px;border-radius:4px}
.track{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:22px 24px;margin:22px 0}
.track-h{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 16px;margin-bottom:6px}.tnum{font-family:var(--fm);font-size:12px;letter-spacing:.14em;color:var(--gold)}
.chips{display:flex;flex-wrap:wrap;gap:6px;width:100%}.chip{font-size:12.5px;padding:3px 10px;border:1px solid var(--line);border-radius:999px;color:var(--mute);background:var(--bg2)}
.chip.ok{color:var(--ok);border-color:rgba(94,229,138,.4)}.chip.bad{color:var(--bad);border-color:rgba(255,107,107,.4)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:26px}@media(max-width:900px){.grid2{grid-template-columns:1fr}.wrap{grid-template-columns:1fr}nav.toc{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)}}
ul.files,ul.changes,ul.checks{padding-left:18px}ul.checks{list-style:none;padding:0;display:flex;flex-wrap:wrap;gap:4px 14px;font-family:var(--fm);font-size:12px}
ul.checks li.ok{color:var(--ok)}ul.checks li.bad{color:var(--bad)}
svg.tl,svg.env{width:100%;height:auto;display:block;margin:6px 0 14px}.tl-lbl{font:11px var(--fm);fill:var(--ink)}.tl-tag{font:11px var(--fm);fill:var(--mute)}.tl-tag.lime{fill:var(--lime)}.tl-tag.red{fill:var(--red)}.tl-tag.gold{fill:var(--gold)}.tl-tick{font:10px var(--fm);fill:var(--mute)}
.small{font-size:13px;color:var(--mute)}.warn{color:var(--red)}
details{border:1px dashed var(--line);border-radius:6px;padding:8px 14px;margin-top:12px}summary{cursor:pointer;color:var(--mute)}
.steps{counter-reset:st;list-style:none;padding:0}.steps>li{position:relative;padding:12px 0 12px 54px;border-bottom:1px solid var(--line)}
.steps>li::before{counter-increment:st;content:counter(st);position:absolute;left:0;top:12px;width:36px;height:36px;border-radius:50%;border:1.5px solid var(--lime);color:var(--lime);display:grid;place-items:center;font:600 15px var(--fm);text-shadow:0 0 10px rgba(198,255,61,.5)}
.steps>li.h::before{border-color:var(--red);color:var(--red);text-shadow:0 0 10px rgba(255,45,85,.6)}
.kv{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px;font-size:14px}.kv dt{color:var(--mute)}.kv dd{margin:0}
.badge{display:inline-block;font:600 11px var(--fm);letter-spacing:.08em;padding:2px 8px;border-radius:4px;border:1px solid}
.badge.auto{color:var(--lime);border-color:rgba(198,255,61,.5)}.badge.human{color:var(--red);border-color:rgba(255,45,85,.5)}.badge.both{color:var(--gold);border-color:rgba(203,176,106,.5)}
footer{margin-top:60px;padding-top:18px;border-top:1px solid var(--line);color:var(--mute);font-size:13px}
@media(prefers-reduced-motion:no-preference){.track{transition:border-color .2s}.track:hover{border-color:rgba(198,255,61,.35)}}
:focus-visible{outline:2px solid var(--lime);outline-offset:2px}
"""


def render_table(cols, rows, cls=""):
    head = "".join(f"<th>{c}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tbl"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def build():
    content = j(os.path.join(ROOT, "docs", "content.json"), {})
    tracks = sorted(glob.glob(os.path.join(ROOT, "tracks", "*")))
    panels = "".join(track_panel(td, i + 1) for i, td in enumerate(tracks))
    S = content.get("sections", {})
    def sec(key, num, title, body):
        return f'<h2 id="{key}"><span class="step">STEP {num}</span>{title}</h2>{body}'
    toc = "".join(f'<li><a href="#{k}">{t}</a></li>' for k, t in content.get("toc", []))
    track_toc = "".join(f'<li><a href="#{os.path.basename(td)}">🎵 {os.path.basename(td)}</a></li>' for td in tracks)
    body_parts = []
    for s in content.get("order", []):
        if s == "TRACKS":
            body_parts.append(f'<h2 id="tracks"><span class="step">STEP {content["track_step"]}</span>{content["track_title"]}</h2>{content.get("track_intro", "")}{panels}')
        else:
            spec = S[s]
            html_body = spec.get("html", "")
            for t in spec.get("tables", []):
                html_body = html_body.replace("{{" + t["id"] + "}}", render_table(t["cols"], t["rows"], t.get("cls", "")))
            body_parts.append(sec(s, spec["step"], spec["title"], html_body))
    page = f'''<title>{esc(content.get("title", "사람+AI 편곡 튜토리얼"))}</title>
<meta name="description" content="{esc(content.get("description", ""))}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@600;700&family=Noto+Sans+KR:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>{CSS}</style>
<div class="wrap">
<nav class="toc"><div class="brand">🌿 {esc(content.get("brand", "편곡 튜토리얼"))}</div><ol>{toc}{track_toc}</ol></nav>
<main>
<div class="hero"><div class="eyebrow">{esc(content.get("eyebrow", ""))}</div><h1>{content.get("h1", "")}</h1>{content.get("hero_html", "")}</div>
{"".join(body_parts)}
<footer>{content.get("footer_html", "")}</footer>
</main></div>
<script>
document.querySelectorAll('nav.toc a').forEach(a=>a.addEventListener('click',e=>{{const t=document.querySelector(a.getAttribute('href'));if(t){{e.preventDefault();t.scrollIntoView({{behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'}});history.replaceState(null,'',a.getAttribute('href'));}}}}));
</script>'''
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    out = os.path.join(ROOT, "docs", "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print("wrote", out, len(page), "bytes")


if __name__ == "__main__":
    build()
