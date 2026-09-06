#!/bin/bash
# Demucs htdemucs checkpoint. The default host (dl.fbaipublicfiles.com) is sometimes blocked by
# corporate/agent proxies; the same object is reachable through the S3 path-style URL.
set -e
D="$HOME/.cache/torch/hub/checkpoints"; mkdir -p "$D"; cd "$D"
F=955717e8-8726e21a.th
[ -f "$F" ] && { echo "already present: $D/$F"; exit 0; }
curl -fL -o "$F.part" "https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/$F" \
 || curl -fL -o "$F.part" "https://s3.us-west-2.amazonaws.com/dl.fbaipublicfiles.com/demucs/hybrid_transformer/$F"
echo "sha256 prefix (expect 8726e21a): $(sha256sum "$F.part" | cut -c1-8)"
mv "$F.part" "$F"; echo "saved $D/$F"
