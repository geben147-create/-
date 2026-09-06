---
name: web-crawl
description: Pick the right web crawling / browsing / research tool for the job and use it. Use when the user says "크롤링", "스크래핑", "웹 조사", "브라우저로 열어", "사이트 데이터 뽑아", "리서치", "요즘 뭐라 하는지", "최근 30일", "browse", "scrape", "crawl", "research this topic". Routes to Playwright MCP, agent-browser, Chrome DevTools MCP, Agent360 browser-mcp (logged-in Chrome), Firecrawl, Brave Search, or the last30days plugin.
---

# Web crawl / browse / research router

| Need | Use | How |
|---|---|---|
| Quick facts, recent news | Built-in `WebSearch` / `WebFetch`; Brave Search MCP if key set | `brave_web_search` tool |
| "What are people saying about X in the last 30 days" (Reddit, X, YouTube, HN, TikTok...) | **last30days plugin** | `/last30days <topic>` (`--discover`, `--deep`, `--youtube` flags) |
| Read one page cleanly (JS-rendered, paywall-ish) | Firecrawl MCP (`firecrawl_scrape`), or Playwright `browser_navigate` + `browser_snapshot` | needs `FIRECRAWL_API_KEY` for Firecrawl |
| Crawl a whole site / many URLs → markdown | Firecrawl `firecrawl_crawl` / `firecrawl_map`; free alternative `pip install crawl4ai` then `crwl <url> -o markdown` | |
| Click, fill forms, log in, screenshot, test a web app | **Playwright MCP** (`browser_*` tools) or **agent-browser** CLI (`agent-browser open <url>` → `snapshot -i` → `click @e3`) | headless Chromium |
| Use the user's REAL logged-in Chrome (cookies, 2FA, CAPTCHA, internal dashboards) | **Agent360 browser-mcp** (`@agent360/browser-mcp` + Chrome extension) or Claude Code's own `claude --chrome` / `/chrome` | user must have the extension installed |
| Debug performance/network/console of a page | **Chrome DevTools MCP** (`chrome-devtools-mcp`) | |
| YouTube-specific | `youtube-analysis` skill (yt-dlp) or `youtube-transcript` MCP | |

## Rules
1. Prefer the lightest tool that works: WebFetch → Firecrawl scrape → Playwright → real Chrome.
2. Respect robots/ToS; throttle bulk crawls (≥1 s between requests) and cache results under `./crawl/<domain>/`.
3. Save raw pages as markdown/JSON before summarizing so the user can verify.
4. For Korean sites (Naver, Daum, 커뮤니티) use Playwright with `browser_snapshot` (accessibility tree) rather than screenshots to save tokens.
5. agent-browser quick reference:
   ```bash
   agent-browser open https://example.com
   agent-browser snapshot -i          # interactive elements with @eN refs
   agent-browser click @e2 ; agent-browser fill @e3 "text"
   agent-browser screenshot out.png ; agent-browser get text body ; agent-browser close
   ```
