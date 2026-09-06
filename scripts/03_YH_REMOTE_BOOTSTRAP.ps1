<#
  03_YH_REMOTE_BOOTSTRAP.ps1  -  보조 PC를 메인에서 조종 가능하게 세팅
  ------------------------------------------------------------------
  반드시 [관리자] PowerShell 에서 실행.
  각 보조 PC(YH-AUTO / YH-FINISH / YH-STORE)에서 1회씩.

  실행: powershell -ExecutionPolicy Bypass -File .\03_YH_REMOTE_BOOTSTRAP.ps1 -Role AUTO
#>
param(
  [ValidateSet('AUTO','FINISH','STORE','CTRL')][string]$Role = 'AUTO',
  [switch]$SkipRustDesk   # Windows Pro 라서 RDP 쓸 거면 이걸 붙이세요
)

$ErrorActionPreference = 'Stop'
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Write-Host "관리자 권한 PowerShell 로 다시 실행하세요." -ForegroundColor Red; exit 1
}

Write-Host "=== YH-$Role 원격 세팅 ($env:COMPUTERNAME) ===" -ForegroundColor Cyan

# --- 0. Windows 에디션 확인 : RDP 가능 여부 ---
$edition = (Get-CimInstance Win32_OperatingSystem).Caption
Write-Host "`n[0] OS: $edition"
$canRdp = $edition -notmatch 'Home'
if ($canRdp) { Write-Host "    -> Pro/Enterprise: RDP 사용 가능 (RustDesk 없어도 됨)" -ForegroundColor Green }
else         { Write-Host "    -> Home: RDP 호스트 불가 -> RustDesk 필요" -ForegroundColor Yellow }

# --- 1. winget 확인 ---
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  Write-Host "winget 이 없습니다. Microsoft Store 에서 '앱 설치 관리자' 설치 후 다시 실행하세요." -ForegroundColor Red
  exit 1
}

# --- 2. Tailscale ---
Write-Host "`n[1] Tailscale 설치" -ForegroundColor Green
winget install --id Tailscale.Tailscale -e --accept-source-agreements --accept-package-agreements --silent
Write-Host "    설치 후 사람이 직접: Tailscale 실행 -> Log in -> 브라우저 로그인" -ForegroundColor Yellow

# --- 3. OpenSSH 서버 (CLI 원격조작의 핵심) ---
Write-Host "`n[2] OpenSSH Server" -ForegroundColor Green
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd
# 기본 셸을 PowerShell 로 (기본은 cmd 라 불편)
New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' -Name DefaultShell `
  -Value "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" `
  -PropertyType String -Force | Out-Null
Write-Host "    sshd: $((Get-Service sshd).Status)" -ForegroundColor Cyan

# --- 4. 방화벽: SSH 는 Tailscale 대역(100.64.0.0/10)에서만 허용 ---
Write-Host "`n[3] 방화벽 규칙 (Tailscale 대역만 허용)" -ForegroundColor Green
Remove-NetFirewallRule -DisplayName 'YH SSH (Tailscale only)' -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName 'YH SSH (Tailscale only)' `
  -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow `
  -RemoteAddress '100.64.0.0/10' | Out-Null
Write-Host "    22번 포트: Tailscale 내부에서만 열림 (인터넷 노출 X)" -ForegroundColor Cyan

# --- 5. RDP (Pro 이상) ---
if ($canRdp) {
  Write-Host "`n[4] 원격 데스크톱 활성화" -ForegroundColor Green
  Set-ItemProperty 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name fDenyTSConnections -Value 0
  Remove-NetFirewallRule -DisplayName 'YH RDP (Tailscale only)' -ErrorAction SilentlyContinue
  New-NetFirewallRule -DisplayName 'YH RDP (Tailscale only)' `
    -Direction Inbound -Protocol TCP -LocalPort 3389 -Action Allow `
    -RemoteAddress '100.64.0.0/10' | Out-Null
  Write-Host "    RDP: Tailscale 대역만 허용" -ForegroundColor Cyan
} elseif (-not $SkipRustDesk) {
  Write-Host "`n[4] RustDesk 설치 (Home 에디션이라 RDP 대체)" -ForegroundColor Green
  winget install --id RustDesk.RustDesk -e --accept-source-agreements --accept-package-agreements --silent
  Write-Host "    설치 후 사람이 직접: 설정 -> 보안 -> 무인접속 영구 비밀번호" -ForegroundColor Yellow
  Write-Host "    그 비밀번호는 AI/채팅에 절대 붙여넣지 마세요." -ForegroundColor Red
}

# --- 6. 절전 끄기 (24시간 서버 역할일 때만) ---
if ($Role -in 'AUTO','STORE') {
  Write-Host "`n[5] 절전/최대절전 해제 (24시간 가동용)" -ForegroundColor Green
  powercfg /change standby-timeout-ac 0
  powercfg /change hibernate-timeout-ac 0
  powercfg /change monitor-timeout-ac 15
  powercfg /hibernate off
  Write-Host "    화면만 15분 뒤 꺼지고, 본체는 안 잡니다." -ForegroundColor Cyan
}

# --- 7. 역할별 기본 도구 ---
Write-Host "`n[6] 역할별 도구" -ForegroundColor Green
switch ($Role) {
  'FINISH' {
    winget install --id Gyan.FFmpeg -e --silent --accept-package-agreements
    Write-Host "    ffmpeg 설치. 재로그인 후 확인: ffmpeg -encoders | findstr nvenc" -ForegroundColor Cyan
  }
  'STORE'  {
    winget install --id Rclone.Rclone -e --silent --accept-package-agreements
    Write-Host "    rclone 설치 (구글드라이브 백업용)" -ForegroundColor Cyan
  }
  'AUTO'   {
    Write-Host "    Docker Desktop 은 수동 설치 권장 (WSL2 백엔드 선택 필요)" -ForegroundColor Yellow
  }
}

# --- 8. 결과 ---
Write-Host "`n=== 완료 ===" -ForegroundColor Cyan
Write-Host "PC 이름: $env:COMPUTERNAME"
Write-Host "사람이 해야 할 일:"
Write-Host "  1) Tailscale 로그인"
if (-not $canRdp -and -not $SkipRustDesk) { Write-Host "  2) RustDesk 영구 비밀번호 설정" }
Write-Host "`n메인 PC 에서 SSH 키 등록 (메인에서 실행):" -ForegroundColor Yellow
Write-Host "  ssh-keygen -t ed25519          # 키 없으면 1회"
Write-Host "  type `$env:USERPROFILE\.ssh\id_ed25519.pub | ssh $env:USERNAME@$env:COMPUTERNAME `"cat >> .ssh\authorized_keys`""
Write-Host "  !! 이 계정이 [관리자] 계정이면 authorized_keys 가 무시됩니다." -ForegroundColor Red
Write-Host "     그 경우 키를 여기에 넣으세요: C:\ProgramData\ssh\administrators_authorized_keys" -ForegroundColor Red
Write-Host "     (권한: icacls 로 Administrators/SYSTEM 만 남기고 상속 제거)" -ForegroundColor DarkGray
