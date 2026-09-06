# stayfade 무료 스택 설치 (Windows PowerShell)
# 관리자 권한 없이 실행하세요. winget 이 필요합니다.
$ErrorActionPreference = "Stop"
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
try { & py -3.11 -V | Out-Null; $hasPy = $true } catch { $hasPy = $false }
if (-not $hasPy) { Write-Host "== Python 3.11 설치"; winget install --id Python.Python.3.11 -e --source winget }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "== ffmpeg 설치"; winget install --id Gyan.FFmpeg -e --source winget
}

if (-not (Test-Path $Venv)) { py -3.11 -m venv $Venv }
$pip = Join-Path $Venv "Scripts\pip.exe"
$py  = Join-Path $Venv "Scripts\python.exe"

Write-Host "== 코어 설치 (필수)"
& $pip install --upgrade pip wheel setuptools
& $pip install numpy scipy librosa soundfile pyloudnorm mido pretty_midi jsonschema

Write-Host "== Basic Pitch (오디오→MIDI)"
& $pip install basic-pitch onnxruntime

Write-Host "== Matchering (마스터링)"
& $pip install matchering

Write-Host "== Demucs (스템 분리, 선택)"
try { & $pip install demucs } catch { Write-Host "  demucs 실패 — HPSS 폴백으로 계속 동작합니다" }

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
