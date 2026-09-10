<#
.SYNOPSIS
    전체 화면(모든 모니터)을 캡처해서 PNG 파일로 저장합니다.

.DESCRIPTION
    Win+PrintScreen 의 기본 동작에 의존하지 않는 독립 캡처 스크립트입니다.
    - 모든 모니터를 합친 가상 화면 전체를 캡처
    - DPI 배율(125%, 150% 등)에서도 실제 해상도로 캡처
    - 저장 경로: <폴더>\Screenshot_2026-09-10_20-51-33.png

.PARAMETER OutputFolder
    저장할 폴더. 없으면 자동으로 만듭니다. 기본값: D:\스크린샷

.PARAMETER Clipboard
    파일로 저장하면서 클립보드에도 같이 복사합니다.

.PARAMETER Cursor
    마우스 커서까지 함께 그립니다.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\Capture-Screen.ps1

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\Capture-Screen.ps1 -OutputFolder "D:\스크린샷" -Clipboard
#>
[CmdletBinding()]
param(
    [string]$OutputFolder = 'D:\스크린샷',
    [switch]$Clipboard,
    [switch]$Cursor
)

$ErrorActionPreference = 'Stop'

# DPI 배율이 100% 가 아닐 때 화면이 축소 캡처되는 것을 막는다.
# (System.Windows.Forms 를 불러오기 '전에' 호출해야 효과가 있다)
if (-not ('ScreenCaptureDpi' -as [type])) {
    Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public static class ScreenCaptureDpi {
    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();
}
'@
}
try { [ScreenCaptureDpi]::SetProcessDPIAware() | Out-Null } catch { }

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

# 저장 폴더 준비
if (-not (Test-Path -LiteralPath $OutputFolder)) {
    New-Item -ItemType Directory -Path $OutputFolder -Force | Out-Null
}

$bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bitmap   = $null
$graphics = $null

try {
    $bitmap   = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)

    if ($Cursor) {
        $pos = [System.Windows.Forms.Cursor]::Position
        $rect = New-Object System.Drawing.Rectangle(
            ($pos.X - $bounds.X), ($pos.Y - $bounds.Y), 32, 32)
        [System.Windows.Forms.Cursors]::Default.Draw($graphics, $rect)
    }

    # 같은 초에 두 번 눌러도 파일이 겹치지 않게 필요하면 -2, -3 을 붙인다.
    $stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
    $path  = Join-Path $OutputFolder ("Screenshot_{0}.png" -f $stamp)
    $n = 2
    while (Test-Path -LiteralPath $path) {
        $path = Join-Path $OutputFolder ("Screenshot_{0}-{1}.png" -f $stamp, $n)
        $n++
    }

    $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)

    if ($Clipboard) {
        try { [System.Windows.Forms.Clipboard]::SetImage($bitmap) } catch { }
    }

    Write-Output $path
}
finally {
    if ($graphics) { $graphics.Dispose() }
    if ($bitmap)   { $bitmap.Dispose() }
}
