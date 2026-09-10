<#
.SYNOPSIS
    Ctrl + PrintScreen 으로 전체 화면을 캡처해 D:\스크린샷 에 자동 저장되게 설정합니다.

.DESCRIPTION
    처리 내용

      1) 저장 폴더(기본 D:\스크린샷)를 만든다.
      2) 윈도우의 '스크린샷'(Screenshots) 기본 폴더 위치를 그 폴더로 옮긴다.
         -> 이걸 해두면 Win+PrintScreen 만 눌러도 D 드라이브에 바로 저장된다.
      3) Capture-Screen.ps1 / CtrlPrintScreen.ahk 를 설치 폴더로 복사하고
         저장 경로와 동작 모드를 스크립트 안에 박아 넣는다.
      4) AutoHotkey 를 찾아 시작 프로그램(시작 폴더)에 바로가기를 만든다.
         -> 부팅할 때마다 Ctrl+PrintScreen 단축키가 자동으로 살아난다.
      5) 지금 바로 한 번 실행해서 단축키를 활성화한다.

.PARAMETER Folder
    스크린샷 저장 폴더. 기본값 D:\스크린샷

.PARAMETER Mode
    native : Windows 기본 Win+PrintScreen 을 대신 눌러 준다 (빠름, 기본값)
    script : Capture-Screen.ps1 로 직접 캡처한다 (폴더 위치 변경에 의존하지 않음)

.PARAMETER InstallDir
    스크립트를 설치할 폴더. 기본값 %LOCALAPPDATA%\CtrlPrintScreen

.PARAMETER SkipFolderRelocation
    윈도우 '스크린샷' 기본 폴더 위치는 그대로 두고 단축키만 설정합니다.
    (이 경우 -Mode script 를 함께 쓰세요)

.EXAMPLE
    # 일반 사용자 권한 PowerShell 에서 (관리자 권한 필요 없음!)
    powershell -ExecutionPolicy Bypass -File .\Setup-ScreenshotHotkey.ps1

.EXAMPLE
    # 폴더 위치는 안 건드리고, 직접 캡처 방식으로만 쓰고 싶을 때
    powershell -ExecutionPolicy Bypass -File .\Setup-ScreenshotHotkey.ps1 -Mode script -SkipFolderRelocation

.NOTES
    관리자 권한으로 실행하면 '관리자 계정'의 폴더 설정이 바뀔 수 있으므로,
    평소 쓰는 계정에서 그냥 실행하는 것이 좋습니다.
#>
[CmdletBinding()]
param(
    [string]$Folder = 'D:\스크린샷',
    [ValidateSet('native', 'script')]
    [string]$Mode = 'native',
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'CtrlPrintScreen'),
    [switch]$SkipFolderRelocation
)

$ErrorActionPreference = 'Stop'

function Write-Step { param([string]$Text) Write-Host ""; Write-Host "==> $Text" -ForegroundColor Cyan }
function Write-Ok   { param([string]$Text) Write-Host "    [OK]   $Text" -ForegroundColor Green }
function Write-Warn { param([string]$Text) Write-Host "    [주의] $Text" -ForegroundColor Yellow }
function Write-Info { param([string]$Text) Write-Host "    -      $Text" -ForegroundColor Gray }

$scriptRoot = $PSScriptRoot
if (-not $scriptRoot) { $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path }

Write-Host ""
Write-Host "==========================================================" -ForegroundColor White
Write-Host " Ctrl+PrintScreen -> 전체 화면 캡처 -> $Folder" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor White

# ------------------------------------------------ 1. 저장 폴더 만들기 --------
Write-Step "저장 폴더를 준비합니다"

$drive = [System.IO.Path]::GetPathRoot($Folder)
if (-not (Test-Path -LiteralPath $drive)) {
    Write-Host ""
    Write-Host "$drive 드라이브를 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "-Folder 옵션으로 다른 경로를 지정하세요. 예: -Folder 'C:\스크린샷'" -ForegroundColor Red
    Write-Host ""
    exit 1
}

if (-not (Test-Path -LiteralPath $Folder)) {
    New-Item -ItemType Directory -Path $Folder -Force | Out-Null
    Write-Ok "폴더 생성: $Folder"
} else {
    Write-Ok "폴더 확인: $Folder"
}

# -------------------------------- 2. 윈도우 '스크린샷' 폴더 위치 변경 --------
if (-not $SkipFolderRelocation) {
    Write-Step "윈도우 기본 '스크린샷' 폴더를 $Folder 로 옮깁니다"

    if (-not ('ScreenshotSetup.KnownFolder' -as [type])) {
        Add-Type -Namespace 'ScreenshotSetup' -Name 'KnownFolder' -MemberDefinition @'
[DllImport("shell32.dll", CharSet = CharSet.Unicode)]
public static extern int SHSetKnownFolderPath(ref Guid rfid, uint dwFlags, IntPtr hToken, string pszPath);

[DllImport("shell32.dll", CharSet = CharSet.Unicode)]
public static extern void SHChangeNotify(int wEventId, uint uFlags, IntPtr dwItem1, IntPtr dwItem2);
'@
    }

    # FOLDERID_Screenshots
    $screenshotsGuid = [Guid]'b7bede81-df94-4682-a7d8-57a52620b86f'
    $relocated = $false
    try {
        $hr = [ScreenshotSetup.KnownFolder]::SHSetKnownFolderPath([ref]$screenshotsGuid, 0, [IntPtr]::Zero, $Folder)
        if ($hr -eq 0) {
            $relocated = $true
            Write-Ok "'스크린샷' 기본 폴더 위치 변경 완료"
            # SHCNE_ASSOCCHANGED = 0x08000000 -> 탐색기에 변경 알림
            [ScreenshotSetup.KnownFolder]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
        } else {
            Write-Warn ("SHSetKnownFolderPath 실패 (HRESULT 0x{0:X8}) - 레지스트리로 재시도" -f $hr)
        }
    } catch {
        Write-Warn "SHSetKnownFolderPath 호출 실패 - 레지스트리로 재시도: $($_.Exception.Message)"
    }

    if (-not $relocated) {
        $guidName = '{B7BEDE81-DF94-4682-A7D8-57A52620B86F}'
        $userShell = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
        $shell     = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        try {
            New-ItemProperty -Path $userShell -Name $guidName -Value $Folder -PropertyType ExpandString -Force | Out-Null
            New-ItemProperty -Path $shell     -Name $guidName -Value $Folder -PropertyType String       -Force | Out-Null
            Write-Ok "레지스트리로 폴더 위치 지정 완료 (로그아웃 후 다시 로그인하면 적용)"
        } catch {
            Write-Warn "레지스트리 변경도 실패했습니다: $($_.Exception.Message)"
            Write-Info "수동 방법: 사진 폴더 안의 '스크린샷' 폴더 우클릭 -> 속성 -> 위치 -> 이동"
            Write-Info "또는 이 스크립트를 '-Mode script -SkipFolderRelocation' 으로 다시 실행하세요."
        }
    }

    # 파일 번호(Screenshot (1).png ...) 카운터 초기화
    try {
        Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer' `
            -Name 'ScreenshotIndex' -Value 1 -Type DWord
        Write-Ok "스크린샷 번호 카운터 초기화"
    } catch {
        Write-Info "번호 카운터 초기화는 건너뜀 (동작에 영향 없음)"
    }
} else {
    Write-Info "'스크린샷' 폴더 위치 변경은 -SkipFolderRelocation 옵션으로 건너뜀"
    if ($Mode -eq 'native') {
        Write-Warn "-SkipFolderRelocation 을 쓰면서 -Mode native 면 D 드라이브에 저장되지 않습니다."
        Write-Info "'-Mode script' 를 함께 쓰는 것을 권합니다."
    }
}

# ------------------------------------------- 3. 스크립트 설치 + 경로 주입 ----
Write-Step "스크립트를 설치합니다"

if (-not (Test-Path -LiteralPath $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$srcCapture = Join-Path $scriptRoot 'Capture-Screen.ps1'
$srcAhk     = Join-Path $scriptRoot 'CtrlPrintScreen.ahk'
foreach ($src in @($srcCapture, $srcAhk)) {
    if (-not (Test-Path -LiteralPath $src)) {
        Write-Host ""
        Write-Host "필요한 파일이 없습니다: $src" -ForegroundColor Red
        Write-Host "Capture-Screen.ps1, CtrlPrintScreen.ahk 를 이 스크립트와 같은 폴더에 두세요." -ForegroundColor Red
        Write-Host ""
        exit 1
    }
}

$dstCapture = Join-Path $InstallDir 'Capture-Screen.ps1'
$dstAhk     = Join-Path $InstallDir 'CtrlPrintScreen.ahk'
Copy-Item -LiteralPath $srcCapture -Destination $dstCapture -Force
Write-Ok "복사: $dstCapture"

# AHK 파일 안의 MODE / SAVE_FOLDER 값을 실제 선택값으로 바꿔 저장
$ahkLines = [System.IO.File]::ReadAllLines($srcAhk)
for ($i = 0; $i -lt $ahkLines.Count; $i++) {
    if ($ahkLines[$i] -match '^\s*MODE\s*:=') {
        $ahkLines[$i] = ('MODE           := "{0}"' -f $Mode)
    } elseif ($ahkLines[$i] -match '^\s*SAVE_FOLDER\s*:=') {
        $ahkLines[$i] = ('SAVE_FOLDER    := "{0}"' -f $Folder)
    }
}
# AutoHotkey 는 한글을 읽으려면 BOM 있는 UTF-8 이 필요하다
[System.IO.File]::WriteAllLines($dstAhk, $ahkLines, (New-Object System.Text.UTF8Encoding($true)))
Write-Ok "복사: $dstAhk  (MODE=$Mode)"

# ------------------------------------------------- 4. AutoHotkey 찾기 -------
Write-Step "AutoHotkey 를 찾습니다"

$ahkCandidates = @()
foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, (Join-Path $env:LOCALAPPDATA 'Programs'))) {
    if (-not $base) { continue }
    $ahkCandidates += @(
        (Join-Path $base 'AutoHotkey\v2\AutoHotkey64.exe'),
        (Join-Path $base 'AutoHotkey\v2\AutoHotkey32.exe'),
        (Join-Path $base 'AutoHotkey\AutoHotkey64.exe'),
        (Join-Path $base 'AutoHotkey\AutoHotkey32.exe'),
        (Join-Path $base 'AutoHotkey\AutoHotkey.exe')
    )
}
try {
    $regDir = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\AutoHotkey' -Name 'InstallDir' -ErrorAction Stop).InstallDir
    if ($regDir) {
        $ahkCandidates += @(
            (Join-Path $regDir 'v2\AutoHotkey64.exe'),
            (Join-Path $regDir 'AutoHotkey64.exe'),
            (Join-Path $regDir 'AutoHotkey.exe')
        )
    }
} catch { }

$ahkExe = $ahkCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1

if ($ahkExe) {
    Write-Ok "발견: $ahkExe"
} else {
    Write-Warn "AutoHotkey 가 설치되어 있지 않습니다."
    Write-Info "설치 방법 1:  winget install --id AutoHotkey.AutoHotkey"
    Write-Info "설치 방법 2:  https://www.autohotkey.com  (v2 다운로드)"
    Write-Info "설치한 뒤 이 스크립트를 다시 실행하세요."
    Write-Info "AutoHotkey 없이 쓰려면 PowerToys 의 '키보드 관리자' 로"
    Write-Info "Ctrl+PrintScreen -> Win+PrintScreen 리맵을 등록해도 됩니다."
}

# ------------------------------------- 5. 시작 프로그램 등록 + 즉시 실행 ----
Write-Step "시작 프로그램에 등록합니다"

$startupDir  = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupDir 'CtrlPrintScreen.lnk'

try {
    $wshell = New-Object -ComObject WScript.Shell
    $shortcut = $wshell.CreateShortcut($shortcutPath)
    if ($ahkExe) {
        $shortcut.TargetPath = $ahkExe
        $shortcut.Arguments  = ('"{0}"' -f $dstAhk)
    } else {
        # AHK 가 없으면 파일 연결에 맡긴다 (설치 후 자동으로 동작)
        $shortcut.TargetPath = $dstAhk
    }
    $shortcut.WorkingDirectory = $InstallDir
    $shortcut.Description      = "Ctrl+PrintScreen -> $Folder"
    $shortcut.Save()
    Write-Ok "바로가기 생성: $shortcutPath"
} catch {
    Write-Warn "시작 프로그램 등록 실패: $($_.Exception.Message)"
    Write-Info "수동 방법: Win+R -> shell:startup -> 아래 파일의 바로가기를 넣기"
    Write-Info "  $dstAhk"
}

if ($ahkExe) {
    Write-Step "단축키를 지금 바로 켭니다"
    try {
        # 같은 스크립트가 이미 돌고 있으면 #SingleInstance Force 가 알아서 교체한다
        Start-Process -FilePath $ahkExe -ArgumentList ('"{0}"' -f $dstAhk) -WorkingDirectory $InstallDir
        Write-Ok "실행됨 - 이제 Ctrl+PrintScreen 을 눌러 보세요"
    } catch {
        Write-Warn "실행 실패: $($_.Exception.Message)"
    }
}

# ------------------------------------------------------- 마무리 -------------
Write-Host ""
Write-Host "----------------------------------------------------------" -ForegroundColor White
Write-Host " 설정 요약" -ForegroundColor White
Write-Host "----------------------------------------------------------" -ForegroundColor White
Write-Host "  저장 폴더        : $Folder"
Write-Host "  단축키           : Ctrl + PrintScreen (전체 화면)"
Write-Host "  동작 모드        : $Mode"
Write-Host "  설치 위치        : $InstallDir"
Write-Host "  시작 프로그램    : $shortcutPath"
Write-Host ""
Write-Host "  * Win + PrintScreen 도 같은 폴더에 저장됩니다." -ForegroundColor Gray
Write-Host "  * 캡처가 안 되면 CtrlPrintScreen.ahk 의 MODE 를" -ForegroundColor Gray
Write-Host '    "script" 로 바꾸고 트레이 아이콘 우클릭 -> Reload.' -ForegroundColor Gray
Write-Host ""
