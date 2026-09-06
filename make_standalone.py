#!/usr/bin/env python3
"""
dist/index.standalone.html — CSS/JS 를 인라인한 단일 파일 랜딩 페이지.
저장소 없이 파일 하나만 열어도 그대로 동작한다 (영상은 Pollo CDN 참조).

  python3 make_standalone.py
"""
import pathlib, re, json

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "dist"; DIST.mkdir(exist_ok=True)

html = (ROOT / "index.html").read_text(encoding="utf-8")
css  = (ROOT / "assets/css/site.css").read_text(encoding="utf-8")
js   = (ROOT / "assets/js/site.js").read_text(encoding="utf-8")

# 동작 줄이기 규칙이 참조하던 상대경로는 인라인 후 의미가 없다 (이미 제거된 상태)
html = html.replace('<link rel="stylesheet" href="assets/css/site.css">',
                    "<style>\n" + css + "\n</style>")
html = html.replace('<script src="assets/js/site.js"></script>',
                    "<script>\n" + js + "\n</script>")
# 파이프라인 문서 링크는 단일 파일에서는 저장소 안내로 대체
html = html.replace('href="pipeline.html"', 'href="https://github.com/geben147-create/-/blob/claude/cinematic-scroll-pipeline-ajcxs8/pipeline.html"')

out = DIST / "index.standalone.html"
out.write_text(html, encoding="utf-8")
kb = out.stat().st_size / 1024
print(f"dist/index.standalone.html — {kb:.1f} KB (CSS/JS 인라인, 영상은 CDN 참조)")
