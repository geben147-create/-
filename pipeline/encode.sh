#!/usr/bin/env bash
# ============================================================
# STEP 4 — web encoding.  Raw Pollo mp4 -> web-ready media.
#
#   pipeline/raw/<clip>.mp4        (input,  fetched by fetch-media.sh)
#   site/media/<clip>-1920.mp4     (loop background, desktop)
#   site/media/<clip>-1920.webm    (smaller alternative, browser picks)
#   site/media/<clip>-1080v.mp4    (vertical source, mobile)
#   site/media/<clip>-scrub.mp4    (all-intra, seekable frame by frame)
#   site/media/poster/<clip>.webp  (first frame — required before load)
#
# Usage:  pipeline/encode.sh              # everything present in raw/
#         pipeline/encode.sh s1-hero      # one clip
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW="$ROOT/pipeline/raw"
OUT="$ROOT/site/media"
mkdir -p "$OUT/poster" "$OUT/frames"

command -v ffmpeg >/dev/null || { echo "ffmpeg not found"; exit 1; }

# Tone-match pass. Clips generated one at a time never match exactly; this is
# the single place the whole set is pulled onto one grade. Tune, don't remove.
GRADE="eq=brightness=0.01:contrast=1.03:saturation=0.94"

loop_desktop() {           # $1 clip name
  ffmpeg -y -loglevel error -i "$RAW/$1.mp4" -an \
    -vf "scale=1920:-2:flags=lanczos,$GRADE,fps=30" \
    -c:v libx264 -crf 24 -preset slow -profile:v high -pix_fmt yuv420p \
    -movflags +faststart "$OUT/$1-1920.mp4"

  ffmpeg -y -loglevel error -i "$RAW/$1.mp4" -an \
    -vf "scale=1920:-2:flags=lanczos,$GRADE,fps=30" \
    -c:v libvpx-vp9 -crf 34 -b:v 0 -row-mt 1 "$OUT/$1-1920.webm"
}

loop_mobile() {            # $1 clip name — expects a real 9:16 source
  ffmpeg -y -loglevel error -i "$RAW/$1.mp4" -an \
    -vf "scale=1080:-2:flags=lanczos,$GRADE,fps=30" \
    -c:v libx264 -crf 25 -preset slow -pix_fmt yuv420p \
    -movflags +faststart "$OUT/$1-1080v.mp4"
}

tile() {                   # $1 clip name — small card loop, 3s is plenty
  ffmpeg -y -loglevel error -i "$RAW/$1.mp4" -an -t 3 \
    -vf "scale=960:-2:flags=lanczos,$GRADE,fps=30" \
    -c:v libx264 -crf 26 -preset slow -pix_fmt yuv420p \
    -movflags +faststart "$OUT/$1-960.mp4"
}

# keyint=1 makes every frame a keyframe, so currentTime lands on the exact
# frame instead of the nearest keyframe 1-2s away. Costs 3-5x the bytes —
# only ever run this on the one scrub clip.
scrub() {                  # $1 clip name
  ffmpeg -y -loglevel error -i "$RAW/$1.mp4" -an \
    -vf "scale=1600:-2:flags=lanczos,$GRADE,fps=24" \
    -c:v libx264 -x264opts keyint=1:min-keyint=1:no-scenecut \
    -crf 23 -preset slow -pix_fmt yuv420p \
    -movflags +faststart "$OUT/$1-scrub.mp4"
}

# Fallback for when even all-intra stutters (iOS Safari). canvas + WebP has no
# device variance — this is what Apple actually ships.
sequence() {               # $1 clip name
  mkdir -p "$OUT/frames/$1"
  ffmpeg -y -loglevel error -i "$RAW/$1.mp4" \
    -vf "fps=16,scale=1600:-2:flags=lanczos,$GRADE" -q:v 78 \
    "$OUT/frames/$1/%04d.webp"
  echo "  frames: $(ls "$OUT/frames/$1" | wc -l)"
}

poster() {                 # $1 clip name — from the ENCODED file, so the
  ffmpeg -y -loglevel error -i "$2" -vframes 1 -q:v 82 \
    "$OUT/poster/$1.webp"  # poster matches the graded video exactly
}

budget() {                 # $1 label  $2 file  $3 limit in MB
  [ -f "$2" ] || return 0
  local mb; mb=$(python3 -c "import os,sys;print(round(os.path.getsize(sys.argv[1])/1048576,2))" "$2")
  if python3 -c "import sys;sys.exit(0 if float(sys.argv[1])<=float(sys.argv[2]) else 1)" "$mb" "$3"; then
    printf '  %-34s %6s MB  <= %s MB  ok\n' "$1" "$mb" "$3"
  else
    printf '  %-34s %6s MB  >  %s MB  OVER BUDGET\n' "$1" "$mb" "$3"
  fi
}

clips=("$@")
if [ ${#clips[@]} -eq 0 ]; then
  shopt -s nullglob
  for f in "$RAW"/*.mp4; do clips+=("$(basename "${f%.mp4}")"); done
fi
[ ${#clips[@]} -gt 0 ] || { echo "nothing in $RAW — run pipeline/fetch-media.sh first"; exit 1; }

for c in "${clips[@]}"; do
  echo "== $c"
  case "$c" in
    *-mobile)  loop_mobile "$c";  poster "$c" "$OUT/$c-1080v.mp4"
               budget "$c mobile loop" "$OUT/$c-1080v.mp4" 1.2 ;;
    s3-*)      scrub "$c";        poster "$c" "$OUT/$c-scrub.mp4"
               sequence "$c"
               budget "$c scrub" "$OUT/$c-scrub.mp4" 6 ;;
    s4-*)      tile "$c";         poster "$c" "$OUT/$c-960.mp4"
               budget "$c tile loop" "$OUT/$c-960.mp4" 1.5 ;;
    s1-*)      loop_desktop "$c"; poster "$c" "$OUT/$c-1920.mp4"
               budget "$c hero loop (mp4)"  "$OUT/$c-1920.mp4"  2.5
               budget "$c hero loop (webm)" "$OUT/$c-1920.webm" 2.5 ;;
    *)         loop_desktop "$c"; poster "$c" "$OUT/$c-1920.mp4"
               budget "$c section loop (mp4)"  "$OUT/$c-1920.mp4"  1.5
               budget "$c section loop (webm)" "$OUT/$c-1920.webm" 1.5 ;;
  esac
done

echo
echo "Encoded into $OUT. Flip site/media/sources.js  use:'local'  to serve them."
