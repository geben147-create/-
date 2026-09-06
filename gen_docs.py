#!/usr/bin/env python3
"""pipeline.template.html 의 {{SHOTCARDS}} / {{RECEIPTS}} 를 manifest.json 으로 채운다."""
import json, pathlib, html

ROOT = pathlib.Path(__file__).parent
man = json.loads((ROOT / "media" / "manifest.json").read_text(encoding="utf-8"))

# ---------------------------------------------------------------- 샷 카드
cards = []
for key, s in man["shots"].items():
    scrub = s.get("mode") == "scrub"
    tags = [f'<span class="tag tag--id">{html.escape(s["id"])}</span>']
    tags.append(f'<span class="tag tag--{"scrub" if scrub else "loop"}">{"스크럽 + 핀" if scrub else "루프"}</span>')
    tags.append(f'<span class="tag">{html.escape(s["ratio"])}</span>')
    tags.append(f'<span class="tag">{html.escape(s["duration"])}</span>')

    links = []
    if s.get("img"):
        links.append(f'<a href="{html.escape(s["img"])}" target="_blank" rel="noopener">첫 프레임 ↗</a>')
    if s.get("vid"):
        links.append(f'<a href="{html.escape(s["vid"])}" target="_blank" rel="noopener">생성 영상 ↗</a>')

    prompts = ""
    if s.get("img_prompt") or s.get("vid_prompt"):
        blocks = []
        if s.get("img_prompt"):
            blocks.append("[첫 프레임 · %s]\n%s" % (man["models"]["image"], s["img_prompt"]))
        if s.get("vid_prompt"):
            blocks.append("[모션 · %s]\n%s" % (man["models"]["video"], s["vid_prompt"]))
        prompts = ('<details><summary>실제 사용한 프롬프트 펼치기</summary><pre>'
                   + html.escape("\n\n".join(blocks)) + '</pre></details>')

    cards.append(
        '<div class="shot">'
        f'<div class="shot__h">{"".join(tags)}</div>'
        f'<h4>{html.escape(s["title"])}</h4>'
        f'<p>{html.escape(s["intent"])}</p>'
        + (f'<div class="plink">{"".join(links)}</div>' if links else "")
        + prompts +
        '</div>'
    )
shotcards = "\n".join(cards)

# ---------------------------------------------------------------- 실제 수치
c = man["credits"]
n_img, n_vid = c["image_count"], c["video_count"]
receipts = f'''
<div class="tablewrap">
  <table>
    <thead><tr><th>단계</th><th>도구 / 모델</th><th>건수</th><th>크레딧</th></tr></thead>
    <tbody>
      <tr><td>첫 프레임 이미지</td><td><code>{html.escape(man["models"]["image"])}</code> · 2K</td>
          <td>{n_img}</td><td class="ok"><b>0</b> <span class="dim">(Ultra 무제한)</span></td></tr>
      <tr><td>배경 영상</td><td><code>{html.escape(man["models"]["video"])}</code> · pro · 5s</td>
          <td>{n_vid}</td><td><b>{c["per_video"]} × {n_vid} = {c["video_total"]}</b></td></tr>
      <tr><td>웹 인코딩</td><td><code>ffmpeg</code> (libx264 / libvpx-vp9 / libwebp)</td>
          <td>—</td><td class="ok"><b>0</b></td></tr>
      <tr><td>웹 조립</td><td>순수 HTML / CSS / JS <span class="dim">(외부 라이브러리 0개)</span></td>
          <td>—</td><td class="ok"><b>0</b></td></tr>
      <tr><td colspan="3"><b>합계</b></td><td><b>{c["video_total"]} 크레딧</b></td></tr>
    </tbody>
  </table>
</div>
<div class="note">
  <b>추가 결제 없음.</b> 이미지는 무제한 플랜이라 0크레딧, 영상만 기존 잔액
  ({c["balance_before"]:,} 크레딧)에서 <b>{c["video_total"]}</b> 크레딧이 차감됐다
  — 잔액의 약 {c["video_total"]/c["balance_before"]*100:.1f}%.
</div>

<h3>왜 이 모델들인가</h3>
<div class="tablewrap">
  <table>
    <thead><tr><th>목적</th><th>선택</th><th>이유</th></tr></thead>
    <tbody>
      <tr><td>첫 프레임 (구도 확정)</td><td><code>google / nano-banana-pro</code></td>
          <td>프롬프트 순응도가 높아 &ldquo;중앙 26% 안에 배치, 좌우는 어둡게 비움&rdquo; 같은 <b>세이프존 지시가 실제로 먹힌다.</b> 조명·질감도 안정적.</td></tr>
      <tr><td>루프 배경</td><td><code>kling-ai / kling-v2-5-turbo</code> <span class="dim">pro</span></td>
          <td><b><code>imageTail</code>(끝 프레임)을 받는다.</b> 시작·끝에 같은 이미지를 넣으면 루프가 자연스럽게 닫혀 이음매가 안 보인다. 이게 결정적 이유.</td></tr>
      <tr><td>톤 통일</td><td>프롬프트 HEX 고정</td>
          <td>6샷 전부에 <code>#080A0E</code> / <code>#E8A33D</code> 를 명시. 샷마다 따로 생성해도 같은 세트로 보인다.</td></tr>
    </tbody>
  </table>
</div>

<h3>이 환경에서 실행하지 못한 단계</h3>
<div class="note blocked">
  <b>STEP 4 (웹 인코딩) 은 로컬에서 실행해야 한다.</b>
  이 저장소를 만든 실행 환경은 조직 egress 정책이 <code>videocdn.pollo.ai</code> 를 차단한다
  (<code>403 CONNECT</code>). 생성은 MCP 채널로 정상 수행됐지만 <b>결과물 바이트를 컨테이너로 내려받을 수 없어</b>
  ffmpeg 인코딩·포스터 추출·용량 측정을 대신 수행하지 못했다. 정책을 우회하지 않고 그대로 남겨 둔다.<br><br>
  <b>해결:</b> 네트워크가 열린 로컬에서 <code>./build.sh</code> 한 번.
  다운로드 → 인코딩 → <code>index.html</code> 을 자체 호스팅 모드로 재생성까지 자동으로 끝난다.
  그때까지 <code>index.html</code> 은 Pollo CDN URL 을 직접 참조하므로 <b>지금 그대로도 재생된다.</b>
</div>

<h3>남은 검수 — 눈으로 봐야 하는 것</h3>
<div class="note warn">
  같은 이유로 <b>생성된 프레임을 직접 열어보는 시각 검수(07번 체크리스트)를 수행하지 못했다.</b>
  프롬프트 차원의 세이프존·어두운 톤 강제는 전부 걸어 두었지만,
  실제로 <b>390px 폭에서 피사체가 살아 있는지</b>와 <b>가장 밝은 프레임에서 글자가 읽히는지</b>는
  브라우저에서 한 번 확인해야 한다. 어긋나는 샷이 있으면 해당 샷만 다시 생성하면 된다
  (첫 프레임 재생성은 0크레딧).
</div>
'''

tpl = (ROOT / "pipeline.template.html").read_text(encoding="utf-8")
out = tpl.replace("{{SHOTCARDS}}", shotcards).replace("{{RECEIPTS}}", receipts)
(ROOT / "pipeline.html").write_text(out, encoding="utf-8")
print(f"pipeline.html rendered — {len(man['shots'])} shot cards")
