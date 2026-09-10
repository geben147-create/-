<#
.SYNOPSIS
    RustDesk 무인 접속(승인 클릭 없이 폰에서 바로 연결) 설정 스크립트.

.DESCRIPTION
    아래 항목을 한 번에 처리합니다.

      1) RustDesk 프로세스/서비스를 잠시 멈춤 (설정 파일을 덮어쓰지 못하게)
      2) 찾을 수 있는 모든 RustDesk2.toml 의 [options] 에 다음을 강제 기록
             verification-method = 'use-permanent-password'   (영구 비밀번호만 사용)
             approve-mode        = 'password'                 (비밀번호만으로 승인 = 수락 클릭 없음)
             allow-remote-config-modification = 'N'           (원격에서 이 설정을 못 바꾸게)
      3) 영구 비밀번호가 실제로 저장돼 있는지 확인 (없으면 경고)
      4) RustDesk 서비스를 '자동 시작' 으로 바꾸고 시작
      5) 로그인 사용자용 트레이 앱을 시작 프로그램(Run 키)에 등록
      6) 절전/최대 절전으로 PC 가 자버려서 폰에서 못 붙는 일을 막음 (AC 전원 기준)

    실행 후에는 PC 를 한 번 재부팅하고, 폰에서 ID + 영구 비밀번호로 접속하면서
    "비밀번호 저장" 을 체크하면 그 다음부터는 아무 조작 없이 연결됩니다.

.PARAMETER SkipPowerSettings
    절전 설정은 건드리지 않습니다.

.PARAMETER SkipTrayAutostart
    시작 프로그램(트레이 앱) 등록을 건너뜁니다. 서비스 자동 시작은 그대로 적용됩니다.

.EXAMPLE
    # 관리자 PowerShell 에서
    powershell -ExecutionPolicy Bypass -File .\Setup-RustDeskUnattended.ps1

.NOTES
    * 반드시 "관리자 권한" PowerShell 에서 실행하세요.
    * 영구 비밀번호 자체는 이 스크립트가 만들지 않습니다.
      RustDesk 창 -> 설정 -> 보안 -> 영구 비밀번호 에서 먼저 한 번 지정해 주세요.
      (비밀번호는 해시/암호화되어 저장되므로 스크립트로 안전하게 심을 수 없습니다.)
#>
[CmdletBinding()]
param(
    [switch]$SkipPowerSettings,
    [switch]$SkipTrayAutostart
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------- 유틸 --------
function Write-Step { param([string]$Text) Write-Host ""; Write-Host "==> $Text" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Text) Write-Host "    [OK]   $Text" -ForegroundColor Green }
function Write-Warn { param([string]$Text) Write-Host "    [주의] $Text" -ForegroundColor Yellow }
function Write-Info { param([string]$Text) Write-Host "    -      $Text" -ForegroundColor Gray }

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    (New-Object Security.Principal.WindowsPrincipal($id)).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

# RustDesk2.toml 의 [options] 섹션에 키를 강제로 써넣는다.
# TOML 전체를 파싱하지 않고, 대상 키 줄만 지우고 [options] 바로 아래에 다시 넣는 방식.
function Set-TomlOptions {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][hashtable]$Options
    )

    $dir = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $list = [System.Collections.Generic.List[string]]::new()
    if (Test-Path -LiteralPath $Path) {
        # 백업은 한 번만 (여러 번 돌려도 원본 백업이 덮이지 않게)
        $backup = "$Path.bak"
        if (-not (Test-Path -LiteralPath $backup)) {
            Copy-Item -LiteralPath $Path -Destination $backup -Force
        }
        foreach ($line in [System.IO.File]::ReadAllLines($Path)) { $list.Add($line) }
    }

    # 1) 기존에 흩어져 있는 같은 키 줄을 모두 제거
    foreach ($key in $Options.Keys) {
        $pattern = '^\s*"?' + [regex]::Escape($key) + '"?\s*='
        for ($i = $list.Count - 1; $i -ge 0; $i--) {
            if ($list[$i] -match $pattern) { $list.RemoveAt($i) }
        }
    }

    # 2) [options] 섹션 위치 찾기 (없으면 파일 끝에 새로 만든다)
    $optIndex = -1
    for ($i = 0; $i -lt $list.Count; $i++) {
        if ($list[$i].Trim() -eq '[options]') { $optIndex = $i; break }
    }
    if ($optIndex -lt 0) {
        if ($list.Count -gt 0 -and $list[$list.Count - 1].Trim() -ne '') { $list.Add('') }
        $list.Add('[options]')
        $optIndex = $list.Count - 1
    }

    # 3) [options] 바로 아래에 키를 삽입
    $insertAt = $optIndex + 1
    foreach ($key in ($Options.Keys | Sort-Object)) {
        $list.Insert($insertAt, ("{0} = '{1}'" -f $key, $Options[$key]))
        $insertAt++
    }

    # RustDesk 는 BOM 없는 UTF-8 을 기대하므로 BOM 없이 저장
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($Path, $list, $utf8NoBom)
}

# ------------------------------------------------------- 0. 관리자 권한 확인 --
if (-not (Test-Admin)) {
    Write-Host ""
    Write-Host "이 스크립트는 관리자 권한이 필요합니다." -ForegroundColor Red
    Write-Host "PowerShell 을 [관리자 권한으로 실행] 한 뒤 다시 실행하세요." -ForegroundColor Red
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "======================================================" -ForegroundColor White
Write-Host " RustDesk 무인 접속 설정 (승인 클릭 없이 폰에서 연결)" -ForegroundColor White
Write-Host "======================================================" -ForegroundColor White

# --------------------------------------------- 1. RustDesk 잠시 멈추기 -------
Write-Step "RustDesk 를 잠시 멈춥니다 (설정 파일 덮어쓰기 방지)"

$service = Get-Service -Name 'RustDesk' -ErrorAction SilentlyContinue
if ($service) {
    if ($service.Status -ne 'Stopped') {
        Stop-Service -Name 'RustDesk' -Force -ErrorAction SilentlyContinue
        Write-Ok "RustDesk 서비스 중지"
    } else {
        Write-Info "RustDesk 서비스는 이미 중지 상태"
    }
} else {
    Write-Warn "RustDesk 서비스가 없습니다. 무인 접속에는 '설치판'(서비스 모드)이 필요합니다."
    Write-Info "휴대용(portable) exe 만 쓰고 있다면 공식 설치판으로 설치한 뒤 다시 실행하세요."
}

Get-Process -Name 'rustdesk' -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Ok "rustdesk.exe 프로세스 정리 완료"

# ------------------------------------------- 2. 설정 파일 위치 모으기 --------
Write-Step "RustDesk 설정 파일(RustDesk2.toml)을 찾습니다"

$configRoots = [System.Collections.Generic.List[string]]::new()

# (a) 현재 사용자 + 모든 로컬 사용자 프로필
$userRoots = @()
if ($env:APPDATA) { $userRoots += (Join-Path $env:APPDATA 'RustDesk\config') }
$usersDir = Join-Path $env:SystemDrive 'Users'
if (Test-Path -LiteralPath $usersDir) {
    Get-ChildItem -LiteralPath $usersDir -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { $userRoots += (Join-Path $_.FullName 'AppData\Roaming\RustDesk\config') }
}

# (b) 서비스가 쓰는 시스템 계정 프로필 (버전/설치 방식에 따라 위치가 다름)
$serviceRoots = @(
    (Join-Path $env:SystemRoot 'ServiceProfiles\LocalService\AppData\Roaming\RustDesk\config'),
    (Join-Path $env:SystemRoot 'ServiceProfiles\NetworkService\AppData\Roaming\RustDesk\config'),
    (Join-Path $env:SystemRoot 'System32\config\systemprofile\AppData\Roaming\RustDesk\config')
)

foreach ($root in ($userRoots + $serviceRoots)) {
    if ($root -and -not $configRoots.Contains($root)) { $configRoots.Add($root) }
}

$existingRoots = @($configRoots | Where-Object { Test-Path -LiteralPath $_ })
if ($existingRoots.Count -eq 0) {
    Write-Warn "기존 설정 폴더를 못 찾았습니다. RustDesk 를 한 번 실행해 설정을 생성한 뒤 다시 돌려주세요."
} else {
    foreach ($root in $existingRoots) { Write-Info $root }
}

# ------------------------------------------ 3. 무인 접속 옵션 기록 -----------
Write-Step "무인 접속 옵션을 기록합니다"

$desired = @{
    'verification-method'               = 'use-permanent-password'  # 영구 비밀번호만 사용
    'approve-mode'                      = 'password'                # 비밀번호만으로 승인 (수락 클릭 없음)
    'allow-remote-config-modification'  = 'N'                       # 원격에서 이 설정 변경 금지
}

$patched = 0
foreach ($root in $existingRoots) {
    $toml = Join-Path $root 'RustDesk2.toml'
    try {
        Set-TomlOptions -Path $toml -Options $desired
        Write-Ok "적용: $toml"
        $patched++
    } catch {
        Write-Warn "적용 실패: $toml ($($_.Exception.Message))"
    }
}
if ($patched -eq 0) { Write-Warn "적용된 설정 파일이 없습니다. RustDesk 설정 창에서 직접 지정하세요 (가이드 참고)." }

# ------------------------------------ 4. 영구 비밀번호 존재 여부 확인 --------
Write-Step "영구 비밀번호가 저장돼 있는지 확인합니다"

$hasPassword = $false
foreach ($root in $existingRoots) {
    $main = Join-Path $root 'RustDesk.toml'
    if (-not (Test-Path -LiteralPath $main)) { continue }
    $content = Get-Content -LiteralPath $main -Raw -ErrorAction SilentlyContinue
    if ($content -match "(?m)^\s*password\s*=\s*'([^']+)'") { $hasPassword = $true; break }
    if ($content -match '(?m)^\s*password\s*=\s*"([^"]+)"') { $hasPassword = $true; break }
}

if ($hasPassword) {
    Write-Ok "영구 비밀번호가 저장되어 있습니다."
} else {
    Write-Warn "영구 비밀번호가 비어 있습니다!"
    Write-Info "RustDesk 창 -> 설정 -> 보안 -> '영구 비밀번호' 에서 비밀번호를 지정하고 확인을 누르세요."
    Write-Info "비밀번호가 없으면 폰에서 붙을 때 계속 PC 쪽 '수락' 클릭을 요구합니다."
}

# ------------------------------------- 5. 서비스 자동 시작 + 시작 ------------
Write-Step "RustDesk 서비스를 '자동 시작' 으로 설정합니다"

if ($service) {
    & "$env:SystemRoot\System32\sc.exe" config RustDesk start= auto | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Ok "서비스 시작 유형: 자동(Automatic)" }
    else { Write-Warn "서비스 시작 유형 변경 실패 (sc.exe 종료 코드 $LASTEXITCODE)" }

    # 재부팅 직후 네트워크가 늦게 올라와 실패했을 때 스스로 재시도하도록
    & "$env:SystemRoot\System32\sc.exe" failure RustDesk reset= 60 actions= restart/5000/restart/5000/restart/5000 | Out-Null

    try {
        Start-Service -Name 'RustDesk'
        Write-Ok "서비스 시작됨"
    } catch {
        Write-Warn "서비스 시작 실패: $($_.Exception.Message)"
    }
} else {
    Write-Warn "RustDesk 서비스가 없어 건너뜁니다."
}

# ----------------------------------------- 6. 트레이 앱 시작 프로그램 -------
if (-not $SkipTrayAutostart) {
    Write-Step "시작 프로그램에 RustDesk 트레이 앱을 등록합니다"

    $programDirs = @($env:ProgramFiles, ${env:ProgramFiles(x86)}) |
        Where-Object { $_ -and $_.Trim() -ne '' }
    $exeCandidates = @(
        foreach ($dir in $programDirs) { Join-Path $dir 'RustDesk\rustdesk.exe' }
    ) | Where-Object { Test-Path -LiteralPath $_ }

    if ($exeCandidates.Count -gt 0) {
        $exe = $exeCandidates[0]
        $runKey = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run'
        Set-ItemProperty -Path $runKey -Name 'RustDesk' -Value ('"{0}" --tray' -f $exe) -Type String
        Write-Ok "등록: $exe --tray"
        Write-Info "무인 접속은 서비스가 담당하므로, 트레이 앱은 상태 확인용입니다."
    } else {
        Write-Warn "rustdesk.exe 를 Program Files 에서 찾지 못해 건너뜁니다."
    }
} else {
    Write-Info "시작 프로그램 등록은 -SkipTrayAutostart 옵션으로 건너뜀"
}

# ------------------------------------------------- 7. 절전 방지 --------------
if (-not $SkipPowerSettings) {
    Write-Step "PC 가 자버려서 폰에서 못 붙는 일을 막습니다 (AC 전원 기준)"

    & "$env:SystemRoot\System32\powercfg.exe" /change standby-timeout-ac 0   | Out-Null
    & "$env:SystemRoot\System32\powercfg.exe" /change hibernate-timeout-ac 0 | Out-Null
    Write-Ok "절전/최대 절전 시간: 사용 안 함"
    Write-Info "모니터 꺼짐 시간은 그대로 뒀습니다 (원격 접속에는 영향 없음)."
} else {
    Write-Info "절전 설정은 -SkipPowerSettings 옵션으로 건너뜀"
}

# ------------------------------------------------------ 마무리 ---------------
Write-Host ""
Write-Host "------------------------------------------------------" -ForegroundColor White
Write-Host " 남은 할 일" -ForegroundColor White
Write-Host "------------------------------------------------------" -ForegroundColor White
Write-Host ""
Write-Host " 1. (아직 안 했다면) RustDesk -> 설정 -> 보안 -> 영구 비밀번호 지정" -ForegroundColor White
Write-Host " 2. PC 를 한 번 재부팅" -ForegroundColor White
Write-Host " 3. 폰 RustDesk 앱에서 PC 의 ID 입력 -> 영구 비밀번호 입력" -ForegroundColor White
Write-Host "    -> '비밀번호 저장' 체크 후 연결" -ForegroundColor White
Write-Host " 4. 이후부터는 PC 에서 아무 것도 누르지 않아도 바로 연결됩니다." -ForegroundColor White
Write-Host ""

# 적용 결과 확인용 출력
Write-Step "현재 기록된 값 확인"
foreach ($root in $existingRoots) {
    $toml = Join-Path $root 'RustDesk2.toml'
    if (-not (Test-Path -LiteralPath $toml)) { continue }
    Write-Host "  [$toml]" -ForegroundColor DarkGray
    Select-String -LiteralPath $toml -Pattern 'verification-method|approve-mode|allow-remote-config-modification' |
        ForEach-Object { Write-Host "    $($_.Line.Trim())" -ForegroundColor Gray }
}
Write-Host ""
