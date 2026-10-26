# -*- coding: utf-8 -*-
import base64, os, html, json
D="/tmp/claude-0/-home-user--/4b2bd38e-8d7f-52a5-bb39-0e1615b1f404/scratchpad/an1"
OUT="/home/user/-/docs/풍성하게.html"; BR="claude/manual-composition"
rep=json.load(open(f"{D}/master_report.json",encoding="utf-8"))
def au(f,label,note=""):
    p=os.path.join(D,f)
    if not os.path.exists(p): return f'<div class="pl miss">— {html.escape(label)}</div>'
    b=base64.b64encode(open(p,"rb").read()).decode()
    n=f'<span class="pn">{html.escape(note)}</span>' if note else ""
    return (f'<div class="pl"><div class="pt">{html.escape(label)}{n}</div>'
            f'<audio controls preload="none" src="data:audio/mpeg;base64,{b}"></audio></div>')
CSS=r"""
:root{--ink:#F2F5F6;--dim:#A5B0B6;--faint:#6E7A80;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
--sans:"IBM Plex Sans KR",-apple-system,"Malgun Gothic",system-ui,sans-serif;--serif:"Gowun Batang",Georgia,serif;
--b0:#0B0E10;--b1:#15241A;--b2:#2A1A0C;--b3:#101D33;--b4:#261120;--b5:#13181C;
--c1:#6BE08A;--c2:#FFB347;--c3:#7FA8FF;--c4:#FF7FB0;--c5:#C9D3D8}
*{box-sizing:border-box}html{color-scheme:dark}
body{margin:0;background:var(--b0);color:var(--ink);font-family:var(--sans);font-weight:300;font-size:16px;line-height:1.75}
.w{width:min(1000px,92vw);margin:0 auto}
h1,h2,h3{font-family:var(--serif);font-weight:700;margin:0;line-height:1.24;text-wrap:balance}
p{margin:0 0 1em;max-width:70ch}
code{font-family:var(--mono);font-size:.86em;background:rgba(255,255,255,.09);padding:2px 7px;border-radius:4px}
pre{font-family:var(--mono);font-size:12.5px;line-height:1.7;background:rgba(0,0,0,.45);border:1px solid rgba(255,255,255,.13);
    border-radius:7px;padding:14px 16px;overflow-x:auto;margin:14px 0}
a{color:inherit;border-bottom:1px solid currentColor;text-decoration:none}
header{padding:54px 0 40px;background:linear-gradient(165deg,#16301F,#0B0E10 72%);border-bottom:1px solid rgba(255,255,255,.1)}
.eye{font-family:var(--mono);font-size:11.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--c1);margin-bottom:14px}
h1{font-size:clamp(27px,4.6vw,43px)}h1 em{font-style:normal;color:var(--c1)}
.lead{color:var(--dim);margin-top:16px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}
.chip{font-family:var(--mono);font-size:12px;padding:5px 12px;border-radius:99px;border:1px solid rgba(255,255,255,.2);
      background:rgba(255,255,255,.05);color:var(--dim)}
.s{padding:50px 0;border-bottom:1px solid rgba(255,255,255,.09)}
.s1{background:var(--b1)}.s2{background:var(--b2)}.s3{background:var(--b3)}.s4{background:var(--b4)}.s5{background:var(--b5)}
.hd{display:flex;gap:17px;align-items:flex-start;margin-bottom:8px}
.num{flex:none;width:52px;height:52px;border-radius:13px;display:grid;place-items:center;font-family:var(--mono);
     font-size:19px;font-weight:600;border:2px solid currentColor}
.s1 .num,.s1 .hi{color:var(--c1)}.s2 .num,.s2 .hi{color:var(--c2)}.s3 .num,.s3 .hi{color:var(--c3)}
.s4 .num,.s4 .hi{color:var(--c4)}.s5 .num,.s5 .hi{color:var(--c5)}
.hd h2{font-size:clamp(19px,3vw,27px)}
.sub{color:var(--dim);margin:2px 0 22px;max-width:72ch}
.pl{display:flex;align-items:center;gap:14px;flex-wrap:wrap;padding:11px 14px;margin:8px 0;background:rgba(0,0,0,.34);
    border:1px solid rgba(255,255,255,.13);border-radius:7px}
.pl.miss{color:var(--faint);font-family:var(--mono);font-size:13px}
.pt{flex:1 1 250px;min-width:0;font-size:14.5px}
.pn{display:block;color:var(--faint);font-size:12.5px;margin-top:2px}
.pl audio{flex:2 1 280px;min-width:220px;height:36px}
.tw{overflow-x:auto;margin:18px 0;border:1px solid rgba(255,255,255,.14);border-radius:8px}
table{border-collapse:collapse;width:100%;min-width:620px;font-size:14px}
th,td{padding:10px 13px;text-align:left;border-bottom:1px solid rgba(255,255,255,.1);vertical-align:top}
thead th{background:rgba(0,0,0,.4);font-family:var(--mono);font-size:11px;letter-spacing:.09em;text-transform:uppercase;
         color:var(--dim);font-weight:400;white-space:nowrap}
tbody tr:last-child td{border-bottom:none}
.ok{color:#6BE08A;font-weight:500}.no{color:#FF7FB0;font-weight:500}.mid{color:#FFB347;font-weight:500}
.note{border-left:3px solid currentColor;background:rgba(0,0,0,.3);padding:15px 19px;border-radius:0 6px 6px 0;margin:18px 0;font-size:15px}
.note b{color:#fff}.ng{color:#6BE08A}.nr{color:#FF7FB0}.ny{color:#FFB347}.nb{color:#7FA8FF}
ul,ol{color:var(--dim);padding-left:1.3em;max-width:72ch}li{margin-bottom:.5em}li b{color:var(--ink);font-weight:500}
.grid{display:grid;gap:15px;margin:20px 0}.g2{grid-template-columns:repeat(auto-fit,minmax(290px,1fr))}
.card{background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.14);border-radius:8px;padding:18px 20px}
.card h3{font-size:16px;margin-bottom:7px}.card p{font-size:14px;color:var(--dim);margin:0}
.kb{display:inline-block;font-family:var(--mono);font-size:12px;padding:2px 8px;border-radius:5px;
    border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.07);margin:0 2px}
footer{padding:38px 0 66px;color:var(--faint);font-size:13.5px;background:var(--b0)}
:focus-visible{outline:2px solid var(--c1);outline-offset:3px}
@media(max-width:640px){.num{width:42px;height:42px;font-size:16px}.hd{gap:12px}.s{padding:36px 0}}
"""
b=rep["before"]; a=rep["after"]
PAGE=f"""<title>풍성하게 만들기</title>
<meta name="description" content="Studio One 프로젝트를 읽어 멜로디를 건드리지 않고 음을 두껍게 만드는 방법과, 마스터링 전후 비교.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@700&family=IBM+Plex+Sans+KR:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>{CSS}</style>
<header><div class="w">
  <div class="eye">2026-10-26 · .song 프로젝트 분석 · 풍성하게 + 마스터링</div>
  <h1>음은 그대로 두고<br><em>두껍게만</em> 만들었습니다</h1>
  <p class="lead"><b class="hi">새 멜로디는 한 음도 안 썼습니다.</b> 당신이 친 화음과 오스티나토를
  옥타브로 겹치고, 당신 화음의 구성음만으로 패드를 깔고, 드럼을 붙였습니다.
  작곡은 여전히 당신 것입니다.</p>
  <div class="chips"><span class="chip">🎵 140 BPM · D minor</span><span class="chip">🎚️ −14.15 LUFS · −1.0 dBTP</span>
  <span class="chip">🔊 미리듣기 3개</span><span class="chip">💰 전부 오픈소스</span></div>
</div></header>

<section class="s s1"><div class="w">
  <div class="hd"><div class="num">1</div><div><h2>프로젝트 열어보니 — <b class="hi">재료가 이미 있습니다</b></h2></div></div>
  <p class="sub">.song 파일은 ZIP이라 안을 들여다볼 수 있었습니다. <b class="hi">가장 중요한 발견부터 말씀드립니다.</b></p>
  <div class="note ng"><b>풍성하게 만드는 가장 빠른 방법 — 이미 만들어 두신 걸 켜기만 하면 됩니다</b><br>
  <b class="hi">EZkeys 트랙 3개가 전부 뮤트돼 있습니다.</b> 그 안에 합쳐서 <b>4,337개 노트</b>가 들어 있습니다.
  이걸 켜는 것만으로 곡이 훨씬 두꺼워집니다. 새로 만들 필요가 없습니다.</div>
  <div class="tw"><table>
    <thead><tr><th>트랙</th><th>노트</th><th>상태</th><th>내용</th></tr></thead><tbody>
    <tr><td><b>올겐</b></td><td class="ok">9,525</td><td class="ok">켜짐</td>
      <td>프로젝트에서 가장 큰 파트입니다. E·C#·A가 압도적이라 <b class="hi">A major 중심</b> — 당신 진행의 V 화음입니다.</td></tr>
    <tr><td><b>EZkeys 4</b></td><td class="mid">1,809</td><td class="no">뮤트</td><td>D·A·G·E 중심. 음역 33~94로 넓습니다.</td></tr>
    <tr><td><b>EZkeys 3</b></td><td class="mid">1,580</td><td class="no">뮤트</td><td>D·A·E·G 중심.</td></tr>
    <tr><td><b>EZkeys 2</b></td><td class="mid">948</td><td class="no">뮤트</td><td>E·A·C·D 중심.</td></tr>
    <tr><td>피아노</td><td>84</td><td class="ok">켜짐</td><td>화성의 뼈대. 2마디마다 4성 화음.</td></tr>
    <tr><td>STRING / STRING 2</td><td>65 / 71</td><td class="ok">켜짐</td><td>16분 오스티나토.</td></tr>
    <tr><td>베이스</td><td>12</td><td class="ok">켜짐</td><td>근음만.</td></tr>
    </tbody></table></div>
  <div class="note nb"><b>그 밖에 확인한 것</b>
  <ul style="margin:8px 0 0">
    <li>템포가 <b class="hi">140 BPM</b>입니다. 지난번 보내주신 MIDI는 120이었으니 그 사이에 올리셨습니다.</li>
    <li>쓰고 계신 음원: <b>Korg TRITON ×2, Korg M1, EZkeys ×4, EZdrummer 3, Impact ×2</b>.
      이미 좋은 걸 갖고 계셔서 새로 살 게 없습니다.</li>
    <li>오디오 트랙 15개(노래 1·2·3, 클린기타, 드라이브기타 등)는 <b>비어 있습니다</b> — 자리만 만들어 두신 상태입니다.</li>
  </ul></div>
</div></section>

<section class="s s2"><div class="w">
  <div class="hd"><div class="num">2</div><div><h2>제가 <b class="hi">두껍게</b> 만든 결과</h2></div></div>
  <p class="sub">지난번 MIDI를 140 BPM으로 맞추고 레이어를 쌓았습니다. 마스터링 전후를 나란히 들어보세요.</p>
  {au("a_있는그대로.mp3","① 원래 1안","스트링 중복, 드럼 롱노트, 베이스 높음")}
  {au("d_풍성한버전_마스터전.mp3","② 풍성하게 (마스터링 전)","레이어 10개, 768노트")}
  {au("e_풍성한버전_마스터후.mp3","③ 풍성하게 + 마스터링","−14.15 LUFS, −1.0 dBTP")}
  <div class="tw"><table>
    <thead><tr><th>측정</th><th>마스터링 전</th><th>후</th><th>뜻</th></tr></thead><tbody>
    <tr><td>라우드니스</td><td>{b['lufs']} LUFS</td><td class="ok">{a['lufs']} LUFS</td><td>스트리밍 기준에 맞췄습니다</td></tr>
    <tr><td>트루 피크</td><td>{b['true_peak']} dBTP</td><td class="ok">{a['true_peak']} dBTP</td><td>인코딩해도 안 터집니다</td></tr>
    <tr><td>클리핑</td><td>{b['clipped']}</td><td class="ok">{a['clipped']}</td><td>없음</td></tr>
    <tr><td>DC 오프셋</td><td>—</td><td class="ok">{a['dc']:.2e}</td><td>제거됨</td></tr>
    </tbody></table></div>
  <p class="sub" style="margin-top:4px">체인: 20 Hz 하이패스 → 미드/사이드 폭 0.95 → −14 LUFS 정규화 → 4배 오버샘플 리미터 −1.0 dBTP.
  <b>마스터링은 제작이지 작곡이 아닙니다.</b> 누가 곡을 썼는지는 전혀 바뀌지 않습니다.</p>
</div></section>

<section class="s s3"><div class="w">
  <div class="hd"><div class="num">3</div><div><h2>무엇이 <b class="hi">당신 것</b>이고 무엇이 제가 더한 것인가</h2></div></div>
  <p class="sub">이게 가장 중요한 표입니다. <b class="hi">AI 작곡이 되면 안 된다</b>고 하셨으니 한 줄씩 명시합니다.</p>
  <div class="tw"><table>
    <thead><tr><th>레이어</th><th>노트</th><th>누구 것</th><th>설명</th></tr></thead><tbody>
    <tr><td>피아노</td><td>16</td><td class="ok">✅ 당신이 친 그대로</td><td>화음 4개. 손도 안 댔습니다.</td></tr>
    <tr><td>STRING</td><td>126</td><td class="ok">✅ 당신이 친 그대로</td><td>16분 오스티나토.</td></tr>
    <tr><td>베이스</td><td>4</td><td class="ok">✅ 당신이 친 그대로</td><td>근음.</td></tr>
    <tr><td>STRING 한 옥타브 아래</td><td>126</td><td class="mid">🔁 당신 음에서 파생</td>
      <td><b class="hi">새 음이 아닙니다.</b> 당신 음을 12반음 내리고 16ms 늦춰 폭만 만들었습니다.</td></tr>
    <tr><td>STRING 한 옥타브 위</td><td>126</td><td class="mid">🔁 당신 음에서 파생</td><td>반짝임용. 음 이름은 동일합니다.</td></tr>
    <tr><td>서브베이스</td><td>4</td><td class="mid">🔁 당신 음에서 파생</td><td>당신 베이스를 2옥타브 내린 것.</td></tr>
    <tr><td>패드</td><td>64</td><td class="mid">🔁 당신 화음의 구성음만</td>
      <td><b class="hi">당신 피아노가 치는 음만</b> 길게 늘였습니다. 새 화성을 만들지 않았습니다.</td></tr>
    <tr><td>합창 (9~16마디)</td><td>32</td><td class="mid">🔁 당신 화음의 구성음만</td><td>한 옥타브 위로.</td></tr>
    <tr><td>9~16마디 베이스</td><td>4</td><td class="mid">🔁 당신 화음의 근음</td><td>빈 구간에 당신 진행을 한 번 더.</td></tr>
    <tr><td><b>드럼</b></td><td>266</td><td class="no">🆕 제가 새로 만든 반주</td>
      <td><b class="hi">유일하게 새로 만든 것</b>입니다. 킥·스네어·하이햇·필인.
      멜로디가 아니라 반주라 작곡 귀속에 영향이 적지만, 마음에 안 드시면 지우시면 됩니다.</td></tr>
    </tbody></table></div>
  <div class="note ng"><b>정리하면</b><br>
  당신 음 <b class="hi">146개</b> · 당신 음에서 파생 <b class="hi">356개</b> · 제가 새로 만든 드럼 <b>266개</b>.<br>
  <b>멜로디는 제가 한 음도 쓰지 않았습니다.</b> 옥타브를 겹치는 건 편곡이지 작곡이 아닙니다 —
  같은 음을 다른 높이에서 한 번 더 울리는 것뿐입니다.</div>
  <div class="note nr"><b>그래도 남는 약점</b><br>
  <b class="hi">아직 멜로디가 없습니다.</b> 지금 곡은 반주만 두꺼워진 상태라 "노래"가 아니라 "배경음악"입니다.
  이건 제가 채우면 안 되는 자리입니다. 8마디만 흥얼거려 주시면 MIDI로 만들어 드립니다.</div>
</div></section>

<section class="s s4"><div class="w">
  <div class="hd"><div class="num">4</div><div><h2>당신이 Studio One에서 <b class="hi">바로 할 것</b></h2></div></div>
  <p class="sub">가장 간편한 순서입니다. 위에서부터 하시면 됩니다.</p>
  <div class="grid g2">
    <div class="card"><h3>① EZkeys 뮤트 풀기 <span style="color:var(--c1)">(30초)</span></h3>
      <p>EZkeys 2·3·4 트랙의 <b class="kb">M</b> 버튼을 끄세요. <b class="hi">4,337개 노트가 바로 살아납니다.</b>
      너무 두꺼우면 볼륨을 −6 dB씩 내리세요. 이게 가장 빠른 "풍성하게"입니다.</p></div>
    <div class="card"><h3>② 드럼1 트랙에 드럼 음원 <span style="color:var(--c1)">(1분)</span></h3>
      <p>Browser에서 <b>EZdrummer 3</b>(이미 갖고 계십니다)을 드럼1 트랙에 끌어다 놓고
      <b>Replace</b>. 지금은 C2가 저음으로 나고 있습니다.</p></div>
    <div class="card"><h3>③ STRING 2를 한 옥타브 내리기 <span style="color:var(--c1)">(30초)</span></h3>
      <p>STRING과 음이 똑같아 중복입니다. 파트를 선택하고 <b class="kb">Shift</b>+<b class="kb">↓</b>
      두 번이면 한 옥타브 내려갑니다. 그 순간 소리가 넓어집니다.</p></div>
    <div class="card"><h3>④ 리버브 버스 하나 <span style="color:var(--c1)">(2분)</span></h3>
      <p>콘솔에서 <b>FX 채널</b>을 하나 만들고 <b>Room Reverb</b>(기본 내장)를 걸어,
      스트링·피아노·합창을 −18 dB쯤 보내세요. <b class="hi">공간감이 생기면 훨씬 풍성하게 들립니다.</b></p></div>
    <div class="card"><h3>⑤ 베이스 2옥타브 내리기 <span style="color:var(--c1)">(30초)</span></h3>
      <p>지금 A2~D3는 중저음입니다. 두 옥타브 내리면 아이언맨 같은 무게가 생깁니다.
      TRITON이나 M1의 신스 베이스 프리셋을 쓰세요.</p></div>
    <div class="card"><h3>⑥ 9~16마디 채우기 <span style="color:var(--c4)">(당신 몫)</span></h3>
      <p>피아노·베이스가 8마디에서 끝납니다. 같은 화음을 복사해 붙이되
      <b class="hi">한 화음만 다른 걸로 바꾸세요.</b> 그러면 16마디 구조가 됩니다.</p></div>
  </div>
  <div class="note ny"><b>마스터링은 마지막에, 한 번만</b><br>
  위 작업을 다 하신 뒤 <code>Session → Export Mixdown</code>으로 WAV를 뽑아 저한테 주시면
  제가 마스터링해 드립니다. 또는 Studio One의 <b>Project 페이지</b>에 내장 마스터링이 있으니 그걸 쓰셔도 됩니다.
  <b class="hi">중간중간 마스터링하지 마세요</b> — 편곡이 바뀌면 다시 해야 합니다.</div>
</div></section>

<section class="s s5"><div class="w">
  <div class="hd"><div class="num">5</div><div><h2>오픈소스로 할 수 있는 것</h2></div></div>
  <p class="sub">지금 이 페이지의 모든 소리와 마스터링은 <b class="hi">전부 무료 오픈소스</b>로 만들었습니다. 설치하실 필요는 없습니다 — 제가 돌립니다.</p>
  <div class="tw"><table>
    <thead><tr><th>도구</th><th>라이선스</th><th>역할</th><th>당신이 설치?</th></tr></thead><tbody>
    <tr><td><b>FluidSynth</b> + FluidR3_GM</td><td class="ok">LGPL / 무료</td><td>MIDI를 소리로 렌더</td><td class="ok">불필요 (제가 실행)</td></tr>
    <tr><td><b>pretty_midi · mido</b></td><td class="ok">MIT</td><td>MIDI 읽기·쓰기·편집</td><td class="ok">불필요</td></tr>
    <tr><td><b>numpy · scipy</b></td><td class="ok">BSD</td><td>마스터링 DSP (HPF·M/S·리미터)</td><td class="ok">불필요</td></tr>
    <tr><td><b>pyloudnorm</b></td><td class="ok">MIT</td><td>LUFS 측정 (EBU R128)</td><td class="ok">불필요</td></tr>
    <tr><td><b>librosa</b></td><td class="ok">ISC</td><td>조성·코드·음색 분석</td><td class="ok">불필요</td></tr>
    <tr><td><b>ffmpeg</b></td><td class="ok">LGPL</td><td>MP3·FLAC 인코딩</td><td class="ok">불필요</td></tr>
    <tr><td>Studio One 내장 Room Reverb·Compressor</td><td class="mid">이미 보유</td><td>공간감·다이내믹</td><td class="mid">이미 있음</td></tr>
    <tr><td>EZkeys · EZdrummer · TRITON · M1</td><td class="mid">이미 보유</td><td>음원</td><td class="mid">이미 있음</td></tr>
    </tbody></table></div>
  <div class="note ng"><b>새로 사실 건 없습니다</b><br>
  TRITON·M1·EZkeys·EZdrummer를 이미 갖고 계시고, 부족한 부분은 제가 무료 오픈소스로 처리합니다.
  <b class="hi">돈을 더 쓰는 것보다 EZkeys 뮤트를 푸는 게 훨씬 큽니다.</b></div>
  <div class="note nb"><b>.song 파일을 읽은 방법</b><br>
  <code>.song</code>은 ZIP이라 풀어서 <code>Song/song.xml</code>(트랙·템포)과
  <code>Performances/*.musicx</code>(음표)를 직접 읽었습니다.
  musicx는 공개 문서가 없는 형식이라 <b>바이트를 뜯어보고 파서를 새로 만들었습니다</b>
  (<code>compose/musicx.py</code>). 노트 수·음역·음 분포는 신뢰할 만하지만,
  <b class="hi">시간 단위 해석에는 불확실성이 남아</b> 마디 위치는 보수적으로만 썼습니다.</div>
</div></section>

<footer><div class="w">
  <p>이 페이지의 수치는 올려주신 <code>.song</code>과 <code>.mid</code>를 직접 읽어서 나온 값입니다.
  풍성한 버전의 MIDI와 마스터 WAV도 만들어 두었으니 말씀하시면 보내드립니다.</p>
  <p style="margin-top:12px">도구 <code>compose/enrich.py</code> · <code>compose/master_simple.py</code> ·
  <code>compose/musicx.py</code> · 저장소
  <a href="https://github.com/geben147-create/-/tree/{BR}" target="_blank" rel="noopener">geben147-create/- · {BR}</a></p>
</div></footer>
"""
os.makedirs(os.path.dirname(OUT),exist_ok=True)
open(OUT,"w",encoding="utf-8").write(PAGE)
print("wrote",OUT,f"{os.path.getsize(OUT)/1048576:.2f} MB")
