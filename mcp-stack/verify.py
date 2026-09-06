#!/usr/bin/env python3
"""
Verify every configured MCP server by actually speaking the protocol to it:
spawn it, initialize, list its tools, count them. Stdlib only, so it runs
under any Python 3.9+ without installing anything.

    python3 verify.py                # verify servers.json in this directory
    python3 verify.py --json         # machine-readable
    python3 verify.py --client codex # verify what a client's config actually has
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

PROTOCOL = "2025-06-18"


def probe(command: str, args: list[str], env_extra: dict | None = None,
          timeout: float = 90.0) -> dict:
    exe = command if os.path.sep in command else shutil.which(command)
    if exe is None or not Path(exe).exists():
        return {"ok": False, "error": f"not found: {command}"}

    env = dict(os.environ)
    env.update(env_extra or {})
    try:
        proc = subprocess.Popen([exe, *args], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, bufsize=1, env=env)
    except OSError as exc:
        return {"ok": False, "error": f"spawn failed: {exc}"}

    q: queue.Queue = queue.Queue()

    def pump():
        try:
            for line in proc.stdout:
                q.put(line)
        except Exception:
            pass
        q.put(None)

    threading.Thread(target=pump, daemon=True).start()

    def send(obj):
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def wait_for(msg_id):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                line = q.get(timeout=max(0.01, deadline - time.time()))
            except queue.Empty:
                return None
            if line is None:
                return None
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue  # servers that log plain text to stdout
            if obj.get("id") == msg_id:
                return obj
        return None

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": PROTOCOL, "capabilities": {},
            "clientInfo": {"name": "mcp-verify", "version": "1.0"}}})
        init = wait_for(1)
        if init is None:
            try:
                proc.kill()
                tail = (proc.stderr.read() or "").strip().splitlines()[-4:]
            except Exception:
                tail = []
            return {"ok": False, "error": "no initialize response",
                    "stderr": " | ".join(tail)[:400]}
        if "error" in init:
            return {"ok": False, "error": f"initialize error: {init['error']}"}

        result = init.get("result", {})
        info = result.get("serverInfo", {})
        send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        tools, cursor, next_id = [], None, 2
        while True:
            params = {"cursor": cursor} if cursor else {}
            send({"jsonrpc": "2.0", "id": next_id, "method": "tools/list", "params": params})
            resp = wait_for(next_id)
            next_id += 1
            if resp is None:
                return {"ok": False, "error": "no tools/list response",
                        "server": info.get("name")}
            if "error" in resp:
                return {"ok": False, "error": f"tools/list error: {resp['error']}"}
            page = resp.get("result", {})
            tools += page.get("tools", [])
            cursor = page.get("nextCursor")
            if not cursor:
                break

        return {"ok": True, "server": info.get("name"),
                "version": info.get("version"),
                "protocol": result.get("protocolVersion"),
                "tool_count": len(tools),
                "tools": [t.get("name") for t in tools]}
    finally:
        try:
            proc.kill()
        except Exception:
            pass


# --------------------------------------------------------------------------

def load_from_servers_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {name: spec for name, spec in data["servers"].items()}


def load_from_client(client: str) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from configure_clients import CLIENTS, read_client_servers  # noqa: E402
    if client not in CLIENTS:
        raise SystemExit(f"unknown client '{client}'. known: {', '.join(CLIENTS)}")
    return read_client_servers(client)


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify MCP servers by handshake.")
    ap.add_argument("--servers", default=str(Path(__file__).with_name("servers.json")))
    ap.add_argument("--client", help="verify what this client's config actually contains")
    ap.add_argument("--only", help="verify a single server by name")
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    specs = (load_from_client(args.client) if args.client
             else load_from_servers_json(Path(args.servers)))
    if args.only:
        specs = {k: v for k, v in specs.items() if k == args.only}
        if not specs:
            print(f"no server named {args.only}", file=sys.stderr)
            return 2

    results, failures = {}, 0
    for name, spec in specs.items():
        res = probe(spec.get("command", ""), spec.get("args", []),
                    spec.get("env"), args.timeout)
        floor = spec.get("expect_min_tools")
        if res.get("ok") and floor and res["tool_count"] < floor:
            res["ok"] = False
            res["error"] = f"only {res['tool_count']} tools, expected >= {floor}"
        results[name] = res
        failures += 0 if res.get("ok") else 1

    if args.as_json:
        print(json.dumps(results, indent=2))
    else:
        src = f"client:{args.client}" if args.client else Path(args.servers).name
        print(f"\nMCP verification  ({src})")
        print("-" * 74)
        print(f"{'SERVER':<22}{'STATUS':<8}{'TOOLS':>7}  DETAIL")
        print("-" * 74)
        for name, res in results.items():
            if res.get("ok"):
                print(f"{name:<22}{'PASS':<8}{res['tool_count']:>7}  "
                      f"{res.get('server')} v{res.get('version')} "
                      f"(MCP {res.get('protocol')})")
            else:
                print(f"{name:<22}{'FAIL':<8}{'-':>7}  {res.get('error')}")
                if res.get("stderr"):
                    print(f"{'':<37}{res['stderr']}")
        print("-" * 74)
        print(f"{len(results) - failures}/{len(results)} passed\n")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
