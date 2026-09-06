#!/usr/bin/env python3
"""
index.template.html 의 {{TOKEN}} 을 실제 미디어 경로로 치환해 index.html 을 만든다.

  python3 render.py remote   # Pollo CDN URL 을 그대로 사용 (기본값, 즉시 동작)
  python3 render.py local    # build.sh 로 인코딩한 media/ 로컬 파일 사용

remote 모드는 지금 바로 열어볼 수 있고, local 모드는 build.sh 를 돌린 뒤
자체 호스팅(용량·캐시·오프라인 제어)으로 전환할 때 쓴다.
"""
import json, sys, pathlib

ROOT = pathlib.Path(__file__).parent
mode = (sys.argv[1] if len(sys.argv) > 1 else "remote").lower()
if mode not in ("remote", "local"):
    sys.exit("usage: render.py [remote|local]")

man = json.loads((ROOT / "media" / "manifest.json").read_text(encoding="utf-8"))

# 토큰 → (shot key, 종류)
TOKENS = {
    "S1_IMG":  ("s1_hero",    "img"), "S1_VID":  ("s1_hero",    "vid"),
    "S1V_VID": ("s1_hero_v",  "vid"),
    "S2_IMG":  ("s2_problem", "img"), "S2_VID":  ("s2_problem", "vid"),
    "S3_IMG":  ("s3_solve",   "img"), "S3_VID":  ("s3_solve",   "vid"),
    "S4A_IMG": ("s4a_brand",  "img"), "S4A_VID": ("s4a_brand",  "vid"),
    "S4B_IMG": ("s4b_char",   "img"), "S4B_VID": ("s4b_char",   "vid"),
    "S4C_IMG": ("s4c_vfx",    "img"), "S4C_VID": ("s4c_vfx",    "vid"),
}

# local 모드에서 쓰는 파일 이름 (build.sh 출력과 1:1)
LOCAL = {
    ("s1_hero", "img"): "media/s1-hero-poster.webp",
    ("s1_hero", "vid"): "media/s1-hero-1920.mp4",
    ("s1_hero_v", "vid"): "media/s1-hero-1080v.mp4",
    ("s2_problem", "img"): "media/s2-problem-poster.webp",
    ("s2_problem", "vid"): "media/s2-problem-1920.mp4",
    ("s3_solve", "img"): "media/s3-solve-poster.webp",
    ("s3_solve", "vid"): "media/s3-solve-scrub.mp4",
    ("s4a_brand", "img"): "media/s4a-brand-poster.webp",
    ("s4a_brand", "vid"): "media/s4a-brand-1280.mp4",
    ("s4b_char", "img"): "media/s4b-char-poster.webp",
    ("s4b_char", "vid"): "media/s4b-char-1280.mp4",
    ("s4c_vfx", "img"): "media/s4c-vfx-poster.webp",
    ("s4c_vfx", "vid"): "media/s4c-vfx-1280.mp4",
}

html = (ROOT / "index.template.html").read_text(encoding="utf-8")
missing = []
for token, (key, kind) in TOKENS.items():
    if mode == "remote":
        val = (man["shots"].get(key) or {}).get(kind) or ""
    else:
        val = LOCAL[(key, kind)]
    if not val:
        missing.append(token)
    html = html.replace("{{%s}}" % token, val)

(ROOT / "index.html").write_text(html, encoding="utf-8")
print(f"index.html rendered [{mode}]" + (f" — 비어 있는 토큰: {', '.join(missing)}" if missing else ""))
