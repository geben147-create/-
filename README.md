# claude-tools — 영상 분석 · 유튜브 자막 · OCR · 크롤링 · last30days 전역 설치 키트

Claude Code **와** Codex CLI 양쪽에 전역으로 설치됩니다.

```bash
bash setup-global.sh        # macOS / Linux / WSL
.\setup-global.ps1          # Windows PowerShell
```

들어있는 것:

- `youtube-analysis` 스킬 — yt-dlp로 메타데이터 + 크리에이터 자막 + **자동 자막(ko/en/전체)** + 댓글 수집 → 요약
- `video-analysis` 스킬 — ffmpeg 장면 프레임 + faster-whisper 음성 인식(한국어)
- `ocr` 스킬 — Tesseract(kor+eng) 이미지/PDF/프레임 텍스트 추출
- `web-crawl` 스킬 — Playwright MCP · agent-browser · Agent360 browser-mcp · Chrome DevTools MCP · Firecrawl · Brave · crawl4ai 라우팅
- 플러그인: **last30days**, **claude-video-vision**
- MCP: playwright, chrome-devtools, youtube-transcript, browser-mcp, brave-search, firecrawl
- CLI: yt-dlp, ffmpeg, tesseract, faster-whisper, agent-browser, codex

상세 설명·링크·API 키·사용법·대안 → **[SETUP.md](SETUP.md)**
