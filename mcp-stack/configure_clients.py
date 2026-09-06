#!/usr/bin/env python3
"""
Write the MCP server definitions from servers.json into every MCP client
installed on this machine — Claude Code, Codex, Cursor, Claude Desktop,
Windsurf, VS Code, LM Studio and Gemini CLI.

Existing config is preserved: files are merged key-by-key and backed up
before the first change. Stdlib only.

    python3 configure_clients.py --list          # what is detected here
    python3 configure_clients.py                 # write to every detected client
    python3 configure_clients.py --all           # write even where not detected
    python3 configure_clients.py --client codex  # one client
    python3 configure_clients.py --remove        # take our servers back out
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import sys
from pathlib import Path

HOME = Path.home()
SYSTEM = platform.system()          # Darwin | Windows | Linux
APPDATA = Path(os.environ.get("APPDATA", HOME / "AppData/Roaming"))
XDG = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config"))


def _per_os(darwin: Path, windows: Path, linux: Path) -> Path:
    return {"Darwin": darwin, "Windows": windows}.get(SYSTEM, linux)


# name -> (config path, file format, JSON key holding the server map)
CLIENTS: dict[str, dict] = {
    "claude-code": {
        "path": HOME / ".claude.json",
        "format": "json", "key": "mcpServers",
        "note": "Claude Code user scope (all projects)",
    },
    "codex": {
        "path": HOME / ".codex/config.toml",
        "format": "toml", "key": "mcp_servers",
        "note": "OpenAI Codex CLI",
    },
    "cursor": {
        "path": HOME / ".cursor/mcp.json",
        "format": "json", "key": "mcpServers",
        "note": "Cursor (global)",
    },
    "claude-desktop": {
        "path": _per_os(HOME / "Library/Application Support/Claude/claude_desktop_config.json",
                        APPDATA / "Claude/claude_desktop_config.json",
                        XDG / "Claude/claude_desktop_config.json"),
        "format": "json", "key": "mcpServers",
        "note": "Claude Desktop",
    },
    "windsurf": {
        "path": HOME / ".codeium/windsurf/mcp_config.json",
        "format": "json", "key": "mcpServers",
        "note": "Windsurf",
    },
    "vscode": {
        "path": _per_os(HOME / "Library/Application Support/Code/User/mcp.json",
                        APPDATA / "Code/User/mcp.json",
                        XDG / "Code/User/mcp.json"),
        "format": "json", "key": "servers", "stdio_type": True,
        "note": "VS Code / GitHub Copilot (uses 'servers' + type:stdio)",
    },
    "lmstudio": {
        "path": HOME / ".lmstudio/mcp.json",
        "format": "json", "key": "mcpServers",
        "note": "LM Studio",
    },
    "gemini-cli": {
        "path": HOME / ".gemini/settings.json",
        "format": "json", "key": "mcpServers",
        "note": "Gemini CLI",
    },
}

# A client counts as present if its config file exists, or its directory does
# (installed but never given an MCP server yet).
def detected(client: str) -> bool:
    p = CLIENTS[client]["path"]
    return p.exists() or p.parent.exists()


def load_servers(servers_json: Path) -> dict[str, dict]:
    data = json.loads(servers_json.read_text(encoding="utf-8"))
    out = {}
    for name, spec in data["servers"].items():
        entry = {"command": spec["command"], "args": spec.get("args", [])}
        if spec.get("env"):
            entry["env"] = spec["env"]
        out[name] = entry
    return out


def _backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():                     # keep the pre-first-run original
        shutil.copy2(path, bak)
    return bak


# ---------------------------------------------------------------- JSON clients

def _write_json(client: str, servers: dict, remove: bool) -> dict:
    cfg = CLIENTS[client]
    path: Path = cfg["path"]
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = {}
    if path.exists() and path.stat().st_size:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return {"client": client, "ok": False,
                    "error": f"existing config is not valid JSON ({exc}); left untouched"}
        if not isinstance(doc, dict):
            return {"client": client, "ok": False,
                    "error": "existing config is not a JSON object; left untouched"}

    bak = _backup(path)
    block = doc.setdefault(cfg["key"], {})
    changed = []
    for name, entry in servers.items():
        if remove:
            if block.pop(name, None) is not None:
                changed.append(name)
            continue
        payload = dict(entry)
        if cfg.get("stdio_type"):
            payload = {"type": "stdio", **payload}
        if block.get(name) != payload:
            block[name] = payload
            changed.append(name)

    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return {"client": client, "ok": True, "path": str(path),
            "changed": changed, "backup": str(bak) if bak else None}


# ---------------------------------------------------------------- TOML (Codex)

def _toml_str(value: str) -> str:
    # TOML basic strings share JSON's escaping rules for the characters that
    # occur in paths, so json.dumps produces a valid TOML literal here.
    return json.dumps(value)


def _strip_toml_block(text: str, header: str) -> str:
    """Remove one [section] block: its header line through the next top-level header."""
    # Multiline but NOT dotall: with re.S the trailing `.*` swallows newlines and
    # the block eats every following section, silently deleting config the user
    # wrote. [^\r\n]* keeps each repetition to a single line.
    pattern = re.compile(
        r"(?m)^[ \t]*\[" + re.escape(header)
        + r"\][ \t]*\r?\n(?:(?!^[ \t]*\[)[^\r\n]*\r?\n?)*"
    )
    return pattern.sub("", text)


def _write_toml(client: str, servers: dict, remove: bool) -> dict:
    cfg = CLIENTS[client]
    path: Path = cfg["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    bak = _backup(path)

    changed = []
    for name in servers:
        header = f"{cfg['key']}.{name}"
        if f"[{header}]" in text:
            text = _strip_toml_block(text, header)
            changed.append(name)
        elif not remove:
            changed.append(name)

    if not remove:
        if text and not text.endswith("\n"):
            text += "\n"
        for name, entry in servers.items():
            text += f"\n[{cfg['key']}.{name}]\n"
            text += f"command = {_toml_str(entry['command'])}\n"
            args = ", ".join(_toml_str(a) for a in entry.get("args", []))
            text += f"args = [{args}]\n"
            if entry.get("env"):
                text += f"\n[{cfg['key']}.{name}.env]\n"
                for k, v in entry["env"].items():
                    text += f"{k} = {_toml_str(str(v))}\n"

    path.write_text(text, encoding="utf-8")

    # Prove we did not corrupt the file: Python 3.11+ can parse TOML natively.
    try:
        import tomllib
        parsed = tomllib.loads(text)
        got = sorted(parsed.get(cfg["key"], {}))
        if not remove and not set(servers).issubset(set(got)):
            return {"client": client, "ok": False,
                    "error": f"post-write check failed; {cfg['key']} has {got}"}
    except ModuleNotFoundError:
        pass
    except Exception as exc:
        if bak and bak.exists():
            shutil.copy2(bak, path)
        return {"client": client, "ok": False,
                "error": f"wrote invalid TOML ({exc}); restored backup"}

    return {"client": client, "ok": True, "path": str(path),
            "changed": changed, "backup": str(bak) if bak else None}


# ---------------------------------------------------------------- read-back

def read_client_servers(client: str) -> dict[str, dict]:
    """Read back what a client's config actually holds — used by verify.py."""
    cfg = CLIENTS[client]
    path: Path = cfg["path"]
    if not path.exists():
        return {}
    if cfg["format"] == "json":
        block = json.loads(path.read_text(encoding="utf-8")).get(cfg["key"], {})
    else:
        import tomllib
        block = tomllib.loads(path.read_text(encoding="utf-8")).get(cfg["key"], {})
    return {name: {"command": spec.get("command", ""),
                   "args": spec.get("args", []),
                   "env": spec.get("env")}
            for name, spec in block.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description="Install MCP servers into every MCP client.")
    ap.add_argument("--servers", default=str(Path(__file__).with_name("servers.json")))
    ap.add_argument("--client", action="append", help="limit to these clients")
    ap.add_argument("--all", action="store_true",
                    help="write even to clients not detected on this machine")
    ap.add_argument("--remove", action="store_true", help="remove our servers again")
    ap.add_argument("--list", action="store_true", dest="do_list")
    args = ap.parse_args()

    if args.do_list:
        print(f"\nMCP clients on this machine ({SYSTEM})")
        print("-" * 78)
        for name, cfg in CLIENTS.items():
            print(f"{'FOUND' if detected(name) else '  -  '}  {name:<16}{cfg['note']}")
            print(f"{'':<9}{cfg['path']}")
        print()
        return 0

    servers = load_servers(Path(args.servers))
    unresolved = [n for n, s in servers.items()
                  if "{{" in s["command"] or any("{{" in a for a in s["args"])]
    if unresolved:
        print(f"servers.json still has unresolved placeholders in: "
              f"{', '.join(unresolved)}. Run install.sh / install.ps1 first.",
              file=sys.stderr)
        return 2

    targets = args.client or [c for c in CLIENTS if args.all or detected(c)]
    if not targets:
        print("No MCP client detected. Use --all to write configs anyway.", file=sys.stderr)
        return 1

    results = []
    for client in targets:
        if client not in CLIENTS:
            results.append({"client": client, "ok": False, "error": "unknown client"})
            continue
        writer = _write_json if CLIENTS[client]["format"] == "json" else _write_toml
        results.append(writer(client, servers, args.remove))

    verb = "Removed from" if args.remove else "Installed into"
    print(f"\n{verb} MCP clients")
    print("-" * 78)
    failures = 0
    for r in results:
        if r["ok"]:
            what = ", ".join(r["changed"]) if r["changed"] else "(already current)"
            print(f"OK    {r['client']:<16}{what}")
            print(f"{'':<6}{r['path']}")
        else:
            failures += 1
            print(f"FAIL  {r['client']:<16}{r['error']}")
    print("-" * 78)
    print(f"{len(results) - failures}/{len(results)} clients written\n")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
