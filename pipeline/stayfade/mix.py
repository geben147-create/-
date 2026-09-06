"""08 mixmaster — 구조 재조립 + 믹스 + 마스터.

체인: 구조 조립 → 스템 게인 오토메이션(180 ms 전환) → 새 파트 합성 →
      20 Hz HPF → M/S side gain → 4배 오버샘플 리미터 → LUFS 정규화.
"""
from __future__ import annotations

import numpy as np
from scipy import signal as sig

from .common import lin, to_stereo


def hpf(y: np.ndarray, sr: int, fc: float = 20.0, order: int = 2) -> np.ndarray:
    sos = sig.butter(order, fc / (sr / 2), btype="high", output="sos")
    return sig.sosfilt(sos, y, axis=-1).astype(np.float32)


def ms_width(y: np.ndarray, side_gain: float = 1.0) -> np.ndarray:
    y = to_stereo(y)
    m = (y[0] + y[1]) / 2
    s = (y[0] - y[1]) / 2 * side_gain
    return np.vstack([m + s, m - s]).astype(np.float32)


def ramp(n: int, up: bool = True) -> np.ndarray:
    """등파워 전환 곡선."""
    t = np.linspace(0, 1, max(2, n))
    c = np.sin(t * np.pi / 2) ** 2
    return c if up else (1 - c)


def gain_automation(y: np.ndarray, sr: int, regions: list[dict], transition_ms: float = 180.0) -> np.ndarray:
    """regions: [{"start":s,"end":e,"gain_db":-1.5}] — 경계는 등파워 180 ms 전환."""
    y = to_stereo(y).copy()
    n = y.shape[1]
    env = np.ones(n, dtype=np.float32)
    tn = max(2, int(transition_ms / 1000.0 * sr))
    for r in regions:
        g = lin(float(r.get("gain_db", 0.0)))
        a = max(0, int(float(r["start"]) * sr))
        b = min(n, int(float(r["end"]) * sr))
        if b <= a:
            continue
        seg = np.full(b - a, g, dtype=np.float32)
        f_in = min(tn, len(seg) // 2)
        if f_in > 1:
            seg[:f_in] = 1.0 + (g - 1.0) * ramp(f_in, up=True)
            seg[-f_in:] = 1.0 + (g - 1.0) * ramp(f_in, up=False)
        env[a:b] = env[a:b] * seg
    return (y * env).astype(np.float32)


def crossfade_concat(pieces: list[np.ndarray], sr: int, xfade_ms: float = 180.0) -> np.ndarray:
    pieces = [to_stereo(p) for p in pieces if p is not None and p.shape[-1] > 0]
    if not pieces:
        return np.zeros((2, 1), dtype=np.float32)
    xn = max(2, int(xfade_ms / 1000.0 * sr))
    out = pieces[0]
    for p in pieces[1:]:
        k = min(xn, out.shape[1], p.shape[1])
        head, tail = out[:, :-k], out[:, -k:]
        fade_out = tail * ramp(k, up=False)
        fade_in = p[:, :k] * ramp(k, up=True)
        out = np.concatenate([head, fade_out + fade_in, p[:, k:]], axis=1)
    return out.astype(np.float32)


def _release_envelope(need: np.ndarray, release_samples: int, release_db: float = 20.0) -> np.ndarray:
    """즉시 감쇠(attack) + 선형 dB 복귀(release) 게인 곡선.

    재귀식  v[i] = min(need_db[i], v[i-1] + step)  를 그대로 만족하는 닫힌 형태:
        w[i] = need_db[i] - i*step,   v[i] = i*step + cummin(w)[i]
    파이썬 루프 없이 정확히 같은 결과가 나오고, 곡 길이에 비례해 선형으로만 느려진다.
    """
    if len(need) == 0:
        return need
    step = release_db / max(release_samples, 1)          # 샘플당 복귀량 (dB)
    need_db = 20.0 * np.log10(np.maximum(need, 1e-9))
    idx = np.arange(len(need), dtype=np.float64)
    v = idx * step + np.minimum.accumulate(need_db - idx * step)
    return 10.0 ** (np.minimum(v, 0.0) / 20.0)


def limiter(y: np.ndarray, sr: int, ceiling_db: float = -1.0, oversample: int = 4,
            lookahead_ms: float = 5.0, release_ms: float = 80.0) -> tuple[np.ndarray, dict]:
    """오버샘플 피크 리미터 (인터샘플 피크 억제)."""
    from scipy.ndimage import minimum_filter1d

    y = to_stereo(y).astype(np.float64)
    # 다운샘플 필터의 링잉으로 최종 트루피크가 약간 올라갈 수 있어 0.2 dB 여유를 둔다
    ceiling = lin(ceiling_db - 0.2)
    up = sig.resample_poly(y, oversample, 1, axis=-1)
    peak = np.max(np.abs(up), axis=0)
    la = max(1, int(lookahead_ms / 1000.0 * sr * oversample))
    rel = max(1, int(release_ms / 1000.0 * sr * oversample))
    need = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    need_min = minimum_filter1d(need, size=la, mode="nearest")   # lookahead
    g = _release_envelope(need_min, rel)
    up = up * g
    out = sig.resample_poly(up, 1, oversample, axis=-1)[:, : y.shape[1]]
    gain_reduction_db = float(20 * np.log10(max(g.min(), 1e-9)))
    out = np.clip(out, -0.999969, 0.999969)
    return out.astype(np.float32), {"max_gain_reduction_db": round(gain_reduction_db, 2),
                                    "ceiling_dbtp_target": ceiling_db, "oversample": oversample}


def normalize_lufs(y: np.ndarray, sr: int, target_lufs: float = -14.0) -> tuple[np.ndarray, dict]:
    import pyloudnorm as pyln
    y = to_stereo(y)
    meter = pyln.Meter(sr)
    cur = meter.integrated_loudness(y.T.astype(np.float64))
    if not np.isfinite(cur):
        return y, {"applied_db": 0.0, "before_lufs": None, "target": target_lufs}
    delta = target_lufs - cur
    return (y * lin(delta)).astype(np.float32), {"applied_db": round(float(delta), 2),
                                                 "before_lufs": round(float(cur), 2), "target": target_lufs}


def master_chain(y: np.ndarray, sr: int, target_lufs: float = -14.0, side_gain: float = 1.0,
                 hpf_hz: float = 20.0, ceiling_db: float = -1.0) -> tuple[np.ndarray, dict]:
    log = {}
    y = hpf(to_stereo(y), sr, hpf_hz)
    log["hpf_hz"] = hpf_hz
    if abs(side_gain - 1.0) > 1e-6:
        y = ms_width(y, side_gain)
    log["side_gain"] = side_gain
    y, ninfo = normalize_lufs(y, sr, target_lufs + 1.0)  # 리미터가 약 1 dB 정도 잡아먹는 것을 감안
    log["pre_normalize"] = ninfo
    y, linfo = limiter(y, sr, ceiling_db=ceiling_db)
    log["limiter"] = linfo
    y, ninfo2 = normalize_lufs(y, sr, target_lufs)
    log["final_normalize"] = ninfo2
    # 최종 안전장치: 샘플 피크와 트루피크(4배 오버샘플) 모두 천장 아래로
    peak = float(np.abs(y).max())
    if peak > lin(ceiling_db):
        y = y * (lin(ceiling_db) / peak)
        log["post_trim_db"] = round(20 * np.log10(lin(ceiling_db) / peak), 3)
    tp_lin = float(np.abs(sig.resample_poly(to_stereo(y).astype(np.float64), 4, 1, axis=-1)).max())
    if tp_lin > lin(ceiling_db):
        factor = lin(ceiling_db) / tp_lin
        y = (y * factor).astype(np.float32)
        log["true_peak_trim_db"] = round(20 * np.log10(factor), 3)
    log["final_true_peak_dbtp"] = round(20 * np.log10(max(float(np.abs(
        sig.resample_poly(to_stereo(y).astype(np.float64), 4, 1, axis=-1)).max()), 1e-12)), 2)
    return y, log


def assemble(base: np.ndarray, sr: int, new_layers: dict[str, np.ndarray],
             intro: np.ndarray | None = None, bridge: np.ndarray | None = None,
             bridge_at: float | None = None, xfade_ms: float = 180.0,
             layer_gains_db: dict[str, float] | None = None) -> tuple[np.ndarray, dict]:
    """base(감산 편집된 원곡 바탕) 위에 새 레이어를 얹고, 인트로/브리지를 삽입."""
    layer_gains_db = layer_gains_db or {}
    base = to_stereo(base).copy()
    n = base.shape[1]
    for name, y in new_layers.items():
        y = to_stereo(y) * lin(layer_gains_db.get(name, 0.0))
        m = min(y.shape[1], n)
        base[:, :m] += y[:, :m]
    timeline = {"intro_sec": 0.0, "bridge_inserted_at": None}
    pieces = []
    if intro is not None and intro.shape[-1] > 0:
        pieces.append(to_stereo(intro))
        timeline["intro_sec"] = round(intro.shape[-1] / sr, 3)
    if bridge is not None and bridge_at is not None:
        cut = int(bridge_at * sr)
        cut = max(0, min(cut, n))
        pieces += [base[:, :cut], to_stereo(bridge), base[:, cut:]]
        timeline["bridge_inserted_at"] = round(timeline["intro_sec"] + bridge_at, 3)
        timeline["bridge_sec"] = round(bridge.shape[-1] / sr, 3)
    else:
        pieces.append(base)
    out = crossfade_concat(pieces, sr, xfade_ms)
    timeline["total_sec"] = round(out.shape[1] / sr, 3)
    timeline["xfade_ms"] = xfade_ms
    return out, timeline


def subtract_stems(original: np.ndarray, stems: dict[str, np.ndarray], reductions_db: dict[str, float],
                   sr: int, regions: list[dict] | None = None, transition_ms: float = 180.0) -> np.ndarray:
    """원곡에서 특정 스템을 부분 감산 (구간 지정 가능). 감산 = 원곡 - stem*(1-gain)."""
    out = to_stereo(original).copy()
    n = out.shape[1]
    for name, red_db in reductions_db.items():
        s = stems.get(name)
        if s is None:
            continue
        s = to_stereo(np.atleast_2d(s))
        m = min(s.shape[1], n)
        factor = 1.0 - lin(red_db)  # e.g. -3 dB → 제거 비율 0.29
        env = np.zeros(m, dtype=np.float32)
        if regions:
            tn = max(2, int(transition_ms / 1000.0 * sr))
            for r in regions:
                a, b = max(0, int(r["start"] * sr)), min(m, int(r["end"] * sr))
                if b <= a:
                    continue
                seg = np.ones(b - a, dtype=np.float32)
                f = min(tn, len(seg) // 2)
                if f > 1:
                    seg[:f] = ramp(f, up=True)
                    seg[-f:] = ramp(f, up=False)
                env[a:b] = np.maximum(env[a:b], seg)
        else:
            env[:] = 1.0
        out[:, :m] -= s[:, :m] * factor * env
    return out.astype(np.float32)
