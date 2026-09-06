"""Tests for configure_clients.py — the parts that edit files a user already owns.

Run with:  python3 -m pytest tests/ -q      (or: python3 tests/test_config_writer.py)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import configure_clients as cc  # noqa: E402

SERVERS = {
    "music-toolkit": {"command": "/opt/venv/bin/python", "args": ["/opt/mt/server.py"]},
    "reaper-twelvetake": {"command": "/opt/bin/twelvetake-reaper-mcp", "args": []},
}


def _codex(tmp_path: Path, text: str):
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    cc.CLIENTS["codex"]["path"] = path
    return path


def test_strip_block_leaves_following_sections_alone():
    """The regex must stop at the next section header, not run to end of file."""
    text = (
        '[mcp_servers.music-toolkit]\ncommand = "x"\nargs = []\n\n'
        '[mcp_servers.user-server]\ncommand = "keep"\n\n'
        '[tui]\ntheme = "dark"\n'
    )
    out = cc._strip_toml_block(text, "mcp_servers.music-toolkit")
    assert "music-toolkit" not in out
    assert "[mcp_servers.user-server]" in out
    assert '[tui]' in out and 'theme = "dark"' in out


def test_codex_remove_preserves_unrelated_sections(tmp_path):
    path = _codex(tmp_path, (
        '# my comment\nmodel = "gpt-5"\n\n'
        '[mcp_servers.music-toolkit]\ncommand = "old"\nargs = []\n\n'
        '[mcp_servers.user-server]\ncommand = "keep"\n\n'
        '[tui]\ntheme = "dark"\n'
    ))
    res = cc._write_toml("codex", SERVERS, remove=True)
    assert res["ok"], res
    out = path.read_text(encoding="utf-8")
    assert "music-toolkit" not in out
    assert "[mcp_servers.user-server]" in out
    assert "# my comment" in out and 'model = "gpt-5"' in out
    assert "[tui]" in out


def test_codex_write_then_rewrite_is_idempotent(tmp_path):
    path = _codex(tmp_path, 'model = "gpt-5"\n')
    for _ in range(3):
        assert cc._write_toml("codex", SERVERS, remove=False)["ok"]
    out = path.read_text(encoding="utf-8")
    for name in SERVERS:
        assert out.count(f"[mcp_servers.{name}]") == 1
    assert 'model = "gpt-5"' in out
    import tomllib
    parsed = tomllib.loads(out)
    assert set(SERVERS).issubset(parsed["mcp_servers"])
    assert parsed["mcp_servers"]["music-toolkit"]["args"] == ["/opt/mt/server.py"]


def test_json_client_preserves_other_keys(tmp_path):
    path = tmp_path / "mcp.json"
    path.write_text(json.dumps({"mcpServers": {"mine": {"command": "keep"}},
                                "otherSetting": True}), encoding="utf-8")
    cc.CLIENTS["cursor"]["path"] = path
    assert cc._write_json("cursor", SERVERS, remove=False)["ok"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["otherSetting"] is True
    assert doc["mcpServers"]["mine"] == {"command": "keep"}
    assert set(SERVERS).issubset(doc["mcpServers"])

    assert cc._write_json("cursor", SERVERS, remove=True)["ok"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert list(doc["mcpServers"]) == ["mine"]


def test_vscode_gets_stdio_type(tmp_path):
    path = tmp_path / "mcp.json"
    cc.CLIENTS["vscode"]["path"] = path
    assert cc._write_json("vscode", SERVERS, remove=False)["ok"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["servers"]["music-toolkit"]["type"] == "stdio"


def test_malformed_json_is_left_untouched(tmp_path):
    path = tmp_path / "mcp.json"
    path.write_text("{ this is not json", encoding="utf-8")
    cc.CLIENTS["cursor"]["path"] = path
    res = cc._write_json("cursor", SERVERS, remove=False)
    assert not res["ok"]
    assert path.read_text(encoding="utf-8") == "{ this is not json"


if __name__ == "__main__":
    import tempfile, traceback
    failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_"):
            continue
        with tempfile.TemporaryDirectory() as td:
            try:
                fn(Path(td)) if fn.__code__.co_argcount else fn()
                print(f"PASS  {name}")
            except Exception:
                failed += 1
                print(f"FAIL  {name}")
                traceback.print_exc()
    raise SystemExit(1 if failed else 0)
