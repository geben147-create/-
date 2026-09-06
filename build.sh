#!/usr/bin/env bash
# =============================================================================
#  build.sh — Pollo 원본을 받아 웹용으로 인코딩하고 자체 호스팅으로 전환한다.
#
#  이 저장소를 만든 실행 환경은 조직 egress 정책 때문에 videocdn.pollo.ai 에
#  접근할 수 없어서 이 단계를 대신 실행하지 못했다. 네트워크가 열린 로컬에서
#  이 스크립트를 돌리면 파이프라인 STEP 4(웹 인코딩)가 그대로 완료된다.
#
#  사용법:
#     ./build.sh          # 다운로드 + 인코딩 + index.html 을 local 모드로 재생성
#     ./build.sh --fetch  # 다운로드만
#
#  필요: ffmpeg, curl, python3
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

SRC=media/src
OUT=media
mkdir -p "$SRC" "$OUT"

command -v ffmpeg >/dev/null || { echo "ffmpeg 가 필요합니다: https://ffmpeg.org/download.html"; exit 1; }
command -v python3 >/dev/null || { echo "python3 가 필요합니다"; exit 1; }

# ---------------------------------------------------------------- 1. 다운로드
echo "▸ [1/4] 원본 내려받기"
python3 - <<'PY'
import json, pathlib, subprocess
man = json.loads(pathlib.Path("media/manifest.json").read_text(encoding="utf-8"))
for key, v in man["shots"].items():
    for kind, ext in (("img", "png"), ("vid", "mp4")):
        url = (v or {}).get(kind)
        if not url:
            print(f"  · {key}.{kind} — URL 없음, 건너뜀"); continue
        dst = pathlib.Path("media/src") / f"{key}.{ext}"
        if dst.exists() and dst.stat().st_size > 0:
            print(f"  · {dst} 이미 있음"); continue
        print(f"  ↓ {dst}")
        subprocess.run(["curl","-fsSL","--retry","3","-o",str(dst),url], check=True)
PY

if [ "${1:-}" = "--fetch" ]; then echo "다운로드만 완료."; exit 0; fi

# ------------------------------------------------------- 2. 루프 배경 인코딩
# 가이드 07-A. faststart 로 첫 바이트에서 바로 재생 시작.
echo "▸ [2/4] 루프 배경 인코딩 (mp4 + webm)"
loop_encode () {  # $1=입력 $2=출력접두사 $3=가로폭 $4=crf
  local in="$1" base="$2" w="$3" crf="$4"
  [ -f "$in" ] || { echo "  · $in 없음, 건너뜀"; return; }
  ffmpeg -hide_banner -loglevel error -y -i "$in" -an \
    -vf "scale=${w}:-2,fps=30" \
    -c:v libx264 -crf "$crf" -preset slow -profile:v high -pix_fmt yuv420p \
    -movflags +faststart "${base}.mp4"
  ffmpeg -hide_banner -loglevel error -y -i "$in" -an \
    -vf "scale=${w}:-2,fps=30" \
    -c:v libvpx-vp9 -crf $((crf + 10)) -b:v 0 -row-mt 1 "${base}.webm"
  echo "  ✓ ${base}.mp4 ($(du -h "${base}.mp4" | cut -f1))  ${base}.webm ($(du -h "${base}.webm" | cut -f1))"
}

loop_encode "$SRC/s1_hero.mp4"    "$OUT/s1-hero-1920"    1920 24
loop_encode "$SRC/s2_problem.mp4" "$OUT/s2-problem-1920" 1920 25
loop_encode "$SRC/s4a_brand.mp4"  "$OUT/s4a-brand-1280"  1280 26
loop_encode "$SRC/s4b_char.mp4"   "$OUT/s4b-char-1280"   1280 26
loop_encode "$SRC/s4c_vfx.mp4"    "$OUT/s4c-vfx-1280"    1280 26

# 모바일 세로 히어로 (별도 생성한 9:16 소스)
if [ -f "$SRC/s1_hero_v.mp4" ]; then
  ffmpeg -hide_banner -loglevel error -y -i "$SRC/s1_hero_v.mp4" -an \
    -vf "scale=1080:-2,fps=30" \
    -c:v libx264 -crf 25 -preset slow -pix_fmt yuv420p \
    -movflags +faststart "$OUT/s1-hero-1080v.mp4"
  echo "  ✓ s1-hero-1080v.mp4 ($(du -h "$OUT/s1-hero-1080v.mp4" | cut -f1))"
fi

# --------------------------------------------------------- 3. 스크럽 인코딩
# 가이드 07-B. keyint=1 — 전 프레임 키프레임이라야 currentTime seek 이 즉시 먹는다.
echo "▸ [3/4] 스크럽 클립 인코딩 (전 프레임 키프레임)"
if [ -f "$SRC/s3_solve.mp4" ]; then
  ffmpeg -hide_banner -loglevel error -y -i "$SRC/s3_solve.mp4" -an \
    -vf "scale=1600:-2,fps=24" \
    -c:v libx264 -x264opts keyint=1:min-keyint=1:no-scenecut \
    -crf 22 -preset slow -pix_fmt yuv420p \
    -movflags +faststart "$OUT/s3-solve-scrub.mp4"
  echo "  ✓ s3-solve-scrub.mp4 ($(du -h "$OUT/s3-solve-scrub.mp4" | cut -f1))"

  # 이미지 시퀀스 폴백 (iOS Safari 에서 스크럽이 끊길 때 — 가이드 07-C)
  # mkdir -p "$OUT/frames" && ffmpeg -i "$SRC/s3_solve.mp4" -vf "fps=24,scale=1600:-2" -q:v 78 "$OUT/frames/%04d.webp"
fi

# ----------------------------------------------------------- 4. 포스터 추출
# 영상 로드 전 표시. 필수 — 없으면 iOS 저전력 모드에서 검은 화면이 된다.
echo "▸ [4/4] 포스터 추출"
poster () {
  local in="$1" out="$2"
  [ -f "$in" ] || return
  ffmpeg -hide_banner -loglevel error -y -i "$in" -vframes 1 -vf "scale=1280:-2" -q:v 82 "$out"
  echo "  ✓ $out ($(du -h "$out" | cut -f1))"
}
poster "$SRC/s1_hero.mp4"    "$OUT/s1-hero-poster.webp"
poster "$SRC/s2_problem.mp4" "$OUT/s2-problem-poster.webp"
poster "$SRC/s3_solve.mp4"   "$OUT/s3-solve-poster.webp"
poster "$SRC/s4a_brand.mp4"  "$OUT/s4a-brand-poster.webp"
poster "$SRC/s4b_char.mp4"   "$OUT/s4b-char-poster.webp"
poster "$SRC/s4c_vfx.mp4"    "$OUT/s4c-vfx-poster.webp"

# ------------------------------------------------- index.html 을 local 모드로
python3 render.py local

echo
echo "완료. 용량 예산 점검 (가이드 07 상한):"
echo "  히어로 데스크톱 ≤ 2.5MB / 모바일 ≤ 1.2MB / 일반 섹션 ≤ 1.5MB / 스크럽 ≤ 6MB"
du -h $OUT/*.mp4 $OUT/*.webm 2>/dev/null | sort -h || true
