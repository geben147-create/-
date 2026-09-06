# stayfade 한 곡 처리 (Windows) — 단계를 순서대로 실행하고 사람 결정 앞에서 멈춥니다.
#
#   powershell -ExecutionPolicy Bypass -File skill\scripts\run_windows.ps1 -Audio "C:\Users\나\Music\곡.wav" -Name mysong
#
# -Key 를 주면 조성 자동 추정을 덮어씁니다 (예: -Key Ebm).
param(
    [Parameter(Mandatory = $true)][string]$Audio,
    [string]$Name = "mysong",
    [string]$Key = "",
    [string]$Title = "",
    [string]$Artist = "",
    [double]$TargetLufs = -14,
    [string]$Distributor = "routenote",
    [string]$Venv = "$HOME\stayfade\.venv"
)
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$py = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $py)) { throw "가상환경이 없습니다: $py`n먼저 skill\scripts\install_windows.ps1 을 실행하세요." }
if (-not (Test-Path $Audio)) { throw "원본 파일이 없습니다: $Audio" }

$env:PYTHONPATH = Join-Path $repo "pipeline"
$proj = Join-Path $repo "work\$Name"
if ($Title -eq "") { $Title = [IO.Path]::GetFileNameWithoutExtension($Audio) }

function Step($label, $arguments) {
    Write-Host ""
    Write-Host "== $label" -ForegroundColor Green
    & $py -m stayfade --project $proj @arguments
    if ($LASTEXITCODE -ne 0) { throw "$label 단계에서 멈췄습니다. 위 메시지를 확인하세요." }
}

Step "00 원본 보존" @("init", $Audio, "--title", $Title, "--artist", $Artist,
                      "--target-lufs", $TargetLufs, "--distributor", $Distributor)

$analyzeArgs = @("analyze")
if ($Key -ne "") { $analyzeArgs += @("--key", $Key) }
Step "01-03 분리 · 분석 · 채보" $analyzeArgs

Step "04-05 후보 생성 · 미리듣기" @("candidates")
Step "06 사람 결정 관문" @("gate")

$decisions = Join-Path $proj "human_decisions.json"
$d = Get-Content $decisions -Raw | ConvertFrom-Json
if ($d.status -ne "DECIDED") {
    Write-Host ""
    Write-Host "여기서 멈춥니다. 다음을 하세요:" -ForegroundColor Yellow
    Write-Host "  1) 미리듣기를 전부 들어보세요:  $proj\04_render"
    Write-Host "  2) 결정 파일을 채우세요:        $decisions"
    Write-Host "     - 각 항목의 choice 에 고른 옵션 id"
    Write-Host "     - note_edits 로 최소 몇 개는 직접 수정"
    Write-Host "     - status 를 DECIDED, decided_by 를 human 으로"
    Write-Host "  3) 이 스크립트를 다시 실행하면 이어서 진행합니다."
    Start-Process explorer.exe (Join-Path $proj "04_render")
    Start-Process notepad.exe $decisions
    exit 0
}

Step "07-08 보컬 · 믹스 · 마스터" @("build")
Step "09 기술 QC" @("qc")
Step "10 증빙" @("evidence")

& $py (Join-Path $repo "skill\scripts\validate.py") $proj

Write-Host ""
Write-Host "완료. 결과물:" -ForegroundColor Green
Write-Host "  마스터 :  $proj\07_master\arranged_master_44k1_24bit.wav"
Write-Host "  유통용 :  $proj\07_master\distributor_candidate_44k1_16bit.flac"
Write-Host "  A/B    :  $proj\08_qc\AB_original_vs_arranged.wav"
Write-Host "  증빙   :  $proj\09_evidence\"
Write-Host ""
Write-Host "제출 전에 반드시: 전체 청취 · 모노 청취 · 권리 증빙 · 커버/메타데이터 확인" -ForegroundColor Yellow
Start-Process explorer.exe (Join-Path $proj "07_master")
