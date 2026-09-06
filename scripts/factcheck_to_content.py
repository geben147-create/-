"""Turns docs/factcheck_raw.json (agent fact-check results) into the STEP 8 table rows in docs/content.json."""
import json, html, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw = json.load(open(os.path.join(ROOT, "docs", "factcheck_raw.json"), encoding="utf-8"))
C = json.load(open(os.path.join(ROOT, "docs", "content.json"), encoding="utf-8"))
BADGE = {"confirmed": '<span class="badge auto">확인</span>', "partially_correct": '<span class="badge both">부분 정정</span>',
         "refuted": '<span class="badge human">반박·정정</span>', "unverifiable": '<span class="badge" style="color:var(--mute);border-color:var(--line)">미확인</span>'}
GROUP_KO = {"routenote": "RouteNote", "korea": "한국 (KOMCA·정산·Sound Republica)", "symphonic": "Symphonic", "distrokid_others": "DistroKid·Amuse·TuneCore·CD Baby·LANDR",
            "suno_law": "Suno·저작권청·YouTube", "voice_tools": "보이스 도구", "daw_tools": "DAW·MCP·분리 도구"}
rows = []
for r in raw:
    src = r.get("evidence_url") or ""
    link = f'<a href="{html.escape(src)}" target="_blank" rel="noopener">원문</a>' if src.startswith("http") else "—"
    skept = r.get("skeptic")
    note = f'<br><small class="small">🕵️ 2차 검증: {html.escape(skept)}</small>' if skept else ""
    rows.append([f'<small class="small">{GROUP_KO.get(r.get("group",""), r.get("group",""))}</small><br>{html.escape(r["claim"][:160])}',
                 BADGE.get(r["status"], r["status"]),
                 f'<details><summary>{html.escape(r["correction"][:140])}…</summary>{html.escape(r["correction"])}{note}</details>' if len(r["correction"]) > 160 else html.escape(r["correction"]) + note,
                 link])
counts = {}
for r in raw:
    counts[r["status"]] = counts.get(r["status"], 0) + 1
C["sections"]["factcheck"]["tables"] = [{"id": "fc", "cols": ["주장 (앞선 문서)", "판정", "2026-09-06 기준 정확한 내용 (영문 원문 유지)", "출처"], "rows": rows}]
summary = f'<p class="small">검증 {len(raw)}건: ' + " · ".join(f'{BADGE.get(k,k)} {v}' for k, v in counts.items()) + '. 이 세션 망에서는 RouteNote·Symphonic·Sound Republica 페이지를 직접 열지 못해 검색엔진 스니펫으로 확인한 항목이 있습니다 — 표의 원문 링크를 제출일에 다시 여세요.</p>'
key = """<div class="callout"><b class="red">핵심 정정 6가지 (한국어 요약)</b>
<ol>
<li><mark class="r">RouteNote Premium은 “연 $9.99”가 아니라</mark> 싱글 <b>$10 선불 + 2년차부터 $9.99/년</b>(EP $20, 앨범 $30, 확장앨범 $45). 무료 85% / 프리미엄 100% 정산은 맞음. 심사는 “<b>25~27 working days</b>”로 수시로 바뀌니 날짜와 함께 인용.</li>
<li><mark class="r">DistroKid AI 공시는 신규 업로드에만 적용된다는 말은 틀림</mark> — 이미 발매된 곡도 앨범 페이지/credits에서 추가·수정 가능. 공시 항목은 <b>가사 · 보컬 · 연주 + “All of the audio”</b>(전체 AI면 아티스트가 사람인지 AI 페르소나인지 추가 질문). 피치보정·AI 믹싱/마스터링은 공시 불필요.</li>
<li><mark class="r">CD Baby는 “완전 AI만” 거부가 아니라</mark> <b>부분 AI도 거부</b>(원본 소리를 섞어도). <mark class="r">LANDR 한도는 12곡이 아니라</mark> <b>AI 생성곡 월 30곡</b>(2026-08 기준). Amuse의 “7일당 10릴리스”는 <b>AI 생성 녹음이 포함된 릴리스에만</b> 적용.</li>
<li>Symphonic Starter <b>$29.99/년</b>(2026-05-11 인상)·primary artist 1명·DSP 수익 100%(단, YouTube 등 UGC 수익은 수수료 있음). GenAI 제한 파트너에 <b>Audible Magic·Meta·Bandcamp·YouTube Content ID</b> 명시 확인. 다만 “8/21 개정”은 확인 못 함(검색 색인은 7/2 갱신).</li>
<li>TuneCore의 “clear, provable and dominant”는 <b>공식 문서가 아니라 인터뷰/3자 보도 표현</b>. 공식 문구는 “100% AI 생성물은 배포하지 않는다” + “완전 라이선스 데이터셋 GenAI만”.</li>
<li>한국 스트리밍 정산 <b>35 / 48.25 / 10.5 / 6.25</b>는 맞음(2019-01-01 시행). “68.42/31.58 개정안”은 <b>어떤 출처에서도 확인되지 않음</b> → 문서에서 삭제. KOMCA 8/3 도입 → 8/25 철회·유보는 확인.</li>
</ol></div>"""
BASE = C["sections"]["factcheck"]["html"].split(chr(60)+"div class=\"callout\"")[0].split("{{fc}}")[0]
C["sections"]["factcheck"]["html"] = BASE + key + summary + "{{fc}}"
json.dump(C, open(os.path.join(ROOT, "docs", "content.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("factcheck rows:", len(rows), counts)
