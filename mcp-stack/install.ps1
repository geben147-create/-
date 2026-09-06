<#
.SYNOPSIS
  Install the music MCP stack globally on Windows and register it with every
  MCP client (Claude Code, Codex, Cursor, Claude Desktop, Windsurf, VS Code,
  LM Studio, Gemini CLI).

.EXAMPLE
  .\install.ps1
  .\install.ps1 -Full -Prefetch
  .\install.ps1 -ReaperBridge
  .\install.ps1 -Uninstall
#>
[CmdletBinding()]
param(
    [switch]$Full,
    [switch]$Prefetch,
    [switch]$ReaperBridge,
    [switch]$Uninstall,
    [switch]$AllClients,
    [string[]]$Client
)

$ErrorActionPreference = 'Stop'
$SrcDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = if ($env:MUSIC_MCP_HOME) { $env:MUSIC_MCP_HOME }
        else { Join-Path $env:LOCALAPPDATA 'music-mcp' }

function Say($msg) { Write-Host "`n$msg" -ForegroundColor Cyan }

# uv installs to %USERPROFILE%\.local\bin, which is not on PATH in a fresh shell.
$UserBin = Join-Path $env:USERPROFILE '.local\bin'
if (Test-Path $UserBin) { $env:PATH = "$UserBin;$env:PATH" }

if ($Uninstall) {
    Say 'Removing MCP servers from client configs'
    python (Join-Path $Root 'configure_clients.py') --remove --all
    Write-Host "Client configs cleaned. Installed files remain at: $Root"
    Write-Host "Delete with:  Remove-Item -Recurse -Force '$Root'"
    Write-Host "              uv tool uninstall twelvetake-reaper-mcp xdarkzx-reaper-mcp"
    exit 0
}

# ------------------------------------------------------------------ 1. python
Say '[1/7] Checking Python'
$Py = $null
foreach ($cand in @('python', 'python3', 'py')) {
    $exe = Get-Command $cand -ErrorAction SilentlyContinue
    if (-not $exe) { continue }
    # The Microsoft Store stub named python.exe exits 9009 without running anything.
    & $cand -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,10) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) { $Py = $cand; break }
}
if (-not $Py) {
    Write-Error "Python 3.10+ not found. Install it with:  winget install Python.Python.3.12"
    exit 1
}
Write-Host "  $(& $Py --version)"

# ---------------------------------------------------------------------- 2. uv
Say '[2/7] Checking uv'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host '  installing uv...'
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    if (Test-Path $UserBin) { $env:PATH = "$UserBin;$env:PATH" }
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error 'uv install failed. See https://docs.astral.sh/uv/'
    exit 1
}
Write-Host "  $(uv --version)"
$UvBin = Split-Path -Parent (Get-Command uv).Source

# --------------------------------------------------------- 3. REAPER servers
Say '[3/7] Installing the REAPER MCP servers'
uv tool install --force twelvetake-reaper-mcp
# The [analysis] extra is what enables its loudness/clipping/QC tools - without
# it the server starts fine but silently registers 7 fewer tools.
uv tool install --force 'xdarkzx-reaper-mcp[analysis]'

# ---------------------------------------------------------- 4. toolkit venv
Say "[4/7] Building the music-toolkit environment at $Root"
New-Item -ItemType Directory -Force -Path $Root | Out-Null
$VenvPy = Join-Path $Root 'venv\Scripts\python.exe'
if (-not (Test-Path $VenvPy)) { uv venv (Join-Path $Root 'venv') --python 3.11 }

uv pip install --python $VenvPy -q 'mcp>=1.2,<2' numpy soundfile librosa pyloudnorm imageio-ffmpeg
Write-Host '  core audio stack installed'

if ($Full) {
    Write-Host '  installing Demucs + Basic Pitch (several GB, takes a while)'
    # Prefer CPU-only torch: the default wheel pulls ~5 GB of CUDA libraries
    # that do nothing without an NVIDIA GPU.
    uv pip install --python $VenvPy -q torch --index-strategy unsafe-best-match `
        --extra-index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE -ne 0) { uv pip install --python $VenvPy -q torch }
    uv pip install --python $VenvPy -q demucs 'basic-pitch[onnx]'
    Write-Host '  Demucs + Basic Pitch installed'
}

Copy-Item (Join-Path $SrcDir 'music_toolkit') $Root -Recurse -Force
Copy-Item (Join-Path $SrcDir 'configure_clients.py') $Root -Force
Copy-Item (Join-Path $SrcDir 'verify.py') $Root -Force

# ------------------------------------------------------------ 5. servers.json
Say '[5/7] Writing resolved server definitions'
$tpl = Get-Content (Join-Path $SrcDir 'servers.json') -Raw
# JSON-escape the backslashes in Windows paths before substituting them in.
$tpl = $tpl.Replace('{{ROOT}}',        $Root.Replace('\', '\\'))
$tpl = $tpl.Replace('{{VENV_PYTHON}}', $VenvPy.Replace('\', '\\'))
$tpl = $tpl.Replace('{{UV_BIN}}',      $UvBin.Replace('\', '\\'))
$ServersPath = Join-Path $Root 'servers.json'
$cfg = $tpl | ConvertFrom-Json
# On Windows the uv-installed console commands are .exe files; the template
# carries the bare name because that is what macOS and Linux use.
foreach ($name in $cfg.servers.PSObject.Properties.Name) {
    $srv = $cfg.servers.$name
    if ($srv.command -notmatch '\.(exe|py)$') { $srv.command = $srv.command + '.exe' }
    Write-Host ("    {0,-20}{1}" -f $name, $srv.command)
}
# -Depth matters: Windows PowerShell 5.1 truncates nested objects at depth 2.
$cfg | ConvertTo-Json -Depth 20 | Set-Content $ServersPath -Encoding UTF8
Write-Host "  $(Join-Path $Root 'servers.json')"

# ------------------------------------------------------------- 6. prefetch
if ($Prefetch) {
    Say '[6/7] Downloading model weights'
    & $VenvPy -c @"
try:
    from demucs.pretrained import get_model
    get_model('htdemucs'); print('  demucs htdemucs weights cached')
except Exception as exc:
    print(f'  demucs weights FAILED: {exc}')
try:
    from basic_pitch import ICASSP_2022_MODEL_PATH
    print(f'  basic-pitch model at {ICASSP_2022_MODEL_PATH}')
except Exception as exc:
    print(f'  basic-pitch model FAILED: {exc}')
"@
} else {
    Say '[6/7] Skipping model prefetch (pass -Prefetch to download now)'
}

if ($ReaperBridge) {
    Say 'Installing the REAPER Lua bridge'
    twelvetake-reaper-mcp --install-bridge
}

# -------------------------------------------------------- 7. clients + verify
Say '[7/7] Registering with MCP clients'
$cfgArgs = @('--servers', (Join-Path $Root 'servers.json'))
if ($AllClients) { $cfgArgs += '--all' }
foreach ($c in $Client) { $cfgArgs += @('--client', $c) }
& $Py (Join-Path $Root 'configure_clients.py') @cfgArgs

Say 'Verifying by MCP handshake'
& $Py (Join-Path $Root 'verify.py') --servers (Join-Path $Root 'servers.json')

Write-Host @"

Installed at: $Root
Re-verify any time:   python $Root\verify.py
Check one client:     python $Root\verify.py --client codex
Add a client later:   python $Root\configure_clients.py --client cursor
Remove everything:    .\install.ps1 -Uninstall

Restart your MCP clients so they re-read their config.
The two REAPER servers list their tools without REAPER, but calling those tools
needs REAPER open with the bridge script running.
"@
