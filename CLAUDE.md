# Project: 영상 분석 · 크롤링 · 리서치 도구 세트

Everything here is tooling for analyzing videos (YouTube + local), OCR, web crawling / browser automation,
and 30-day topic research. Read `SETUP.md` for the full map.

## When the user asks to…
- analyze / summarize a **YouTube URL** → use the `youtube-analysis` skill (`.claude/skills/youtube-analysis`). It pulls creator + auto captions via yt-dlp. Never say captions are unavailable before running the script.
- analyze a **local video** or a video with no captions → `video-analysis` skill (frames + faster-whisper), or `/watch-video` from the claude-video-vision plugin.
- read text from **images / screenshots / PDFs / frames** → `ocr` skill (Tesseract kor+eng), then verify visually with the Read tool.
- **crawl / scrape / browse / research** → `web-crawl` skill decides between Playwright MCP, agent-browser, Agent360 browser-mcp, Firecrawl, Brave, and `/last30days`.
- know **what people are saying about a topic recently** → `/last30days <topic>`.

## Conventions
- Save outputs under `yt-analysis/`, `video-analysis/`, `crawl/` (git-ignored). Reports are Markdown with timestamps.
- Install / update tooling only through `setup-global.sh` (or `setup-global.ps1`) so the global install stays reproducible.
- API keys live in `~/.config/last30days/.env`; never commit them.
