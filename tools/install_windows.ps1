# Free music stack for Windows (PowerShell). Run:  powershell -ExecutionPolicy Bypass -File tools\install_windows.ps1
# Installs: Python 3.11, Git, ffmpeg (winget), then the Python audio stack into .venv, then Demucs weights.
# REAPER / Reaper-MCP / MAutoPitch / Graillon are installed manually (links printed at the end).
$ErrorActionPreference = "Stop"
foreach ($id in @("Python.Python.3.11", "Git.Git", "Gyan.FFmpeg")) {
  if (-not (winget list --id $id -e | Select-String $id)) { winget install --id $id -e --source winget --accept-package-agreements --accept-source-agreements }
}
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip wheel
& .\.venv\Scripts\pip.exe install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
& .\.venv\Scripts\pip.exe install -r tools\requirements.txt
$D = "$env:USERPROFILE\.cache\torch\hub\checkpoints"; New-Item -ItemType Directory -Force -Path $D | Out-Null
$F = "$D\955717e8-8726e21a.th"
if (-not (Test-Path $F)) {
  try { Invoke-WebRequest "https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/955717e8-8726e21a.th" -OutFile $F }
  catch { Invoke-WebRequest "https://s3.us-west-2.amazonaws.com/dl.fbaipublicfiles.com/demucs/hybrid_transformer/955717e8-8726e21a.th" -OutFile $F }
}
& .\.venv\Scripts\python.exe -c "import demucs, basic_pitch, librosa; print('stack OK')"
Write-Host ""
Write-Host "Manual (free) installs for the human steps:"
Write-Host "  REAPER (60-day full trial)  https://www.reaper.fm/download.php"
Write-Host "  Reaper-MCP                  https://github.com/xDarkzx/Reaper-MCP"
Write-Host "  MAutoPitch (free)           https://www.meldaproduction.com/MAutoPitch"
Write-Host "  Graillon 3 Free Edition     https://www.auburnsounds.com/products/Graillon.html"
Write-Host "  Seed-VC (voice conversion)  https://github.com/Plachtaa/seed-vc"
Write-Host "Then run:  .\.venv\Scripts\python.exe scripts\pipeline.py tracks\01_xxx"
