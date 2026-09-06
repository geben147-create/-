#!/usr/bin/env bash
# =====================================================================
#  setup-global.sh — Claude Code + Codex 전역(global) 설치 스크립트
#  영상분석(yt-dlp/자막/Whisper/프레임/OCR) + 크롤링/브라우저 에이전트 + last30days
#  macOS / Linux / WSL 용.  Windows PowerShell 은 setup-global.ps1 사용.
#  다시 실행해도 안전(idempotent). 실패한 항목은 건너뛰고 마지막에 요약 출력.
# =====================================================================
set -u
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OK=(); FAIL=(); SKIP=()
ok(){ OK+=("$1"); printf '\033[32m✔ %s\033[0m\n' "$1"; }
fail(){ FAIL+=("$1"); printf '\033[31m✘ %s\033[0m\n' "$1"; }
skip(){ SKIP+=("$1"); printf '\033[33m– %s (skip)\033[0m\n' "$1"; }
have(){ command -v "$1" >/dev/null 2>&1; }
OS="$(uname -s)"; SUDO=""; [[ $EUID -ne 0 ]] && have sudo && SUDO=sudo

echo "== 0. 패키지 매니저 / Node / Python 확인"
if [[ "$OS" == "Darwin" ]]; then
  have brew || { echo "Homebrew 설치 중"; /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; }
  PKG="brew install"
elif have apt-get; then PKG="$SUDO apt-get install -y"; $SUDO apt-get update -qq || true
elif have dnf; then PKG="$SUDO dnf install -y"
elif have pacman; then PKG="$SUDO pacman -S --noconfirm"
else PKG=""; fi
have node && [[ "$(node -v | cut -c2-3)" -ge 20 ]] || { [[ "$OS" == "Darwin" ]] && brew install node || { [[ -n "$PKG" ]] && $PKG nodejs npm; }; }
have node && ok "node $(node -v)" || fail "node (https://nodejs.org 에서 22+ 설치 후 재실행)"
have python3 && ok "python3 $(python3 --version | cut -d' ' -f2)" || { [[ -n "$PKG" ]] && $PKG python3 python3-pip; have python3 && ok python3 || fail python3; }
PIP="python3 -m pip install -q -U --user"; python3 -m pip --version >/dev/null 2>&1 || PIP="pip3 install -q -U --user"
export PATH="$HOME/.local/bin:$PATH"

echo "== 1. 시스템 도구: ffmpeg, tesseract(+kor), poppler"
if [[ "$OS" == "Darwin" ]]; then brew install ffmpeg tesseract tesseract-lang poppler >/dev/null 2>&1 || true
elif [[ -n "$PKG" ]]; then $PKG ffmpeg tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng poppler-utils >/dev/null 2>&1 || true; fi
have ffmpeg && ok "ffmpeg" || fail "ffmpeg (수동: brew install ffmpeg / sudo apt install ffmpeg)"
have tesseract && ok "tesseract ($(tesseract --list-langs 2>/dev/null | tail -n +2 | tr '\n' ' '))" || fail "tesseract (brew install tesseract tesseract-lang / apt install tesseract-ocr tesseract-ocr-kor)"

echo "== 2. Python 도구: yt-dlp, faster-whisper, youtube-transcript-api, OCR, crawl4ai"
$PIP yt-dlp youtube-transcript-api pytesseract pillow >/dev/null 2>&1 && ok "yt-dlp $(yt-dlp --version 2>/dev/null) + youtube-transcript-api + pytesseract" || fail "yt-dlp/pytesseract (pip install -U yt-dlp youtube-transcript-api pytesseract pillow)"
$PIP faster-whisper >/dev/null 2>&1 && ok "faster-whisper (음성→텍스트, 자막 없는 영상용)" || fail "faster-whisper (pip install faster-whisper)"
$PIP crawl4ai >/dev/null 2>&1 && ok "crawl4ai (무료 크롤러, 명령: crwl <url> -o markdown)" || skip "crawl4ai (선택)"

echo "== 3. Node CLI: Codex, agent-browser, Playwright 브라우저"
have claude && ok "claude $(claude --version 2>/dev/null | head -1)" || { npm i -g @anthropic-ai/claude-code >/dev/null 2>&1 && ok "claude (설치됨)" || fail "claude (npm i -g @anthropic-ai/claude-code)"; }
npm i -g @openai/codex >/dev/null 2>&1 && ok "codex $(codex --version 2>/dev/null)" || fail "codex (npm i -g @openai/codex)"
npm i -g agent-browser >/dev/null 2>&1 && ok "agent-browser $(agent-browser --version 2>/dev/null)" || fail "agent-browser (npm i -g agent-browser)"
if have agent-browser; then
  if [[ "$OS" == "Linux" ]]; then agent-browser install --with-deps >/dev/null 2>&1 || agent-browser install >/dev/null 2>&1; else agent-browser install >/dev/null 2>&1; fi
  ok "agent-browser install (Chrome for Testing 다운로드)"
fi
npx -y playwright@latest install chromium >/dev/null 2>&1 && ok "playwright chromium (Playwright MCP 용)" || skip "playwright chromium (MCP 첫 실행 시 자동 설치됨)"

echo "== 4. Claude Code 전역 MCP 서버 (--scope user → ~/.claude.json, 모든 프로젝트에서 사용)"
mcp(){ local name="$1"; shift
  claude mcp remove --scope user "$name" >/dev/null 2>&1 || true
  claude mcp add --scope user "$name" "$@" >/dev/null 2>&1 && ok "mcp: $name" || fail "mcp: $name"; }
if have claude; then
  mcp playwright          -- npx -y @playwright/mcp@latest
  mcp chrome-devtools     -- npx -y chrome-devtools-mcp@latest
  mcp youtube-transcript  -- npx -y @fabriqa.ai/youtube-transcript-mcp@latest
  mcp browser-mcp         -- npx -y @agent360/browser-mcp@latest
  mcp brave-search   -e "BRAVE_API_KEY=${BRAVE_API_KEY:-\${BRAVE_API_KEY}}"       -- npx -y @brave/brave-search-mcp-server
  mcp firecrawl      -e "FIRECRAWL_API_KEY=${FIRECRAWL_API_KEY:-\${FIRECRAWL_API_KEY}}" -- npx -y firecrawl-mcp
else skip "MCP 등록 (claude 없음)"; fi

echo "== 5. Claude Code 플러그인 (user scope): last30days, claude-video-vision"
if have claude; then
  claude plugin marketplace add mvanhorn/last30days-skill >/dev/null 2>&1 || true
  claude plugin marketplace add jordanrendric/claude-video-vision >/dev/null 2>&1 || true
  claude plugin install last30days@last30days-skill --scope user >/dev/null 2>&1 && ok "plugin: last30days (전역)" || fail "plugin: last30days"
  claude plugin install claude-video-vision@claude-video-vision --scope user >/dev/null 2>&1 && ok "plugin: claude-video-vision (/watch-video)" || fail "plugin: claude-video-vision"
fi

echo "== 6. 전역 스킬 (~/.claude/skills 및 ~/.codex/skills)"
mkdir -p "$HOME/.claude/skills" "$HOME/.codex/skills"
for s in youtube-analysis video-analysis ocr web-crawl; do
  rm -rf "$HOME/.claude/skills/$s" "$HOME/.codex/skills/$s"
  cp -R "$REPO_DIR/.claude/skills/$s" "$HOME/.claude/skills/$s" && cp -R "$REPO_DIR/.claude/skills/$s" "$HOME/.codex/skills/$s" \
    && ok "skill: $s → ~/.claude/skills + ~/.codex/skills" || fail "skill: $s"
done
# 커뮤니티 스킬: last30days(codex용), agent-browser, video-frames  — skills CLI (-g = 전역, -a = 대상 에이전트)
for pkg in "mvanhorn/last30days-skill" "vercel-labs/agent-browser" "mugnimaestra/video-frames-skill"; do
  npx -y skills add "$pkg" -g -a claude-code codex -y --copy >/dev/null 2>&1 && ok "skills add $pkg (claude-code + codex, 전역)" || fail "skills add $pkg"
done

echo "== 7. last30days 사전점검 + API 키 파일"
mkdir -p "$HOME/.config/last30days"
[[ -f "$HOME/.config/last30days/.env" ]] || cp "$REPO_DIR/.env.example" "$HOME/.config/last30days/.env"
L30="$(ls -d "$HOME/.claude/plugins/cache"/*/last30days*/*/skills/last30days 2>/dev/null | head -1)"
[[ -z "$L30" ]] && L30="$(ls -d "$HOME/.claude/skills/last30days" 2>/dev/null | head -1)"
[[ -n "$L30" && -f "$L30/scripts/last30days.py" ]] && { python3 "$L30/scripts/last30days.py" --preflight 2>&1 | tail -15; ok "last30days --preflight ($L30)"; } || skip "last30days preflight (Claude Code 안에서 /last30days 처음 실행 시 자동 설정)"

echo; echo "=================== 결과 ==================="
printf '설치됨 (%d): %s\n' "${#OK[@]}" "$(printf '%s; ' "${OK[@]}")"
[[ ${#SKIP[@]} -gt 0 ]] && printf '건너뜀 (%d): %s\n' "${#SKIP[@]}" "$(printf '%s; ' "${SKIP[@]}")"
[[ ${#FAIL[@]} -gt 0 ]] && printf '\033[31m실패 (%d): %s\033[0m\n' "${#FAIL[@]}" "$(printf '%s; ' "${FAIL[@]}")"
cat <<'MSG'

다음 단계:
 1) API 키(선택): ~/.config/last30days/.env 편집 → BRAVE_API_KEY, FIRECRAWL_API_KEY, GEMINI_API_KEY
    셸에서도 쓰려면 ~/.zshrc(또는 ~/.bashrc)에  export BRAVE_API_KEY=...  추가
 2) 크롬 확장(실제 로그인 브라우저 제어):  Agent360 Browser MCP  https://chromewebstore.google.com/detail/agent360-browser-mcp/jdehgalffmffhfhmmhaokfbfnafnmgcl
    Claude in Chrome (공식 문서에서 확장 링크):  https://code.claude.com/docs/en/chrome   → claude --chrome
 3) Codex 로그인: codex  (ChatGPT 계정)  → /skills 로 last30days, youtube-analysis 확인
 4) Claude Code 재시작 후 확인:  claude mcp list  /  /plugin list  /  /skills
    사용:  /last30days AI 에이전트 근황     /watch-video ./a.mp4 "요약"     "이 유튜브 분석해줘 https://youtu.be/..."
MSG
