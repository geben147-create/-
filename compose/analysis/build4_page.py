# -*- coding: utf-8 -*-
"""Preview page for the three orchestral versions."""
import os, sys, json, base64, html

D, OUTHTML = sys.argv[1], sys.argv[2]
V = os.path.join(D, "v4")
rep = json.load(open(f"{V}/report.json", encoding="utf-8"))
KEYS = ["1_트레몰로", "2_피치카토", "3_트레몰로_팀파니"]

def b64(p): return "data:audio/mpeg;base64," + base64.b64encode(open(p, "rb").read()).decode()
AUD, missing = {}, []
for k in KEYS:
    p = f"{V}/{k}.mp3"
    AUD.__setitem__(k, b64(p)) if os.path.exists(p) else missing.append(p)
oldp = f"{D}/v3/C_둘다.mp3"
if os.path.exists(oldp): AUD["OLD"] = b64(oldp)

def player(key, label=""):
    if key not in AUD: return f'<p class="warn">오디오 없음</p>'
    return (f'<div class="pl">{f"<span class=plab>{html.escape(label)}</span>" if label else ""}'
            f'<audio controls preload="metadata" src="{AUD[key]}"></audio></div>')

# ------------------------------------------------------------------ stage plan svg
SW, SH = 780, 300
def stage_svg(stage):
    o = [f'<svg viewBox="0 0 {SW} {SH}" role="img" aria-label="무대 배치도" '
         f'style="width:100%;height:auto;max-width:100%">']
    o.append(f'<ellipse cx="{SW/2}" cy="{SH-18}" rx="{SW*0.47}" ry="{SH*0.82}" class="stg"/>')
    o.append(f'<text x="{SW/2}" y="{SH-4}" class="svt svax" text-anchor="middle">← 듣는 사람 →</text>')
    # depth from the hall send: more room = further back
    sends = [s["send_db"] for s in stage]
    lo, hi = min(sends), max(sends)
    for s in stage:
        x = SW/2 + s["pan"] * SW * 0.42
        depth = (s["send_db"] - lo) / max(hi - lo, .001)        # 0 = wettest = back
        y = 34 + depth * (SH - 92)
        r = 7 + max(0.0, (s["gain_db"] + 16)) * 0.55
        cls = {"당신": "yours", "당신(교정)": "fixed"}.get(s["who"], "mine")
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" class="pt p-{cls}"/>')
        anchor = "end" if s["pan"] < -0.15 else ("start" if s["pan"] > 0.15 else "middle")
        dx = -(r + 6) if anchor == "end" else ((r + 6) if anchor == "start" else 0)
        o.append(f'<text x="{x+dx:.1f}" y="{y+4:.1f}" class="svt svnm" text-anchor="{anchor}">'
                 f'{html.escape(s["name"].split(" — ")[0])}</text>')
    o.append("</svg>")
    return "\n".join(o)

EDITS = "".join(
    f"<tr><td class=mono>{i+1}</td><td><strong>{html.escape(e['what'].split('.')[0])}</strong>"
    f"<div class=sub>{html.escape('. '.join(e['what'].split('.')[1:]).strip())}</div></td>"
    f"<td class=mono>{html.escape(e['exact'])}</td></tr>"
    for i, e in enumerate(rep["edits"]))

def vcard(key, chip):
    v = rep["versions"][key]
    rows = "".join(
        f"<tr><td>{html.escape(n)}</td><td class=mono>{w['avg_db']:+.1f}</td>"
        f"<td class=mono>{w['peak_db']:+.1f}</td></tr>"
        for n, w in sorted(v["layer_worth_db"].items(), key=lambda kv: kv[1]["peak_db"], reverse=True))
    return f"""<article class="vc">
  <div class="vh"><span class="vchip" style="background:{chip}"></span><h3>{html.escape(v['title'])}</h3></div>
  <p>{html.escape(v['blurb'])}</p>
  {player(key)}
  <div class="scroll"><table class="tiny">
    <thead><tr><th>더한 레이어</th><th>평균</th><th>가장 크게</th></tr></thead>
    <tbody>{rows}</tbody></table></div>
  <div class="vmeta">
    <div><dt>당신 음</dt><dd class=mono>{v['notes_yours']}</dd></div>
    <div><dt>제가 더한 음</dt><dd class=mono>{v['notes_mine']}</dd></div>
    <div><dt>길이</dt><dd class=mono>{v['length_sec']}초</dd></div>
    <div><dt>마스터</dt><dd class=mono>{v['master']['after']['lufs']} LUFS</dd></div>
  </div></article>"""

S1 = rep["versions"][KEYS[2]]["stage"]

PAGE = f"""<title>오케스트라 세 편성</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="드럼과 신스 베이스를 걷어내고 오케스트라로 다시 짠 세 가지. 화음 충돌 0, 끝 블록 박자 교정.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Song+Myung&family=Gothic+A1:wght@300;400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a vertical score. Each step is a full-width band with its own ground colour,
   separated by a staff rule, so the steps read as movements of one piece. */
:root{{
  --ink:#F5F2E9; --dim:#B4AFA1; --faint:#7F7B6F;
  --disp:"Song Myung",Georgia,serif;
  --body:"Gothic A1","Malgun Gothic",-apple-system,system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
  --g0:#12141A; --g1:#2A1013; --g2:#0F1C25; --g3:#112218; --g4:#1B1330; --g5:#291D0B;
  --g6:#0D1D1A; --g7:#14161A;
  --bad:#FF6B5E; --good:#7BE3A0; --warn:#FFC44D; --cool:#79B6FF; --viol:#C39BFF;
  --rule:rgba(245,242,233,.14);
  color-scheme:dark;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--g0);color:var(--ink);font-family:var(--body);
  font-weight:300;font-size:16px;line-height:1.78;-webkit-text-size-adjust:100%}}
.band{{width:100%}}
.w{{width:100%;max-width:980px;margin:0 auto;
  padding-left:max(16px,env(safe-area-inset-left,0px));
  padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:56px}}
h1,h2,h3{{font-family:var(--disp);font-weight:400;margin:0;line-height:1.26;text-wrap:balance}}
h1{{font-size:clamp(30px,5.4vw,52px);letter-spacing:-.01em}}
h2{{font-size:clamp(23px,3.3vw,33px)}} h3{{font-size:19px}}
p{{margin:0 0 1.05em;max-width:66ch}}
.mono{{font-family:var(--mono);font-size:.84em;font-variant-numeric:tabular-nums}}
.eye{{font-family:var(--mono);font-size:11px;letter-spacing:.24em;text-transform:uppercase;
  color:var(--faint);margin-bottom:12px;display:flex;align-items:center;gap:10px}}
.eye b{{font-weight:500;color:var(--ink)}}
.chip{{width:11px;height:11px;border-radius:2px;flex:none}}
.lead{{color:var(--dim);font-size:17.5px;max-width:62ch}}
.staff{{height:17px;background:repeating-linear-gradient(to bottom,
  transparent 0 3px, var(--rule) 3px 4px);opacity:.75}}
table{{width:100%;border-collapse:collapse;font-size:14.5px}}
table.tiny{{font-size:12.5px}} table.tiny th,table.tiny td{{padding:6px 8px}}
.scroll{{overflow-x:auto;margin:18px 0;-webkit-overflow-scrolling:touch}}
.scroll svg{{min-width:560px}}
th,td{{text-align:left;padding:11px 13px;border-bottom:1px solid var(--rule);vertical-align:top}}
th{{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--faint);font-weight:500;white-space:nowrap}}
td .sub{{color:var(--dim);font-size:13px;line-height:1.6;margin-top:3px}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,270px),1fr));gap:18px;margin:24px 0}}
.stat{{border:1px solid var(--rule);border-radius:3px;padding:16px 18px;min-width:0}}
.stat .k{{font-family:var(--mono);font-size:10.5px;letter-spacing:.15em;text-transform:uppercase;color:var(--faint)}}
.stat .v{{font-family:var(--mono);font-size:26px;font-variant-numeric:tabular-nums;margin:7px 0 2px}}
.stat .n{{color:var(--dim);font-size:13px;line-height:1.6}}
.vfrom{{color:var(--bad)}} .vto{{color:var(--good)}}
.pl{{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:14px 0}}
.plab{{font-family:var(--mono);font-size:11.5px;letter-spacing:.1em;color:var(--dim);min-width:72px;flex:none}}
audio{{flex:1;min-width:min(100%,230px);height:38px}}
.vc{{border:1px solid var(--rule);border-radius:3px;padding:20px;min-width:0;display:flex;flex-direction:column}}
.vh{{display:flex;align-items:center;gap:11px;margin-bottom:9px}}
.vchip{{width:13px;height:30px;border-radius:2px;flex:none}}
.vc p{{color:var(--dim);font-size:14.5px;line-height:1.72;margin:0 0 4px}}
.vmeta{{margin-top:8px;padding-top:12px;border-top:1px solid var(--rule);
  display:grid;grid-template-columns:1fr 1fr;gap:9px 16px}}
.vmeta div{{min-width:0}}
.vmeta dt{{font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--faint)}}
.vmeta dd{{margin:2px 0 0}}
.svt{{font-family:var(--mono)}}
.svnm{{font-size:11.5px;fill:var(--ink)}} .svax{{font-size:10.5px;fill:var(--faint)}}
.stg{{fill:rgba(245,242,233,.04);stroke:var(--rule)}}
.pt{{stroke-width:1.5}}
.p-yours{{fill:rgba(123,227,160,.55);stroke:var(--good)}}
.p-fixed{{fill:rgba(255,196,77,.5);stroke:var(--warn)}}
.p-mine{{fill:rgba(121,182,255,.42);stroke:var(--cool)}}
.key{{display:flex;flex-wrap:wrap;gap:8px 20px;margin:12px 0 0;font-family:var(--mono);font-size:11px;color:var(--dim)}}
.key span{{display:flex;align-items:center;gap:7px}}
.key i{{width:12px;height:12px;border-radius:50%;display:block}}
.prog{{display:flex;flex-wrap:wrap;gap:9px;margin:20px 0;font-family:var(--mono)}}
.blk{{border:1px solid var(--rule);border-radius:3px;padding:11px 15px;min-width:118px;flex:1}}
.blk .bn{{font-size:10px;letter-spacing:.14em;color:var(--faint);text-transform:uppercase}}
.blk .bc{{font-size:20px;margin-top:4px}} .blk .bf{{font-size:11px;color:var(--dim);margin-top:3px}}
.blk.fix{{border-color:var(--good);background:rgba(123,227,160,.07)}}
.cell{{font-family:var(--mono);font-size:13px;display:flex;flex-wrap:wrap;gap:6px;margin:14px 0}}
.cell b{{border:1px solid var(--rule);border-radius:3px;padding:5px 9px;font-weight:400}}
.cell b.add{{border-color:var(--good);color:var(--good)}}
.cell b.col{{border-color:var(--warn);color:var(--warn)}}
ol.steps{{counter-reset:s;list-style:none;padding:0;margin:22px 0 0;display:flex;flex-direction:column;gap:15px}}
ol.steps li{{counter-increment:s;padding-left:46px;position:relative;max-width:66ch}}
ol.steps li::before{{content:counter(s);position:absolute;left:0;top:1px;width:30px;height:30px;
  border:1px solid var(--rule);border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-family:var(--mono);font-size:12.5px;color:var(--dim)}}
ol.steps b{{font-weight:500;color:var(--ink)}}
code{{font-family:var(--mono);font-size:.85em;background:rgba(245,242,233,.1);padding:2px 6px;border-radius:3px}}
.note{{border-left:2px solid var(--warn);padding:2px 0 2px 16px;color:var(--dim);font-size:14.5px;margin:20px 0;max-width:64ch}}
.warn{{color:var(--bad);font-family:var(--mono);font-size:13px}}
a{{color:inherit;border-bottom:1px solid var(--faint);text-decoration:none}}
:focus-visible{{outline:2px solid var(--warn);outline-offset:3px}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}}}
</style>

<div class="band" style="background:var(--g0)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--faint)"></span>D minor · 120 BPM · 39초 · 드럼 없음</div>
  <h1>오케스트라 세 편성</h1>
  <p class="lead">쿵짝거리던 신스 펄스를 걷어냈습니다. 움직임은 이제 오케스트라가 쓰는 방법으로 냅니다 —
  현악 트레몰로, 피치카토, 아주 약한 팀파니 롤, 그리고 위에서 얇게 울리는 글로켄슈필.
  연주는 각 악기를 따로 녹음해서 무대에 앉히고 홀 울림을 입혔습니다.</p>
  <div class="grid2">
    <div class="stat"><div class="k">화음 충돌</div><div class="v vto">0</div>
      <div class="n">처음 227개 → 40개 → 이제 0개. 반음·단9도로 부딪히는 구간이 없습니다</div></div>
    <div class="stat"><div class="k">당신 멜로디 대역</div>
      <div class="v"><span class="vfrom">8.8%</span> → <span class="vto">28.0%</span></div>
      <div class="n">500–1000 Hz 비중. 이제 전 대역 중 가장 큰 몫입니다</div></div>
    <div class="stat"><div class="k">당신 베이스 기여도</div>
      <div class="v"><span class="vfrom">+0.9</span> → <span class="vto">+16.1 dB</span></div>
      <div class="n">베이스를 빼면 95–190 Hz가 얼마나 줄어드는지</div></div>
    <div class="stat"><div class="k">다이내믹 (크레스트)</div><div class="v">15.2 dB</div>
      <div class="n">눌러 붙이지 않았습니다. 클리핑 0샘플</div></div>
  </div>
</div></div>
<div class="staff"></div>

<div class="band" style="background:var(--g1)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--bad)"></span><b>1</b> 끝 블록</div>
  <h2>박자가 어긋난 건 마지막 네 마디였습니다</h2>
  <p>맞습니다. 1·2·3번째 블록은 8분음표 격자(0.25초)에 <strong>정확히</strong> 맞는데,
  마지막 블록만 음 간격이 0.125초와 0.25초로 들쭉날쭉했습니다. 게다가 다른 블록이 16음인데
  거기만 <strong>15음</strong>이었습니다. 한 음이 비어 있었던 겁니다.</p>
  <p>당신이 친 음을 네 개씩 묶어보면 패턴이 보입니다. 마지막 묶음만 세 개입니다 —
  그래서 셋째 묶음과 짝이 맞도록 <strong>C♯5 하나</strong>를 채우고, 순서는 그대로 격자에 올렸습니다.
  당신 선율에 더한 음은 이 하나뿐입니다.</p>
  <div class="cell">
    <b>C♯5 E5 G5 E5</b><b>C♯5 E5 G5 C♯5</b><b>A4 C♯5 E5 C♯5</b>
    <b class="col">A♯4 C♯5 E5</b><b class="add">+ C♯5</b>
  </div>
  <p class="note">셋째 묶음이 <span class="mono">A4</span>로 시작하고 넷째가
  <span class="mono">A♯4</span>로 시작합니다. 반음 올라가는 짝이었던 거죠.
  그래서 A♯를 고치지 않았습니다 — 실수가 아니라 당신이 만든 짝입니다.</p>
</div></div>
<div class="staff"></div>

<div class="band" style="background:var(--g2)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--cool)"></span><b>2</b> 화성</div>
  <h2>A♯는 두고, 그 밑의 루트를 옮겼습니다</h2>
  <p>그 A♯4는 A7 화음 위의 ♭9입니다. B♭은 D 하모닉 마이너의 6도라 조성 안의 음입니다.
  문제는 음이 아니라 <strong>바로 밑에 루트 A3가 깔려 있던 것</strong>이었습니다. 단9도로 부딪히죠.</p>
  <p>그래서 당신 A♯는 그대로 두고 <strong>화음의 A3를 G3로 한 번만 내렸습니다.</strong>
  G는 당신 STRING이 이미 G5로 치고 있는 음입니다. 그러면 화음이 G–C♯–E가 되어 <strong>제대로 된 A7</strong>이
  되고, A♯ 밑에는 루트가 없어집니다. 한 음으로 둘 다 해결됩니다.</p>
  <div class="prog">
    <div class="blk"><div class="bn">블록 1</div><div class="bc">Dm</div><div class="bf">i</div></div>
    <div class="blk"><div class="bn">블록 2</div><div class="bc">B♭</div><div class="bf">VI</div></div>
    <div class="blk fix"><div class="bn">블록 3</div><div class="bc">F</div><div class="bf">III · 화음 C→F</div></div>
    <div class="blk fix"><div class="bn">블록 4</div><div class="bc">A7</div><div class="bf">V7 · A3→G3</div></div>
  </div>
  <p>그 밖에, 당신이 누른 긴 음들이 블록 끝까지 못 가고 끊기고 있었습니다.
  베이스는 첫 블록의 <strong>49%만</strong> 소리가 나고 2초가 비어 있었고, 화음은 매번
  0.44초 구멍을 두고 다시 쳤습니다. 길이만 늘려 메웠습니다 — 음높이도 시작점도 안 건드렸습니다.</p>
  <div class="scroll"><table>
    <thead><tr><th></th><th>무엇을</th><th>정확히</th></tr></thead>
    <tbody>{EDITS}</tbody></table></div>
</div></div>
<div class="staff"></div>

<div class="band" style="background:var(--g3)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--good)"></span><b>3</b> 무대</div>
  <h2>악기를 하나씩 따로 녹음해서 앉혔습니다</h2>
  <p>지난 버전들은 전부 한 덩어리로 뽑았습니다. 이번엔 악기마다 따로 뽑아서
  좌우에 앉히고, 뒤에 앉은 악기일수록 홀 울림을 더 보냈습니다. 풍부해지는 건
  압축이 아니라 이겁니다.</p>
  <div class="scroll">{stage_svg(S1)}</div>
  <div class="key">
    <span><i style="background:rgba(123,227,160,.55);border:1px solid var(--good)"></i>당신이 친 것</span>
    <span><i style="background:rgba(255,196,77,.5);border:1px solid var(--warn)"></i>당신 음을 교정</span>
    <span><i style="background:rgba(121,182,255,.42);border:1px solid var(--cool)"></i>제가 더한 반주</span>
    <span>원 크기 = 음량 · 위아래 = 홀 울림의 양</span>
  </div>
  <p class="note">홀은 합성했습니다. 초기 반사 6개를 먼저 놓고, 저역 2.6초·중역 2.1초·고역 1.0초로
  주파수마다 잔향 길이를 다르게 줬습니다. 실제 홀이 그렇게 울리기 때문에,
  이렇게 해야 금속성 링이 아니라 공간처럼 들립니다.</p>
</div></div>
<div class="staff"></div>

<div class="band" style="background:var(--g4)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--viol)"></span><b>4</b> 세 편성</div>
  <h2>움직임을 무엇으로 낼지</h2>
  <p>셋 다 같은 음, 같은 화음, 같은 무대입니다. 다른 건 둘째 바퀴에 들어오는
  <strong>움직임 레이어 하나</strong>뿐입니다. 표의 숫자는 그 레이어를 빼고 다시 믹스해서
  잰 겁니다 — 평균은 곡 전체 대비, "가장 크게"는 제일 잘 들리는 0.2초 구간입니다.</p>
  <div class="grid2">
    {vcard(KEYS[0], 'var(--cool)')}
    {vcard(KEYS[1], 'var(--viol)')}
    {vcard(KEYS[2], 'var(--warn)')}
  </div>
  <p class="note">글로켄슈필이 당신이 말한 그 "쨍"입니다. 셋 다 들어 있고,
  가장 크게 들리는 순간에도 곡보다 <span class="mono">20 dB</span> 아래입니다.
  드럼이 아니라 오케스트라 타악기라 때리는 느낌이 없습니다.</p>
  {player('OLD', '직전 신스')}
  <p class="note" style="border-color:var(--bad)">위가 당신이 "쿵짝거린다"고 한 버전입니다.
  비교용으로 넣어뒀습니다.</p>
</div></div>
<div class="staff"></div>

<div class="band" style="background:var(--g6)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--good)"></span><b>5</b> 누가 썼나</div>
  <h2>멜로디는 여전히 제가 안 썼습니다</h2>
  <div class="scroll"><table>
    <thead><tr><th>구분</th><th>내용</th><th>노트</th></tr></thead><tbody>
      <tr><td><strong>당신이 친 그대로</strong></td>
        <td>제1·제2바이올린 (당신 STRING 두 트랙), 콘트라베이스 (당신 베이스)
        <div class="sub">음높이 그대로. 마지막 블록만 격자에 올리고 C♯5 한 개를 채웠습니다</div></td>
        <td class="mono">264</td></tr>
      <tr><td><strong>당신 음을 고친 것</strong></td>
        <td>호른 (당신 화음), 콘트라베이스 저음 루트
        <div class="sub">3블록 두 음, 4블록 루트 한 음, 베이스와 겹치던 맨 아래 음 4개 제거, C2 고정 저음을 당신 화음의 루트로</div></td>
        <td class="mono">32</td></tr>
      <tr><td><strong>제가 만든 반주</strong></td>
        <td>합창 · 글로켄슈필 · 트레몰로/피치카토/팀파니
        <div class="sub">전부 당신이 친 화음의 구성음입니다. 새로 만든 건 리듬과 음색뿐</div></td>
        <td class="mono">80–336</td></tr>
      <tr><td><strong>아예 없음</strong></td>
        <td>드럼 킷, 신스 베이스<div class="sub">둘 다 제거</div></td>
        <td class="mono">0</td></tr>
    </tbody></table></div>
  <p>노래하는 선은 전부 당신이 친 STRING입니다. 제가 더한 것은 화음을 받쳐주는
  소리뿐이고, 그 음들도 당신이 누른 화음 안에서만 골랐습니다.</p>
</div></div>
<div class="staff"></div>

<div class="band" style="background:var(--g7)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--dim)"></span><b>6</b> 다음</div>
  <h2>정해주실 것</h2>
  <ol class="steps">
    <li><b>1·2·3안 중에 고르세요.</b> 섞어도 됩니다 — "2안인데 팀파니도" 같은 식으로요.</li>
    <li><b>악기를 바꾸고 싶으면 말씀하세요.</b> 지금 당신 화음은 호른이 받고 있습니다.
      피아노로 되돌리거나, 첼로·클라리넷·하프로 바꾸는 건 한 줄이면 됩니다.</li>
    <li><b>.mid 를 Studio One에 끌어다 놓으세요.</b> 고른 편성의 MIDI를 보내드립니다.
      트랙이 악기 이름을 달고 열립니다.</li>
    <li><b>멜로디를 올리세요.</b> 지금 노래하는 선은 당신 STRING 오스티나토뿐입니다.
      그 위에 올릴 주선율은 비어 있고, 그건 당신이 쓰셔야 당신 곡입니다.</li>
    <li><b>뒤를 더 쓰세요.</b> 지금은 네 화음을 두 번 돈 39초입니다.</li>
  </ol>
  <p class="note" style="margin-top:28px">전부 무료 오픈소스입니다 — pretty_midi로 당신 .mid를 읽고,
  FluidSynth + FluidR3_GM으로 악기마다 따로 연주하고, NumPy/SciPy로 홀 울림과
  무대 배치를 만들고, pyloudnorm으로 EBU R128을 쟀습니다.
  세 편성 모두 −14.00 LUFS / −1.0 dBTP, 클리핑 0샘플입니다.</p>
</div></div>
"""
open(OUTHTML, "w", encoding="utf-8").write(PAGE)
print(f"wrote {OUTHTML}  {os.path.getsize(OUTHTML)/1e6:.2f} MB")
print(f"오디오 {len(AUD)} | 빈 {len(missing)}", missing or "")
