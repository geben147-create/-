# stayfade 무료 스택 설치 (Windows PowerShell)
# 관리자 권한 없이 실행하세요. winget 이 필요합니다.
$ErrorActionPreference = "Stop"

function Need($label) {
    # PowerShell 5.1 은 외부 명령의 0 아닌 종료코드를 예외로 만들지 않습니다. 직접 확인해야 합니다.
    if ($LASTEXITCODE -ne 0) { throw "$label 실패 — 위 메시지를 확인하고 다시 실행하세요." }
}
function Refresh-Path {
    $env:PATH = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path','User')
}

$Root = Join-Path $HOME "stayfade"
$Venv = Join-Path $Root ".venv"

Write-Host "== 작업 폴더: $Root"
New-Item -ItemType Directory -Force -Path $Root | Out-Null
Set-Location $Root

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "winget 이 없습니다. Microsoft Store 에서 '앱 설치 관리자'를 업데이트하세요."
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "== Git 설치"; winget install --id Git.Git -e --source winget
}
$hasPy = $false
try { & py -3.11 -V 2>$null | Out-Null; $hasPy = ($LASTEXITCODE -eq 0) } catch { $hasPy = $false }
if (-not $hasPy) {
    Write-Host "== Python 3.11 설치"
    winget install --id Python.Python.3.11 -e --source winget
    Refresh-Path
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "== ffmpeg 설치"; winget install --id Gyan.FFmpeg -e --source winget; Refresh-Path
}

Refresh-Path
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "Python 을 방금 설치했습니다. PowerShell 창을 닫았다 다시 열고 이 스크립트를 한 번 더 실행하세요." -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $Venv)) { py -3.11 -m venv $Venv }
$pip = Join-Path $Venv "Scripts\pip.exe"
$py  = Join-Path $Venv "Scripts\python.exe"

Write-Host "== 코어 설치 (필수)"
& $pip install --upgrade pip wheel setuptools
Need "pip 업그레이드"
& $pip install numpy scipy librosa soundfile pyloudnorm mido pretty_midi jsonschema
Need "코어 패키지 설치"

Write-Host "== Basic Pitch (오디오→MIDI)"
& $pip install basic-pitch onnxruntime
Need "Basic Pitch 설치"

Write-Host "== Matchering (마스터링, 선택)"
& $pip install matchering
if ($LASTEXITCODE -ne 0) { Write-Host "  matchering 설치 실패 — 파이프라인은 이것 없이도 동작합니다" }

Write-Host "== Demucs (스템 분리, 선택)"
& $pip install demucs
if ($LASTEXITCODE -ne 0) { Write-Host "  demucs 설치 실패 — HPSS 폴백으로 계속 동작합니다 (품질은 낮습니다)" }

Write-Host ""
Write-Host "다음 단계 (수동):"
Write-Host " 1) REAPER 설치 (60일 무료 평가):  https://www.reaper.fm/download.php"
Write-Host " 2) 무료 피치 보정 플러그인:"
Write-Host "      Graillon 3 Free   https://www.auburnsounds.com/products/Graillon.html"
Write-Host "      MAutoPitch        https://www.meldaproduction.com/MAutoPitch"
Write-Host " 3) 스템 분리 GUI(선택): Ultimate Vocal Remover  https://github.com/Anjok07/ultimatevocalremovergui"
Write-Host ""
Write-Host "사용:"
Write-Host "  `$env:PYTHONPATH='<repo>\pipeline'"
Write-Host "  $py -m stayfade --project .\work\mysong init <원본.wav>"
