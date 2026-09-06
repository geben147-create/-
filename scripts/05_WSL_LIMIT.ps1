<#
  05_WSL_LIMIT.ps1  -  WSL/Docker 메모리 상한 설정
  ------------------------------------------------------------------
  !! Hermes / n8n / Docker 를 다른 PC 로 옮긴 "뒤에" 실행하세요.
     wsl --shutdown 이 들어가므로 지금 WSL 안에서 도는 것들이 전부 내려갑니다.

  실행: powershell -ExecutionPolicy Bypass -File .\05_WSL_LIMIT.ps1 -MemoryGB 8 -Processors 6
#>
param(
  [int]$MemoryGB = 8,
  [int]$Processors = 6,
  [int]$SwapGB = 4,
  [switch]$Force
)

$wslconfig = Join-Path $env:USERPROFILE '.wslconfig'
$totalGB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB, 0)
$cores   = (Get-CimInstance Win32_Processor | Measure-Object NumberOfLogicalProcessors -Sum).Sum

Write-Host "이 PC: RAM ${totalGB}GB / 논리코어 ${cores}개" -ForegroundColor Cyan
Write-Host "설정할 값: WSL RAM ${MemoryGB}GB / CPU ${Processors} / Swap ${SwapGB}GB" -ForegroundColor Cyan

if ($MemoryGB -ge $totalGB) { Write-Host "WSL 메모리가 전체 RAM 이상입니다. 낮추세요." -ForegroundColor Red; exit 1 }
if ($Processors -gt $cores) { Write-Host "CPU 수가 실제 코어보다 많습니다. 낮추세요." -ForegroundColor Red; exit 1 }

if (Test-Path $wslconfig) {
  $bak = "$wslconfig.bak_$(Get-Date -Format 'yyyyMMdd_HHmm')"
  Copy-Item $wslconfig $bak
  Write-Host "기존 .wslconfig 백업: $bak" -ForegroundColor DarkGray
}

@"
[wsl2]
memory=${MemoryGB}GB
processors=${Processors}
swap=${SwapGB}GB
# 디스크를 지운 만큼 vhdx 도 줄어들게 함 (Windows 11 / 최신 WSL)
sparseVhd=true
# 유휴 시 메모리를 Windows 로 돌려줌
autoMemoryReclaim=gradual
"@ | Set-Content $wslconfig -Encoding UTF8

Write-Host "`n.wslconfig 작성 완료:" -ForegroundColor Green
Get-Content $wslconfig | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }

if (-not $Force) {
  Write-Host "`n적용하려면 WSL 을 내려야 합니다. 지금 도는 컨테이너가 전부 멈춥니다." -ForegroundColor Yellow
  $ans = Read-Host "지금 적용하려면 YES 입력 (나중에 하려면 엔터)"
  if ($ans -ne 'YES') { Write-Host "설정만 저장했습니다. 다음 WSL 재시작 때 적용됩니다." -ForegroundColor Cyan; exit 0 }
}
wsl --shutdown
Write-Host "적용 완료." -ForegroundColor Green
