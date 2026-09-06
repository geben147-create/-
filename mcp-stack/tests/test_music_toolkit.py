"""Tests for music_toolkit/server.py's result sanitising.

numpy scalars are not JSON-serialisable; when one leaks into a tool result the
MCP layer replaces the whole result with "Unable to serialize unknown type",
so the caller sees no data and no useful error. _py() is what prevents that.

Run with:  python3 tests/test_music_toolkit.py
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "mt_server", ROOT / "music_toolkit" / "server.py")
mt = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mt)
except ModuleNotFoundError as exc:      # mcp not installed in this interpreter
    print(f"SKIP  music_toolkit tests ({exc})")
    raise SystemExit(0)


def test_py_converts_numpy_scalars():
    try:
        import numpy as np
    except ModuleNotFoundError:
        print("SKIP  numpy not available")
        return
    payload = {
        "flag": np.bool_(True),
        "value": np.float64(1.5),
        "count": np.int64(7),
        "nested": {"checks": {"a": np.bool_(False)}},
        "list": [np.float32(0.25), np.bool_(True)],
        "array": np.array([1, 2, 3]),
    }
    clean = mt._py(payload)
    json.dumps(clean)                      # the actual requirement
    assert clean["flag"] is True
    assert isinstance(clean["value"], float)
    assert isinstance(clean["count"], int)
    assert clean["nested"]["checks"]["a"] is False
    assert clean["array"] == [1, 2, 3]


def test_py_passes_builtins_through_unchanged():
    payload = {"s": "x", "i": 1, "f": 1.0, "b": True, "n": None, "l": [1, "a"]}
    assert mt._py(payload) == {"s": "x", "i": 1, "f": 1.0, "b": True,
                               "n": None, "l": [1, "a"]}


def test_audio_qc_reports_missing_file_instead_of_raising():
    out = mt._audio_qc_impl("/definitely/not/here.wav")
    assert "error" in out


def test_every_tool_is_registered():
    expected = {"list_capabilities", "audio_qc", "detect_tempo_key",
                "detect_sections", "audio_to_midi", "split_stems",
                "prefetch_models", "make_distribution_master",
                "provenance_manifest"}
    for name in expected:
        assert callable(getattr(mt, name, None)) or hasattr(mt, name), name


if __name__ == "__main__":
    import traceback
    failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            fn()
            print(f"PASS  {name}")
        except Exception:
            failed += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
    raise SystemExit(1 if failed else 0)
