<#
  02_YH_DISK_RECLAIM.ps1  -  400GB 옮기기 전에 "먼저 지울 것" 정리
  ------------------------------------------------------------------
  구글드라이브로 옮기기 전에 이걸 먼저 돌리세요.
  경험상 100~200GB는 옮길 필요 없이 그냥 사라집니다.

  기본은 DRY RUN (조회만). 실제 삭제는 -Apply 를 붙여야 실행됩니다.

  조회:  powershell -ExecutionPolicy Bypass -File .\02_YH_DISK_RECLAIM.ps1
  실행:  powershell -ExecutionPolicy Bypass -File .\02_YH_DISK_RECLAIM.ps1 -Apply
#>
param([switch]$Apply)

$ErrorActionPreference = 'SilentlyContinue'
$mode = if ($Apply) { 'APPLY (실제 삭제)' } else { 'DRY RUN (조회만)' }
Write-Host "=== YH DISK RECLAIM :: $mode ===" -ForegroundColor Cyan
if (-not $Apply) { Write-Host "실제로 지우려면 -Apply 를 붙여 다시 실행하세요.`n" -ForegroundColor Yellow }

function Get-SizeGB($p) {
  if (-not (Test-Path $p)) { return 0 }
  [math]::Round(((Get-ChildItem $p -Recurse -File -Force -ErrorAction SilentlyContinue |
                  Measure-Object Length -Sum).Sum) / 1GB, 2)
}

# --- 안전하게 지워도 되는 것들 (전부 재생성되는 캐시) ---
$safe = @(
  @{ n='pip 캐시';            p="$env:LOCALAPPDATA\pip\Cache" }
  @{ n='npm 캐시';            p="$env:APPDATA\npm-cache" }
  @{ n='torch hub 캐시';      p="$env:USERPROFILE\.cache\torch" }
  @{ n='유저 Temp';           p="$env:TEMP" }
  @{ n='Windows Temp';        p='C:\Windows\Temp' }
  @{ n='Windows Update 캐시'; p='C:\Windows\SoftwareDistribution\Download' }
  @{ n='NVIDIA 설치잔여';     p='C:\NVIDIA' }
  @{ n='썸네일 캐시';         p="$env:LOCALAPPDATA\Microsoft\Windows\Explorer" }
)

$total = 0
Write-Host "--- 자동 삭제 대상 (재생성되는 캐시) ---" -ForegroundColor Green
foreach ($s in $safe) {
  $gb = Get-SizeGB $s.p
  if ($gb -le 0.01) { continue }
  $total += $gb
  Write-Host ("  {0,-24} {1,8} GB   {2}" -f $s.n, $gb, $s.p)
  if ($Apply) {
    Get-ChildItem $s.p -Force -ErrorAction SilentlyContinue |
      Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "     -> 삭제함" -ForegroundColor DarkGray
  }
}

# --- 도구가 직접 정리해야 하는 것 ---
Write-Host "`n--- 도구로 정리 (명령이 안전하게 처리) ---" -ForegroundColor Green

$hf = Get-SizeGB "$env:USERPROFILE\.cache\huggingface"
Write-Host ("  {0,-24} {1,8} GB" -f 'HuggingFace 모델캐시', $hf)
Write-Host "     -> 확인:  huggingface-cli scan-cache" -ForegroundColor DarkGray
Write-Host "     -> 정리:  huggingface-cli delete-cache   (지울 모델 직접 선택)" -ForegroundColor DarkGray
Write-Host "     !! 자동삭제 안 함: ComfyUI/LTX가 쓰는 모델이 섞여 있음" -ForegroundColor Yellow

if (Get-Command docker -ErrorAction SilentlyContinue) {
  Write-Host "`n  Docker 사용량:" -ForegroundColor White
  docker system df
  Write-Host "     -> 정리:  docker system prune -a --volumes" -ForegroundColor DarkGray
  Write-Host "     !! --volumes 는 n8n/DB 데이터도 날립니다. 볼륨 백업 후에만." -ForegroundColor Red
  if ($Apply) {
    Write-Host "     -> 볼륨 제외하고 정리 실행" -ForegroundColor DarkGray
    docker system prune -a -f   # 볼륨은 의도적으로 보존
  }
}

# --- WSL / Docker 가상디스크 축소 ---
Write-Host "`n--- WSL vhdx 축소 (파일 지워도 vhdx 는 안 줄어듭니다) ---" -ForegroundColor Green
$vhdx = @()
$vhdx += Get-ChildItem "$env:LOCALAPPDATA\Packages" -Recurse -Filter '*.vhdx' -Force -ErrorAction SilentlyContinue
$vhdx += Get-ChildItem "$env:LOCALAPPDATA\Docker"   -Recurse -Filter '*.vhdx' -Force -ErrorAction SilentlyContinue
foreach ($v in $vhdx) {
  Write-Host ("  {0,8} GB   {1}" -f [math]::Round($v.Length/1GB,2), $v.FullName)
}
Write-Host @"
     -> 축소 방법 (WSL 안 작업 먼저 저장하고):
        wsl --shutdown
        diskpart
          select vdisk file="<위 경로>"
          attach vdisk readonly
          compact vdisk
          detach vdisk
          exit
     !! 자동 실행 안 함: wsl --shutdown 이 Hermes/Docker 를 내립니다.
"@ -ForegroundColor DarkGray

# --- node_modules / __pycache__ 스캔 ---
Write-Host "`n--- 프로젝트 잔여물 (D:) ---" -ForegroundColor Green
foreach ($pat in @('node_modules','__pycache__','.venv','venv')) {
  $found = Get-ChildItem 'D:\' -Recurse -Directory -Filter $pat -Force -ErrorAction SilentlyContinue -Depth 4
  if ($found) {
    $sum = 0
    foreach ($f in $found) { $sum += (Get-ChildItem $f.FullName -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum }
    Write-Host ("  {0,-16} {1,4}개  {2,8} GB" -f $pat, $found.Count, [math]::Round($sum/1GB,2))
  }
}
Write-Host "     !! 자동삭제 안 함: 활성 프로젝트가 깨집니다. 죽은 프로젝트만 골라서 지우세요." -ForegroundColor Yellow

Write-Host "`n=== 자동 회수 가능 합계: $total GB ===" -ForegroundColor Cyan
if (-not $Apply) { Write-Host "실제 삭제하려면: .\02_YH_DISK_RECLAIM.ps1 -Apply" -ForegroundColor Yellow }
