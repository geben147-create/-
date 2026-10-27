# -*- coding: utf-8 -*-
"""Black-background status page with the listening versions. python3 build_status_page.py <scratch dir> <out.html>"""
import os, sys, base64, html, json
D, OUT = sys.argv[1], sys.argv[2]
def b64(p): return "data:audio/mpeg;base64," + base64.b64encode(open(p, "rb").read()).decode()
A = {}
for k, p in {"violin": "/home/user/-/compose/out/trio77/trio77.mp3", "cello": f"{D}/v10/p6.mp3", "user": f"{D}/uo/useronly.mp3"}.items():
    if os.path.exists(p): A[k] = b64(p)
def pl(k, label):
    return (f'<div class="pl"><span class="pk">{html.escape(label)}</span><audio controls preload="metadata" src="{A[k]}"></audio></div>'
            if k in A else f'<p class="warn">{html.escape(label)}: 파일 없음</p>')

PAGE = f"""<title>노래 파일 점검</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gothic+A1:wght@300;400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: black ledger. Each topic is a full-width band with its own accent line, so the topics read as separate sheets. */
:root{{--bg:#000;--ink:#F3F1EA;--dim:#A9A79E;--faint:#6B6A64;--rule:rgba(243,241,234,.16);
--red:#FF5C4D;--amber:#FFC44D;--green:#6FE3A0;--blue:#7DB4FF;--violet:#C7A0FF;
--body:"Gothic A1","Malgun Gothic",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;color-scheme:dark}}
*{{box-sizing:border-box}}html{{background:#000}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);font-weight:300;font-size:16px;line-height:1.8;-webkit-text-size-adjust:100%}}
.w{{width:100%;max-width:960px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:44px}}
section{{border-top:1px solid var(--rule)}} section .w{{border-left:3px solid var(--acc,#fff);padding-left:max(18px,env(safe-area-inset-left,0px))}}
h1,h2{{font-weight:600;margin:0;line-height:1.3;text-wrap:balance}} h1{{font-size:clamp(26px,4.6vw,42px)}} h2{{font-size:clamp(20px,3vw,27px);margin-bottom:10px}}
p{{margin:0 0 1em;max-width:66ch}} .lead{{color:var(--dim);font-size:17px}}
.eye{{font-family:var(--mono);font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--acc,var(--faint));margin-bottom:10px}}
.mono{{font-family:var(--mono);font-size:.86em;font-variant-numeric:tabular-nums}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,210px),1fr));gap:14px;margin:20px 0}}
.k{{border:1px solid var(--rule);padding:14px 16px;min-width:0}} .k b{{display:block;font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint);font-weight:400}}
.k i{{display:block;font-style:normal;font-family:var(--mono);font-size:22px;margin:6px 0 2px}} .k span{{color:var(--dim);font-size:13px;line-height:1.5}}
.bad{{color:var(--red)}} .good{{color:var(--green)}}
.pl{{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:12px 0}} .pk{{font-family:var(--mono);font-size:12px;color:var(--dim);min-width:150px}}
audio{{flex:1;min-width:min(100%,240px);height:38px}}
.scroll{{overflow-x:auto;margin:16px 0}} table{{width:100%;border-collapse:collapse;font-size:14.5px}}
th,td{{text-align:left;padding:10px 12px;border-bottom:1px solid var(--rule);vertical-align:top}}
th{{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--faint);font-weight:400;white-space:nowrap}}
td .s{{color:var(--dim);font-size:13px}}
ol{{margin:0;padding-left:1.3em}} li{{margin-bottom:.5em;max-width:64ch}}
.note{{border-left:2px solid var(--amber);padding:2px 0 2px 14px;color:var(--dim);font-size:14.5px;margin:16px 0;max-width:64ch}}
.warn{{color:var(--red);font-family:var(--mono);font-size:13px}}
a{{color:inherit;border-bottom:1px solid var(--faint);text-decoration:none}} :focus-visible{{outline:2px solid var(--amber);outline-offset:3px}}
svg{{display:block;max-width:100%;height:auto}}
</style>

<header class="w" style="padding-bottom:30px"><div class="eye" style="--acc:var(--faint)">trio77 · D minor · 140 BPM</div>
<h1>노래 파일 점검과 새 버전</h1>
<p class="lead">보내주신 프로젝트 안의 녹음 파일에서 목소리가 나오지 않았습니다. 그래서 목소리·가사·음정 보정은 아직 못 했습니다. 아래에 근거 숫자와, 지금 만든 세 가지 버전을 정리했습니다.</p></header>

<section style="--acc:var(--red)"><div class="w"><div class="eye">1 · 녹음 확인</div>
<h2>MIC 2000(2).flac에는 목소리가 없습니다</h2>
<p>파일을 열어 소리를 쟀습니다. 61.03초 길이인데, 가장 큰 순간이 <b class="bad">−91.7 dBFS</b>입니다. 보통 목소리는 −10~−20 dBFS 근처입니다.</p>
<div class="grid">
<div class="k"><b>최대 음량</b><i class="bad">−91.7 dBFS</i><span>정상 녹음의 1/10,000 수준</span></div>
<div class="k"><b>평균 음량(RMS)</b><i class="bad">−105.6 dB</i><span>전 구간이 거의 같은 값</span></div>
<div class="k"><b>스펙트럼 평탄도</b><i class="bad">0.52</i><span>백색 잡음은 0.5~1, 목소리는 0.05 미만</span></div>
<div class="k"><b>24비트 단계 수</b><i class="bad">410</i><span>음악이면 수만 단계를 씁니다</span></div>
</div>
<p>Studio One이 프로젝트 안에 직접 적어둔 값도 같습니다. 이 클립의 <span class="mono">peak="2.6e-05"</span>이고, 이건 −91.7 dBFS입니다. 소프트웨어가 보기에도 무음입니다.</p>
<div class="note">시간에 따라 크기가 변하지 않고 전부 잡음 모양입니다. 일부러 작게 녹은 목소리가 아니라, 마이크 신호가 들어오지 않은 상태로 녹음된 파일입니다.</div>
<p><b>확인해 볼 것</b></p><ol>
<li>Studio One에서 이 오디오 트랙의 <b>파형이 보이는지</b> 봅니다. 평평한 선이면 같은 문제입니다.</li>
<li><b>입력 채널</b>이 마이크가 꽂힌 입력으로 지정돼 있는지, 트랙의 <b>녹음 대기(R)</b>가 켜져 있는지 봅니다.</li>
<li>오디오 인터페이스의 <b>게인 노브</b>와 마이크 전원(팬텀 +48V가 필요한 마이크인 경우)을 확인합니다.</li>
<li>5초만 말해 보는 <b>테스트 녹음</b>을 하고 파형이 커지는지 봅니다.</li>
<li>예전에 녹음한 다른 파일(<span class="mono">Media</span> 폴더의 <span class="mono">pp1(2).wav</span>, <span class="mono">Light Dropooo.wav</span> 등)이 있으면 그것도 올려주세요.</li></ol>
<p>소리가 있는 파일을 받으면 음정 보정, 풍성한 보컬 처리, 두 번째 마디부터 시작, 가사 추출을 바로 하겠습니다.</p></div></section>

<section style="--acc:var(--green)"><div class="w"><div class="eye">2 · 들어보기</div>
<h2>지금 만든 세 가지 버전</h2>
<p>목소리 없이 만든 것입니다. 셋 다 140 BPM, D minor입니다.</p>
{pl('violin','A · 바이올린 메인 (77초)')}
{pl('cello','B · 첼로 메인 (77초)')}
{pl('user','C · 당신이 넣은 것만 (26초)')}
<div class="scroll"><table><thead><tr><th>버전</th><th>멜로디를 누가</th><th>추가한 것</th></tr></thead><tbody>
<tr><td>A</td><td>솔로 바이올린(스타카토) + 비올라 한 옥타브 아래</td><td>비올라·바이올린·첼로 4분음표 펄스, 호른, 트롬본, 팀파니 등 22블록</td></tr>
<tr><td>B</td><td>첼로(한 옥타브 아래, 스타카토)가 메인, 바이올린은 한 걸음 뒤</td><td>A와 같은 반주</td></tr>
<tr><td>C</td><td>당신 STRING 두 트랙 그대로(바이올린 음색)</td><td><b class="good">없음.</b> 당신이 친 276개 음 전부, 길이도 그대로</td></tr></tbody></table></div>
<div class="note">연장 버전(노래를 반복해서 늘린 것)은 만들지 않았습니다. 목소리가 없는 상태에서는 어색한지 판단할 수 없고, 4화음 루프만 두 배로 늘리면 반복이 지루합니다. 목소리를 받으면 그 위에서 판단하겠습니다.</div></div></section>

<section style="--acc:var(--blue)"><div class="w"><div class="eye">3 · 유통사</div>
<h2>1분 17초는 허용될까</h2>
<p>찾은 자료로는 <b class="good">문제 없어 보입니다.</b> 다만 공식 기준이 아니라 요약·2차 인용이라, 올리는 유통사의 안내 페이지에서 한 번 더 확인하세요.</p>
<div class="scroll"><table><thead><tr><th>유통사</th><th>찾은 기준</th><th>77초는</th></tr></thead><tbody>
<tr><td>RouteNote</td><td>릴리스 전체 최소 30초, 트랙은 3초 이상. 일부만 자른 곡(미리듣기 조각)은 받지 않음</td><td class="good">통과</td></tr>
<tr><td>DistroKid</td><td>트랙 길이 상한은 없고, 앨범은 평균 트랙 길이가 60초 미만이면 거절된다는 2차 인용(싱글 기준은 못 찾음)</td><td class="good">통과(60초 이상)</td></tr>
<tr><td>스트리밍 집계</td><td>30초 이상 들어야 1회로 센다는 2차 설명(공식 확인 못 함)</td><td class="good">해당 없음</td></tr></tbody></table></div>
<p class="mono" style="color:var(--dim);font-size:12.5px">출처: support.routenote.com 「Is there a minimum release/track length?」, 「Can I upload a partial track?」 / Spotify Community 스레드(DistroKid 거절 사례)</p>
<p>짧은 곡은 한 가지만 조심하면 됩니다. 시작이나 끝에 8초 넘는 무음이 있으면 반려되는 경우가 있습니다. 지금 파일은 시작에 무음이 없고, 끝은 짧은 페이드로 끝납니다.</p></div></section>

<section style="--acc:var(--violet)"><div class="w"><div class="eye">4 · 진행 상황</div>
<h2>되는 것과 막힌 것</h2>
<div class="scroll"><table><thead><tr><th>항목</th><th>상태</th><th>이유 / 다음</th></tr></thead><tbody>
<tr><td>첼로 메인 버전</td><td class="good">완료</td><td>위 B</td></tr>
<tr><td>당신이 넣은 것만 버전</td><td class="good">완료</td><td>위 C</td></tr>
<tr><td>원본 아이언맨 대 현재 곡 비교</td><td>에이전트 작업 중</td><td>끝나면 별도 페이지로 드립니다</td></tr>
<tr><td>제출용 작곡 증빙 서류(HTML + MD)</td><td>에이전트 작업 중</td><td>끝나면 별도 페이지로 드립니다</td></tr>
<tr><td>목소리 음정 보정 · 풍성하게 · 두 번째 마디부터</td><td class="bad">막힘</td><td>녹음에 목소리가 없음. 소리 있는 파일 필요</td></tr>
<tr><td>가사(자막) 추출</td><td class="bad">막힘</td><td>같은 이유. 소리가 있어도 한국어 음성 인식 도구를 이 환경에서 받을 수 있는지는 아직 모름</td></tr>
<tr><td>BBC Symphony Orchestra Discover 버전</td><td class="bad">불가</td><td>계정으로 받는 Windows/Mac 설치형 플러그인이고, 저는 Linux에서 돌아갑니다</td></tr>
<tr><td>무료 샘플 악기(VSCO 2 CE)로 렌더</td><td class="bad">권한 거부</td><td>외부 코드를 받아 빌드하는 작업이라 거부됐고, 우회하지 않았습니다</td></tr></tbody></table></div></div></section>
"""
open(OUT, "w", encoding="utf-8").write(PAGE)
print(f"wrote {OUT} {os.path.getsize(OUT)/1e6:.2f} MB, audio {sorted(A)}")
