# -*- coding: utf-8 -*-
"""Build the preview page for the three corrected versions."""
import os, sys, json, base64, html

HERE = os.path.dirname(os.path.abspath(__file__))
D = sys.argv[1]                               # folder holding v3/
OUTHTML = sys.argv[2]
V3 = os.path.join(D, "v3")
rep = json.load(open(f"{V3}/report.json", encoding="utf-8"))

def b64(p):
    with open(p, "rb") as f:
        return "data:audio/mpeg;base64," + base64.b64encode(f.read()).decode()

AUD = {}
missing = []
for k in ["A_깔린베이스", "B_짜짜베이스", "C_둘다"]:
    p = f"{V3}/{k}.mp3"
    (AUD.__setitem__(k, b64(p)) if os.path.exists(p) else missing.append(p))
for k in ["as_played_Bb", "retuned_A"]:
    p = f"{V3}/ab/{k}.mp3"
    (AUD.__setitem__(k, b64(p)) if os.path.exists(p) else missing.append(p))
old = f"{D}/an1/e_풍성한버전_마스터후.mp3"
if os.path.exists(old): AUD["OLD"] = b64(old)
else: missing.append(old)

def player(key, label=""):
    if key not in AUD:
        return f'<p class="warn">오디오 없음: {html.escape(key)}</p>'
    return (f'<div class="pl">{f"<span class=plab>{html.escape(label)}</span>" if label else ""}'
            f'<audio controls preload="metadata" src="{AUD[key]}"></audio></div>')

# ---------------------------------------------------------------- register map
W, ML, MR = 780, 86, 18
P0, P1 = 30, 84
def px(p): return ML + (p - P0) / (P1 - P0) * (W - ML - MR)

BEFORE = [("저음 (드럼1)", 36, 36, "one"), ("베이스", 45, 50, "clash"),
          ("피아노", 45, 65, "clash"), ("STRING ×2", 69, 81, "ok")]
AFTER = [("저음 루트", 33, 41, "ok"), ("베이스", 45, 50, "good"), ("짜짜 펄스", 45, 57, "ok"),
         ("피아노", 53, 65, "ok"), ("합창", 57, 67, "ok"), ("STRING ×2", 69, 81, "ok")]

def reg_svg(rows, title, note):
    rh, top = 26, 40
    H = top + len(rows) * rh + 44
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(title)} 음역 지도" '
         f'style="width:100%;height:auto;max-width:100%">']
    o.append(f'<text x="{ML}" y="20" class="svt svtt">{html.escape(title)}</text>')
    for p, lab in [(36, "C2"), (48, "C3"), (60, "C4"), (72, "C5"), (84, "C6")]:
        x = px(p)
        o.append(f'<line x1="{x:.1f}" y1="{top-10}" x2="{x:.1f}" y2="{top+len(rows)*rh-4}" class="svg-grid"/>')
        o.append(f'<text x="{x:.1f}" y="{H-24}" class="svt svax" text-anchor="middle">{lab}</text>')
    for i, (name, a, b, kind) in enumerate(rows):
        y = top + i * rh
        o.append(f'<text x="{ML-10}" y="{y+13}" class="svt svnm" text-anchor="end">{html.escape(name)}</text>')
        x0, x1 = px(a), px(max(b, a + 0.6))
        o.append(f'<rect x="{x0:.1f}" y="{y+2}" width="{max(x1-x0,5):.1f}" height="15" rx="3" class="bar b-{kind}"/>')
    if note:
        o.append(f'<text x="{ML}" y="{H-6}" class="svt svnote">{html.escape(note)}</text>')
    o.append("</svg>")
    return "\n".join(o)

EDIT_ROWS = "".join(
    f"<tr><td class=mono>{i+1}</td><td><strong>{html.escape(e['what'].split('.')[0])}</strong>"
    f"<div class=sub>{html.escape('.'.join(e['what'].split('.')[1:]).strip())}</div></td>"
    f"<td class=mono>{html.escape(e['exact'])}</td></tr>"
    for i, e in enumerate(rep["edits"]))

VER = rep["versions"]
def vcard(key, chip):
    v = VER[key]
    pulse = v["tracks"].get("짜짜짜 펄스 (당신 음고, 리듬만 새로)", 0)
    sub = v["tracks"].get("저음 루트 (당신 트랙 음고 교정)", 0)
    return f"""<article class="vc">
  <div class="vh"><span class="vchip" style="background:{chip}"></span>
    <h3>{html.escape(v['title'])}</h3></div>
  <p>{html.escape(v['blurb'])}</p>
  {player(key)}
  <dl class="vmeta">
    <div><dt>깔린 저음</dt><dd class=mono>{sub}개 {'(끝까지)' if sub>=8 else '(첫 바퀴만)'}</dd></div>
    <div><dt>짜짜짜 펄스</dt><dd class=mono>{pulse if pulse else '없음'}{'개' if pulse else ''}</dd></div>
    <div><dt>전체 노트</dt><dd class=mono>{v['total_notes']}</dd></div>
    <div><dt>마스터</dt><dd class=mono>{v['master']['after']['lufs']} LUFS / {v['master']['after']['true_peak']} dBTP</dd></div>
  </dl></article>"""

CHOIR_V = " → ".join(" ".join(v) for v in rep["added"]["choir"]["voicing"])

PAGE = f"""<title>세 가지 저음</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="당신 draft의 화음 충돌 6군데를 고치고, 드럼을 빼고, 저음을 세 가지로 만든 미리 듣기.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Song+Myung&family=Gothic+A1:wght@300;400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a vertical score. Each step is a full-width band with its own ground colour,
   separated by a five-line staff rule, so the steps read as movements. */
:root{{
  --ink:#F4F1E8; --dim:#B2AEA0; --faint:#7E7A6E;
  --disp:"Song Myung",Georgia,serif;
  --body:"Gothic A1","Malgun Gothic",-apple-system,system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
  --g0:#14161C;  /* header   */
  --g1:#2B1216;  /* 진단      */
  --g2:#101C26;  /* 음역 지도  */
  --g3:#12231A;  /* 고친 것    */
  --g4:#1D1430;  /* 세 버전    */
  --g5:#2A1E0C;  /* 한 음      */
  --g6:#0E1E1B;  /* 저작권     */
  --g7:#15171A;  /* 스튜디오원  */
  --bad:#FF6B5E; --good:#7BE3A0; --warn:#FFC44D; --cool:#79B6FF; --viol:#C39BFF;
  --rule:rgba(244,241,232,.14);
  color-scheme:dark;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--g0);color:var(--ink);font-family:var(--body);
  font-weight:300;font-size:16px;line-height:1.78;-webkit-text-size-adjust:100%}}
.band{{width:100%}}
.w{{width:100%;max-width:980px;margin:0 auto;
  padding-left:max(16px,env(safe-area-inset-left,0px));
  padding-right:max(16px,env(safe-area-inset-right,0px));
  padding-block:56px}}
h1,h2,h3{{font-family:var(--disp);font-weight:400;margin:0;line-height:1.26;text-wrap:balance}}
h1{{font-size:clamp(30px,5.4vw,52px);letter-spacing:-.01em}}
h2{{font-size:clamp(23px,3.3vw,33px)}}
h3{{font-size:19px}}
p{{margin:0 0 1.05em;max-width:66ch}}
.mono{{font-family:var(--mono);font-size:.84em;font-variant-numeric:tabular-nums}}
.eye{{font-family:var(--mono);font-size:11px;letter-spacing:.24em;text-transform:uppercase;
  color:var(--faint);margin-bottom:12px;display:flex;align-items:center;gap:10px}}
.eye b{{font-weight:500;color:var(--ink)}}
.chip{{width:11px;height:11px;border-radius:2px;flex:none}}
.lead{{color:var(--dim);font-size:17.5px;max-width:62ch}}
/* five-line staff rule between bands */
.staff{{height:17px;background:repeating-linear-gradient(to bottom,
  transparent 0 3px, var(--rule) 3px 4px);opacity:.75}}
table{{width:100%;border-collapse:collapse;font-size:14.5px}}
.scroll{{overflow-x:auto;margin:20px 0;-webkit-overflow-scrolling:touch}}
/* the register map carries 11px labels; let it scroll rather than shrink them away */
.scroll svg{{min-width:580px}}
th,td{{text-align:left;padding:11px 13px;border-bottom:1px solid var(--rule);vertical-align:top}}
th{{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--faint);font-weight:500;white-space:nowrap}}
td .sub{{color:var(--dim);font-size:13px;line-height:1.6;margin-top:3px}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:18px;margin:24px 0}}
.stat{{border:1px solid var(--rule);border-radius:3px;padding:16px 18px;min-width:0}}
.stat .k{{font-family:var(--mono);font-size:10.5px;letter-spacing:.15em;text-transform:uppercase;color:var(--faint)}}
.stat .v{{font-family:var(--mono);font-size:27px;font-variant-numeric:tabular-nums;margin:7px 0 2px}}
.stat .n{{color:var(--dim);font-size:13px;line-height:1.6}}
.vfrom{{color:var(--bad)}} .vto{{color:var(--good)}}
.pl{{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:14px 0}}
.plab{{font-family:var(--mono);font-size:11.5px;letter-spacing:.1em;color:var(--dim);
  min-width:84px;flex:none}}
audio{{flex:1;min-width:min(100%,230px);height:38px}}
.vc{{border:1px solid var(--rule);border-radius:3px;padding:20px;min-width:0;
  display:flex;flex-direction:column;gap:2px}}
.vh{{display:flex;align-items:center;gap:11px;margin-bottom:9px}}
.vchip{{width:13px;height:30px;border-radius:2px;flex:none}}
.vc p{{color:var(--dim);font-size:14.5px;line-height:1.72;margin:0 0 6px}}
.vmeta{{margin:10px 0 0;padding-top:12px;border-top:1px solid var(--rule);
  display:grid;grid-template-columns:1fr 1fr;gap:9px 16px}}
.vmeta div{{min-width:0}}
.vmeta dt{{font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--faint)}}
.vmeta dd{{margin:2px 0 0}}
.svt{{font-family:var(--mono)}}
.svtt{{font-size:12px;letter-spacing:.14em;fill:var(--dim);text-transform:uppercase}}
.svnm{{font-size:12.5px;fill:var(--ink)}}
.svax{{font-size:10.5px;fill:var(--faint)}}
.svnote{{font-size:11px;fill:var(--dim)}}
.svg-grid{{stroke:var(--rule);stroke-width:1;stroke-dasharray:2 4}}
.bar{{stroke-width:1}}
.b-ok{{fill:rgba(121,182,255,.42);stroke:var(--cool)}}
.b-good{{fill:rgba(123,227,160,.46);stroke:var(--good)}}
.b-clash{{fill:rgba(255,107,94,.40);stroke:var(--bad)}}
.b-one{{fill:rgba(255,196,77,.40);stroke:var(--warn)}}
.key{{display:flex;flex-wrap:wrap;gap:8px 20px;margin:14px 0 0;font-family:var(--mono);font-size:11px;color:var(--dim)}}
.key span{{display:flex;align-items:center;gap:7px}}
.key i{{width:13px;height:9px;border-radius:2px;display:block}}
.prog{{display:flex;flex-wrap:wrap;gap:9px;margin:20px 0;font-family:var(--mono)}}
.blk{{border:1px solid var(--rule);border-radius:3px;padding:11px 15px;min-width:120px;flex:1}}
.blk .bn{{font-size:10px;letter-spacing:.14em;color:var(--faint);text-transform:uppercase}}
.blk .bc{{font-size:20px;margin-top:4px}}
.blk .bf{{font-size:11px;color:var(--dim);margin-top:3px}}
.blk.fix{{border-color:var(--good);background:rgba(123,227,160,.07)}}
ol.steps{{counter-reset:s;list-style:none;padding:0;margin:22px 0 0;display:flex;
  flex-direction:column;gap:15px}}
ol.steps li{{counter-increment:s;padding-left:46px;position:relative;max-width:66ch}}
ol.steps li::before{{content:counter(s);position:absolute;left:0;top:1px;width:30px;height:30px;
  border:1px solid var(--rule);border-radius:50%;display:flex;align-items:center;
  justify-content:center;font-family:var(--mono);font-size:12.5px;color:var(--dim)}}
ol.steps b{{font-weight:500;color:var(--ink)}}
code{{font-family:var(--mono);font-size:.85em;background:rgba(244,241,232,.1);
  padding:2px 6px;border-radius:3px}}
.note{{border-left:2px solid var(--warn);padding:2px 0 2px 16px;color:var(--dim);
  font-size:14.5px;margin:20px 0;max-width:64ch}}
.warn{{color:var(--bad);font-family:var(--mono);font-size:13px}}
a{{color:inherit;border-bottom:1px solid var(--faint);text-decoration:none}}
:focus-visible{{outline:2px solid var(--warn);outline-offset:3px}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}}}
</style>

<div class="band" style="background:var(--g0)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--faint)"></span>D minor · 120 BPM · 32초</div>
  <h1>세 가지 저음</h1>
  <p class="lead">드럼을 전부 뺐습니다. 당신 draft에서 화음이 부딪히던 곳 여섯 군데를 고쳤고,
  묻혀 있던 당신 베이스를 꺼냈습니다. 저음을 서로 다르게 깐 세 가지 버전입니다.</p>
  <div class="grid2">
    <div class="stat"><div class="k">드럼</div><div class="v vto">없음</div>
      <div class="n">둥탕·둥툭탕 전부 제거. 킥·스네어·하이햇 0개</div></div>
    <div class="stat"><div class="k">당신 멜로디 대역</div>
      <div class="v"><span class="vfrom">8.8%</span> → <span class="vto">15.2%</span></div>
      <div class="n">500–1000 Hz 에너지 비중. 전 버전 대비 +73%</div></div>
    <div class="stat"><div class="k">당신 베이스 기여도</div>
      <div class="v"><span class="vfrom">+0.9</span> → <span class="vto">+5.1 dB</span></div>
      <div class="n">베이스 트랙을 빼면 95–190 Hz가 얼마나 줄어드는지</div></div>
    <div class="stat"><div class="k">반음 충돌</div>
      <div class="v"><span class="vfrom">227</span> → <span class="vto">40</span></div>
      <div class="n">트랙끼리 반음·단9도로 부딪히는 20 ms 구간 수</div></div>
  </div>
</div></div>
<div class="staff"></div>

<div class="band" style="background:var(--g1)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--bad)"></span><b>1</b> 무엇이 엉망이었나</div>
  <h2>지난 버전이 왜 그렇게 들렸는지, 숫자로</h2>
  <p>당신 말이 맞았습니다. 지난 버전에서 당신 멜로디가 차지한 에너지는 전체의
  <strong>8.8%</strong>였고, 제가 깔아놓은 서브베이스가 <strong>26.7%</strong>를 먹고 있었습니다.
  드럼까지 그 위에 얹혀 있었으니 당신이 친 게 들릴 수가 없었습니다.</p>
  <p>그런데 더 큰 문제가 draft 자체에 있었습니다.
  <strong>당신 베이스 트랙과 피아노의 맨 아래 음이 완전히 같은 음, 같은 옥타브, 같은 타이밍</strong>이었습니다.
  D3 대 D3, B♭2 대 B♭2, C3 대 C3, A2 대 A2. 네 블록 전부. 베이스 선이 피아노 안에 숨어버려서,
  베이스 트랙을 아예 지워도 소리가 <span class="mono">0.9 dB</span>밖에 안 줄었습니다. 있으나 없으나였던 겁니다.</p>
  {player('OLD', '지난 버전')}
  <p class="note">위 소리를 기준으로 삼으세요. 아래 세 버전과 번갈아 들으면
  뭐가 달라졌는지 바로 잡힙니다.</p>
</div></div>
<div class="staff"></div>

<div class="band" style="background:var(--g2)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--cool)"></span><b>2</b> 음역 지도</div>
  <h2>트랙마다 자기 자리를 주는 것</h2>
  <p>악기가 안 들리는 이유는 보통 작아서가 아니라, 같은 음역에 다른 악기가 앉아 있어서입니다.
  아래가 그 그림입니다. 빨간 칸이 서로 겹친 부분입니다.</p>
  <div class="scroll">{reg_svg(BEFORE, "before — 당신 draft", "베이스(45–50)가 피아노(45–65) 안에 완전히 들어가 있고, 저음은 C2 한 음을 네 화음 내내 붙잡고 있었습니다.")}</div>
  <div class="scroll">{reg_svg(AFTER, "after — 고친 뒤", "피아노의 중복된 맨 아래 음을 빼서 베이스에게 45–50을 넘겼습니다. 합창은 57–67로, 당신 STRING(69–81) 아래에 앉혔습니다.")}</div>
  <div class="key">
    <span><i class="bar b-clash" style="background:rgba(255,107,94,.4);border:1px solid var(--bad)"></i>겹쳐서 안 들림</span>
    <span><i style="background:rgba(255,196,77,.4);border:1px solid var(--warn)"></i>한 음에 고정</span>
    <span><i style="background:rgba(123,227,160,.46);border:1px solid var(--good)"></i>되살린 트랙</span>
    <span><i style="background:rgba(121,182,255,.42);border:1px solid var(--cool)"></i>자기 자리 확보</span>
  </div>
</div></div>
<div class="staff"></div>

<div class="band" style="background:var(--g3)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--good)"></span><b>3</b> 고친 것 여섯 군데</div>
  <h2>화음이 안 맞던 곳</h2>
  <p>가장 컸던 건 3번째 블록입니다. <strong>피아노는 C major를, STRING은 F major를 동시에</strong>
  치고 있었습니다. 피아노의 E와 STRING의 F가 반음으로 부딪히는데, 이게 4초 내내 계속됐습니다.
  곡 전체를 끌고 가는 쪽이 STRING이니 피아노를 F로 맞췄습니다. 두 음만 움직였습니다.</p>
  <div class="prog">
    <div class="blk"><div class="bn">블록 1</div><div class="bc">Dm</div><div class="bf">i · 그대로</div></div>
    <div class="blk"><div class="bn">블록 2</div><div class="bc">B♭</div><div class="bf">VI · 그대로</div></div>
    <div class="blk fix"><div class="bn">블록 3</div><div class="bc">F</div><div class="bf">III · 피아노 C→F 수정</div></div>
    <div class="blk"><div class="bn">블록 4</div><div class="bc">A7</div><div class="bf">V7 · 그대로</div></div>
  </div>
  <p>i – VI – III – V7. D 하모닉 마이너의 교과서적인 진행이고, 당신이 전에 분석해달라던
  아이언맨 쪽 진행(i – VI – III – VII)과 같은 계열입니다.</p>
  <div class="scroll"><table>
    <thead><tr><th></th><th>무엇을</th><th>정확히</th></tr></thead>
    <tbody>{EDIT_ROWS}</tbody>
  </table></div>
</div></div>
<div class="staff"></div>

<div class="band" style="background:var(--g4)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--viol)"></span><b>4</b> 세 가지 버전</div>
  <h2>저음을 어떻게 깔지</h2>
  <p>셋 다 같은 음, 같은 화음, 같은 길이입니다. <strong>다른 건 저음뿐</strong>입니다.
  당신이 말한 그 짜짜짜짜 — 잘게 부서지면서 고조되는 소리 — 는 16분음표 스타카토 펄스로 만들었고,
  둘째 바퀴에서 들어옵니다. 세지 않게, 블록마다 조금씩 커지도록 했습니다.</p>
  <div class="grid2">
    {vcard('A_깔린베이스', 'var(--cool)')}
    {vcard('B_짜짜베이스', 'var(--viol)')}
    {vcard('C_둘다', 'var(--warn)')}
  </div>
  <p class="note">B는 둘째 바퀴에서 깔린 저음을 아예 빼버립니다.
  20–120 Hz가 <span class="mono">−27.9 dB</span>에서 <span class="mono">−40.9 dB</span>로 떨어지고
  펄스가 그 자리를 받습니다. 바닥이 바뀌는 느낌이 가장 분명한 버전입니다.</p>
</div></div>
<div class="staff"></div>

<div class="band" style="background:var(--g5)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--warn)"></span><b>5</b> 한 음은 당신이</div>
  <h2>A♯인지 A인지</h2>
  <p>4번째 블록에서 당신 STRING이 <span class="mono">A♯4</span>를 한 번 칩니다. A7 화음 위의 B♭,
  즉 ♭9입니다. B♭은 D 하모닉 마이너의 6도이니 <strong>조성에서 벗어난 음이 아닙니다</strong>.
  틀린 음이 아니라 맛을 내는 음입니다. 다만 피아노의 A3와 단9도로 부딪히기 때문에,
  남아 있는 충돌 40개가 전부 이 한 음입니다.</p>
  <p>그래서 제가 임의로 고치지 않았습니다. 같은 8초를 두 가지로 만들어 뒀으니 들어보고 정해주세요.
  합창에서는 루트 A를 빼서 제가 이 긴장을 더 키우지는 않도록 했습니다.</p>
  {player('as_played_Bb', 'A♯ 그대로')}
  {player('retuned_A', 'A로 내림')}
  <p class="note">"A♯ 그대로" 쪽이 더 조이는 소리, "A로 내림" 쪽이 더 순한 소리입니다.
  어느 쪽인지만 말해주시면 세 버전 전부에 반영해서 다시 드립니다.</p>
</div></div>
<div class="staff"></div>

<div class="band" style="background:var(--g6)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--good)"></span><b>6</b> 누가 썼나</div>
  <h2>멜로디는 제가 안 썼습니다</h2>
  <p>AI 작곡이 되면 안 된다고 하셨으니, 무엇이 당신 것이고 무엇이 제가 한 것인지 분리해 둡니다.</p>
  <div class="scroll"><table>
    <thead><tr><th>구분</th><th>내용</th><th>노트</th></tr></thead>
    <tbody>
      <tr><td><strong>당신이 친 그대로</strong></td>
        <td>STRING 오스티나토 ×2 (곡을 끌고 가는 선), 베이스 4음<div class="sub">음고·리듬 손대지 않음. 둘째 바퀴 위치만 0.7초 밀어 블록을 4.0초로 맞췄습니다</div></td>
        <td class="mono">256 + 8</td></tr>
      <tr><td><strong>당신 음을 고친 것</strong></td>
        <td>피아노 화음<div class="sub">3번째 블록 두 음(G3→A3, E4→F4), 베이스와 유니즌이던 맨 아래 음 4개 제거</div></td>
        <td class="mono">24</td></tr>
      <tr><td><strong>당신 음고로 교정</strong></td>
        <td>저음 루트<div class="sub">C2 하나로 고정돼 있던 것을 당신이 이미 연주한 각 화음의 루트로. D2 B♭1 F2 A1</div></td>
        <td class="mono">8</td></tr>
      <tr><td><strong>리듬만 새로</strong></td>
        <td>짜짜짜 16분음표 펄스<div class="sub">음고는 전부 당신이 친 음 — D3 B♭2 F3 A2 / A3 F3 C3 E3. 새로 만든 건 리듬</div></td>
        <td class="mono">128</td></tr>
      <tr><td><strong>제가 만든 반주</strong></td>
        <td>합창 패드<div class="sub">당신 화음의 구성음만 길게. {html.escape(CHOIR_V)}</div></td>
        <td class="mono">24</td></tr>
      <tr><td><strong>아예 없음</strong></td>
        <td>드럼<div class="sub">전부 제거</div></td>
        <td class="mono">0</td></tr>
    </tbody>
  </table></div>
  <p>멜로디 라인은 비어 있습니다. 그건 당신이 써야 할 부분이고, 제가 채우면
  당신 곡이 아니게 됩니다. 지금 들리는 노래하는 선은 전부 당신이 친 STRING입니다.</p>
</div></div>
<div class="staff"></div>

<div class="band" style="background:var(--g7)"><div class="w">
  <div class="eye"><span class="chip" style="background:var(--dim)"></span><b>7</b> 당신이 할 것</div>
  <h2>Studio One에서</h2>
  <ol class="steps">
    <li><b>마음에 드는 버전을 고르세요.</b> A·B·C 중 하나. 아니면 "B인데 깔린 저음도 조금"처럼
      말해주시면 섞어 드립니다.</li>
    <li><b>A♯ / A 중 하나 고르세요.</b> 5번 항목의 두 클립을 번갈아 들어보고요.</li>
    <li><b>.mid 파일을 끌어다 놓으세요.</b> 고른 버전의 MIDI를 보내드립니다.
      Studio One 트랙 영역에 그대로 끌어다 놓으면 6~7개 트랙이 자기 이름을 달고 열립니다.</li>
    <li><b>묻혀 있던 EZkeys를 켜보세요.</b> 당신 <code>.song</code> 안에 EZkeys 2·3·4 트랙이
      음소거된 채로 노트 4,337개를 들고 있습니다. M 버튼만 끄면 바로 소리가 납니다.
      다만 지금 고친 화음과 맞는지 확인이 필요합니다.</li>
    <li><b>멜로디를 올리세요.</b> 지금 비어 있는 자리입니다. 치신 걸 .mid로 주시면
      화음에 맞는지 봐드리고, 어느 악기가 어울릴지 추천하겠습니다.</li>
    <li><b>9마디 이후를 채우세요.</b> 지금은 4블록을 두 번 돈 32초입니다.
      뒤를 더 쓰실 거면 화음 진행을 먼저 정하고 말씀해주세요.</li>
  </ol>
  <p class="note" style="margin-top:28px">전부 무료 오픈소스로 만들었습니다 —
  pretty_midi로 당신 .mid를 읽고, FluidSynth + FluidR3_GM 사운드폰트로 소리를 내고,
  pyloudnorm으로 EBU R128 음량을 재고, SciPy로 4배 오버샘플 트루피크 리미터를 돌렸습니다.
  세 버전 모두 −14 LUFS / −1.0 dBTP, 클리핑 0개입니다.</p>
</div></div>
"""

open(OUTHTML, "w", encoding="utf-8").write(PAGE)
print(f"wrote {OUTHTML}  {os.path.getsize(OUTHTML)/1e6:.2f} MB")
print(f"오디오 {len(AUD)}개 | 빈 {len(missing)}개", missing or "")
