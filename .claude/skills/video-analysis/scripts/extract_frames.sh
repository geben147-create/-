#!/usr/bin/env bash
# extract_frames.sh <video> [max_frames=24] [mode=scene|interval]
# env: START=00:00:00 END=00:00:00 (optional range), SCENE=0.3 (scene threshold), WIDTH=1280
set -euo pipefail
VIDEO="${1:?video path}"; MAX="${2:-24}"; MODE="${3:-scene}"
SCENE="${SCENE:-0.3}"; WIDTH="${WIDTH:-1280}"
NAME="$(basename "${VIDEO%.*}")"
OUT="${OUT:-video-analysis/$NAME/frames}"; mkdir -p "$OUT"; rm -f "$OUT"/frame_*.jpg
command -v ffmpeg >/dev/null || { echo "ffmpeg missing: brew install ffmpeg / sudo apt install ffmpeg / winget install ffmpeg" >&2; exit 1; }
RANGE=(); [[ -n "${START:-}" ]] && RANGE+=(-ss "$START"); [[ -n "${END:-}" ]] && RANGE+=(-to "$END")
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VIDEO" | cut -d. -f1)
FONT=""; for f in /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf /System/Library/Fonts/Helvetica.ttc C:/Windows/Fonts/arial.ttf; do [[ -f "$f" ]] && FONT="fontfile=$f:" && break; done
OVERLAY="drawtext=${FONT}text='%{pts\:hms}':x=10:y=h-th-10:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5"
if [[ "$MODE" == "scene" ]]; then
  VF="select='gt(scene,${SCENE})',${OVERLAY},scale=${WIDTH}:-2"
else
  FPS=$(python3 -c "print(max(${MAX}/max(${DUR:-1},1),0.01))")
  VF="fps=${FPS},${OVERLAY},scale=${WIDTH}:-2"
fi
ffmpeg -v error "${RANGE[@]}" -i "$VIDEO" -vf "$VF" -vsync vfr -frame_pts 1 -q:v 3 "$OUT/tmp_%06d.jpg"
# rename to timestamp-based names using frame pts (seconds) via ffprobe of showinfo is heavy; approximate by order
i=0; n=$(ls "$OUT"/tmp_*.jpg 2>/dev/null | wc -l)
if [[ "$n" -eq 0 && "$MODE" == "scene" ]]; then
  echo "no scene changes above $SCENE, falling back to interval mode" >&2
  exec env OUT="$OUT" "$0" "$VIDEO" "$MAX" interval
fi
# thin out to MAX evenly
python3 - "$OUT" "$MAX" "$DUR" "$n" "$MODE" <<'PY'
import os, sys, glob, shutil
out, mx, dur, n, mode = sys.argv[1], int(sys.argv[2]), int(sys.argv[3] or 0), int(sys.argv[4]), sys.argv[5]
files = sorted(glob.glob(os.path.join(out, "tmp_*.jpg")))
keep = files if len(files) <= mx else [files[int(i*len(files)/mx)] for i in range(mx)]
res = []
for idx, f in enumerate(files):
    if f not in keep:
        os.remove(f); continue
    # estimated timestamp: frame_pts encoded in name is pts in frames for -frame_pts 1 (input fps units); use even spacing fallback
    t = int(dur * (files.index(f) / max(len(files)-1, 1))) if dur else idx
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    dst = os.path.join(out, f"frame_{h:02d}-{m:02d}-{s:02d}_{idx:04d}.jpg")
    shutil.move(f, dst); res.append(dst)
import json; print(json.dumps({"frames": res, "count": len(res), "mode": mode, "duration_s": dur}, indent=1))
PY
