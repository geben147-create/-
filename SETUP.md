# 영상 분석 · 크롤링 · 리서치 올인원 설치 가이드 (Claude Code + Codex, 전역)

이 저장소는 **Claude Code와 Codex CLI 양쪽에 전역(global)으로** 아래 도구를 깔아주는 설치 스크립트와 스킬 모음입니다.

| 분류 | 도구 | 무엇을 해주나 | 키 필요? |
|---|---|---|---|
| YouTube | **yt-dlp** + `youtube-analysis` 스킬 | 메타데이터 · 크리에이터 자막 · **자동생성 자막(ko/en/전체)** · 댓글 · 오디오/영상 다운로드 → 요약/분석 | 없음 |
| YouTube | `youtube-transcript` MCP | URL만 주면 트랜스크립트 바로 가져오기 | 없음 |
| 영상 | `video-analysis` 스킬 (ffmpeg + faster-whisper) | 장면 전환 프레임 추출 → Claude 비전으로 보기, 음성 → 텍스트(한국어 OK) | 없음 |
| 영상 | **claude-video-vision** 플러그인 | `/watch-video 파일 "질문"` 한 방에 프레임+오디오 분석 | Gemini 키(무료) 선택 |
| 영상 | `video-frames` 스킬 | 장면 감지 · OCR 프리셋 · 토큰 추정 프레임 추출 | 없음 |
| OCR | **Tesseract**(kor+eng) + `ocr` 스킬 | 이미지/스크린샷/PDF/프레임 글자 추출 | 없음 |
| 리서치 | **last30days** 플러그인 | 최근 30일간 Reddit·X·YouTube·HN·TikTok·GitHub·웹에서 뭐라 하는지 종합 | 대부분 무료, 일부 선택 |
| 검색 | Brave Search MCP | 웹 검색 (last30days도 사용) | 무료 티어 키 |
| 크롤링 | Firecrawl MCP | JS 렌더링 페이지 스크레이핑 · 사이트 전체 크롤 → 마크다운 | 무료 크레딧 키 |
| 크롤링 | crawl4ai | 완전 무료 로컬 크롤러 (`crwl <url> -o markdown`) | 없음 |
| 브라우저 | **Playwright MCP** | 헤드리스 크롬 조작(클릭·입력·스크린샷·스냅샷) | 없음 |
| 브라우저 | **agent-browser** (Vercel) | CLI형 브라우저 에이전트, Claude/Codex 둘 다 스킬 제공 | 없음 |
| 브라우저 | **Agent360 Browser MCP** | **내 실제 로그인된 크롬**을 조작 (2FA·CAPTCHA·내부 대시보드) | 크롬 확장 |
| 브라우저 | Chrome DevTools MCP | 네트워크·콘솔·퍼포먼스 디버깅 | 없음 |
| 브라우저 | Claude in Chrome (`claude --chrome`) | Claude Code 공식 크롬 제어 | 크롬 확장 |
| 코딩 에이전트 | **Codex CLI** | OpenAI 에이전트, 같은 스킬(`~/.codex/skills`) 사용 | ChatGPT 로그인 |

---

## 1. 설치 (한 번만)

```bash
git clone https://github.com/geben147-create/-.git claude-tools && cd claude-tools
bash setup-global.sh          # macOS / Linux / WSL
```
```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force; .\setup-global.ps1   # Windows
```

스크립트는 다시 실행해도 안전하며, 마지막에 **설치됨 / 건너뜀 / 실패** 목록을 출력합니다.
실패 항목 옆에 적힌 수동 명령을 그대로 실행하면 됩니다.

### 전역이란 정확히 어디에 깔리나

| 항목 | 위치 | 확인 명령 |
|---|---|---|
| MCP 서버 (user scope) | `~/.claude.json` | `claude mcp list` |
| 플러그인 (user scope) | `~/.claude/settings.json` → `enabledPlugins`, 캐시 `~/.claude/plugins/cache` | `claude plugin list` |
| Claude 스킬 | `~/.claude/skills/<이름>/SKILL.md` | Claude Code 안에서 `/skills` |
| Codex 스킬 | `~/.codex/skills/<이름>/SKILL.md` | Codex 안에서 `/skills` |
| API 키 | `~/.config/last30days/.env` (+ 셸 프로필 `export`) | |

이 저장소를 열었을 때만 쓰이는 **프로젝트 범위** 설정(`.mcp.json`, `.claude/settings.json`, `.claude/skills/`)도 같이 들어 있어, 전역 설치를 안 해도 이 폴더에서는 전부 동작합니다.

---

## 2. 수동 설치 명령 (스크립트가 하는 일 그대로)

### 시스템 도구
```bash
# macOS
brew install ffmpeg tesseract tesseract-lang poppler node
# Ubuntu/Debian/WSL
sudo apt install -y ffmpeg tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng poppler-utils nodejs npm
# Windows
winget install Gyan.FFmpeg UB-Mannheim.TesseractOCR OpenJS.NodeJS.LTS Python.Python.3.12
```

### Python
```bash
pip install -U yt-dlp youtube-transcript-api faster-whisper pytesseract pillow crawl4ai
```

### Node CLI
```bash
npm i -g @anthropic-ai/claude-code @openai/codex agent-browser
agent-browser install            # Linux는 --with-deps
npx playwright install chromium
```

### Claude Code 전역 MCP
```bash
claude mcp add --scope user playwright         -- npx -y @playwright/mcp@latest
claude mcp add --scope user chrome-devtools    -- npx -y chrome-devtools-mcp@latest
claude mcp add --scope user youtube-transcript -- npx -y @fabriqa.ai/youtube-transcript-mcp@latest
claude mcp add --scope user browser-mcp        -- npx -y @agent360/browser-mcp@latest
claude mcp add --scope user brave-search -e BRAVE_API_KEY=여기키 -- npx -y @brave/brave-search-mcp-server
claude mcp add --scope user firecrawl    -e FIRECRAWL_API_KEY=여기키 -- npx -y firecrawl-mcp
```

### 플러그인 (전역 = `--scope user`, 기본값)
```bash
claude plugin marketplace add mvanhorn/last30days-skill
claude plugin install last30days@last30days-skill
claude plugin marketplace add jordanrendric/claude-video-vision
claude plugin install claude-video-vision@claude-video-vision
```

### 스킬 (Claude + Codex 동시, 전역)
```bash
npx skills add mvanhorn/last30days-skill      -g -a claude-code codex -y --copy
npx skills add vercel-labs/agent-browser      -g -a claude-code codex -y --copy
npx skills add mugnimaestra/video-frames-skill -g -a claude-code codex -y --copy
cp -R .claude/skills/{youtube-analysis,video-analysis,ocr,web-crawl} ~/.claude/skills/
cp -R .claude/skills/{youtube-analysis,video-analysis,ocr,web-crawl} ~/.codex/skills/
```
주의: `-a` 뒤 에이전트는 **공백**으로 구분합니다 (`claude-code,codex` 처럼 콤마로 쓰면 "Invalid agents" 오류).

---

## 3. 크롬 확장 (링크)

- Agent360 Browser MCP: <https://chromewebstore.google.com/detail/agent360-browser-mcp/jdehgalffmffhfhmmhaokfbfnafnmgcl>
- Claude in Chrome (Claude Code `--chrome`): 문서 <https://code.claude.com/docs/en/chrome> (확장 설치 링크와 `/chrome` 설정 방법 포함)

## 4. API 키 (전부 선택, 링크)

| 키 | 발급 | 용도 |
|---|---|---|
| `BRAVE_API_KEY` | <https://brave.com/search/api/> (무료 2,000회/월) | Brave Search MCP, last30days 웹검색 |
| `FIRECRAWL_API_KEY` | <https://www.firecrawl.dev/app/api-keys> | Firecrawl 크롤링 |
| `GEMINI_API_KEY` | <https://aistudio.google.com/apikey> | claude-video-vision 오디오 백엔드 |
| `PERPLEXITY_API_KEY` | <https://www.perplexity.ai/settings/api> | last30days 심층 검색 |
| `SCRAPECREATORS_API_KEY` | <https://scrapecreators.com> | last30days TikTok/Instagram/Threads |
| `YOUTUBE_API_KEY` | <https://console.cloud.google.com/apis/credentials> | (선택) 채널 통계·댓글 대량 수집 |

파일: `~/.config/last30days/.env` (스크립트가 `.env.example`을 복사해 둡니다).

---

## 5. 사용법

```text
# YouTube (자막 자동 수집 → 요약)
이 영상 분석해줘 https://www.youtube.com/watch?v=XXXX            ← youtube-analysis 스킬 자동 발동
python3 ~/.claude/skills/youtube-analysis/scripts/yt_subs.py URL --langs ko,en --comments 30

# 자막 없는 영상 → 음성 인식
python3 ~/.claude/skills/youtube-analysis/scripts/yt_subs.py URL --audio
python3 ~/.claude/skills/video-analysis/scripts/transcribe.py yt-analysis/<id>/audio.m4a --lang ko

# 로컬 영상 (프레임 + 음성 + OCR)
/watch-video ./lecture.mp4 "핵심 정리해줘"
bash ~/.claude/skills/video-analysis/scripts/extract_frames.sh lecture.mp4 24 scene
python3 ~/.claude/skills/ocr/scripts/ocr.py "video-analysis/lecture/frames/*.jpg" --lang kor+eng

# 리서치
/last30days 클로드 코드 스킬 트렌드
/last30days --discover "AI 영상 분석"

# 브라우저 / 크롤링
"네이버에서 OOO 검색해서 상위 10개 제목 뽑아줘"     ← Playwright MCP
agent-browser open https://site.com && agent-browser snapshot -i
claude --chrome                                     ← 내 크롬으로
```

YouTube가 "Sign in to confirm you're not a bot"을 띄우면
`--cookies-from-browser chrome` 옵션을 붙이세요.

---

## 6. 더 좋은 대안 / 추천

- **Gemini 영상 이해** — 영상을 다운로드하지 않고 URL 그대로 요약·프레임 캡처: `yt-analysis` MCP (Gemini 키 필요). 긴 강의 영상엔 가장 빠릅니다.
- **한국어 OCR 정확도**가 중요하면 Tesseract 대신 `pip install paddleocr` (PP-OCRv4) 또는 `easyocr`.
- **음성 인식 정확도**: `transcribe.py --model large-v3` (GPU 권장). CPU면 `medium`.
- **YouTube 채널 단위 분석**(구독자·인기도·댓글 대량): [claude-code-youtube-mcp](https://github.com/wynandw87/claude-code-youtube-mcp) (YouTube Data API 키).
- **유료 크롤링 API**: claude.ai 플러그인 카탈로그의 **Browser Use**, **Tavily**, **Bright Data**, **Nimble** 도 `/plugin`에서 설치 가능. 봇 차단이 심한 사이트는 Bright Data가 가장 강함.
- **완전 무료 크롤러**: crawl4ai (`crwl URL -o markdown`), 스크립트가 설치합니다.

## 7. 문제 해결

| 증상 | 해결 |
|---|---|
| `Invalid agents: claude-code,codex` | `-a claude-code codex` (공백 구분) |
| `/plugin` 안 보임 | `npm i -g @anthropic-ai/claude-code@latest` 후 재시작 |
| 스킬이 안 뜸 | Claude Code에서 `/reload-skills` 또는 재시작. 플러그인은 `/reload-plugins` |
| MCP 서버 연결 실패 | `claude mcp get <이름>` 으로 확인, `npx -y <패키지>` 직접 실행해 에러 확인 |
| yt-dlp 403 / 봇 확인 | `yt-dlp -U` 후 `--cookies-from-browser chrome` |
| tesseract `kor` 없음 | macOS `brew install tesseract-lang`, Ubuntu `apt install tesseract-ocr-kor`, Windows는 스크립트가 `kor.traineddata` 자동 다운로드 |

## 출처 / 공식 링크

- last30days: <https://github.com/mvanhorn/last30days-skill>
- yt-dlp: <https://github.com/yt-dlp/yt-dlp> (자막 옵션 `--write-subs --write-auto-subs --sub-langs ko,en`)
- Playwright MCP: <https://playwright.dev/docs/getting-started-mcp>
- agent-browser: <https://github.com/vercel-labs/agent-browser> · <https://agent-browser.dev/skills>
- Agent360 browser-mcp: <https://github.com/Agent360dk/browser-mcp>
- Chrome DevTools MCP: <https://github.com/ChromeDevTools/chrome-devtools-mcp>
- Claude Code + Chrome: <https://code.claude.com/docs/en/chrome>
- Brave Search MCP: <https://brave.com/search/api/guides/use-with-claude-desktop-with-mcp/>
- Firecrawl MCP: <https://github.com/firecrawl/firecrawl-mcp-server>
- youtube-transcript MCP: <https://github.com/hancengiz/youtube-transcript-mcp>
- claude-video-vision: <https://github.com/jordanrendric/claude-video-vision>
- video-frames-skill: <https://github.com/mugnimaestra/video-frames-skill>
- faster-whisper: <https://github.com/SYSTRAN/faster-whisper>
- Codex CLI: <https://www.npmjs.com/package/@openai/codex>
- Claude Code MCP 문서: <https://code.claude.com/docs/en/mcp> · 플러그인: <https://code.claude.com/docs/en/discover-plugins>
- skills CLI: <https://www.skills.sh/agent/claude-code>
