#!/usr/bin/env python3
"""
검수 자동화 — 가이드 10번(STEP 7) 체크리스트를 실제로 실행한다.

배경 영상 자리에 '순백 영상'을 넣고 돌린다. 스크림이 순백을 견디면
어떤 프레임에서도 글자가 읽힌다 (= 최악 프레임 기준 검사).

  python3 verify/check.py
"""
import json, re, pathlib, subprocess, sys, threading, http.server, socketserver, functools, io
from playwright.sync_api import sync_playwright
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
VER  = ROOT / "verify"
OUT  = VER / "out"; OUT.mkdir(exist_ok=True)
PORT = 8731
# 이 환경에 미리 설치된 크로미움을 그대로 쓴다 (playwright install 금지)
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
ON_VIDEO = (0xF2, 0xF5, 0xF9)          # --on-video

# ---------------------------------------------------------------- 검수용 HTML
def build_page():
    tpl = (ROOT / "index.template.html").read_text(encoding="utf-8")
    sub = {
        "S1_IMG": "media/white.webp", "S1_VID": "media/white.mp4", "S1V_VID": "media/white-v.mp4",
        "S2_IMG": "media/white.webp", "S2_VID": "media/white.mp4",
        "S3_IMG": "media/white.webp", "S3_VID": "media/white.mp4",
        "S4A_IMG": "media/white.webp", "S4A_VID": "media/white.mp4",
        "S4B_IMG": "media/white.webp", "S4B_VID": "media/white.mp4",
        "S4C_IMG": "media/white.webp", "S4C_VID": "media/white.mp4",
    }
    for k, v in sub.items():
        tpl = tpl.replace("{{%s}}" % k, v)
    tpl = tpl.replace('href="assets/css/site.css"', 'href="../assets/css/site.css"')
    tpl = tpl.replace('src="assets/js/site.js"',    'src="../assets/js/site.js"')
    (VER / "index.html").write_text(tpl, encoding="utf-8")

def _stub_fonts(page):
    """이 실행 환경은 fonts.googleapis.com 을 차단한다(egress 정책).
    폰트 네트워크 실패가 콘솔 에러로 잡히면 진짜 에러가 묻히므로 빈 CSS 로 응답시킨다.
    폰트는 시스템 폴백으로 렌더되며, 레이아웃/대비 검사에는 영향이 없다."""
    page.route("**://fonts.googleapis.com/**",
               lambda r: r.fulfill(status=200, content_type="text/css", body=""))
    page.route("**://fonts.gstatic.com/**", lambda r: r.fulfill(status=200, body=""))
    # scroll-behavior:smooth 가 켜져 있으면 측정이 애니메이션 도중 값을 읽는다 → 즉시 스크롤로 고정
    page.add_init_script("""
      document.addEventListener('DOMContentLoaded', () => {
        const st = document.createElement('style');
        st.textContent = 'html{scroll-behavior:auto !important}';
        document.head.appendChild(st);
      });
    """)

# ---------------------------------------------------------------- 대비비 계산
def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def luminance(rgb):
    r, g, b = (_lin(x) for x in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b
def contrast(fg, bg):
    l1, l2 = luminance(fg), luminance(bg)
    lo, hi = sorted((l1, l2))
    return (hi + 0.05) / (lo + 0.05)

def worst_bg_in(img, box, pad=2):
    """box 영역에서 가장 밝은(=최악) 배경 픽셀을 찾는다."""
    x, y, w, h = (int(box["x"]) + pad, int(box["y"]) + pad,
                  max(1, int(box["width"]) - 2 * pad), max(1, int(box["height"]) - 2 * pad))
    x, y = max(0, x), max(0, y)
    crop = img.crop((x, y, min(img.width, x + w), min(img.height, y + h))).convert("RGB")
    px = list(crop.getdata())
    if not px:
        return (0, 0, 0)
    return max(px, key=luminance)

# ---------------------------------------------------------------- 실행
def main():
    build_page()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{PORT}/verify/index.html"

    report = {"console": [], "viewports": [], "contrast": [], "stacking": [], "ancestors": [],
              "sticky": None, "reduced_motion": None, "pass": True}

    def fail(msg):
        report["pass"] = False
        report.setdefault("failures", []).append(msg)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=CHROME,
            args=["--autoplay-policy=no-user-gesture-required"])

        # ---------- 1. 콘솔 에러 + 뷰포트별 오버플로 ----------
        for w, h, label in [(1920,1080,"1920 데스크톱"), (1440,900,"1440 노트북"),
                            (1280,620,"1280 낮은창"), (1024,768,"1024 태블릿"),
                            (768,1024,"768 태블릿세로"), (390,844,"390 아이폰"), (360,740,"360 안드로이드")]:
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
            page = ctx.new_page()
            _stub_fonts(page)
            errs = []
            page.on("console", lambda m: errs.append(f"{m.type}: {m.text}") if m.type == "error" else None)
            page.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
            page.goto(base, wait_until="load")
            page.wait_for_timeout(900)

            over = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            heroh = page.evaluate("document.querySelector('.hero').getBoundingClientRect().height")
            # 히어로 카피가 화면 안에 완전히 들어오는가
            copy_ok = page.evaluate("""() => {
              const c = document.querySelector('.hero__copy .inner');
              if (!c) return false;
              const r = c.getBoundingClientRect();
              return r.top >= -1 && r.bottom <= window.innerHeight + 1 && r.left >= -1;
            }""")
            row = {"viewport": label, "overflow_px": over, "hero_height": round(heroh),
                   "hero_copy_fits": copy_ok, "console_errors": len(errs)}
            report["viewports"].append(row)
            if over > 0: fail(f"{label}: 가로 오버플로 {over}px")
            if errs:
                report["console"].extend([f"[{label}] {e}" for e in errs]); fail(f"{label}: 콘솔 에러 {len(errs)}건")
            if not copy_ok: fail(f"{label}: 히어로 카피가 화면 밖으로 벗어남")

            if label in ("1920 데스크톱", "390 아이폰"):
                page.screenshot(path=str(OUT / f"hero-{w}.png"))
            ctx.close()

        # ---------- 2. 최악 프레임 대비비 (순백 배경) ----------
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page(); _stub_fonts(page)
        page.goto(base, wait_until="load"); page.wait_for_timeout(1200)

        # 영상 위에 얹히는 텍스트 전부. 대형 헤드라인 3:1, 본문/라벨 4.5:1.
        targets = [(".hero h1", "히어로 헤드라인", 3.0),
                   (".hero__lede", "히어로 리드문", 4.5),
                   (".hero .eyebrow", "히어로 아이브로우", 4.5),
                   (".hero__meta b", "히어로 수치", 3.0),
                   (".vsec h2", "S2 헤드라인", 3.0),
                   (".vsec__body", "S2 본문", 4.5),
                   (".pains li", "S2 리스트", 4.5),
                   (".scrub__copy h2", "스크럽 헤드라인", 3.0),
                   (".scrub__copy p", "스크럽 본문", 4.5),
                   (".card h3", "카드 제목", 3.0),
                   (".card p", "카드 본문", 4.5),
                   (".card li", "카드 리스트", 4.5),
                   (".cta h2", "CTA 헤드라인", 3.0),
                   (".cta__lede", "CTA 리드문", 4.5),
                   (".price b", "CTA 가격", 3.0)]

        HIDE = ("h1,h2,h3,h4,p,li,span,b,s,em,i,a,div.stat,.eyebrow"
                "{color:transparent !important;-webkit-text-fill-color:transparent !important}")

        for sel, name, need in targets:
            el = page.query_selector(sel)
            if not el:
                continue
            el.scroll_into_view_if_needed()
            page.wait_for_timeout(450)
            b = el.bounding_box()
            if not b or b["width"] < 2 or b["height"] < 2:
                continue
            # ::before 로 그린 액센트 불릿은 텍스트가 아니라 장식이다.
            # padding-left 만큼 잘라내야 '글자 뒤 배경'만 측정된다.
            pl = page.evaluate("el => parseFloat(getComputedStyle(el).paddingLeft) || 0", el)
            if pl > 0:
                b = {"x": b["x"] + pl, "y": b["y"], "width": max(2, b["width"] - pl), "height": b["height"]}
            # 글자만 투명하게 만들어 '그 자리의 배경'을 촬영
            tag = page.add_style_tag(content=HIDE)
            page.wait_for_timeout(220)
            shot = Image.open(io.BytesIO(page.screenshot()))
            page.evaluate("el => el.remove()", tag)
            bg = worst_bg_in(shot, b)
            cr = contrast(ON_VIDEO, bg)
            ok = cr >= need
            report["contrast"].append({"element": name, "selector": sel,
                                       "worst_bg": "#%02X%02X%02X" % bg,
                                       "ratio": round(cr, 2), "required": need, "pass": ok})
            if not ok: fail(f"대비 미달: {name} {cr:.2f}:1 < {need}:1 (최악 배경 #%02X%02X%02X)" % bg)
        ctx.close()

        # ---------- 3. 스택 컨텍스트 / 조상 transform ----------
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page(); _stub_fonts(page)
        page.goto(base, wait_until="load"); page.wait_for_timeout(800)

        # 텍스트 지점에서 elementFromPoint 가 영상이 아니라 텍스트를 반환해야 한다
        hit = page.evaluate("""() => {
          const out = [];
          for (const sel of ['.hero h1', '.hero__lede', '.card h3', '.scrub__copy h2']) {
            const el = document.querySelector(sel);
            if (!el) { out.push({sel, ok:false, reason:'없음'}); continue; }
            el.scrollIntoView({block:'center', behavior:'instant'});
            const r = el.getBoundingClientRect();
            const top = document.elementFromPoint(r.left + Math.min(8, r.width/2), r.top + r.height/2);
            const isText = el.contains(top) || top === el;
            out.push({sel, ok:isText, hit: top ? top.className || top.tagName : 'null'});
          }
          return out;
        }""")
        report["stacking"] = hit
        for h in hit:
            if not h["ok"]: fail(f"스택 사고: {h['sel']} 위를 {h['hit']} 가 덮고 있음")

        # .hero 조상에 transform/filter/opacity 가 없는지
        anc = page.evaluate("""() => {
          const bad = [];
          document.querySelectorAll('.hero, .vsec, .scrub, .card').forEach(node => {
            let p = node.parentElement;
            while (p && p !== document.documentElement) {
              const s = getComputedStyle(p);
              if (s.transform !== 'none' || s.filter !== 'none' ||
                  (parseFloat(s.opacity) < 1) || s.perspective !== 'none') {
                bad.push({el: node.className, ancestor: p.tagName + '.' + p.className,
                          transform: s.transform, filter: s.filter, opacity: s.opacity});
              }
              p = p.parentElement;
            }
          });
          return bad;
        }""")
        report["ancestors"] = anc
        if anc: fail(f"조상에 stacking context 생성 속성 발견 ({len(anc)}건) — fixed/핀이 깨진다")

        # ---------- 4. 스크럽 핀이 실제로 붙어 있는가 ----------
        sticky = page.evaluate("""async () => {
          const sec = document.querySelector('[data-scrub]');
          const stage = sec.querySelector('.scrub__stage');
          const startY = sec.offsetTop;
          // sticky 유효 구간: 섹션 상단이 뷰포트 top 에 닿는 순간부터
          //                  섹션 하단 - 스테이지 높이 까지.
          const span = sec.offsetHeight - stage.offsetHeight;
          const tops = [];
          for (const frac of [0.05, 0.3, 0.6, 0.9]) {
            window.scrollTo({top: startY + span * frac, behavior: 'instant'});
            await new Promise(r => setTimeout(r, 340));
            tops.push(Math.round(stage.getBoundingClientRect().top));
          }
          return {tops, position: getComputedStyle(stage).position,
                  span: Math.round(span), stageH: stage.offsetHeight};
        }""")
        report["sticky"] = sticky
        if sticky["position"] != "sticky": fail("스크럽 스테이지가 sticky 가 아님 — 핀이 안 걸린다")
        if max(abs(t) for t in sticky["tops"]) > 4:
            fail(f"핀이 미끄러짐: stage top = {sticky['tops']}")
        ctx.close()

        # ---------- 5. 동작 줄이기 ----------
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        page = ctx.new_page(); _stub_fonts(page)
        page.goto(base, wait_until="load"); page.wait_for_timeout(700)
        rm = page.evaluate("""() => {
          const vids = [...document.querySelectorAll('video')];
          return {playing_videos: vids.filter(x => !x.paused).length,
                  lazy_src_attached: vids.filter(x => x.dataset.src && x.src).length,
                  hero_has_poster: !!document.querySelector('.hero__bg').poster};
        }""")
        report["reduced_motion"] = rm
        if rm["playing_videos"] != 0: fail(f"동작 줄이기에서 {rm['playing_videos']}개 영상이 재생 중")
        if rm["lazy_src_attached"] != 0: fail("동작 줄이기인데 지연 로딩 영상이 네트워크를 씀")
        if not rm["hero_has_poster"]: fail("동작 줄이기: 히어로에 poster 가 없어 빈 화면이 된다")
        ctx.close()
        browser.close()
    srv.shutdown()

    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------ 출력
    print("\n" + "=" * 68)
    print("  검수 리포트 — 최악 프레임(순백 영상) 기준")
    print("=" * 68)
    print("\n[ 뷰포트 ]")
    for v in report["viewports"]:
        mark = "OK " if v["overflow_px"] <= 0 and v["hero_copy_fits"] and v["console_errors"] == 0 else "!! "
        print(f"  {mark}{v['viewport']:<16} 오버플로 {v['overflow_px']:>3}px · 히어로 {v['hero_height']:>4}px"
              f" · 카피 {'들어감' if v['hero_copy_fits'] else '벗어남'} · 콘솔 {v['console_errors']}")
    print("\n[ 대비비 · 순백 프레임 위 ]")
    for c in report["contrast"]:
        print(f"  {'OK ' if c['pass'] else '!! '}{c['element']:<14} {c['ratio']:>6.2f} : 1   "
              f"(기준 {c['required']}:1, 최악 배경 {c['worst_bg']})")
    print("\n[ 스택 컨텍스트 ]")
    for h in report["stacking"]:
        print(f"  {'OK ' if h['ok'] else '!! '}{h['sel']:<18} → {h.get('hit')}")
    print(f"  {'OK ' if not report['ancestors'] else '!! '}조상 transform/filter/opacity: {len(report['ancestors'])}건")
    print("\n[ 스크럽 핀 ]")
    s = report["sticky"]
    print(f"  {'OK ' if s['position']=='sticky' and max(abs(t) for t in s['tops'])<=4 else '!! '}"
          f"position={s['position']}, 유효구간 {s['span']}px 안에서 stage top = {s['tops']}")
    print("\n[ 동작 줄이기 ]")
    r = report["reduced_motion"]
    print(f"  {'OK ' if r['playing_videos']==0 and r['lazy_src_attached']==0 and r['hero_has_poster'] else '!! '}"
          f"재생 중 {r['playing_videos']}개 · 지연로딩 src 부착 {r['lazy_src_attached']}개 · "
          f"히어로 poster {'있음' if r['hero_has_poster'] else '없음'}")
    print("\n" + "=" * 68)
    if report["pass"]:
        print("  전체 통과")
    else:
        print("  실패:")
        for f in report.get("failures", []): print("   ·", f)
    print("=" * 68 + "\n")
    return 0 if report["pass"] else 1

if __name__ == "__main__":
    sys.exit(main())
