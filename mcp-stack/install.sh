#!/usr/bin/env bash
# Install the music MCP stack globally and register it with every MCP client
# on this machine (Claude Code, Codex, Cursor, Claude Desktop, Windsurf,
# VS Code, LM Studio, Gemini CLI).
#
#   ./install.sh                 core audio tools (~350 MB) + both REAPER servers
#   ./install.sh --full          also Demucs + Basic Pitch (multi-GB, needs torch)
#   ./install.sh --full --prefetch   also download the model weights up front
#   ./install.sh --reaper-bridge     also copy the Lua bridge into REAPER
#   ./install.sh --uninstall     remove the servers from every client config
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${MUSIC_MCP_HOME:-$HOME/.local/share/music-mcp}"
FULL=0; PREFETCH=0; BRIDGE=0; UNINSTALL=0; CLIENT_ARGS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --full)          FULL=1 ;;
    --prefetch)      PREFETCH=1 ;;
    --reaper-bridge) BRIDGE=1 ;;
    --uninstall)     UNINSTALL=1 ;;
    --all-clients)   CLIENT_ARGS+=(--all) ;;
    --client)        CLIENT_ARGS+=(--client "$2"); shift ;;
    -h|--help)       sed -n '2,12p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }

# Homebrew is often off PATH when a script is launched from Finder.
if [ "$(uname -s)" = "Darwin" ]; then
  for hb in /usr/local /opt/homebrew; do
    [ -x "$hb/bin/brew" ] && case ":$PATH:" in *":$hb/bin:"*) ;; *) PATH="$hb/bin:$PATH";; esac
  done
fi
export PATH="$HOME/.local/bin:$PATH"

if [ "$UNINSTALL" = 1 ]; then
  say "Removing MCP servers from client configs"
  python3 "$ROOT/configure_clients.py" --remove --all || true
  echo "Client configs cleaned. The installed files are still at: $ROOT"
  echo "Delete them with:  rm -rf \"$ROOT\"  &&  uv tool uninstall twelvetake-reaper-mcp xdarkzx-reaper-mcp"
  exit 0
fi

# ---------------------------------------------------------------- 1. python
say "[1/7] Checking Python"
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 python3 python; do
  command -v "$cand" >/dev/null 2>&1 || continue
  if "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,10) else 1)' 2>/dev/null; then
    PY="$cand"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.10+ is required and was not found." >&2
  echo "  macOS:   brew install python@3.12" >&2
  echo "  Ubuntu:  sudo apt install python3 python3-venv python3-pip" >&2
  echo "  Windows: use install.ps1 instead" >&2
  exit 1
fi
echo "  $($PY --version) at $(command -v "$PY")"

# ---------------------------------------------------------------- 2. uv
say "[2/7] Checking uv"
if ! command -v uv >/dev/null 2>&1; then
  echo "  installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
command -v uv >/dev/null 2>&1 || { echo "uv install failed; see https://docs.astral.sh/uv/" >&2; exit 1; }
echo "  $(uv --version)"
UV_BIN="$(dirname "$(command -v uv)")"

# ------------------------------------------------------- 3. REAPER MCP servers
say "[3/7] Installing the REAPER MCP servers"
uv tool install --force twelvetake-reaper-mcp
# The [analysis] extra is what enables its loudness/clipping/QC tools — without
# it the server starts fine but silently registers 7 fewer tools.
uv tool install --force "xdarkzx-reaper-mcp[analysis]"

# ------------------------------------------------------- 4. music-toolkit venv
say "[4/7] Building the music-toolkit environment at $ROOT"
mkdir -p "$ROOT"
[ -d "$ROOT/venv" ] || uv venv "$ROOT/venv" --python 3.11
VENV_PY="$ROOT/venv/bin/python"

uv pip install --python "$VENV_PY" -q \
  "mcp>=1.2,<2" numpy soundfile librosa pyloudnorm imageio-ffmpeg
echo "  core audio stack installed"

if [ "$FULL" = 1 ]; then
  echo "  installing Demucs + Basic Pitch (this is several GB and takes a while)"
  # Prefer the CPU-only torch build: the default PyPI wheel drags in ~5 GB of
  # CUDA libraries that are useless without an NVIDIA GPU. Fall back if that
  # index is unreachable.
  uv pip install --python "$VENV_PY" -q torch \
      --index-strategy unsafe-best-match \
      --extra-index-url https://download.pytorch.org/whl/cpu \
    || uv pip install --python "$VENV_PY" -q torch
  uv pip install --python "$VENV_PY" -q demucs "basic-pitch[onnx]"
  echo "  Demucs + Basic Pitch installed"
fi

cp -R "$SRC_DIR/music_toolkit" "$ROOT/"
cp "$SRC_DIR/configure_clients.py" "$SRC_DIR/verify.py" "$ROOT/"

# ----------------------------------------------------------- 5. servers.json
say "[5/7] Writing resolved server definitions"
python3 - "$SRC_DIR/servers.json" "$ROOT/servers.json" "$ROOT" "$VENV_PY" "$UV_BIN" <<'PYEOF'
import json, sys
src, dst, root, venv_py, uv_bin = sys.argv[1:6]
text = open(src, encoding="utf-8").read()
for token, value in (("{{ROOT}}", root), ("{{VENV_PYTHON}}", venv_py), ("{{UV_BIN}}", uv_bin)):
    text = text.replace(token, value)
data = json.loads(text)
open(dst, "w", encoding="utf-8").write(json.dumps(data, indent=2) + "\n")
print("  " + dst)
for name, spec in data["servers"].items():
    print(f"    {name:<20}{spec['command']}")
PYEOF

# ------------------------------------------------------------- 6. prefetch
if [ "$PREFETCH" = 1 ]; then
  say "[6/7] Downloading model weights"
  "$VENV_PY" - <<'PYEOF'
import sys
sys.path.insert(0, __import__("os").path.expanduser("~/.local/share/music-mcp"))
try:
    from demucs.pretrained import get_model
    get_model("htdemucs"); print("  demucs htdemucs weights cached")
except Exception as exc:
    print(f"  demucs weights FAILED: {exc}")
try:
    from basic_pitch import ICASSP_2022_MODEL_PATH
    print(f"  basic-pitch model at {ICASSP_2022_MODEL_PATH}")
except Exception as exc:
    print(f"  basic-pitch model FAILED: {exc}")
PYEOF
else
  say "[6/7] Skipping model prefetch (pass --prefetch to download now)"
fi

if [ "$BRIDGE" = 1 ]; then
  say "Installing the REAPER Lua bridge"
  twelvetake-reaper-mcp --install-bridge || echo "  bridge install failed - run REAPER once first"
fi

# --------------------------------------------------------- 7. clients + verify
say "[7/7] Registering with MCP clients"
python3 "$ROOT/configure_clients.py" --servers "$ROOT/servers.json" "${CLIENT_ARGS[@]}"

say "Verifying by MCP handshake"
python3 "$ROOT/verify.py" --servers "$ROOT/servers.json" || true

cat <<EOF

Installed at: $ROOT
Re-verify any time:   python3 $ROOT/verify.py
Check one client:     python3 $ROOT/verify.py --client codex
Add a client later:   python3 $ROOT/configure_clients.py --client cursor
Remove everything:    $SRC_DIR/install.sh --uninstall

Restart your MCP clients so they re-read their config.
The two REAPER servers list their tools without REAPER, but calling those tools
needs REAPER open with the bridge script running.
EOF
