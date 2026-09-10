<#
.SYNOPSIS
    설정이 제대로 됐는지 확인만 하는 진단 스크립트. 아무것도 바꾸지 않습니다.

.DESCRIPTION
    RustDesk 무인 접속 설정과 스크린샷 단축키 설정 상태를 한 번에 보여 줍니다.
    문제가 있을 때 이 결과를 그대로 복사해서 보내주시면 원인을 짚기 쉽습니다.

    읽기만 하는 스크립트라서 관리자 권한 없이 실행해도 되고,
    실행해도 설정이 변하지 않습니다.

.PARAMETER Folder
    확인할 스크린샷 폴더. 기본값 D:\스크린샷

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\Check-Status.ps1
#>
[CmdletBinding()]
param(
    [string]$Folder = 'D:\스크린샷'
)

# 진단 스크립트는 중간에 멈추지 않고 끝까지 훑는 게 목적
$ErrorActionPreference = 'Continue'

# 한글은 콘솔에서 두 칸을 차지하므로, 글자 수가 아니라 표시 폭으로 줄을 맞춘다
function Get-DisplayWidth { param([string]$S)
    $w = 0
    foreach ($ch in $S.ToCharArray()) {
        $c = [int]$ch
        if (($c -ge 0x1100 -and $c -le 0x115F) -or ($c -ge 0x2E80 -and $c -le 0xA4CF) -or
            ($c -ge 0xAC00 -and $c -le 0xD7A3) -or ($c -ge 0xF900 -and $c -le 0xFAFF) -or
            ($c -ge 0xFE30 -and $c -le 0xFE6F) -or ($c -ge 0xFF00 -and $c -le 0xFF60) -or
            ($c -ge 0xFFE0 -and $c -le 0xFFE6)) { $w += 2 } else { $w += 1 }
    }
    return $w
}
function Pad-Display { param([string]$S, [int]$Width)
    $S + (' ' * [Math]::Max(1, $Width - (Get-DisplayWidth $S)))
}

function Write-Section { param([string]$T)
    Write-Host ""
    Write-Host "=== $T " -ForegroundColor Cyan -NoNewline
    Write-Host ("=" * [Math]::Max(3, 58 - (Get-DisplayWidth $T))) -ForegroundColor Cyan
}
function Write-Row { param([string]$Label, [string]$Value, [string]$State = 'info')
    $color = switch ($State) { 'good' { 'Green' } 'bad' { 'Red' } 'warn' { 'Yellow' } default { 'Gray' } }
    $mark  = switch ($State) { 'good' { 'O' } 'bad' { 'X' } 'warn' { '!' } default { ' ' } }
    Write-Host ("  [{0}] {1}" -f $mark, (Pad-Display $Label 26)) -NoNewline
    Write-Host $Value -ForegroundColor $color
}

Write-Host ""
Write-Host "############################################################" -ForegroundColor White
Write-Host "  설정 상태 확인 (읽기 전용 - 아무것도 바꾸지 않습니다)" -ForegroundColor White
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')   PC: $env:COMPUTERNAME   사용자: $env:USERNAME" -ForegroundColor DarkGray
Write-Host "############################################################" -ForegroundColor White

Write-Host ""
Write-Host ("  Windows : " + (Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue).Caption) -ForegroundColor DarkGray
Write-Host ("  PowerShell : " + $PSVersionTable.PSVersion.ToString()) -ForegroundColor DarkGray

# =========================================================== RustDesk =======
Write-Section "1. RustDesk 무인 접속"

$svc = Get-Service -Name 'RustDesk' -ErrorAction SilentlyContinue
if ($svc) {
    Write-Row '서비스 상태' $svc.Status ($(if ($svc.Status -eq 'Running') { 'good' } else { 'bad' }))
    $startType = try { (Get-CimInstance Win32_Service -Filter "Name='RustDesk'" -ErrorAction Stop).StartMode } catch { 'unknown' }
    Write-Row '시작 유형' $startType ($(if ($startType -in @('Auto', 'Automatic')) { 'good' } else { 'bad' }))
} else {
    Write-Row '서비스' '설치되지 않음 (무인 접속에는 설치판/서비스 모드 필요)' 'bad'
}

# 설정 파일 훑기
$roots = @()
if ($env:APPDATA) { $roots += (Join-Path $env:APPDATA 'RustDesk\config') }
$roots += @(
    (Join-Path $env:SystemRoot 'ServiceProfiles\LocalService\AppData\Roaming\RustDesk\config'),
    (Join-Path $env:SystemRoot 'ServiceProfiles\NetworkService\AppData\Roaming\RustDesk\config'),
    (Join-Path $env:SystemRoot 'System32\config\systemprofile\AppData\Roaming\RustDesk\config')
)

$anyConfig = $false
$goodConfig = $false
$passwordSet = $false
$rustdeskId = $null

foreach ($root in ($roots | Select-Object -Unique)) {
    $toml = Join-Path $root 'RustDesk2.toml'
    $main = Join-Path $root 'RustDesk.toml'
    if (-not (Test-Path -LiteralPath $toml) -and -not (Test-Path -LiteralPath $main)) { continue }
    $anyConfig = $true

    Write-Host ""
    Write-Host "  경로: $root" -ForegroundColor DarkGray

    if (Test-Path -LiteralPath $toml) {
        $text = Get-Content -LiteralPath $toml -Raw -ErrorAction SilentlyContinue
        $vm = if ($text -match "(?m)^\s*verification-method\s*=\s*['`"]?([^'`"\r\n]+)") { $Matches[1].Trim() } else { '(없음 - 기본값)' }
        $am = if ($text -match "(?m)^\s*approve-mode\s*=\s*['`"]?([^'`"\r\n]+)")        { $Matches[1].Trim() } else { '(없음 - 기본값)' }
        Write-Row 'verification-method' $vm ($(if ($vm -eq 'use-permanent-password') { 'good' } else { 'bad' }))
        Write-Row 'approve-mode'        $am ($(if ($am -eq 'password') { 'good' } else { 'bad' }))
        if ($vm -eq 'use-permanent-password' -and $am -eq 'password') { $goodConfig = $true }
        Write-Row '백업 파일(.bak)' $(if (Test-Path -LiteralPath "$toml.bak") { '있음' } else { '없음' })
    } else {
        Write-Row 'RustDesk2.toml' '없음' 'warn'
    }

    if (Test-Path -LiteralPath $main) {
        $mtext = Get-Content -LiteralPath $main -Raw -ErrorAction SilentlyContinue
        $hasPw = ($mtext -match "(?m)^\s*password\s*=\s*'([^']+)'") -or ($mtext -match '(?m)^\s*password\s*=\s*"([^"]+)"')
        if ($hasPw) { $passwordSet = $true }
        Write-Row '영구 비밀번호' $(if ($hasPw) { '설정됨' } else { '비어 있음 - GUI에서 지정 필요' }) $(if ($hasPw) { 'good' } else { 'bad' })
        if (-not $rustdeskId -and $mtext -match "(?m)^\s*id\s*=\s*'([^']+)'") { $rustdeskId = $Matches[1] }
    }
}

if (-not $anyConfig) {
    Write-Row '설정 파일' '찾을 수 없음 (RustDesk를 한 번 실행하세요)' 'bad'
}
Write-Host ""
if ($rustdeskId) { Write-Row 'RustDesk ID' $rustdeskId }

# 시작 프로그램 등록
$runVal = $null
foreach ($hive in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
                    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run')) {
    $v = (Get-ItemProperty -Path $hive -Name 'RustDesk' -ErrorAction SilentlyContinue).RustDesk
    if ($v) { $runVal = "$v   ($hive)"; break }
}
Write-Row '시작 프로그램 등록' $(if ($runVal) { $runVal } else { '없음' }) $(if ($runVal) { 'good' } else { 'warn' })

# 절전 설정 (powercfg 출력의 마지막 두 hex = AC, DC 설정 인덱스)
$raw = (& "$env:SystemRoot\System32\powercfg.exe" /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE 2>&1) -join "`n"
$hexes = @([regex]::Matches($raw, '0x[0-9a-fA-F]{8}') | ForEach-Object { $_.Value })
if ($hexes.Count -ge 2) {
    $acSeconds = [Convert]::ToInt64($hexes[-2], 16)
    $desc = if ($acSeconds -eq 0) { '사용 안 함 (좋음)' } else { "$([Math]::Round($acSeconds / 60)) 분 후 절전" }
    Write-Row '절전 (AC 전원)' $desc $(if ($acSeconds -eq 0) { 'good' } else { 'warn' })
} else {
    Write-Row '절전 (AC 전원)' '확인 불가' 'warn'
}

# ========================================================= 스크린샷 =========
Write-Section "2. Ctrl+PrintScreen 스크린샷"

# 윈도우 '스크린샷' 기본 폴더 위치
$guidName = '{B7BEDE81-DF94-4682-A7D8-57A52620B86F}'
$usf = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
$shotPath = (Get-ItemProperty -Path $usf -Name $guidName -ErrorAction SilentlyContinue).$guidName
if ($shotPath) {
    $shotPath = [Environment]::ExpandEnvironmentVariables($shotPath)
} else {
    $shotPath = Join-Path ([Environment]::GetFolderPath('MyPictures')) 'Screenshots'
    $shotPath += '  (레지스트리 값 없음 = 윈도우 기본 위치)'
}
$relocated = $shotPath -like "$Folder*"
Write-Row "'스크린샷' 폴더 위치" $shotPath $(if ($relocated) { 'good' } else { 'warn' })

# 저장 폴더
if (Test-Path -LiteralPath $Folder) {
    $files = @(Get-ChildItem -LiteralPath $Folder -File -ErrorAction SilentlyContinue)
    Write-Row '저장 폴더' "$Folder  (파일 $($files.Count) 개)" 'good'
    if ($files.Count -gt 0) {
        $newest = $files | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        Write-Row '가장 최근 파일' "$($newest.Name)  ($($newest.LastWriteTime))"
    }
} else {
    Write-Row '저장 폴더' "$Folder 없음" 'bad'
}

# AutoHotkey
$ahkProc = @(Get-Process -Name 'AutoHotkey*' -ErrorAction SilentlyContinue)
$ahkFound = $null
foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, (Join-Path $env:LOCALAPPDATA 'Programs'))) {
    if (-not $base) { continue }
    foreach ($rel in @('AutoHotkey\v2\AutoHotkey64.exe','AutoHotkey\v2\AutoHotkey32.exe',
                       'AutoHotkey\AutoHotkey64.exe','AutoHotkey\AutoHotkey32.exe','AutoHotkey\AutoHotkey.exe')) {
        $p = Join-Path $base $rel
        if (Test-Path -LiteralPath $p) { $ahkFound = $p; break }
    }
    if ($ahkFound) { break }
}
Write-Row 'AutoHotkey 설치' $(if ($ahkFound) { $ahkFound } else { '없음 - winget install --id AutoHotkey.AutoHotkey' }) $(if ($ahkFound) { 'good' } else { 'bad' })
Write-Row 'AutoHotkey 실행 중' $(if ($ahkProc.Count -gt 0) { "예 ($($ahkProc.Count) 개)" } else { '아니오 - 단축키가 동작하지 않습니다' }) $(if ($ahkProc.Count -gt 0) { 'good' } else { 'bad' })

# 설치된 스크립트 + MODE
$installed = Join-Path $env:LOCALAPPDATA 'CtrlPrintScreen\CtrlPrintScreen.ahk'
if (Test-Path -LiteralPath $installed) {
    $ahkText = Get-Content -LiteralPath $installed -Raw
    $mode = if ($ahkText -match '(?m)^\s*MODE\s*:=\s*"([^"]+)"')        { $Matches[1] } else { '?' }
    $sf   = if ($ahkText -match '(?m)^\s*SAVE_FOLDER\s*:=\s*"([^"]+)"') { $Matches[1] } else { '?' }
    Write-Row '설치된 AHK 스크립트' $installed 'good'
    Write-Row '  MODE' $mode
    Write-Row '  SAVE_FOLDER' $sf $(if ($sf -eq $Folder) { 'good' } else { 'warn' })
    if ($mode -eq 'native' -and -not $relocated) {
        Write-Host "      -> native 모드인데 폴더 이동이 안 됐습니다. -Mode script 로 다시 설치하세요." -ForegroundColor Yellow
    }
    Write-Row '  Capture-Screen.ps1' $(if (Test-Path -LiteralPath (Join-Path (Split-Path $installed) 'Capture-Screen.ps1')) { '있음' } else { '없음' })
} else {
    Write-Row '설치된 AHK 스크립트' '없음 - 2-Setup-Screenshot.cmd 를 실행하세요' 'bad'
}

# 시작 폴더 바로가기
$lnk = Join-Path ([Environment]::GetFolderPath('Startup')) 'CtrlPrintScreen.lnk'
Write-Row '시작 프로그램 바로가기' $(if (Test-Path -LiteralPath $lnk) { $lnk } else { '없음' }) $(if (Test-Path -LiteralPath $lnk) { 'good' } else { 'bad' })

# ============================================================= 요약 =========
Write-Section "요약"

if ($goodConfig -and $passwordSet -and $svc -and $svc.Status -eq 'Running') {
    Write-Host "  RustDesk   : 무인 접속 준비 완료 - 폰에서 ID + 영구 비밀번호로 접속하세요" -ForegroundColor Green
} else {
    Write-Host "  RustDesk   : 아직 설정이 남았습니다" -ForegroundColor Yellow
    if (-not $svc)            { Write-Host "    - RustDesk 설치판(서비스 모드)이 필요합니다" -ForegroundColor Yellow }
    elseif ($svc.Status -ne 'Running') { Write-Host "    - 서비스가 실행 중이 아닙니다" -ForegroundColor Yellow }
    if (-not $passwordSet)    { Write-Host "    - 설정 -> 보안 -> 영구 비밀번호를 지정하세요" -ForegroundColor Yellow }
    if (-not $goodConfig)     { Write-Host "    - 1-Setup-RustDesk.cmd 를 관리자 권한으로 실행하세요" -ForegroundColor Yellow }
}

$shotOk = (Test-Path -LiteralPath $Folder) -and $ahkFound -and ($ahkProc.Count -gt 0) -and (Test-Path -LiteralPath $installed)
if ($shotOk) {
    Write-Host "  스크린샷   : 준비 완료 - Ctrl+PrintScreen 을 눌러 보세요" -ForegroundColor Green
} else {
    Write-Host "  스크린샷   : 아직 설정이 남았습니다" -ForegroundColor Yellow
    if (-not $ahkFound)              { Write-Host "    - AutoHotkey v2 를 설치하세요: winget install --id AutoHotkey.AutoHotkey" -ForegroundColor Yellow }
    if (-not (Test-Path -LiteralPath $installed)) { Write-Host "    - 2-Setup-Screenshot.cmd 를 실행하세요" -ForegroundColor Yellow }
    elseif ($ahkProc.Count -eq 0)    { Write-Host "    - 시작 프로그램 바로가기를 실행하거나 재부팅하세요" -ForegroundColor Yellow }
}

Write-Host ""
Write-Host "  이 화면 전체를 복사해서 보내주시면 원인을 짚어 드립니다." -ForegroundColor DarkGray
Write-Host "  (창 안에서 우클릭 -> 모두 선택 -> Enter 로 복사)" -ForegroundColor DarkGray
Write-Host ""
