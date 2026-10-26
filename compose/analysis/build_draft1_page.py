# -*- coding: utf-8 -*-
import base64, os, html
D="/tmp/claude-0/-home-user--/4b2bd38e-8d7f-52a5-bb39-0e1615b1f404/scratchpad/an1"
OUT="/home/user/-/docs/1안_진단.html"
BR="claude/manual-composition"
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
--b0:#0C0F11;--b1:#0C2420;--b2:#2A1115;--b3:#141B33;--b4:#2A1D0A;--b5:#1A1422;
--c1:#3FD6A8;--c2:#FF6B7A;--c3:#7FA8FF;--c4:#FFB347;--c5:#C98BFF}
*{box-sizing:border-box}html{color-scheme:dark}
body{margin:0;background:var(--b0);color:var(--ink);font-family:var(--sans);font-weight:300;font-size:16px;line-height:1.75}
.w{width:min(1000px,92vw);margin:0 auto}
h1,h2,h3{font-family:var(--serif);font-weight:700;margin:0;line-height:1.24;text-wrap:balance}
p{margin:0 0 1em;max-width:70ch}
code{font-family:var(--mono);font-size:.86em;background:rgba(255,255,255,.09);padding:2px 7px;border-radius:4px}
pre{font-family:var(--mono);font-size:12.5px;line-height:1.7;background:rgba(0,0,0,.45);border:1px solid rgba(255,255,255,.13);
    border-radius:7px;padding:14px 16px;overflow-x:auto;margin:14px 0}
a{color:inherit;border-bottom:1px solid currentColor;text-decoration:none}
header{padding:54px 0 40px;background:linear-gradient(165deg,#102C27,#0C0F11 72%);border-bottom:1px solid rgba(255,255,255,.1)}
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
.ok{color:#5BE59A;font-weight:500}.no{color:#FF6B7A;font-weight:500}.mid{color:#FFB347;font-weight:500}
.note{border-left:3px solid currentColor;background:rgba(0,0,0,.3);padding:15px 19px;border-radius:0 6px 6px 0;margin:18px 0;font-size:15px}
.note b{color:#fff}.ng{color:#5BE59A}.nr{color:#FF6B7A}.ny{color:#FFB347}.nb{color:#7FA8FF}
ul,ol{color:var(--dim);padding-left:1.3em;max-width:72ch}li{margin-bottom:.5em}li b{color:var(--ink);font-weight:500}
.grid{display:grid;gap:15px;margin:20px 0}.g2{grid-template-columns:repeat(auto-fit,minmax(290px,1fr))}
.card{background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.14);border-radius:8px;padding:18px 20px}
.card h3{font-size:16px;margin-bottom:7px}.card p{font-size:14px;color:var(--dim);margin:0}
footer{padding:38px 0 66px;color:var(--faint);font-size:13.5px;background:var(--b0)}
:focus-visible{outline:2px solid var(--c1);outline-offset:3px}
@media(max-width:640px){.num{width:42px;height:42px;font-size:16px}.hd{gap:12px}.s{padding:36px 0}}
"""

PAGE=f"""<title>1안 진단</title>
<meta name="description" content="Studio One에서 만든 첫 스케치를 읽어서 구조와 코드를 분석하고, 고칠 점 다섯 가지와 고친 버전을 들려주는 페이지.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@700&family=IBM+Plex+Sans+KR:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>{CSS}</style>

<header><div class="w">
  <div class="eye">2026-10-26 · 1안 수신 · 읽기 완료</div>
  <h1>보내주신 1안, <em>읽었습니다</em></h1>
  <p class="lead">MCP 연결은 <b>필요 없었습니다.</b> 파일을 올려 주셨고 제가 바로 열었습니다 — 이게 제가 말씀드린 그 방식입니다.
  <b class="hi">결론부터: 뼈대는 다 됐습니다.</b> 어려운 부분(화성과 오스티나토)이 끝났고, 남은 건 편곡입니다.</p>
  <div class="chips"><span class="chip">🎵 D minor · 120 BPM</span><span class="chip">📏 16마디 · 30.5초</span>
  <span class="chip">🎹 트랙 5개 · 276노트</span><span class="chip">🔊 미리듣기 3개</span></div>
</div></header>

<section class="s s1"><div class="w">
  <div class="hd"><div class="num">1</div><div><h2>만드신 것 — <b class="hi">무엇이 들어있나</b></h2></div></div>
  <p class="sub">Save As로 내보내신 게 정확히 됐습니다. <b class="hi">템포 120과 트랙 이름이 그대로 들어왔습니다.</b>
  (제가 4단계에서 알려드린 경로가 맞았다는 뜻입니다.)</p>
  <div class="tw"><table>
    <thead><tr><th>트랙</th><th>노트</th><th>구간</th><th>내용</th></tr></thead><tbody>
    <tr><td><b>피아노</b></td><td>16</td><td>1~8마디</td>
      <td>2마디마다 4성 화음 하나. <b class="hi">이 곡의 화성 전부가 여기 있습니다.</b></td></tr>
    <tr><td><b>STRING</b></td><td>126</td><td>1~16마디</td>
      <td>16분음표 오스티나토 <code>D5–A4–D5–F5</code> 반복. 곡을 끌고 가는 동력입니다.</td></tr>
    <tr><td><b>STRING 2</b></td><td>126</td><td>1~16마디</td>
      <td class="no">STRING과 음이 <b>완전히 똑같습니다.</b> 복제본입니다.</td></tr>
    <tr><td><b>베이스</b></td><td>4</td><td>1~8마디</td>
      <td>피아노 근음을 따라갑니다. D3 · A♯2 · C3 · A2</td></tr>
    <tr><td><b>드럼1</b></td><td>4</td><td>1~8마디</td>
      <td class="no">C2 한 음을 <b>7박씩 길게</b> 눌렀습니다. 드럼 채널이 아닙니다.</td></tr>
    <tr><td colspan="4" style="color:var(--faint)">그 외 비어 있는 트랙 9개 (드럼1 2, 박수, 올겐, EZdrummer 3, EZkeys 2·2·3·4, *)</td></tr>
    </tbody></table></div>

  <h3 style="margin:24px 0 10px">코드 진행 — <b class="hi">좋은 선택을 하셨습니다</b></h3>
  <pre>1~2마디   Dm   (D · F · A)      i
3~4마디   B♭   (B♭ · D · F)     VI
5~6마디   C    (C · E · G)      VII
7~8마디   A    (A · C# · E)     V   ← C#! 화성단음계의 딸림화음</pre>
  <div class="note ng"><b>7마디의 A major가 핵심입니다</b><br>
  D단조의 자연 음계대로라면 7마디는 Am이 나와야 합니다. 그런데 <b class="hi">C#을 써서 A major로 올리셨습니다.</b>
  이게 화성단음계의 딸림화음이고, 1마디 Dm으로 돌아갈 때 <b>끌어당기는 힘</b>을 만듭니다.
  우연이든 의도든 음악적으로 맞는 선택입니다. 이것 때문에 8마디가 맴돌지 않고 앞으로 나아갑니다.</div>
  <div class="note nb"><b>참고 — 아이언맨 원곡과 비교</b><br>
  원곡은 <code>D – B♭ – F – C</code> (i–VI–III–VII)였고, 지금 1안은 <code>Dm – B♭ – C – A</code> (i–VI–VII–V)입니다.
  앞 두 개가 같고 뒤가 다릅니다. <b class="hi">베낀 게 아니라 같은 어법 안에서 다르게 가신 겁니다.</b> 이게 맞는 방향입니다.</div>
</div></section>

<section class="s s2"><div class="w">
  <div class="hd"><div class="num">2</div><div><h2>지금 상태 <b class="hi">그대로</b> 들어보기</h2></div></div>
  <p class="sub">트랙 이름대로 악기만 배정해서 렌더했습니다. 고친 건 하나도 없습니다.</p>
  {au("a_있는그대로.mp3","1안 — 있는 그대로","스트링 2개 중복, 드럼은 롱노트, 베이스 높음")}
  <div class="note nr"><b>들으면 바로 걸리는 것 다섯 가지</b>
  <ol style="margin:10px 0 0">
    <li><b class="hi">드럼이 드럼 소리가 안 납니다.</b> C2를 7박씩 눌러놓으셨는데, 이 트랙이 드럼 채널로 지정돼 있지 않아서
      낮은 음 하나가 길게 울립니다. 킥이 아니라 그냥 저음입니다.</li>
    <li><b class="hi">베이스가 2옥타브 높습니다.</b> A2~D3(110~147Hz)인데, 아이언맨의 그 "빰빰"은 D1~C2(36~73Hz)였습니다.
      지금은 저음이 아니라 중저음이라 무게가 안 실립니다.</li>
    <li><b class="hi">STRING 2가 STRING과 음이 완전히 같습니다.</b> 똑같은 걸 두 번 겹치면 소리만 커지고
      넓어지지는 않습니다. 옥타브를 내리거나 살짝 늦추면 그때 넓어집니다.</li>
    <li><b class="hi">9~16마디에 스트링만 남습니다.</b> 피아노·베이스·드럼이 8마디에서 전부 끝나서
      뒤쪽 절반이 비어 있습니다.</li>
    <li>템포 120은 아이언맨(148)보다 느립니다. 의도하신 거면 괜찮지만, 그 추진력을 원하시면 올려야 합니다.</li>
  </ol></div>
</div></section>

<section class="s s3"><div class="w">
  <div class="hd"><div class="num">3</div><div><h2>다섯 가지를 고치면 <b class="hi">이렇게</b> 됩니다</h2></div></div>
  <p class="sub">위의 다섯 가지만 손봤습니다. <b>당신이 친 음은 하나도 안 바꿨습니다</b> —
  화음도 오스티나토도 베이스 진행도 그대로입니다.</p>
  {au("b_고친버전.mp3","고친 버전 (120 BPM)","드럼 패턴 · 베이스 2옥타브 ↓ · 스트링 분리 · 9~16마디 보강")}
  {au("c_148bpm.mp3","같은 것을 148 BPM으로","아이언맨 템포로 올리면 느낌이 이렇게 달라집니다")}
  <div class="tw"><table>
    <thead><tr><th>고친 것</th><th>어떻게</th><th>당신 음이 바뀌었나</th></tr></thead><tbody>
    <tr><td>드럼</td><td>C2 롱노트 4개 → 킥·스네어·하이햇 패턴 16마디, 4마디마다 크래시</td><td class="ok">아니오 (새로 만듦)</td></tr>
    <tr><td>베이스</td><td>2옥타브 아래로 (A2→A0 대역), 신스 베이스 음색</td><td class="mid">음정은 그대로, 옥타브만</td></tr>
    <tr><td>STRING 2</td><td>1옥타브 아래 + 18ms 지연 + 볼륨 −18 → 폭이 생김</td><td class="mid">음정 그대로, 옥타브·타이밍만</td></tr>
    <tr><td>9~16마디</td><td>같은 코드 진행을 패드와 베이스로 한 번 더</td><td class="ok">아니오 (빈 곳 채움)</td></tr>
    <tr><td>템포</td><td>148 버전 별도 생성</td><td class="ok">아니오 (전체 비율만)</td></tr>
    </tbody></table></div>
  <div class="note ny"><b>옥타브를 내린 건 "고친 것"일까 "바꾼 것"일까</b><br>
  음 이름은 그대로고 높이만 내렸습니다. 작곡에서는 <b>편곡 결정</b>에 해당합니다.
  마음에 안 드시면 원래 높이로 되돌립니다 — 말씀만 하세요. 중간(1옥타브만)도 됩니다.</div>
</div></section>

<section class="s s4"><div class="w">
  <div class="hd"><div class="num">4</div><div><h2>이 상태에서 <b class="hi">제가 할 수 있는 것</b></h2></div></div>
  <p class="sub">지금 파일 하나만으로 가능한 것들입니다. 말씀만 하시면 바로 합니다.</p>
  <div class="grid g2">
    <div class="card"><h3>🎻 악기 바꾸기</h3><p>피아노를 로즈·오르간·하프시코드로, 스트링을 합창·브라스·신스로.
      여러 개를 한꺼번에 렌더해서 나란히 들려드립니다. "피아노를 오르간으로"처럼 말씀하시면 됩니다.</p></div>
    <div class="card"><h3>🥁 드럼 만들기</h3><p>A/B/C 세 가지 그루브를 당신 연주와 섞어서. 고르신 다음
      "12마디 킥 빼줘" 같은 수정도 됩니다.</p></div>
    <div class="card"><h3>🎸 베이스 라인 다시 쓰기</h3><p>지금은 2마디에 한 음입니다. 8분음표로 움직이게,
      경과음을 넣어 다음 코드로 걸어가게 — 세 가지 안을 만들어 드립니다.</p></div>
    <div class="card"><h3>🧱 구조 늘리기</h3><p>8마디 → 16·24·32마디로. 인트로·브레이크·브리지를 붙이고
      어디서 악기가 빠지고 들어올지 배치합니다.</p></div>
    <div class="card"><h3>🎼 코드 대안 제시</h3><p>지금 i–VI–VII–V 말고 다른 4개 진행을
      같은 멜로디 위에서 들려드립니다. 고르시면 됩니다.</p></div>
    <div class="card"><h3>🎹 오스티나토 변형</h3><p>스트링 16분 패턴을 리듬만 바꾼 3안으로.
      지금은 끝까지 똑같이 반복되는데, 구간마다 달라지면 지루하지 않습니다.</p></div>
    <div class="card"><h3>🔍 분석·검증</h3><p>조성·스케일·마디별 코드·음역·밀도. 불협이 생기는 지점,
      음이 겹쳐서 뭉개지는 지점을 짚어 드립니다.</p></div>
    <div class="card"><h3>🎚️ 믹스·마스터</h3><p>−14 LUFS·−1 dBTP로 맞춘 FLAC/MP3.
      다만 최종본은 Studio One의 좋은 음원으로 뽑으시는 게 낫습니다.</p></div>
  </div>
  <div class="note nr"><b>제가 안 하는 것</b><br>
  <b class="hi">멜로디를 대신 만들지 않습니다.</b> 지금 1안에서 화성과 오스티나토는 당신이 만드셨고,
  그게 이 곡을 당신 것으로 만드는 부분입니다. 제가 멜로디까지 쓰면 그 지점이 흐려집니다.
  선율이 필요하면 <b>흥얼거려서 주세요</b> — MIDI로 바꿔 드립니다.</div>
</div></section>

<section class="s s5"><div class="w">
  <div class="hd"><div class="num">5</div><div><h2>이 정도면 <b class="hi">되는가</b></h2></div></div>
  <div class="note ng"><b>네, 충분합니다. 어려운 쪽이 끝났습니다.</b><br>
  작곡에서 힘든 건 <b class="hi">화성을 정하는 것</b>과 <b class="hi">반복될 음형을 찾는 것</b>입니다.
  둘 다 하셨습니다. i–VI–VII–V에 화성단음계 딸림화음까지 넣으셨고,
  16분 오스티나토라는 분명한 동력도 만드셨습니다. 남은 건 편곡과 믹스인데 그건 제가 하는 영역입니다.</div>
  <h3 style="margin:22px 0 10px">다음에 하시면 좋은 것 — 우선순위대로</h3>
  <div class="tw"><table>
    <thead><tr><th>순위</th><th>할 일</th><th>누가</th><th>왜</th></tr></thead><tbody>
    <tr><td>🥇</td><td><b>멜로디를 얹으세요</b></td><td class="no">당신</td>
      <td>지금은 반주만 있습니다. 노래하는 선율이 없어서 "배경음악"에 머뭅니다.
      스트링 위쪽(A5 근처)이나 피아노 오른손으로 8마디만 치시면 곡이 됩니다. 흥얼거려 주셔도 됩니다.</td></tr>
    <tr><td>🥈</td><td><b>9~16마디를 직접 채우세요</b></td><td class="no">당신</td>
      <td>제가 임시로 채운 건 1~8마디 복사입니다. 거기에 <b class="hi">다른 코드</b>를 넣으면
      곡이 16마디짜리 구조가 됩니다. 한 코드만 바꿔도 충분합니다.</td></tr>
    <tr><td>🥉</td><td>드럼 그루브 고르기</td><td class="mid">제가 3안 → 당신이 선택</td>
      <td>고른 기록이 남습니다.</td></tr>
    <tr><td>4</td><td>템포 결정</td><td class="no">당신</td><td>120과 148을 들어보고 정하세요. 중간값도 됩니다.</td></tr>
    <tr><td>5</td><td>악기 확정</td><td class="mid">제가 비교 → 당신이 선택</td><td>후보를 나란히 들려드립니다.</td></tr>
    </tbody></table></div>
  <div class="note nb"><b>Studio One에서 바로 고치실 것 두 가지</b>
  <ul style="margin:8px 0 0">
    <li><b class="hi">드럼1 트랙을 드럼 악기로 바꾸세요.</b> 지금은 일반 악기 트랙이라 C2가 저음으로 납니다.
      Browser에서 드럼 음원(EZdrummer 등)을 그 트랙에 끌어다 놓고 Replace 하시면 바로 킥 소리가 납니다.</li>
    <li><b class="hi">STRING 2를 지우거나 바꾸세요.</b> STRING과 음이 똑같아서 지금은 중복입니다.
      지우시거나, 한 옥타브 내리거나, 다른 악기로 바꾸세요.</li>
  </ul></div>
  <div class="note ny"><b>"MCP 연결"에 대해</b><br>
  이번에 <b class="hi">MCP는 쓰지 않았습니다.</b> 파일을 올려 주셨고 제가 열었습니다 — 그게 전부입니다.
  MCP를 붙여도 달라지는 건 <b>"올리는 단계가 없어지는 것"</b> 하나뿐입니다. 분석도 편집도 지금과 똑같습니다.
  올리는 게 번거로워지시면 그때 데스크톱 앱 로컬 세션을 쓰시면 됩니다.</div>
</div></section>

<footer><div class="w">
  <p>이 페이지의 분석은 올려주신 <code>.mid</code> 파일을 직접 읽어서 나온 값입니다.
  고친 버전의 MIDI 파일도 만들어 두었으니 Studio One에 끌어다 넣으실 수 있습니다 — 말씀하시면 보내드립니다.</p>
  <p style="margin-top:12px">도구 <code>compose/compose.py</code> · 저장소
  <a href="https://github.com/geben147-create/-/tree/{BR}" target="_blank" rel="noopener">geben147-create/- · {BR}</a></p>
</div></footer>
"""
os.makedirs(os.path.dirname(OUT),exist_ok=True)
open(OUT,"w",encoding="utf-8").write(PAGE)
print("wrote",OUT,f"{os.path.getsize(OUT)/1048576:.2f} MB")
