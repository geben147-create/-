#!/bin/bash
# One-shot install of the free stack used in this repo (Linux/macOS). Run from the repo root.
set -e
python3 -m venv .venv && . .venv/bin/activate
pip install --upgrade pip wheel
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu || pip install torch torchaudio
pip install -r tools/requirements.txt
command -v ffmpeg >/dev/null || echo ">> install ffmpeg: sudo apt install ffmpeg  |  brew install ffmpeg"
bash tools/get_demucs_weights.sh
python -c "import demucs, basic_pitch, librosa; print('stack OK')"
