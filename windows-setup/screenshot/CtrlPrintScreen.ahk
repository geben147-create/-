; ============================================================================
;  Ctrl + PrintScreen  ->  전체 화면 캡처  ->  D:\스크린샷 에 자동 저장
;  AutoHotkey v2 용 스크립트
; ----------------------------------------------------------------------------
;  MODE 설명
;    "native" : 윈도우 기본 기능(Win+PrintScreen)을 대신 눌러 준다.
;               가장 빠르고 창 깜빡임이 없다.
;               단, Setup-ScreenshotHotkey.ps1 로 윈도우의 '스크린샷' 폴더
;               위치를 D:\스크린샷 으로 옮겨 둬야 한다.
;
;    "script" : Capture-Screen.ps1 을 직접 실행해서 캡처한다.
;               폴더 위치 변경에 의존하지 않고 지정한 경로에 바로 저장된다.
;               PowerShell 이 뜨는 만큼 0.5~1.5초 느리다.
;
;  native 모드에서 캡처가 안 되면 아래 MODE 를 "script" 로 바꾸고
;  트레이 아이콘 우클릭 -> Reload Script 를 누르세요.
;
;  이 파일을 편집할 때는 반드시 'UTF-8 (BOM 포함)' 으로 저장하세요.
;  그러지 않으면 한글 경로가 깨집니다.
; ============================================================================

#Requires AutoHotkey v2.0
#SingleInstance Force

MODE           := "native"
SAVE_FOLDER    := "D:\스크린샷"
CAPTURE_SCRIPT := A_ScriptDir "\Capture-Screen.ps1"

; ------------------------------------------------------------------ 단축키 --
^PrintScreen:: {
    global MODE, SAVE_FOLDER, CAPTURE_SCRIPT

    if (MODE = "script") {
        CaptureViaScript()
        return
    }

    ; 윈도우는 Win+PrintScreen 에 Ctrl 이 섞여 있으면 무시할 수 있다.
    ; 눌려 있는 Ctrl 을 떼고 Win+PrintScreen 을 한 번에 보낸다.
    Send("{LCtrl up}{RCtrl up}{LWin down}{PrintScreen}{LWin up}")
}

; ------------------------------------------------------------------- 함수 --
CaptureViaScript() {
    global SAVE_FOLDER, CAPTURE_SCRIPT

    if !FileExist(CAPTURE_SCRIPT) {
        TrayTip("Capture-Screen.ps1 을 찾을 수 없습니다:`n" . CAPTURE_SCRIPT,
                "Ctrl+PrintScreen", 0x3)
        return
    }

    args := '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' . CAPTURE_SCRIPT . '" -OutputFolder "' . SAVE_FOLDER . '"'
    try {
        Run('powershell.exe ' . args, , "Hide")
    } catch as err {
        TrayTip("캡처 실패: " . err.Message, "Ctrl+PrintScreen", 0x3)
    }
}

OpenScreenshotFolder(*) {
    global SAVE_FOLDER
    try Run('explorer.exe "' . SAVE_FOLDER . '"')
}

; --------------------------------------------------------------- 트레이 메뉴 --
A_TrayMenu.Insert("1&", "스크린샷 폴더 열기", OpenScreenshotFolder)
A_TrayMenu.Insert("2&")
