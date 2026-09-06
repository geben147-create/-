# setup-global.ps1 — Windows 용 전역 설치 (PowerShell 5+/7, 관리자 권장)
# 실행:  Set-ExecutionPolicy -Scope Process Bypass -Force; .\setup-global.ps1
$ErrorActionPreference = "Continue"
$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path
function Ok($m){ Write-Host "OK  $m" -ForegroundColor Green }
function Bad($m){ Write-Host "ERR $m" -ForegroundColor Red }
function Has($c){ [bool](Get-Command $c -ErrorAction SilentlyContinue) }

Write-Host "== 1. winget: Node, Python, ffmpeg, Tesseract, Poppler"
foreach ($p in "OpenJS.NodeJS.LTS","Python.Python.3.12","Gyan.FFmpeg","UB-Mannheim.TesseractOCR","oschwartz10612.Poppler") {
  winget install -e --id $p --accept-source-agreements --accept-package-agreements --silent | Out-Null
}
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
$tess = "C:\Program Files\Tesseract-OCR"
if (Test-Path $tess) {
  $env:Path += ";$tess"
  $kor = "$tess\tessdata\kor.traineddata"   # 한국어 OCR 데이터
  if (-not (Test-Path $kor)) { Invoke-WebRequest "https://github.com/tesseract-ocr/tessdata_fast/raw/main/kor.traineddata" -OutFile $kor }
}
foreach ($c in "node","python","ffmpeg","tesseract") { if (Has $c) { Ok $c } else { Bad "$c (PATH 확인 후 새 터미널에서 재실행)" } }

Write-Host "== 2. Python: yt-dlp, faster-whisper, youtube-transcript-api, OCR"
python -m pip install -q -U yt-dlp youtube-transcript-api pytesseract pillow faster-whisper crawl4ai
Ok "pip 패키지"

Write-Host "== 3. Node CLI: Claude Code, Codex, agent-browser"
if (-not (Has claude)) { npm i -g @anthropic-ai/claude-code }
npm i -g @openai/codex agent-browser | Out-Null
if (Has codex) { Ok "codex $(codex --version)" } else { Bad "codex" }
if (Has agent-browser) { agent-browser install | Out-Null; Ok "agent-browser $(agent-browser --version)" } else { Bad "agent-browser" }
npx -y playwright@latest install chromium | Out-Null

Write-Host "== 4. Claude Code 전역 MCP (--scope user)"
$mcps = @(
  @("playwright","npx","-y","@playwright/mcp@latest"),
  @("chrome-devtools","npx","-y","chrome-devtools-mcp@latest"),
  @("youtube-transcript","npx","-y","@fabriqa.ai/youtube-transcript-mcp@latest"),
  @("browser-mcp","npx","-y","@agent360/browser-mcp@latest")
)
foreach ($m in $mcps) {
  claude mcp remove --scope user $m[0] 2>$null | Out-Null
  claude mcp add --scope user $m[0] -- $m[1..($m.Length-1)] | Out-Null
  Ok "mcp: $($m[0])"
}
claude mcp remove --scope user brave-search 2>$null | Out-Null
claude mcp add --scope user brave-search -e "BRAVE_API_KEY=`${BRAVE_API_KEY}" -- npx -y @brave/brave-search-mcp-server | Out-Null
Ok "mcp: brave-search"
claude mcp remove --scope user firecrawl 2>$null | Out-Null
claude mcp add --scope user firecrawl -e "FIRECRAWL_API_KEY=`${FIRECRAWL_API_KEY}" -- npx -y firecrawl-mcp | Out-Null
Ok "mcp: firecrawl"

Write-Host "== 5. 플러그인 (user scope)"
claude plugin marketplace add mvanhorn/last30days-skill | Out-Null
claude plugin marketplace add jordanrendric/claude-video-vision | Out-Null
claude plugin install last30days@last30days-skill --scope user | Out-Null; Ok "plugin: last30days"
claude plugin install claude-video-vision@claude-video-vision --scope user | Out-Null; Ok "plugin: claude-video-vision"

Write-Host "== 6. 전역 스킬 -> ~\.claude\skills, ~\.codex\skills"
foreach ($d in "$HOME\.claude\skills","$HOME\.codex\skills") {
  New-Item -ItemType Directory -Force $d | Out-Null
  foreach ($s in "youtube-analysis","video-analysis","ocr","web-crawl") {
    Remove-Item -Recurse -Force "$d\$s" -ErrorAction SilentlyContinue
    Copy-Item -Recurse "$Repo\.claude\skills\$s" "$d\$s"
  }
}
Ok "custom skills"
foreach ($pkg in "mvanhorn/last30days-skill","vercel-labs/agent-browser","mugnimaestra/video-frames-skill") {
  npx -y skills add $pkg -g -a claude-code codex -y --copy | Out-Null
  Ok "skills add $pkg"
}

New-Item -ItemType Directory -Force "$HOME\.config\last30days" | Out-Null
if (-not (Test-Path "$HOME\.config\last30days\.env")) { Copy-Item "$Repo\.env.example" "$HOME\.config\last30days\.env" }
Write-Host ""
Write-Host "완료. 새 터미널을 열고:  claude mcp list  /  claude plugin list  /  codex 실행 후 /skills"
Write-Host "API 키: $HOME\.config\last30days\.env  (BRAVE_API_KEY, FIRECRAWL_API_KEY, GEMINI_API_KEY)"
