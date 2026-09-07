"""빠른 단위 테스트 — 전체 파이프라인을 돌리지 않고 핵심 동작만 검증.

    PYTHONPATH=pipeline python -m pytest pipeline/tests/test_pipeline.py -q
    (pytest 가 없으면)  PYTHONPATH=pipeline python pipeline/tests/test_pipeline.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from stayfade import analyze as A  # noqa: E402
from stayfade import human_gate, midiio, mix, qc, render, synth, variants as V, vocal  # noqa: E402
from stayfade.common import lin, load_audio, save_flac16, save_wav  # noqa: E402

SR = 44100


def _sine(sec=3.0, f=220.0, amp=0.5, sr=SR, detune=1.0):
    t = np.arange(int(sec * sr)) / sr
    return np.vstack([np.sin(2 * np.pi * f * t), np.sin(2 * np.pi * f * detune * t)]).astype(np.float32) * amp


# ---------- synth ----------
def test_synth_handles_negative_start():
    ev = [{"start": -0.5, "end": 0.2, "pitch": 40, "velocity": 100}]
    y = synth.render_events(ev, SR, 2.0, preset="bass")
    assert y.shape == (2, int(2.0 * SR)) and np.isfinite(y).all()
    d = synth.render_events([{"start": -0.3, "end": -0.1, "pitch": 36, "velocity": 100}], SR, 2.0, drums=True)
    assert d.shape[1] == int(2.0 * SR)


def test_synth_events_beyond_end_are_dropped():
    y = synth.render_events([{"start": 99.0, "end": 99.5, "pitch": 60, "velocity": 100}], SR, 1.0)
    assert np.abs(y).max() == 0.0


# ---------- variants ----------
def test_variants_are_deterministic():
    bars = [(i * 2.0, (i + 1) * 2.0) for i in range(4)]
    a = V.make_drums("B_halftime", bars, seed=7)
    b = V.make_drums("B_halftime", bars, seed=7)
    c = V.make_drums("B_halftime", bars, seed=8)
    assert a == b and a != c


def test_variants_produce_notes_for_every_option():
    bars = [(i * 2.0, (i + 1) * 2.0) for i in range(8)]
    for key in V.DRUM_PATTERNS:
        assert len(V.make_drums(key, bars)) > 0
    for key in V.BASS_STYLES:
        assert len(V.make_bass(key, bars, [3, 10, 8, 5], V.NAT_MINOR, 3)) > 0
    for key in V.BRIDGE_SHAPES:
        br = V.make_bridge(key, 0.0, 112, 8, 3, V.NAT_MINOR)
        assert br["melody"] and br["bass"] and br["pad"] and br["bars"] == 8


def test_bass_notes_stay_in_playable_range():
    bars = [(i * 2.0, (i + 1) * 2.0) for i in range(8)]
    for key in V.BASS_STYLES:
        for n in V.make_bass(key, bars, [3, 10, 8, 5], V.NAT_MINOR, 3):
            assert 24 <= n["pitch"] <= 67, f"{key}: {n['pitch']}"


# ---------- midi edits ----------
def test_note_edits_apply_and_report_failures():
    ev = [{"start": i * 0.5, "end": i * 0.5 + 0.4, "pitch": 40 + i, "velocity": 90} for i in range(6)]
    out, log = midiio.apply_note_edits(ev, [
        {"op": "transpose", "index": 1, "semitones": -2},
        {"op": "delete", "index": 0},
        {"op": "velocity", "index": 2, "value": 120},
        {"op": "add", "start": 9.0, "dur": 0.3, "pitch": 55, "velocity": 100},
        {"op": "nope"},
    ])
    assert len(out) == 6                       # 6 - 1 삭제 + 1 추가
    assert sum(1 for r in log if r["applied"]) == 4
    assert any(not r["applied"] and "error" in r for r in log)
    assert all(a["start"] <= b["start"] for a, b in zip(out, out[1:]))


def test_midi_roundtrip():
    bars = [(i * 2.0, (i + 1) * 2.0) for i in range(4)]
    parts = {"bass": V.make_bass("A_root_sustain", bars, [3], V.NAT_MINOR, 3), "drums": V.make_drums("A_straight", bars)}
    with tempfile.TemporaryDirectory() as d:
        p = midiio.write_midi(parts, Path(d) / "t.mid", 112)
        back = midiio.read_midi(p)
        assert sum(len(v) for v in back.values()) == sum(len(v) for v in parts.values())


# ---------- mix / master ----------
def test_limiter_release_matches_reference_recursion():
    rng = np.random.default_rng(0)
    need = np.clip(rng.random(50_000) * 1.2, 0.05, 1.0)
    rel = 4000
    step = 20.0 / rel
    nd = 20 * np.log10(np.maximum(need, 1e-9))
    ref, prev = np.empty_like(nd), 0.0
    for i, x in enumerate(nd):
        prev = min(x, prev + step) if i else x
        ref[i] = prev
    got = 20 * np.log10(np.maximum(mix._release_envelope(need, rel), 1e-12))
    assert np.abs(np.minimum(ref, 0) - got).max() < 1e-9


def test_master_chain_respects_true_peak_and_lufs():
    import pyloudnorm as pyln
    y = _sine(20.0, amp=0.98, detune=1.004)
    y[:, ::5000] = 1.3                                   # 인터샘플 피크 유발
    out, log = mix.master_chain(y, SR, target_lufs=-14.0, ceiling_db=-1.0)
    assert qc.true_peak_db(out, SR) <= -1.0 + 1e-6
    assert abs(pyln.Meter(SR).integrated_loudness(out.T.astype(float)) + 14.0) < 0.3
    assert np.abs(out).max() < 1.0


def test_gain_automation_applies_requested_reduction():
    y = _sine(4.0, amp=0.5)
    g = mix.gain_automation(y, SR, [{"start": 1.0, "end": 3.0, "gain_db": -6.0}])
    mid = np.abs(g[:, int(2.0 * SR): int(2.2 * SR)]).max()
    ref = np.abs(y[:, int(2.0 * SR): int(2.2 * SR)]).max()
    assert abs(20 * np.log10(mid / ref) + 6.0) < 0.5


def test_crossfade_concat_length_and_continuity():
    a, b = _sine(2.0), _sine(2.0, f=330)
    out = mix.crossfade_concat([a, b], SR, xfade_ms=180)
    expected = a.shape[1] + b.shape[1] - int(0.180 * SR)
    assert abs(out.shape[1] - expected) <= 2
    assert np.abs(out).max() <= 1.0


def test_subtract_stems_reduces_energy():
    y = _sine(3.0, amp=0.6)
    stems = {"drums": y * 0.5}
    out = mix.subtract_stems(y, stems, {"drums": -6.0}, SR)
    assert np.abs(out).max() < np.abs(y).max()


# ---------- qc ----------
def test_qc_measures_and_flags_spec():
    with tempfile.TemporaryDirectory() as d:
        w = save_wav(Path(d) / "a.wav", _sine(12.0, amp=0.3, detune=1.002), SR, subtype="PCM_24")
        m = qc.measure(w)
        assert m["duration_sec"] == 12.0 and m["samples_at_or_over_0dbfs"] == 0
        assert m["lufs_i"] is not None and m["true_peak_dbtp"] < 0
        r = qc.check_spec(m, "routenote")
        names = {c["check"] for c in r["checks"] if not c["pass"]}
        assert "포맷" in names and "비트뎁스" in names        # WAV 24bit 은 RouteNote 규격 아님
        f = save_flac16(Path(d) / "a.flac", _sine(12.0, amp=0.3, detune=1.002), SR)
        assert qc.check_spec(qc.measure(f), "routenote")["verdict"] == "PASS"


def test_qc_correlation_handles_mono_and_silence():
    mono = np.vstack([np.sin(np.arange(SR) / 50)] * 2).astype(np.float32)
    s = qc.correlation_stats(mono, SR)
    assert s["overall"] == 1.0 and s["negative_window_ratio_active"] == 0.0
    silent = np.zeros((2, SR), dtype=np.float32)
    assert qc.correlation_stats(silent, SR)["active_windows"] == 0


def test_qc_detects_edge_silence():
    y = np.zeros((2, SR * 10), dtype=np.float32)
    y[:, SR * 3: SR * 5] = _sine(2.0, amp=0.4)
    head, tail = qc.edge_silence(y, SR)
    assert 2.9 < head < 3.1 and 4.9 < tail < 5.1


# ---------- vocal ----------
def test_autotune_reduces_pitch_error():
    t = np.arange(int(SR * 4)) / SR
    x = np.zeros_like(t)
    for f, st, cents in [(233.08, 0, 40), (277.18, 1, -35), (311.13, 2, 50), (233.08, 3, 25)]:
        seg = (t >= st) & (t < st + 0.85)
        x[seg] = np.sin(2 * np.pi * f * 2 ** (cents / 1200) * t[seg]) * 0.4 * np.hanning(seg.sum())
    before = vocal.detect_notes(x, SR)["median_abs_cents_off"]
    y, info = vocal.autotune(x.astype(np.float32), SR, scale_pcs=[3, 5, 6, 8, 10, 11, 1])
    after = vocal.detect_notes(y, SR)["median_abs_cents_off"]
    assert info["notes_corrected"] > 0 and after < before


def test_process_take_never_clips_with_harmony():
    t = np.arange(int(SR * 3)) / SR
    x = (np.sin(2 * np.pi * 233.08 * t) * 0.5 * np.hanning(len(t))).astype(np.float32)
    with tempfile.TemporaryDirectory() as d:
        src = save_wav(Path(d) / "take.wav", np.vstack([x, x]), SR)
        r = vocal.process_take(src, Path(d) / "out", sr_target=SR, do_harmony=True)
        y, _ = load_audio(r["output"])
        assert np.abs(y).max() <= lin(-3.0) + 1e-3


# ---------- human gate ----------
def test_gate_blocks_until_decided_and_validates_choices():
    cands = {"groups": {"drums": {"question_ko": "?", "options": [{"id": "A"}, {"id": "B"}]}}}
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "hd.json"
        dec, ready = human_gate.load_or_create(cands, p)
        assert not ready and dec["status"] == "PENDING"
        dec["decisions"][0]["choice"] = "Z"
        dec["status"] = "DECIDED"
        dec["decided_by"] = "human"
        assert any("없는 옵션" in m for m in human_gate.validate(dec, cands))
        dec["decisions"][0]["choice"] = "B"
        assert human_gate.validate(dec, cands) == []


# ---------- analyze ----------
def test_key_parsing_and_override():
    assert A.parse_key("Ebm") == (3, "minor")
    assert A.parse_key("Gb") == (6, "major")
    assert A.parse_key("C#m") == (1, "minor")
    for bad in ("Hm", "", "xyz"):
        try:
            A.parse_key(bad)
            raise AssertionError(f"{bad} 는 실패해야 합니다")
        except ValueError:
            pass
    o = A.override_key({"key": "Gb", "confidence": 0.3, "ambiguous": True}, "Ebm")
    assert o["key"] == "Ebm" and o["manual"] and not o["ambiguous"]


def test_bar_grid_extends_to_zero_and_end():
    beats = [8.0 + i * 0.5 for i in range(40)]
    bars = A.downbeats_from_beats(beats, 4, duration=40.0)
    assert bars[0] < 2.0 and bars[-1] > 30.0
    assert all(b < a for a, b in zip(bars[1:], bars[:-1]))


# ---------- schema ----------
def test_repo_schemas_accept_example_outputs():
    import jsonschema
    root = Path(__file__).resolve().parents[2]
    ex, sch = root / "docs" / "example_outputs", root / "skill" / "schema"
    if not ex.exists():
        return
    pairs = {"project.json": "project.schema.json", "human_decisions.json": "human_decisions.schema.json",
             "arrangement_manifest.json": "arrangement_manifest.schema.json", "qc.json": "qc.schema.json",
             "candidates.json": "candidates.schema.json", "analysis.json": "analysis.schema.json"}
    for f, s in pairs.items():
        if (ex / f).exists():
            jsonschema.validate(json.loads((ex / f).read_text(encoding="utf-8")),
                                json.loads((sch / s).read_text(encoding="utf-8")))


def test_gate_rejects_empty_or_partial_decisions():
    cands = {"groups": {"drums": {"question_ko": "?", "options": [{"id": "A"}]},
                        "bass": {"question_ko": "?", "options": [{"id": "X"}]}}}
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "hd.json"
        p.write_text(json.dumps({"schema": "stayfade/human_decisions/1", "status": "DECIDED",
                                 "decided_by": "human", "decisions": []}), encoding="utf-8")
        dec, ready = human_gate.load_or_create(cands, p)
        assert not ready and human_gate.validate(dec, cands)
        p.write_text(json.dumps({"schema": "stayfade/human_decisions/1", "status": "DECIDED",
                                 "decided_by": "human",
                                 "decisions": [{"id": "drums", "choice": "A"}]}), encoding="utf-8")
        dec, ready = human_gate.load_or_create(cands, p)
        assert not ready and any("bass" in m for m in human_gate.validate(dec, cands))


def test_transpose_range_edit_applies():
    ev = [{"start": i * 0.5, "end": i * 0.5 + 0.4, "pitch": 60 + i, "velocity": 90} for i in range(6)]
    out, log = midiio.apply_note_edits(ev, [{"op": "transpose_range", "from": 2, "to": 4, "semitones": -2}])
    assert log[0]["applied"] and log[0]["notes_changed"] == 3
    assert [n["pitch"] for n in out] == [60, 61, 60, 61, 62, 65]


def test_drum_synthesis_is_process_stable():
    import hashlib
    import subprocess
    code = ("import sys;sys.path.insert(0,%r);from stayfade import synth;import hashlib;"
            "print(hashlib.sha256(synth.drum_hit('snare',44100,1.0,0).tobytes()).hexdigest())"
            % str(Path(__file__).resolve().parents[1]))
    hashes = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True).stdout.strip()
              for _ in range(2)}
    assert len(hashes) == 1 and hashes != {""}


def test_mono_center_presets_are_correlated():
    y = synth.render_events([{"start": 0.0, "end": 1.0, "pitch": 40, "velocity": 100}], SR, 2.0, preset="bass")
    assert abs(np.corrcoef(y[0], y[1])[0, 1] - 1.0) < 1e-6


def test_crossfade_is_equal_power():
    up, down = mix.ramp(1000, True), mix.ramp(1000, False)
    assert abs(float(up[500] ** 2 + down[500] ** 2) - 1.0) < 1e-6


def test_overlapping_automation_regions_do_not_stack():
    y = np.ones((2, SR * 8), dtype=np.float32)
    g = mix.gain_automation(y, SR, [{"start": 1, "end": 5, "gain_db": -6.0},
                                    {"start": 3, "end": 7, "gain_db": -6.0}])
    assert abs(20 * np.log10(float(np.abs(g[:, int(4 * SR)]).max())) + 6.0) < 0.3


def test_align_to_grid_preserves_head_and_avoids_clicks():
    t = np.arange(int(SR * 4)) / SR
    x = np.zeros_like(t)
    x[: int(0.45 * SR)] = np.sin(2 * np.pi * 180 * t[: int(0.45 * SR)]) * 0.3
    for st in [0.55, 1.03, 1.52, 2.07, 2.55, 3.1]:
        seg = (t >= st) & (t < st + 0.35)
        x[seg] += np.sin(2 * np.pi * 300 * t[seg]) * 0.5 * np.hanning(seg.sum())
    x = x.astype(np.float32)
    out, _ = vocal.align_to_grid(x, SR, [0.5 + i * 0.5 for i in range(8)])
    assert np.sqrt(np.mean(out[: int(0.4 * SR)] ** 2)) > 0.5 * np.sqrt(np.mean(x[: int(0.4 * SR)] ** 2))
    assert float(np.abs(np.diff(out)).max()) <= float(np.abs(np.diff(x)).max()) * 1.5 + 0.02


def test_align_to_grid_skips_unreliable_onsets():
    t = np.arange(int(SR * 4)) / SR
    tone = (np.sin(2 * np.pi * 220 * t) * 0.4).astype(np.float32)
    out, info = vocal.align_to_grid(tone, SR, [0.5 + i * 0.5 for i in range(8)])
    assert info["moved"] == 0 and np.allclose(out, tone)


def test_qc_correlation_json_serialisable_for_dead_channel():
    dead = np.vstack([np.sin(np.arange(SR) / 50), np.zeros(SR)]).astype(np.float32)
    st = qc.correlation_stats(dead, SR)
    assert st["overall"] is None and st["dead_or_constant_channel"] is True
    json.dumps(st)


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in fns:
        try:
            f()
            print(f"  ok  {n}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  FAIL {n}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
