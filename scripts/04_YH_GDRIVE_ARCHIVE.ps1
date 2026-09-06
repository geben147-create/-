<#
  04_YH_GDRIVE_ARCHIVE.ps1  -  D: 대용량 -> 구글드라이브 (복사 -> 검증 -> 그다음 삭제)
  ------------------------------------------------------------------
  ** 02_YH_DISK_RECLAIM.ps1 를 먼저 돌리세요. 옮길 양이 절반으로 줍니다. **

  왜 rclone 인가:
    - "구글 드라이브 데스크톱"(스트리밍)은 20GB 모델파일/ComfyUI 에 최악입니다.
      랜덤 읽기가 느리고, 로컬 캐시가 C: 를 다시 채웁니다.
    - rclone 은 진짜 업로드 + 해시 검증 + 재개가 됩니다.

  1회 준비:
    winget install Rclone.Rclone
    rclone config       -> n(new) -> 이름 gdrive -> drive -> 나머지 기본값 -> 브라우저 로그인

  사용:
    .\04_YH_GDRIVE_ARCHIVE.ps1 -Source "D:\AI_DATA\archive" -Dest "YH_ARCHIVE/AI_DATA/archive"
    .\04_YH_GDRIVE_ARCHIVE.ps1 -Source "D:\AI_DATA\archive" -Dest "YH_ARCHIVE/AI_DATA/archive" -Verify
    .\04_YH_GDRIVE_ARCHIVE.ps1 -Source "D:\AI_DATA\archive" -Dest "YH_ARCHIVE/AI_DATA/archive" -DeleteSourceAfterVerify
#>
param(
  [Parameter(Mandatory)][string]$Source,
  [Parameter(Mandatory)][string]$Dest,
  [string]$Remote = 'gdrive',
  [switch]$Verify,
  [switch]$DeleteSourceAfterVerify,
  [int]$Transfers = 4
)

$ErrorActionPreference = 'Stop'
if (-not (Get-Command rclone -ErrorAction SilentlyContinue)) {
  Write-Host "rclone 이 없습니다:  winget install Rclone.Rclone" -ForegroundColor Red; exit 1
}
if (-not (Test-Path $Source)) { Write-Host "원본 없음: $Source" -ForegroundColor Red; exit 1 }

$target = "${Remote}:$Dest"
$logDir = Join-Path ([Environment]::GetFolderPath('Desktop')) 'YH_GDRIVE_LOG'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$log = Join-Path $logDir ("rclone_{0}.log" -f (Get-Date -Format 'yyyyMMdd_HHmm'))

$sizeGB = [math]::Round(((Get-ChildItem $Source -Recurse -File -Force -EA SilentlyContinue |
           Measure-Object Length -Sum).Sum)/1GB, 2)
Write-Host "원본 : $Source  ($sizeGB GB)" -ForegroundColor Cyan
Write-Host "대상 : $target" -ForegroundColor Cyan
Write-Host "로그 : $log`n" -ForegroundColor DarkGray

# 공통 옵션
#  --drive-chunk-size 128M : 대용량 파일 업로드 속도 개선 (RAM 을 transfers 배수만큼 씀)
#  --transfers 4           : 구글드라이브는 동시성 높이면 오히려 429 를 뱉습니다
#  --tpslimit 8            : API rate limit 회피
$common = @(
  '--transfers', $Transfers, '--checkers', 8, '--tpslimit', 8,
  '--drive-chunk-size', '128M',
  '--progress', '--stats', '20s', '--stats-one-line',
  '--log-file', $log, '--log-level', 'INFO',
  '--exclude', '**/node_modules/**',
  '--exclude', '**/__pycache__/**',
  '--exclude', '**/.git/**',
  '--exclude', 'desktop.ini', '--exclude', 'Thumbs.db'
)

if ($DeleteSourceAfterVerify) {
  # 1) 검증 먼저. 통과 못하면 아무것도 안 지움.
  Write-Host "[검증] 원본 <-> 구글드라이브 해시 비교..." -ForegroundColor Yellow
  rclone check $Source $target @common
  if ($LASTEXITCODE -ne 0) {
    Write-Host "`n검증 실패. 원본을 지우지 않았습니다. 로그를 확인하세요:`n  $log" -ForegroundColor Red
    exit 1
  }
  Write-Host "`n검증 통과." -ForegroundColor Green
  Write-Host "이제 원본을 삭제합니다: $Source" -ForegroundColor Red
  $ans = Read-Host "정말 삭제하려면 DELETE 를 입력하세요"
  if ($ans -ne 'DELETE') { Write-Host "취소했습니다." -ForegroundColor Yellow; exit 0 }
  Remove-Item $Source -Recurse -Force
  Write-Host "삭제 완료. $sizeGB GB 회수." -ForegroundColor Green
  exit 0
}

if ($Verify) {
  Write-Host "[검증만] 해시 비교..." -ForegroundColor Yellow
  rclone check $Source $target @common
  if ($LASTEXITCODE -eq 0) { Write-Host "`n일치합니다. 이제 -DeleteSourceAfterVerify 로 원본 정리 가능." -ForegroundColor Green }
  else { Write-Host "`n불일치. 다시 copy 하세요." -ForegroundColor Red }
  exit $LASTEXITCODE
}

# 기본 동작 = copy (절대 sync 아님. sync 는 대상 파일을 지웁니다)
Write-Host "[복사] rclone copy (중단되면 같은 명령 다시 실행 = 이어받기)" -ForegroundColor Yellow
rclone copy $Source $target @common
Write-Host "`n복사 끝. 다음: -Verify 로 검증하세요." -ForegroundColor Green
Write-Host "  .\04_YH_GDRIVE_ARCHIVE.ps1 -Source `"$Source`" -Dest `"$Dest`" -Verify" -ForegroundColor Cyan
