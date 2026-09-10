# 윈도우 설정 모음

두 가지 설정을 자동으로 처리하는 스크립트와 가이드입니다.

| 폴더 | 내용 |
|---|---|
| [`rustdesk/`](#1-rustdesk--승인-클릭-없이-폰에서-바로-접속) | RustDesk 무인 접속 (폰에서 승인 없이 연결 + 부팅 시 자동 실행) |
| [`screenshot/`](#2-ctrl--printscreen--d스크린샷-자동-저장) | `Ctrl + PrintScreen` → 전체 화면 캡처 → `D:\스크린샷` 자동 저장 |

## 빠른 시작

PC(윈도우)에서 이 폴더를 내려받은 뒤:

```powershell
# 1) RustDesk 무인 접속  -- 반드시 [관리자 권한] PowerShell
powershell -ExecutionPolicy Bypass -File .\rustdesk\Setup-RustDeskUnattended.ps1

# 2) 스크린샷 단축키  -- 평소 쓰는 계정에서 그냥 실행 (관리자 권한 X)
powershell -ExecutionPolicy Bypass -File .\screenshot\Setup-ScreenshotHotkey.ps1
```

> 리포지토리 전체를 받는 방법: GitHub 페이지에서 **Code → Download ZIP** 을 누른 뒤
> 압축을 풀고, 그 안의 `windows-setup` 폴더에서 위 명령을 실행하세요.

---

# 1. RustDesk — 승인 클릭 없이 폰에서 바로 접속

## 왜 계속 PC에서 "수락"을 눌러야 하나?

영구 비밀번호를 설정했는데도 승인 창이 뜬다면, 아래 중 하나입니다. **위쪽이 훨씬 흔한 원인**입니다.

1. **비밀번호 방식이 "임시 비밀번호"로 되어 있다.**
   영구 비밀번호를 입력해 뒀어도, 확인 방식이 임시 비밀번호(one-time password)로 잡혀 있으면
   영구 비밀번호는 무시됩니다. → 설정값 `verification-method` 를 `use-permanent-password` 로.
2. **승인 방식이 "클릭 승인"으로 되어 있다.**
   이 경우 비밀번호가 맞아도 PC에서 사람이 수락을 눌러야 합니다.
   → 설정값 `approve-mode` 를 `password` 로.
3. **영구 비밀번호가 실제로 저장되지 않았다.**
   입력만 하고 확인/저장을 누르지 않으면 빈 값으로 남습니다.
   비밀번호가 없으면 RustDesk는 클릭 승인으로 넘어갑니다.
4. **폰에서 비밀번호를 저장하지 않았다.**
   연결할 때마다 비밀번호를 새로 입력해야 하고, 취소하면 승인 대기로 넘어갑니다.
5. **RustDesk가 서비스로 설치되어 있지 않다** (휴대용 exe만 실행 중).
   서비스 모드가 아니면 재부팅 후·로그인 화면·UAC 화면에서 접속이 안 됩니다.

`Setup-RustDeskUnattended.ps1` 이 1·2·5 번을 자동으로 고치고, 3·4 번은 확인해서 알려 줍니다.

## 스크립트로 한 번에 설정하기

### 0단계 — 영구 비밀번호 먼저 지정 (이것만 수동)

RustDesk 창 → **설정 → 보안** → **영구 비밀번호** 에 비밀번호를 입력하고 확인을 누르세요.

비밀번호는 해시/암호화되어 저장되기 때문에 스크립트가 안전하게 만들어 넣을 수 없습니다.
이 한 번만 손으로 해주시면 됩니다. **12자 이상**을 권합니다 (아래 [보안 주의](#보안-주의) 참고).

### 1단계 — 스크립트 실행

시작 메뉴에서 **PowerShell** 을 찾아 **관리자 권한으로 실행** 한 뒤:

```powershell
cd <내려받은 폴더>\windows-setup\rustdesk
powershell -ExecutionPolicy Bypass -File .\Setup-RustDeskUnattended.ps1
```

스크립트가 하는 일:

| 항목 | 내용 |
|---|---|
| 설정 파일 보호 | RustDesk 서비스·프로세스를 잠깐 멈춤 (안 멈추면 편집한 설정을 덮어씀) |
| 무인 접속 | 모든 `RustDesk2.toml` 의 `[options]` 에 `verification-method = 'use-permanent-password'`, `approve-mode = 'password'` 기록 |
| 원격 변조 방지 | `allow-remote-config-modification = 'N'` (접속한 쪽에서 이 설정을 못 바꾸게) |
| 비밀번호 점검 | 영구 비밀번호가 비어 있으면 경고 |
| 자동 실행 | `RustDesk` 서비스를 **자동 시작**으로 변경 + 실패 시 자동 재시도 등록 |
| 시작 프로그램 | 트레이 앱을 `HKLM\...\Run` 에 등록 |
| 절전 방지 | AC 전원에서 절전·최대 절전 **사용 안 함** (PC가 자면 폰에서 못 붙음) |

원본 설정 파일은 `RustDesk2.toml.bak` 으로 백업됩니다.

옵션:

```powershell
# 절전 설정은 건드리지 않기
... -File .\Setup-RustDeskUnattended.ps1 -SkipPowerSettings

# 시작 프로그램 등록만 건너뛰기 (서비스 자동 시작은 그대로 적용)
... -File .\Setup-RustDeskUnattended.ps1 -SkipTrayAutostart
```

### 2단계 — 재부팅

서비스 자동 시작과 설정이 제대로 물렸는지 확인하려면 한 번 재부팅하세요.

### 3단계 — 폰에서 접속

1. 폰 RustDesk 앱을 열고 PC의 **ID**(9자리 숫자) 입력
2. 연결 → **영구 비밀번호** 입력
3. **"비밀번호 저장"** 을 반드시 체크 ← 이걸 빼면 매번 다시 물어봅니다
4. 다음부터는 최근 목록/주소록에서 탭 한 번으로 바로 연결됩니다

## 스크립트 없이 GUI로 하는 방법

RustDesk 창 → **설정 → 보안** 에서 아래 두 가지를 찾아 바꿉니다.

- **비밀번호 확인 방식**: `영구 비밀번호 사용` 선택
  (라벨이 "확인 방법" / "비밀번호" / `Use permanent password` 등 버전마다 조금씩 다릅니다)
- **승인 방식 / 승인 모드**: `비밀번호만` 선택
  (`Password only` / `비밀번호만 사용`)

그리고 **설정 → 일반 → 서비스** 항목이 **"중지"** 버튼으로 보이면 서비스가 켜져 있는 정상 상태입니다.
("시작" 버튼으로 보이면 서비스가 꺼져 있는 것이니 눌러서 켜세요.)

> 버전에 따라 메뉴 위치와 한글 라벨이 다릅니다. 화면에서 못 찾겠으면 스크립트를 쓰는 편이 확실합니다.
> 스크립트는 설정 파일에 값을 직접 기록하므로 라벨 이름과 무관하게 동작합니다.

## 잘 되는지 확인

```powershell
# 서비스가 자동 시작 + 실행 중인지
Get-Service RustDesk | Format-List Name, Status, StartType

# 실제로 기록된 값 확인
Get-ChildItem -Path "$env:APPDATA\RustDesk\config","$env:SystemRoot\ServiceProfiles","$env:SystemRoot\System32\config\systemprofile" `
    -Recurse -Filter RustDesk2.toml -ErrorAction SilentlyContinue |
    ForEach-Object { $_.FullName; Select-String -LiteralPath $_.FullName -Pattern 'approve-mode|verification-method' }
```

`approve-mode = 'password'` 와 `verification-method = 'use-permanent-password'` 가 보이면 정상입니다.

## 보안 주의

무인 접속은 **ID와 비밀번호만 알면 누구나 내 PC에 들어올 수 있다**는 뜻입니다. 편의와 위험을 같이 받는 설정이니 최소한 이렇게 해두세요.

- 영구 비밀번호를 **12자 이상**, 다른 서비스와 겹치지 않게
- 스크립트가 넣는 `allow-remote-config-modification = 'N'` 를 그대로 두기
  (접속한 쪽이 설정을 바꿔 백도어를 남기는 것을 막음)
- 가능하면 **설정 → 보안 → 화이트리스트**에 접속을 허용할 IP만 등록
- 공용/공유 PC에는 무인 접속을 걸지 않기
- 비밀번호가 새어 나갔다고 의심되면 즉시 영구 비밀번호를 변경

## 되돌리기

```powershell
# 설정 파일 복원 (경로는 위 '확인' 명령으로 찾은 것 사용)
Copy-Item "$env:APPDATA\RustDesk\config\RustDesk2.toml.bak" "$env:APPDATA\RustDesk\config\RustDesk2.toml" -Force

# 시작 프로그램 등록 해제
Remove-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run' -Name 'RustDesk'

# 절전 설정 되돌리기 (예: 30분 후 절전)
powercfg /change standby-timeout-ac 30
```

---

# 2. `Ctrl + PrintScreen` → `D:\스크린샷` 자동 저장

## 원리

윈도우에는 이미 **`Win + PrintScreen` = 전체 화면을 파일로 저장**하는 기능이 있습니다.
저장 위치는 `사진\스크린샷` 폴더입니다. 그래서 설정은 두 조각으로 나뉩니다.

1. **저장 위치 옮기기** — 윈도우의 "스크린샷" 기본 폴더를 `D:\스크린샷` 으로 이동
2. **키 바꾸기** — `Ctrl + PrintScreen` 을 누르면 `Win + PrintScreen` 이 눌리게 연결

`PrintScreen` 키는 윈도우가 직접 잡고 있어서 일반 단축키 설정으로는 바꿀 수 없습니다.
그래서 2번에는 **AutoHotkey**(또는 PowerToys)가 필요합니다.

## 설치

### 1단계 — AutoHotkey v2 설치

```powershell
winget install --id AutoHotkey.AutoHotkey
```

winget이 없으면 https://www.autohotkey.com 에서 **v2** 를 받아 설치하세요.

### 2단계 — 스크립트 실행

**관리자 권한이 아닌**, 평소 쓰는 계정의 PowerShell에서:

```powershell
cd <내려받은 폴더>\windows-setup\screenshot
powershell -ExecutionPolicy Bypass -File .\Setup-ScreenshotHotkey.ps1
```

> 관리자 권한으로 실행하면 *관리자 계정*의 폴더 설정이 바뀔 수 있어서, 일반 권한 실행이 맞습니다.

스크립트가 하는 일:

| 항목 | 내용 |
|---|---|
| 폴더 생성 | `D:\스크린샷` 생성 (D 드라이브가 없으면 안내하고 중단) |
| 폴더 이동 | 윈도우 "스크린샷" 기본 폴더를 `D:\스크린샷` 으로 변경 (`SHSetKnownFolderPath`, 실패 시 레지스트리) |
| 번호 초기화 | `ScreenshotIndex` 를 1로 리셋 |
| 스크립트 설치 | `%LOCALAPPDATA%\CtrlPrintScreen\` 에 복사하고 저장 경로를 파일에 기록 |
| 자동 실행 | 시작 폴더(`shell:startup`)에 바로가기 생성 → **부팅할 때마다 단축키 자동 활성화** |
| 즉시 활성화 | 지금 바로 실행해서 재부팅 없이 사용 가능 |

### 3단계 — 확인

`Ctrl + PrintScreen` 을 누르고 `D:\스크린샷` 폴더를 열어 보세요.
`Win + PrintScreen` 도 같은 폴더에 저장됩니다.

## 두 가지 동작 모드

| 모드 | 동작 | 장점 | 단점 |
|---|---|---|---|
| **`native`** (기본) | 윈도우의 `Win+PrintScreen` 을 대신 눌러 줌 | 즉시 저장, 창 깜빡임 없음 | "스크린샷" 폴더 이동이 되어 있어야 함 |
| `script` | `Capture-Screen.ps1` 로 직접 캡처 | 폴더 이동 없이 원하는 경로에 저장, 확실함 | PowerShell 구동 때문에 0.5~1.5초 느림 |

`native` 모드에서 캡처가 안 되면 `script` 모드로 바꾸세요. 두 가지 방법이 있습니다.

```powershell
# 방법 A: 다시 설치하면서 모드 지정
powershell -ExecutionPolicy Bypass -File .\Setup-ScreenshotHotkey.ps1 -Mode script

# 방법 B: 설치된 파일을 직접 편집
notepad "$env:LOCALAPPDATA\CtrlPrintScreen\CtrlPrintScreen.ahk"
#   MODE := "native"  ->  MODE := "script"  로 바꾸고 저장
#   그다음 트레이의 AutoHotkey 아이콘 우클릭 -> Reload Script
```

## 옵션

```powershell
# 저장 폴더를 바꾸고 싶을 때
... -File .\Setup-ScreenshotHotkey.ps1 -Folder 'E:\캡처'

# 윈도우 기본 "스크린샷" 폴더는 그대로 두고 이 단축키만 쓰고 싶을 때
... -File .\Setup-ScreenshotHotkey.ps1 -Mode script -SkipFolderRelocation
```

`Capture-Screen.ps1` 은 단독으로도 쓸 수 있습니다.

```powershell
# 클립보드에도 같이 복사 / 마우스 커서까지 포함
powershell -NoProfile -ExecutionPolicy Bypass -File .\Capture-Screen.ps1 -Clipboard -Cursor
```

## AutoHotkey를 쓰고 싶지 않다면

**PowerToys** 의 *키보드 관리자* 로 키만 바꿔도 됩니다.

1. `winget install --id Microsoft.PowerToys`
2. PowerToys → **키보드 관리자** → **바로 가기 다시 매핑**
3. `Ctrl + PrintScreen` → `Win + PrintScreen` 으로 매핑
4. 저장 폴더 이동은 아래 "수동 방법"으로 한 번만 처리

이 경우 스크립트는 폴더 이동만 담당하게 실행하세요.

```powershell
powershell -ExecutionPolicy Bypass -File .\Setup-ScreenshotHotkey.ps1
# AutoHotkey 가 없다는 경고만 나오고, 폴더 이동은 정상 처리됩니다
```

## 수동 방법 (스크립트 없이 폴더만 옮기기)

1. `Win + R` → `shell:screenshots` 입력 → 스크린샷 폴더가 열립니다
2. 주소창에서 한 단계 위로 올라가 **스크린샷** 폴더를 우클릭 → **속성**
3. **위치** 탭 → **이동** → `D:\스크린샷` 선택 → **적용**
4. "기존 파일을 옮기겠습니까?" 는 원하는 대로 선택

이렇게 하면 `Win + PrintScreen` 만으로도 `D:\스크린샷` 에 저장됩니다.

## 되돌리기

```powershell
# 시작 프로그램에서 제거
Remove-Item "$([Environment]::GetFolderPath('Startup'))\CtrlPrintScreen.lnk" -Force

# 실행 중인 스크립트 종료
Get-Process AutoHotkey* -ErrorAction SilentlyContinue | Stop-Process -Force

# 설치 폴더 삭제
Remove-Item "$env:LOCALAPPDATA\CtrlPrintScreen" -Recurse -Force
```

"스크린샷" 폴더 위치는 위 *수동 방법* 3번에서 **기본값 복원**을 누르면 되돌아갑니다.

---

# 문제 해결

| 증상 | 확인할 것 |
|---|---|
| `이 시스템에서 스크립트를 실행할 수 없습니다` | 명령 앞에 `powershell -ExecutionPolicy Bypass -File` 를 붙여 실행했는지 |
| 한글 폴더 이름이 깨져서 만들어짐 | `.ps1` / `.ahk` 파일을 편집했다면 **UTF-8 (BOM 포함)** 으로 저장해야 합니다 |
| 폰에서 붙었는데 화면이 검음 | 모니터 없이(헤드리스) 접속한 경우입니다. 더미 HDMI 어댑터가 필요할 수 있습니다 |
| 재부팅 후 폰에서 연결 안 됨 | `Get-Service RustDesk` 의 StartType이 `Automatic` 인지, PC가 절전에 들어가지 않았는지 |
| RustDesk 설정이 원래대로 돌아감 | RustDesk가 실행 중일 때 파일을 고치면 덮어씁니다. 스크립트는 멈춘 뒤 고치므로 스크립트로 다시 실행하세요 |
| `Ctrl+PrintScreen` 이 반응 없음 | 트레이에 AutoHotkey 아이콘이 있는지 확인. 없으면 시작 폴더 바로가기를 직접 실행 |
| 캡처는 되는데 D 드라이브에 없음 | `native` 모드인데 폴더 이동이 안 된 경우입니다. `-Mode script` 로 다시 설치하세요 |
