<#
  06_INSTALL_FFMPEG_GLOBAL.ps1  -  ffmpeg 전역 설치 (모든 사용자 / 모든 프로그램)
  ==================================================================
  왜 winget 만으로는 부족한가:
    winget 의 Gyan.FFmpeg 는 "내 계정" PATH 에만 등록됩니다.
    Codex CLI, VS Code, n8n, Docker, 예약작업(SYSTEM 계정) 처럼
    다른 컨텍스트에서 실행되는 프로그램은 그 PATH 를 못 봅니다.
    -> 그래서 C:\ffmpeg 에 풀고 "시스템 PATH"(Machine)에 등록합니다.

  실행 (반드시 [관리자] PowerShell):
    powershell -ExecutionPolicy Bypass -File .\06_INSTALL_FFMPEG_GLOBAL.ps1

  다시 설치/업데이트:
    ... -File .\06_INSTALL_FFMPEG_GLOBAL.ps1 -Force
#>
param(
  [string]$InstallDir = 'C:\ffmpeg',
  [switch]$Force
)

$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'   # 다운로드 속도 크게 개선

function Ok($m)   { Write-Host "  [OK]   $m" -ForegroundColor Green }
function Info($m) { Write-Host "  [..]   $m" -ForegroundColor Cyan }
function Warn($m) { Write-Host "  [!]    $m" -ForegroundColor Yellow }
function Bad($m)  { Write-Host "  [X]    $m" -ForegroundColor Red }

Write-Host "`n=== ffmpeg 전역 설치 ===" -ForegroundColor Cyan

# ---------- 0. 관리자 확인 ----------
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
         ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
  Bad "관리자 권한이 아닙니다."
  Write-Host ""
  Write-Host "  시작 버튼 우클릭 -> 'Windows PowerShell(관리자)' 또는 '터미널(관리자)'" -ForegroundColor Yellow
  Write-Host "  그 다음 이 명령을 다시 실행하세요:" -ForegroundColor Yellow
  Write-Host "    powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -ForegroundColor White
  exit 1
}
Ok "관리자 권한 확인"

# ---------- 1. 이미 있는지 ----------
$exe = Join-Path $InstallDir 'bin\ffmpeg.exe'
if ((Test-Path $exe) -and -not $Force) {
  Ok "이미 설치돼 있습니다: $exe"
  Info "다시 받으려면 -Force 를 붙이세요."
} else {

  # ---------- 2. 다운로드 ----------
  $tmp = Join-Path $env:TEMP "ffmpeg_dl_$(Get-Random).zip"
  $sources = @(
    @{ n='BtbN (GitHub)'; u='https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip' },
    @{ n='gyan.dev';      u='https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' }
  )
  $got = $false
  foreach ($s in $sources) {
    try {
      Info "다운로드 시도: $($s.n)  (수십 MB, 잠시 걸립니다)"
      [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
      Invoke-WebRequest -Uri $s.u -OutFile $tmp -UseBasicParsing -TimeoutSec 600
      $mb = [math]::Round((Get-Item $tmp).Length/1MB,1)
      if ($mb -lt 5) { throw "받은 파일이 너무 작습니다 ($mb MB)" }
      Ok "다운로드 완료: $mb MB  ($($s.n))"
      $got = $true; break
    } catch {
      Warn "$($s.n) 실패: $($_.Exception.Message)"
      if (Test-Path $tmp) { Remove-Item $tmp -Force -EA SilentlyContinue }
    }
  }
  if (-not $got) {
    Bad "두 소스 모두 실패했습니다. 회사망/백신이 막았을 수 있습니다."
    Write-Host "  수동 방법: https://github.com/BtbN/FFmpeg-Builds/releases 에서" -ForegroundColor Yellow
    Write-Host "  ffmpeg-master-latest-win64-gpl.zip 을 받아 C:\ffmpeg 에 풀고" -ForegroundColor Yellow
    Write-Host "  C:\ffmpeg\bin 을 시스템 환경변수 Path 에 추가하세요." -ForegroundColor Yellow
    exit 1
  }

  # ---------- 3. 압축 해제 ----------
  Info "압축 해제 중..."
  $stage = Join-Path $env:TEMP "ffmpeg_stage_$(Get-Random)"
  Expand-Archive -Path $tmp -DestinationPath $stage -Force

  # zip 안에 ffmpeg-xxxx\bin\ffmpeg.exe 형태로 한 겹 더 들어있음
  $binSrc = Get-ChildItem $stage -Recurse -Filter 'ffmpeg.exe' -File | Select-Object -First 1
  if (-not $binSrc) { Bad "압축 안에서 ffmpeg.exe 를 못 찾았습니다."; exit 1 }
  $root = $binSrc.Directory.Parent.FullName   # ...\ffmpeg-xxxx

  if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force }
  New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
  Copy-Item "$root\*" $InstallDir -Recurse -Force
  Remove-Item $tmp, $stage -Recurse -Force -EA SilentlyContinue
  Ok "설치 위치: $InstallDir"
}

# ---------- 4. 시스템 PATH 등록 (여기가 '전역'의 핵심) ----------
$binDir  = Join-Path $InstallDir 'bin'
$machine = [Environment]::GetEnvironmentVariable('Path','Machine')
$parts   = $machine -split ';' | Where-Object { $_ -ne '' }

if ($parts -notcontains $binDir) {
  [Environment]::SetEnvironmentVariable('Path', (($parts + $binDir) -join ';'), 'Machine')
  Ok "시스템 PATH 에 등록: $binDir"
  Info "이제 모든 사용자 / 모든 프로그램(Codex, VS Code, n8n, 예약작업)이 볼 수 있습니다."
} else {
  Ok "시스템 PATH 에 이미 등록돼 있습니다."
}

# 지금 이 창에서도 바로 쓰이도록
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
            [Environment]::GetEnvironmentVariable('Path','User')

# ---------- 5. 검증 ----------
Write-Host "`n--- 검증 ---" -ForegroundColor Cyan
$ver = & "$binDir\ffmpeg.exe" -hide_banner -version 2>&1 | Select-Object -First 1
Ok $ver

# 새 프로세스에서도 보이는지 (Codex 가 보는 것과 같은 조건)
$fresh = Start-Process powershell -ArgumentList '-NoProfile','-Command','(Get-Command ffmpeg).Source' `
         -Wait -PassThru -NoNewWindow -RedirectStandardOutput "$env:TEMP\ff_check.txt"
$found = (Get-Content "$env:TEMP\ff_check.txt" -EA SilentlyContinue) -join ''
Remove-Item "$env:TEMP\ff_check.txt" -EA SilentlyContinue
if ($found -match 'ffmpeg.exe') { Ok "새 프로세스에서도 인식: $found" }
else { Warn "새 프로세스에서 아직 안 보입니다. 아래 '재시작' 항목을 꼭 읽으세요." }

# ---------- 6. NVENC 판정 (C5 항목) ----------
Write-Host "`n--- 이 PC 의 하드웨어 인코더 ---" -ForegroundColor Cyan
$enc = & "$binDir\ffmpeg.exe" -hide_banner -encoders 2>&1 | Select-String 'nvenc|qsv|amf|videotoolbox'
if ($enc) {
  $enc | ForEach-Object { Write-Host "  $_" -ForegroundColor Green }
  Write-Host ""
  if ($enc -match 'hevc_nvenc') { Ok "NVENC 있음 -> 이 PC 가 인코딩 담당 가능합니다." }
  if ($enc -match 'qsv')        { Info "Intel QSV 도 있습니다 (내장그래픽 인코더)." }
} else {
  Warn "하드웨어 인코더가 없습니다. CPU 인코딩(libx264/libx265)만 가능합니다."
  Info "느리지만 화질/용량 효율은 오히려 더 좋은 경우가 많습니다."
}

# 실제로 동작하는지 3초 테스트 영상으로 확인
Write-Host "`n--- 실제 인코딩 테스트 ---" -ForegroundColor Cyan
$t = Join-Path $env:TEMP 'yh_nvenc_test.mp4'
foreach ($codec in @('hevc_nvenc','h264_nvenc','libx264')) {
  try {
    & "$binDir\ffmpeg.exe" -hide_banner -loglevel error -y `
      -f lavfi -i testsrc=size=640x360:rate=30:duration=2 -c:v $codec $t 2>$null
    if ($LASTEXITCODE -eq 0 -and (Test-Path $t)) {
      Ok "$codec : 동작함"
      Remove-Item $t -Force -EA SilentlyContinue
    } else { Warn "$codec : 사용 불가" }
  } catch { Warn "$codec : 사용 불가" }
}

# ---------- 7. 마무리 안내 ----------
Write-Host "`n=== 완료 ===" -ForegroundColor Green
Write-Host @"

  중요: 이미 열려 있는 프로그램은 PATH 변경을 모릅니다.
  아래를 "완전히 종료 후 다시 실행" 해야 ffmpeg 를 인식합니다.

    - PowerShell / cmd / Windows Terminal 창 전부
    - VS Code  (창만 닫지 말고 완전 종료)
    - Codex CLI / Claude Code
    - Docker Desktop, n8n

  가장 확실한 방법은 재부팅입니다.

  재시작 후 확인:
    ffmpeg -version
    where.exe ffmpeg

"@ -ForegroundColor Yellow
