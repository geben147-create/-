# -*- coding: utf-8 -*-
"""Part-by-part hand-entry guide, generated from the MIDI itself (no hand-copied notes).
python3 build_guide.py <FULL 140bpm .mid> <out.html>"""
import sys, html, collections, json
import numpy as np, pretty_midi

MID, OUT = sys.argv[1], sys.argv[2]
pm = pretty_midi.PrettyMIDI(MID)
TEMPO = float(pm.get_tempo_changes()[1][0]); BLK = 8.0
NM = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
def nn(p): return f"{NM[p % 12]}{p // 12 - 1}".replace("#", "♯")
def bt(t): return t * TEMPO / 60.0
CHN = ["Dm", "B♭", "F/C", "A7"]; CH = [0, 1, 2, 3] * 5 + [0, 0]; NB = 22
def esc(s): return html.escape(str(s))

# name in the MIDI -> (title, sound to look for in Studio One, what it does, kind)
META = {
 "Choir": ("합창 패드", "Choir / Voice Aahs 계열", "당신 화음의 음을 블록 내내 길게 늘인다. 새 음 없음.", "ai"),
 "Glockenspiel": ("글로켄슈필", "Glockenspiel / Celesta / Bell", "위에서 얇게 울리는 종소리. 블록마다 화음 음 2~3개.", "ai"),
 "Low strings bed": ("저음 현악 베드", "Strings Ensemble / Slow Strings", "중저역을 받쳐 주는 긴 음 두 개.", "ai"),
 "Cello ostinato": ("첼로 오스티나토", "Cello (짧게 끊는 아티큘레이션)", "블록 5부터. 처음엔 4분음표, 17블록부터 8분음표로 몰아친다.", "ai"),
 "Viola pulse": ("비올라 펄스 (딴 딴 딴 딴)", "Viola (짧게)", "블록 5부터. 화음의 낮은 음을 4분음표로.", "ai"),
 "Violin pulse": ("바이올린 펄스 (딴 딴 딴 딴)", "Violin (짧게)", "블록 5부터. 화음의 높은 음을 4분음표로.", "ai"),
 "French horns low": ("프렌치 호른 (저음)", "French Horn", "블록 6부터. 긴 음에 음량 스웰을 건다.", "ai"),
 "Trombones": ("트롬본", "Trombone", "블록 9부터. 화음의 낮은 두 음. 스웰.", "ai"),
 "Timpani": ("팀파니", "Timpani", "블록 7부터 한두 번씩 치고, 17블록부터 록 마디의 킥 자리를 맡는다. 마지막 화음에서 큰 한 방.", "ai"),
 "Taiko": ("타이코", "Taiko / Low Tom", "17블록부터 백비트 자리. 마지막 화음에서 한 방.", "ai"),
 "Reverse cymbal swell": ("리버스 심벌 스웰", "Reverse Cymbal (효과음)", "마지막 블록에서 점점 커진다.", "ai"),
 "Violins +8ve": ("바이올린 옥타브", "Violin", "17~22블록. 당신 바이올린 멜로디를 한 옥타브 위로 복사.", "derived"),
 "Sub sine mono (octave below yours)": ("서브 (사인파)", "Sine 계열 신스, 모노", "당신 베이스를 그대로 한 옥타브 아래로. 새 음 없음.", "derived"),
 "Contrabass root": ("저음 루트", "Contrabass", "각 화음의 근음. 당신이 친 베이스 아래.", "fix"),
 "Horns chords (yours)": ("호른 화음 (당신 피아노 화음)", "French Horn", "당신 피아노 화음. 아래 '당신 파트에 가한 수정'을 반영한 형태.", "fix"),
}
ORDER = ["Choir", "Glockenspiel", "Low strings bed", "Cello ostinato", "Viola pulse", "Violin pulse", "French horns low",
         "Trombones", "Timpani", "Taiko", "Reverse cymbal swell", "Violins +8ve", "Sub sine mono (octave below yours)",
         "Contrabass root", "Horns chords (yours)"]

def ranges(xs):
    xs = sorted(set(xs)); out = []; s = p = None
    for x in xs:
        if s is None: s = p = x
        elif x == p + 1: p = x
        else: out.append((s, p)); s = p = x
    if s is not None: out.append((s, p))
    return ", ".join(f"{a}" if a == b else f"{a}–{b}" for a, b in out)

def roll_svg(notes, w=480):
    """one block as a piano roll, drawn to scale: x = beat 1..9, y = pitch"""
    ps = [n[2] for n in notes]; lo, hi = min(ps) - 1, max(ps) + 1; rows = hi - lo + 1; rh = 13 if rows <= 16 else 8
    H = rows * rh + 24; L = 44; pw = w - L - 6
    o = [f'<svg viewBox="0 0 {w} {H}" role="img" aria-label="한 블록 음 위치" style="max-width:100%;height:auto;min-width:420px">']
    for b in range(9):
        x = L + pw * b / 8; o.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{rows*rh}" class="gl{" gm" if b % 4 == 0 else ""}"/>')
        if b < 8: o.append(f'<text x="{x+3:.1f}" y="{rows*rh+14}" class="gt">{b+1}</text>')
    seen = set()
    for p in range(lo, hi + 1):
        y = (hi - p) * rh
        if p in {n[2] for n in notes} and p not in seen:
            o.append(f'<text x="{L-4}" y="{y+rh-3}" class="pt" text-anchor="end">{nn(p)}</text>'); seen.add(p)
    for s, e, p, v in notes:
        x = L + pw * s / 8; ww = max(2.5, pw * (e - s) / 8 - 1); y = (hi - p) * rh
        o.append(f'<rect x="{x:.1f}" y="{y+1}" width="{ww:.1f}" height="{rh-2}" rx="2" class="nt"/>')
    o.append("</svg>"); return "".join(o)

def describe(ev):
    """ev: list of (start_in_block, pitches tuple, length)"""
    if len(ev) > 6:
        st = [e[0] for e in ev]; d = np.diff(st); ln = {e[2] for e in ev}
        if len(set(np.round(d, 3))) == 1 and len(ln) == 1:
            return (f"{len(ev)}번, 매 {d[0]:g}박마다, 길이 {list(ln)[0]:g}박. 음 순서:",
                    " · ".join(" ".join(nn(p) for p in e[1]) for e in ev))
    return None

cards = []; matrix = {}
fixes = []
for key in ORDER:
    inst = next((i for i in pm.instruments if i.name == key), None)
    if inst is None: continue
    title, sound, what, kind = META[key]
    byb = collections.defaultdict(list)
    for n in inst.notes:
        s = bt(n.start); b = int((s + 1e-3) // BLK)
        byb[b].append((s - b * BLK, bt(n.end) - b * BLK, n.pitch, n.velocity))
    if not byb: continue
    matrix[key] = sorted(byb)
    groups = collections.OrderedDict()
    for b in sorted(byb):
        ns = sorted(byb[b], key=lambda x: (x[0], x[2]))
        sig = tuple((round(s * 8) / 8, p, round((min(e, BLK + 6) - s) * 20) / 20) for s, e, p, v in ns)
        groups.setdefault(sig, []).append(b)
    vel = " · ".join(f"블록{b+1}:{int(round(np.mean([x[3] for x in byb[b]])))}" for b in sorted(byb))
    cc = ""
    if inst.control_changes:
        per = collections.defaultdict(list)
        for c in inst.control_changes:
            if c.number == 11: per[int((bt(c.time) + 1e-3) // BLK)].append(c.value)
        if per: cc = " · ".join(f"블록{b+1}:{v[0]}→{v[-1]}" for b, v in sorted(per.items()) if len(v) > 1)
    gh = []
    for gi, (sig, blocks) in enumerate(groups.items(), 1):
        evmap = collections.OrderedDict()
        for s, p, l in sig: evmap.setdefault((s, l), []).append(p)
        ev = [(s, tuple(sorted(ps)), l) for (s, l), ps in evmap.items()]
        chord = " / ".join(sorted({CHN[CH[min(b, NB - 1)]] for b in blocks}))
        bl = ranges([b + 1 for b in blocks])
        first = [x for x in byb[blocks[0]]]
        dsc = describe(ev)
        if dsc: body = f'<p class="pat"><b>{esc(dsc[0])}</b><br><span class="mono">{esc(dsc[1])}</span></p>'
        else:
            rows = "".join(f'<tr><td class="mono">{s+1:g}박</td><td class="mono">{" ".join(nn(p) for p in ps)}</td><td class="mono">{l:g}박</td></tr>' for s, ps, l in ev[:24])
            body = f'<div class="scroll"><table><thead><tr><th>위치</th><th>음</th><th>길이</th></tr></thead><tbody>{rows}</tbody></table></div>'
        gh.append(f'<div class="grp"><div class="gh"><span class="chip">{esc(chord)}</span> <b>블록 {esc(bl)}</b><span class="dim"> · 한 번 입력하고 같은 화음 블록에 복사</span></div>{body}<div class="scroll">{roll_svg(first)}</div></div>')
    allp = [n.pitch for n in inst.notes]
    cards.append(dict(key=key, title=title, sound=sound, what=what, kind=kind, blocks=ranges([b + 1 for b in byb]),
                      lo=nn(min(allp)), hi=nn(max(allp)), vel=vel, cc=cc, groups="".join(gh), n=len(inst.notes)))

KIND = {"ai": ("제가 정한 음 · 직접 입력", "k-ai"), "derived": ("당신 음에서 그대로 파생", "k-der"), "fix": ("당신 파트의 교정형", "k-fix")}
FIXES = [
 ("블록 3, 당신 피아노 화음", "G3 → A3, E4 → F4", "당신 오스티나토가 F 화음(F·A·C)인데 피아노가 C 화음이라 E와 F가 반음으로 4초 내내 부딪힘. 피아노를 F/C로.", "피아노 롤에서 그 두 음을 드래그"),
 ("블록 4, 당신 피아노 화음", "A3 → G3", "당신 STRING의 A♯4(♭9) 바로 밑 루트 A3가 단9도로 부딪힘. A♯4는 그대로 두고 화음 쪽을 G로.", "한 음 이동"),
 ("모든 블록, 당신 피아노 맨 아래 음", "D3, B♭2, C3, A2 삭제", "당신 베이스와 같은 음·같은 옥타브·같은 타이밍이라 베이스가 안 들림.", "삭제 4개"),
 ("제일 낮은 지속음(드럼1 트랙)", "C2 → D2, B♭1, C2, A1 (각 화음 근음)", "C2 하나가 네 화음 내내 이어져 A7의 C♯과 반음 충돌. ※ 이 트랙이 드럼 킥인지 지속음인지 본인만 압니다.", "음높이만 바꿈"),
 ("블록 4(마지막 4블록) STRING", "15음 → 16음, 8분음표 격자에 정렬", "마지막 블록만 박자가 어긋나고 15음이었음. 당신 4음 묶음 [A♯4 C♯5 E5]에 C♯5 한 음을 채워 [C♯5 E5 G5 …] 패턴을 완성.", "당신 STRING을 격자에 정렬(퀀타이즈 1/8)하고 C♯5 한 음 추가"),
 ("당신 STRING 멜로디 두 번째 테이크", "한 옥타브 아래로 복사 (비올라/첼로)", "A♯4만 옥타브를 내리지 않음(A2 베이스와 단9도).", "복사 후 −12 반음. A♯ 음은 그대로"),
 ("당신 STRING 길이", "스타카토 0.30박", "음 길이만 자름. 음높이·시작 위치는 그대로.", "노트 길이를 0.30박(약 0.13초)으로"),
]

def card(c):
    kl, kc = KIND[c["kind"]]
    cc = f'<p class="dim">음량 스웰(CC11): <span class="mono">{esc(c["cc"])}</span></p>' if c["cc"] else ""
    return (f'<article class="card" id="L-{esc(c["key"].split()[0].lower())}-{abs(hash(c["key"]))%1000}" data-key="{esc(c["key"])}">'
            f'<button class="hd" aria-expanded="false"><span class="dot"></span><span class="tt">{esc(c["title"])}</span>'
            f'<span class="tag {kc}">{esc(kl)}</span><span class="meta mono">블록 {esc(c["blocks"])} · {esc(c["lo"])}–{esc(c["hi"])} · {c["n"]}음</span><span class="chev">＋</span></button>'
            f'<div class="bd" hidden><p>{esc(c["what"])}</p><p><b>악기:</b> {esc(c["sound"])}</p>{c["groups"]}'
            f'<p class="dim">블록별 평균 벨로시티(세기): <span class="mono">{esc(c["vel"])}</span></p>{cc}'
            f'<label class="done"><input type="checkbox" class="chk"> 이 파트 입력 완료</label></div></article>')

# block map: rows = layers, columns = blocks 1..22
mx = ['<div class="scroll"><table class="map"><thead><tr><th></th>' + "".join(f'<th>{b}</th>' for b in range(1, NB + 1)) + '</tr></thead><tbody>']
mx.append('<tr class="chrow"><th>화음</th>' + "".join(f'<td class="chd">{esc(CHN[CH[b]])}</td>' for b in range(NB)) + '</tr>')
for c in cards:
    act = set(matrix[c["key"]])
    mx.append(f'<tr><th><button class="jump" data-key="{esc(c["key"])}">{esc(c["title"])}</button></th>' +
              "".join(f'<td class="{"on" if b in act else ""}"></td>' for b in range(NB)) + '</tr>')
mx.append("</tbody></table></div>")

PAGE = f"""<title>파트별 입력 안내서</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gothic+A1:wght@300;400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a checklist ledger on black. Red marks what is still to be entered; a ticked part turns green. */
:root{{--bg:#000;--ink:#F3F1EA;--dim:#A6A49B;--faint:#6B6A64;--rule:rgba(243,241,234,.16);--red:#FF4D4D;--redd:rgba(255,77,77,.14);--green:#6FE3A0;--amber:#FFC44D;--blue:#7DB4FF;
--body:"Gothic A1","Malgun Gothic",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;color-scheme:dark}}
*{{box-sizing:border-box}}html{{background:#000}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);font-weight:300;font-size:16px;line-height:1.75;-webkit-text-size-adjust:100%}}
.w{{width:100%;max-width:980px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:40px}}
h1,h2{{margin:0;font-weight:600;line-height:1.3;text-wrap:balance}} h1{{font-size:clamp(26px,4.6vw,42px)}} h2{{font-size:clamp(20px,3vw,26px);margin-bottom:10px}}
p{{margin:0 0 .9em;max-width:68ch}} .lead{{color:var(--dim);font-size:17px}} .dim{{color:var(--dim);font-size:14px}}
.mono{{font-family:var(--mono);font-size:.85em;font-variant-numeric:tabular-nums}}
section{{border-top:1px solid var(--rule)}}
.prog{{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:#000;border-bottom:1px solid var(--rule);padding:10px max(16px,env(safe-area-inset-left,0px))}}
.prog .in{{max-width:980px;margin:0 auto;display:flex;flex-wrap:wrap;align-items:center;gap:12px}}
.bar{{flex:1;min-width:140px;height:8px;background:var(--rule);border-radius:4px;overflow:hidden}} .bar i{{display:block;height:100%;width:0;background:var(--green);transition:width .25s}}
button{{font:inherit;color:inherit;cursor:pointer}} .rst{{border:1px solid var(--rule);background:none;padding:4px 10px;font-size:12px;color:var(--dim)}}
.card{{border:1px solid var(--rule);margin:10px 0;border-left:4px solid var(--red);background:#050505}}
.card.ok{{border-left-color:var(--green)}} .card.ok .dot{{background:var(--green)}} .card.ok .tt{{color:var(--green)}}
.hd{{width:100%;display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:14px 16px;background:none;border:0;text-align:left}}
.hd:hover{{background:var(--redd)}} .card.ok .hd:hover{{background:rgba(111,227,160,.08)}}
.dot{{width:10px;height:10px;border-radius:50%;background:var(--red);flex:none}} .tt{{font-weight:600;color:var(--red);font-size:17px}}
.meta{{color:var(--dim);flex:1;min-width:0}} .chev{{font-family:var(--mono);color:var(--dim)}}
.tag{{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;padding:2px 8px;border:1px solid currentColor}}
.k-ai{{color:var(--amber)}} .k-der{{color:var(--blue)}} .k-fix{{color:var(--dim)}}
.bd{{padding:4px 18px 16px}} .grp{{border-top:1px dashed var(--rule);padding:12px 0}}
.gh{{margin-bottom:6px}} .chip{{display:inline-block;font-family:var(--mono);font-size:12px;border:1px solid var(--red);color:var(--red);padding:1px 8px;margin-right:6px}}
.pat{{background:#0a0a0a;border:1px solid var(--rule);padding:8px 12px;margin:6px 0}}
.scroll{{overflow-x:auto;margin:8px 0}} table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{text-align:left;padding:6px 10px;border-bottom:1px solid var(--rule);vertical-align:top}}
th{{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;color:var(--faint);font-weight:400;white-space:nowrap}}
.map{{font-size:11px}} .map td{{padding:0;height:20px;min-width:22px;border:1px solid #111}} .map td.on{{background:var(--red);opacity:.85}} .map .chd{{text-align:center;color:var(--dim);font-family:var(--mono);font-size:10px;height:auto;padding:2px}}
.map th button{{background:none;border:0;text-align:left;color:var(--ink);font-size:12px;padding:2px 6px;border-bottom:1px solid var(--faint)}}
.map th button:hover{{color:var(--red)}} .map th{{text-align:center;padding:2px 4px}}
.nt{{fill:var(--red);opacity:.9}} .gl{{stroke:#1a1a1a;stroke-width:1}} .gm{{stroke:#3a3a3a}} .gt{{font-family:var(--mono);font-size:9px;fill:var(--faint)}} .pt{{font-family:var(--mono);font-size:9px;fill:var(--dim)}}
.done{{display:block;margin-top:10px;padding:10px 12px;border:1px solid var(--rule);cursor:pointer}} .done input{{accent-color:var(--green);width:18px;height:18px;vertical-align:-3px;margin-right:8px}}
.note{{border-left:2px solid var(--amber);padding:2px 0 2px 14px;color:var(--dim);font-size:14.5px;margin:14px 0;max-width:68ch}}
:focus-visible{{outline:2px solid var(--amber);outline-offset:2px}}
@media (prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style>

<div class="prog"><div class="in"><b id="pc" class="mono">0 / 0</b><div class="bar"><i id="pb"></i></div><button class="rst" id="rs">체크 모두 지우기</button></div></div>

<header class="w" style="padding-bottom:20px"><div class="dim mono" style="letter-spacing:.2em;font-size:11px">140 BPM · 4/4 · D minor · 22블록</div>
<h1>파트별 입력 안내서</h1>
<p class="lead">이 곡의 반주를 당신이 Studio One에 <b>직접 입력</b>하기 위한 표입니다. 빨간 파트 이름을 누르면 펼쳐지고, 입력을 마치면 체크하세요(초록으로 바뀝니다). 아래 음은 전부 방금 보낸 MIDI에서 코드로 뽑았습니다.</p></header>

<section><div class="w"><h2>보는 법</h2>
<p><b>1블록 = 8박 = 2마디</b>입니다. 블록 n은 <b>{ "2(n−1)+1" }번째 마디</b>에서 시작합니다(블록 1 → 1마디, 블록 5 → 9마디, 블록 17 → 33마디). 위치는 블록 안에서 1~8박으로 적었습니다.</p>
<p>같은 화음의 블록은 패턴이 같아서 <b>한 블록만 입력하고 복사</b>하면 됩니다. 한 화음 패턴이 여러 블록에 쓰이는 곳은 "블록 5–8"처럼 묶어 두었습니다. 화음은 4개가 돕니다. <span class="mono">Dm → B♭ → F/C → A7</span>.</p>
<div class="note">음의 세기(벨로시티)는 파트가 진행될수록 커지게 맞춰 둔 값입니다. 손으로 치실 때는 숫자를 그대로 따르기보다 "점점 세게"라는 방향만 따라가시면 됩니다.</div></div></section>

<section><div class="w"><h2>블록 지도</h2><p class="dim">빨간 칸이 그 파트가 소리 나는 블록입니다. 왼쪽 파트 이름을 누르면 해당 파트로 이동합니다.</p>{"".join(mx)}</div></section>

<section><div class="w"><h2>파트 (빨간 이름을 누르세요)</h2>
{"".join(card(c) for c in cards)}</div></section>

<section><div class="w"><h2>당신 파트에 가한 수정 (되돌리거나 직접 하는 방법)</h2>
<p class="dim">당신이 친 음 중 일곱 군데를 건드렸습니다. 그대로 두고 싶으면 이 항목을 하지 않으면 됩니다.</p>
<div class="scroll"><table><thead><tr><th>어디</th><th>무엇을</th><th>이유</th><th>방법</th></tr></thead><tbody>
{"".join(f'<tr><td>{esc(a)}</td><td class="mono">{esc(b)}</td><td>{esc(c)}</td><td>{esc(d)}</td></tr>' for a,b,c,d in FIXES)}
</tbody></table></div></div></section>

<section><div class="w"><h2>선언할 때 알아둘 것</h2>
<p>이 표의 <b>음은 제가 정했고, 입력은 당신이 합니다.</b> 그러면 음표를 쓰는 행위는 당신 것이지만 "어떤 음을 칠지"는 AI 제안에서 왔습니다. 이걸 AI 사용으로 보는지는 올리는 유통사의 문구가 정합니다. 애매하면 "반주 구성에 AI 제안을 참고했다"고 적는 쪽이 안전합니다.</p>
<p>당신이 표를 보지 않고 스스로 바꾼 음은 그대로 당신 음입니다. 표를 참고하되 마음에 안 드는 곳은 바꾸세요.</p></div></section>

<script>
(function(){{
  var KEY='guide-done-v1', done={{}};
  try{{ done=JSON.parse(localStorage.getItem(KEY)||'{{}}'); }}catch(e){{ done={{}}; }}
  var cards=[].slice.call(document.querySelectorAll('.card'));
  function save(){{ try{{ localStorage.setItem(KEY,JSON.stringify(done)); }}catch(e){{}} }}
  function paint(){{
    var n=0; cards.forEach(function(c){{ var k=c.dataset.key, on=!!done[k]; c.classList.toggle('ok',on); c.querySelector('.chk').checked=on; if(on) n++; }});
    document.getElementById('pc').textContent=n+' / '+cards.length; document.getElementById('pb').style.width=(cards.length?100*n/cards.length:0)+'%';
  }}
  function toggle(c,open){{ var b=c.querySelector('.bd'), h=c.querySelector('.hd'); b.hidden=!open; h.setAttribute('aria-expanded',open); c.querySelector('.chev').textContent=open?'－':'＋'; }}
  cards.forEach(function(c){{
    c.querySelector('.hd').addEventListener('click',function(){{ toggle(c,c.querySelector('.bd').hidden); }});
    c.querySelector('.chk').addEventListener('change',function(e){{ done[c.dataset.key]=e.target.checked; save(); paint(); }});
  }});
  [].forEach.call(document.querySelectorAll('.jump'),function(b){{ b.addEventListener('click',function(){{
    var c=cards.filter(function(x){{return x.dataset.key===b.dataset.key;}})[0]; if(!c) return; toggle(c,true); c.scrollIntoView({{behavior:'smooth',block:'start'}}); }}); }});
  document.getElementById('rs').addEventListener('click',function(){{ done={{}}; save(); paint(); }});
  paint();
}})();
</script>
"""
open(OUT, "w", encoding="utf-8").write(PAGE)
print(f"wrote {OUT}  {len(PAGE)/1e3:.0f} KB, {len(cards)} parts:", [c['key'] for c in cards])
