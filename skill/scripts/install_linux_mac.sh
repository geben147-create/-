#!/usr/bin/env bash
# stayfade 무료 스택 설치 (Linux / macOS)
# 설치 순서는 '무료 + 품질 + 파이프라인 필수도' 순입니다.
set -euo pipefail

PY=${PY:-python3}
VENV=${VENV:-"$HOME/stayfade-venv"}

echo "== 1) 가상환경: $VENV"
$PY -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip wheel setuptools

echo "== 2) 코어 (분석·측정·MIDI) — 필수"
"$VENV/bin/pip" install numpy scipy librosa soundfile pyloudnorm mido pretty_midi jsonschema

echo "== 3) Basic Pitch (오디오→MIDI, 허밍 채보) — 무료 1순위"
"$VENV/bin/pip" install basic-pitch onnxruntime

echo "== 4) Matchering (레퍼런스 마스터링) — 무료"
"$VENV/bin/pip" install matchering

echo "== 5) Demucs (스템 분리) — 무료. 첫 실행 시 모델 가중치를 내려받습니다"
"$VENV/bin/pip" install demucs || echo "  demucs 설치 실패 — 파이프라인은 HPSS 폴백으로 계속 동작합니다"

echo "== 6) ffmpeg / fluidsynth (시스템 패키지)"
if command -v apt-get >/dev/null; then
  sudo apt-get update -qq && sudo apt-get install -y ffmpeg fluidsynth fluid-soundfont-gm
elif command -v brew >/dev/null; then
  brew install ffmpeg fluid-synth
else
  echo "  수동 설치 필요: ffmpeg, fluidsynth"
fi

echo
echo "완료. 사용:"
echo "  export PYTHONPATH=$(pwd)/pipeline"
echo "  $VENV/bin/python -m stayfade --project ./work/mysong init <원본.wav>"
