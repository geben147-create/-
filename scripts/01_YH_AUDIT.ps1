<#
  01_YH_AUDIT.ps1  -  YH 4PC Cluster : READ-ONLY 하드웨어/소프트웨어 점검
  ------------------------------------------------------------------
  이 스크립트는 아무것도 삭제/변경/설치하지 않습니다.
  각 PC에서 1회 실행 -> 바탕화면에 YH_AUDIT_<PC이름>_<날짜> 폴더 생성.

  실행:  powershell -ExecutionPolicy Bypass -File .\01_YH_AUDIT.ps1
#>

$ErrorActionPreference = 'SilentlyContinue'

$stamp   = Get-Date -Format 'yyyyMMdd_HHmm'
$outDir  = Join-Path ([Environment]::GetFolderPath('Desktop')) "YH_AUDIT_${env:COMPUTERNAME}_$stamp"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$report  = Join-Path $outDir 'REPORT.md'

function Section($title) { Add-Content $report "`n## $title`n" }
function Line($text)     { Add-Content $report $text }
function Code($text)     { Add-Content $report ('```' + "`n" + ($text | Out-String).Trim() + "`n" + '```') }

Add-Content $report "# YH AUDIT : $env:COMPUTERNAME"
Line "- 실행시각: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Line "- 사용자: $env:USERNAME"

Write-Host "[1/12] CPU / 메인보드..." -ForegroundColor Cyan
Section 'CPU'
Code (Get-CimInstance Win32_Processor |
      Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed |
      Format-List)

Section '메인보드 / 시스템'
Code (Get-CimInstance Win32_ComputerSystem |
      Select-Object Manufacturer, Model, SystemType, TotalPhysicalMemory | Format-List)
Code (Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product | Format-List)

Write-Host "[2/12] RAM 슬롯..." -ForegroundColor Cyan
Section 'RAM (슬롯별 - 증설 가능 여부 판단용)'
$ram = Get-CimInstance Win32_PhysicalMemory |
  Select-Object DeviceLocator,
    @{n='GB';e={[math]::Round($_.Capacity/1GB,0)}},
    @{n='Speed_MHz';e={$_.ConfiguredClockSpeed}}, Manufacturer, PartNumber
Code ($ram | Format-Table -AutoSize)
Line "**총 RAM: $([math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,1)) GB / 사용중 슬롯: $($ram.Count)개**"
Code (Get-CimInstance Win32_PhysicalMemoryArray | Select-Object MemoryDevices, @{n='MaxGB';e={[math]::Round($_.MaxCapacityEx/1MB,0)}} | Format-List)

Write-Host "[3/12] GPU / VRAM..." -ForegroundColor Cyan
Section 'GPU'
Code (Get-CimInstance Win32_VideoController |
      Select-Object Name, DriverVersion,
        @{n='AdapterRAM_GB_부정확';e={[math]::Round($_.AdapterRAM/1GB,1)}} | Format-List)

Section 'NVIDIA 실제 VRAM / NVENC (nvidia-smi)'
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
  Code (nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap --format=csv)
  nvidia-smi -q > (Join-Path $outDir 'nvidia-smi-full.txt')
} else { Line '_nvidia-smi 없음 (NVIDIA GPU 아님 또는 드라이버 미설치)_' }

Write-Host "[4/12] 디스크..." -ForegroundColor Cyan
Section '물리 디스크 (SSD/HDD 판별)'
Code (Get-PhysicalDisk |
      Select-Object DeviceId, FriendlyName, MediaType, BusType,
        @{n='SizeGB';e={[math]::Round($_.Size/1GB,0)}}, HealthStatus | Format-Table -AutoSize)

Section '볼륨 / 빈 공간'
Code (Get-Volume | Where-Object DriveLetter |
      Select-Object DriveLetter, FileSystemLabel, FileSystem,
        @{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}},
        @{n='FreeGB';e={[math]::Round($_.SizeRemaining/1GB,1)}},
        @{n='Free%';e={[math]::Round(100*$_.SizeRemaining/$_.Size,1)}} | Format-Table -AutoSize)

Write-Host "[5/12] 용량 먹는 폴더 TOP 25 (D:\, 시간 조금 걸림)..." -ForegroundColor Cyan
Section '용량 상위 폴더 (D: 1단계 + 알려진 캐시)'
$targets = @('D:\','C:\Users\' + $env:USERNAME) | Where-Object { Test-Path $_ }
foreach ($t in $targets) {
  Line "`n### $t"
  $rows = Get-ChildItem $t -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $sz = (Get-ChildItem $_.FullName -Recurse -File -Force -ErrorAction SilentlyContinue |
           Measure-Object Length -Sum).Sum
    [pscustomobject]@{ Folder = $_.Name; GB = [math]::Round($sz/1GB,2) }
  } | Sort-Object GB -Descending | Select-Object -First 25
  Code ($rows | Format-Table -AutoSize)
}

Write-Host "[6/12] 회수 가능한 캐시 용량..." -ForegroundColor Cyan
Section '삭제해도 되는 캐시 (지금은 조회만 함)'
$caches = @(
  @{n='HuggingFace 모델캐시'; p="$env:USERPROFILE\.cache\huggingface"},
  @{n='HuggingFace (HF_HOME)'; p="$env:USERPROFILE\.huggingface"},
  @{n='pip 캐시';             p="$env:LOCALAPPDATA\pip\Cache"},
  @{n='npm 캐시';             p="$env:APPDATA\npm-cache"},
  @{n='torch hub 캐시';       p="$env:USERPROFILE\.cache\torch"},
  @{n='유저 Temp';            p="$env:TEMP"},
  @{n='Windows Temp';         p='C:\Windows\Temp'},
  @{n='Windows Update 캐시';  p='C:\Windows\SoftwareDistribution\Download'},
  @{n='NVIDIA 설치잔여';      p='C:\NVIDIA'},
  @{n='Docker (WSL vhdx)';    p="$env:LOCALAPPDATA\Docker\wsl"}
)
$rows = foreach ($c in $caches) {
  if (Test-Path $c.p) {
    $sz = (Get-ChildItem $c.p -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    [pscustomobject]@{ 항목=$c.n; GB=[math]::Round($sz/1GB,2); 경로=$c.p }
  }
}
Code ($rows | Sort-Object GB -Descending | Format-Table -AutoSize)
Line "**회수가능 합계 추정: $([math]::Round(($rows | Measure-Object GB -Sum).Sum,2)) GB**"

Write-Host "[7/12] WSL 배포판 + vhdx 실제 크기..." -ForegroundColor Cyan
Section 'WSL'
if (Get-Command wsl -ErrorAction SilentlyContinue) {
  Code (wsl --list --verbose 2>&1)
  Code (wsl --status 2>&1)
  Line "`n### WSL 디스크 이미지 실제 크기 (여기가 숨은 용량 범인인 경우 많음)"
  $vhdx = Get-ChildItem "$env:LOCALAPPDATA\Packages" -Recurse -Filter '*.vhdx' -Force -ErrorAction SilentlyContinue
  $vhdx += Get-ChildItem "$env:LOCALAPPDATA\Docker" -Recurse -Filter '*.vhdx' -Force -ErrorAction SilentlyContinue
  Code ($vhdx | Select-Object @{n='GB';e={[math]::Round($_.Length/1GB,2)}}, FullName | Sort-Object GB -Descending | Format-Table -AutoSize)
} else { Line '_WSL 미설치_' }

Write-Host "[8/12] Docker..." -ForegroundColor Cyan
Section 'Docker'
if (Get-Command docker -ErrorAction SilentlyContinue) {
  Code (docker --version 2>&1)
  Code (docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' 2>&1)
  Code (docker system df 2>&1)
} else { Line '_Docker 없음_' }

Write-Host "[9/12] 개발 툴체인..." -ForegroundColor Cyan
Section '설치된 툴 버전'
$tools = 'git','node','npm','python','pip','ffmpeg','uv','rclone','tailscale','hermes','gh','code'
$rows = foreach ($t in $tools) {
  $cmd = Get-Command $t -ErrorAction SilentlyContinue
  [pscustomobject]@{
    도구 = $t
    설치 = if ($cmd) { 'O' } else { 'X' }
    버전 = if ($cmd) { (& $t --version 2>&1 | Select-Object -First 1) } else { '' }
    경로 = if ($cmd) { $cmd.Source } else { '' }
  }
}
Code ($rows | Format-Table -AutoSize)

Write-Host "[10/12] FFmpeg 하드웨어 인코더 (NVENC 여부)..." -ForegroundColor Cyan
Section 'FFmpeg 하드웨어 인코더 - 이 PC가 인코딩 담당 가능한지 판정'
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
  Code ((ffmpeg -hide_banner -encoders 2>&1 | Select-String 'nvenc|qsv|amf') -join "`n")
} else { Line '_ffmpeg 미설치 -> winget install Gyan.FFmpeg_' }

Write-Host "[11/12] 네트워크..." -ForegroundColor Cyan
Section '네트워크 (유선 기가비트인지 확인)'
Code (Get-NetAdapter | Where-Object Status -eq 'Up' |
      Select-Object Name, InterfaceDescription,
        @{n='LinkSpeed';e={$_.LinkSpeed}}, MacAddress | Format-Table -AutoSize)
Code (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' } |
      Select-Object InterfaceAlias, IPAddress | Format-Table -AutoSize)

Write-Host "[12/12] OS / 전원 / 자동시작 서비스..." -ForegroundColor Cyan
Section 'OS'
Code (Get-CimInstance Win32_OperatingSystem |
      Select-Object Caption, Version, BuildNumber, OSArchitecture, InstallDate, LastBootUpTime | Format-List)
Line "`n> Windows 에디션이 **Home** 이면 원격데스크톱(RDP) 호스트 불가 -> RustDesk 필요."

Section '전원 계획 (24시간 서버 후보 판정용)'
Code (powercfg /list 2>&1)

Section '자동 시작 서비스 (부하 원인 추적)'
Code (Get-Service | Where-Object { $_.StartType -eq 'Automatic' -and $_.Status -eq 'Running' } |
      Select-Object -ExpandProperty Name | Sort-Object)

Section '메모리 사용 상위 프로세스'
Code (Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 20 `
      Name, @{n='MB';e={[math]::Round($_.WorkingSet64/1MB,0)}}, Id | Format-Table -AutoSize)

Copy-Item $report (Join-Path $outDir "REPORT_$env:COMPUTERNAME.md") -Force
Write-Host "`n완료. 결과 폴더:" -ForegroundColor Green
Write-Host "  $outDir" -ForegroundColor Yellow
Write-Host "이 폴더 전체를 메인 PC 한 곳에 모아주세요." -ForegroundColor Green
Invoke-Item $outDir
