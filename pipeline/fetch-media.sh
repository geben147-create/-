#!/usr/bin/env bash
# ============================================================
# Pull every remote clip named in site/media/sources.js down into
# pipeline/raw/, encode it for the web, then switch the site over to the
# local copies.
#
# Why this is a separate step: the container that generated the media may
# not be allowed to reach the CDN that stores it. Run this anywhere that
# can, then commit site/media/.
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW="$ROOT/pipeline/raw"
SRC="$ROOT/site/media/sources.js"
mkdir -p "$RAW"

command -v node   >/dev/null || { echo "node not found";   exit 1; }
command -v curl   >/dev/null || { echo "curl not found";   exit 1; }
command -v ffmpeg >/dev/null || { echo "ffmpeg not found"; exit 1; }

# sources.js is the single source of truth; read it rather than duplicating it
mapfile -t rows < <(node -e '
  global.window = {};
  require(process.argv[1]);
  const m = window.CLIP_SOURCES.clips;
  for (const [name, c] of Object.entries(m)) {
    for (const slot of ["desktop", "mobile", "webm", "scrub", "tile"]) {
      const u = c[slot] && c[slot].remote;
      if (u) console.log(name + "\t" + slot + "\t" + u);
    }
  }
' "$SRC")

[ ${#rows[@]} -gt 0 ] || { echo "no remote video URLs in $SRC — nothing to fetch"; exit 1; }

declare -A seen
for row in "${rows[@]}"; do
  IFS=$'\t' read -r name slot url <<<"$row"
  # one raw download per clip; the encoder derives every variant from it
  key="$name"
  [ "$slot" = "mobile" ] && key="$name-mobile"
  [ -n "${seen[$key]:-}" ] && continue
  seen[$key]=1

  dest="$RAW/$key.mp4"
  if [ -s "$dest" ]; then echo "have  $key"; continue; fi

  echo "fetch $key"
  for attempt in 1 2 3 4; do
    if curl -fsSL --max-time 300 -o "$dest.part" "$url"; then
      mv "$dest.part" "$dest"; break
    fi
    rm -f "$dest.part"
    if [ "$attempt" = 4 ]; then
      echo "  FAILED after 4 attempts: $url" >&2
      echo "  If this is a 403 from an egress proxy, the CDN host is blocked" >&2
      echo "  by policy — run this script somewhere that can reach it." >&2
      exit 1
    fi
    sleep $((2 ** attempt))
  done
done

"$ROOT/pipeline/encode.sh"

# flip the site over to the encoded local files
node -e '
  const fs = require("fs"), p = process.argv[1];
  const s = fs.readFileSync(p, "utf8").replace(/use:\s*"remote"/, "use: \"local\"");
  fs.writeFileSync(p, s);
' "$SRC"

echo
echo "Done. site/media/sources.js now points at the local, encoded copies."
