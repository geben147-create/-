"""05 render — 후보 파트를 오디오로. numpy 신스 기본, fluidsynth 있으면 선택 가능."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .common import load_audio, save_wav, to_stereo, which
from . import synth


def render_parts(parts: dict[str, list[dict]], sr: int, total_sec: float,
                 gains_db: dict[str, float] | None = None) -> dict[str, np.ndarray]:
    gains_db = gains_db or {}
    out = {}
    for name, events in parts.items():
        if not events:
            continue
        ev = [{"start": e["start"], "end": e.get("end", e["start"] + e.get("dur", 0.25)),
               "pitch": e["pitch"], "velocity": e.get("velocity", 96)} for e in events]
        is_drum = "drum" in name.lower() or "perc" in name.lower()
        preset = ("bass" if "bass" in name else "pad" if "pad" in name or "chord" in name
                  else "lead" if "melody" in name or "lead" in name else "keys")
        y = synth.render_events(ev, sr, total_sec, preset=preset, drums=is_drum)
        g = 10 ** (gains_db.get(name, 0.0) / 20.0)
        out[name] = (y * g).astype(np.float32)
    return out


def render_with_fluidsynth(midi_path: Path, out_wav: Path, sf2: str | None = None, sr: int = 44100) -> Path | None:
    exe = which("fluidsynth")
    if not exe:
        return None
    sf2 = sf2 or _find_sf2()
    if not sf2:
        return None
    from .common import run_cmd
    rc, log = run_cmd([exe, "-ni", "-F", str(out_wav), "-r", str(sr), "-g", "0.7", sf2, str(midi_path)], timeout=1200)
    return out_wav if rc == 0 and Path(out_wav).exists() else None


def _find_sf2() -> str | None:
    for p in ["/usr/share/sounds/sf2/FluidR3_GM.sf2", "/usr/share/sounds/sf2/default-GM.sf2",
              "/usr/share/soundfonts/FluidR3_GM.sf2"]:
        if Path(p).exists():
            return p
    return None


def mixdown(layers: dict[str, np.ndarray], length: int) -> np.ndarray:
    mix = np.zeros((2, length), dtype=np.float32)
    for y in layers.values():
        y = to_stereo(np.atleast_2d(y))
        n = min(y.shape[1], length)
        mix[:, :n] += y[:, :n]
    return mix


def ab_preview(original: Path, arranged: Path, out_path: Path, at_original: float, at_arranged: float,
               seconds: float = 24.0, gap: float = 1.0, match_loudness: bool = True) -> dict:
    """같은 음량으로 맞춘 A/B 파일: 원본 n초 → 무음 → 편곡 n초."""
    import pyloudnorm as pyln
    yo, sro = load_audio(original)
    ya, sra = load_audio(arranged)
    if sro != sra:
        import librosa
        ya = librosa.resample(ya, orig_sr=sra, target_sr=sro, res_type="soxr_hq")
        sra = sro
    sr = sro
    a = to_stereo(yo)[:, int(at_original * sr): int((at_original + seconds) * sr)]
    b = to_stereo(ya)[:, int(at_arranged * sr): int((at_arranged + seconds) * sr)]
    meter = pyln.Meter(sr)
    la = meter.integrated_loudness(a.T.astype(np.float64))
    lb = meter.integrated_loudness(b.T.astype(np.float64))
    target = min(la, lb)
    if match_loudness and np.isfinite(la) and np.isfinite(lb):
        a = a * (10 ** ((target - la) / 20))
        b = b * (10 ** ((target - lb) / 20))
    silence = np.zeros((2, int(gap * sr)), dtype=np.float32)
    out = np.concatenate([a, silence, b], axis=1)
    peak = float(np.abs(out).max())
    if peak > 0.95:
        out = out * (0.95 / peak)
    save_wav(out_path, out, sr, subtype="PCM_24")
    return {"path": str(out_path), "original_lufs": round(float(la), 2), "arranged_lufs": round(float(lb), 2),
            "matched_to_lufs": round(float(target), 2), "seconds_each": seconds,
            "order_ko": "원본 → 무음 1초 → 편곡"}
