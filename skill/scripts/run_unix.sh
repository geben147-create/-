#!/usr/bin/env bash
# stayfade 한 곡 처리 (macOS / Linux) — 사람 결정 앞에서 멈춥니다.
#   bash skill/scripts/run_unix.sh <원본.wav> [프로젝트이름] [조성]
set -euo pipefail
AUDIO=${1:?"사용법: bash skill/scripts/run_unix.sh <원본.wav> [이름] [조성]"}
NAME=${2:-mysong}
KEY=${3:-}
VENV=${VENV:-"$HOME/stayfade-venv"}
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$VENV/bin/python"
[ -x "$PY" ] || { echo "가상환경이 없습니다: $PY — 먼저 skill/scripts/install_linux_mac.sh 를 실행하세요."; exit 1; }
[ -f "$AUDIO" ] || { echo "원본 파일이 없습니다: $AUDIO"; exit 1; }
export PYTHONPATH="$REPO/pipeline"
PROJ="$REPO/work/$NAME"

run() { echo; echo "== $1"; shift; "$PY" -m stayfade --project "$PROJ" "$@"; }

run "00 원본 보존" init "$AUDIO" --title "$(basename "${AUDIO%.*}")"
if [ -n "$KEY" ]; then run "01-03 분리·분석·채보" analyze --key "$KEY"; else run "01-03 분리·분석·채보" analyze; fi
run "04-05 후보·미리듣기" candidates
run "06 사람 결정 관문" gate

if ! "$PY" -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get('status')=='DECIDED' else 1)" \
     "$PROJ/human_decisions.json"; then
  cat <<MSG

여기서 멈춥니다.
  1) 미리듣기를 들어보세요:  $PROJ/04_render
  2) 결정 파일을 채우세요:  $PROJ/human_decisions.json
     choice 채우기 · note_edits 로 직접 수정 · status=DECIDED · decided_by=human
  3) 이 스크립트를 다시 실행하면 이어서 진행합니다.
MSG
  exit 0
fi

run "07-08 보컬·믹스·마스터" build
run "09 기술 QC" qc
run "10 증빙" evidence
"$PY" "$REPO/skill/scripts/validate.py" "$PROJ"
echo
echo "완료:"
echo "  마스터 : $PROJ/07_master/arranged_master_44k1_24bit.wav"
echo "  유통용 : $PROJ/07_master/distributor_candidate_44k1_16bit.flac"
echo "  A/B    : $PROJ/08_qc/AB_original_vs_arranged.wav"
echo "  증빙   : $PROJ/09_evidence/"
echo
echo "제출 전에 반드시: 전체 청취 · 모노 청취 · 권리 증빙 · 커버/메타데이터 확인"
