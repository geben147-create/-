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
    """등파워(equal-power) 크로스페이드 곡선 — 두 곡선의 제곱의 합이 1.

    이전 버전은 sin²/cos² 를 써서 진폭의 합이 1이었고(등이득), 서로 다른 소리를 섞는
    이음매마다 약 3 dB 가 꺼졌습니다. 상관 없는 소재를 섞는 크로스페이드에는 이쪽이 맞습니다.
    """
    t = np.linspace(0, 1, max(2, n))
    return np.sin(t * np.pi / 2) if up else np.cos(t * np.pi / 2)


def ramp_linear(n: int, up: bool = True) -> np.ndarray:
    """게인 값 자체를 부드럽게 옮길 때 쓰는 선형 보간 (크로스페이드 아님)."""
    t = np.linspace(0, 1, max(2, n))
    return t if up else (1 - t)


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
            seg[:f_in] = 1.0 + (g - 1.0) * ramp_linear(f_in, up=True)
            seg[-f_in:] = 1.0 + (g - 1.0) * ramp_linear(f_in, up=False)
        # 구간이 겹칠 때 곱하면 -6 dB + -6 dB = -12 dB 가 됩니다. 요청한 것 중 가장 센 감쇠만 적용.
        env[a:b] = np.minimum(env[a:b], seg)
    return (y * env).astype(np.float32)


def crossfade_concat(pieces: list[np.ndarray], sr: int, xfade_ms: float = 180.0) -> np.ndarray:
    pieces = [to_stereo(p) for p in pieces if p is not None and p.shape[-1] > 0]
    if not pieces:
        return np.zeros((2, 1), dtype=np.float32)
    xn = max(2, int(xfade_ms / 1000.0 * sr))
    out = pieces[0]
    for p in pieces[1:]:
        k = min(xn, out.shape[1], p.shape[1])
        if k < 2:                       # 1 샘플짜리 조각은 크로스페이드 없이 그냥 이어붙인다
            out = np.concatenate([out, p], axis=1)
            continue
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
            lookahead_ms: float = 5.0, release_ms: float = 80.0, passes: int = 3) -> tuple[np.ndarray, dict]:
    """오버샘플 트루피크 리미터.

    게인은 오버샘플 영역에서 구하되 '그룹 최솟값'으로 원래 샘플레이트에 내려 신호에 곱합니다
    (신호를 다시 다운샘플하면 필터 링잉으로 피크가 천장 위로 돌아옵니다).
    게인이 시간에 따라 변하면 곱한 뒤의 보간 피크가 조금 올라갈 수 있어, 천장을 넘으면
    같은 계산을 최대 passes 번 반복해 수렴시킵니다.
    """
    from scipy.ndimage import minimum_filter1d

    y = to_stereo(y).astype(np.float64)
    ceiling = lin(ceiling_db)
    la = max(1, int(lookahead_ms / 1000.0 * sr * oversample))
    rel = max(1, int(release_ms / 1000.0 * sr * oversample))
    total_gain = np.ones(y.shape[1])
    out = y
    used = 0
    for _ in range(max(1, passes)):
        up = sig.resample_poly(out, oversample, 1, axis=-1)
        peak = np.max(np.abs(up), axis=0)
        if peak.max() <= ceiling * (1 + 1e-9):
            break
        used += 1
        need = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
        need_min = minimum_filter1d(need, size=la, mode="nearest")     # lookahead
        g = _release_envelope(need_min, rel)
        pad = (-len(g)) % oversample
        g_pad = np.pad(g, (0, pad), mode="edge")
        g_base = g_pad.reshape(-1, oversample).min(axis=1)[: y.shape[1]]
        if len(g_base) < y.shape[1]:
            g_base = np.pad(g_base, (0, y.shape[1] - len(g_base)), mode="edge")
        total_gain = total_gain * g_base
        out = y * total_gain
    out = np.clip(out, -0.999969, 0.999969)
    return out.astype(np.float32), {
        "max_gain_reduction_db": round(float(20 * np.log10(max(total_gain.min(), 1e-9))), 2),
        "ceiling_dbtp_target": ceiling_db, "oversample": oversample, "passes_used": used}


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
    """20 Hz HPF → M/S 폭 → LUFS 정규화 → 리미터. 리미터를 마지막에 두어야 천장이 지켜집니다."""
    import pyloudnorm as pyln

    log = {}
    y = hpf(to_stereo(y), sr, hpf_hz)
    log["hpf_hz"] = hpf_hz
    if abs(side_gain - 1.0) > 1e-6:
        y = ms_width(y, side_gain)
    log["side_gain"] = side_gain
    y, ninfo = normalize_lufs(y, sr, target_lufs)
    log["normalize"] = ninfo
    y, linfo = limiter(y, sr, ceiling_db=ceiling_db)
    log["limiter"] = linfo

    tp = 20 * np.log10(max(float(np.abs(
        sig.resample_poly(to_stereo(y).astype(np.float64), 4, 1, axis=-1)).max()), 1e-12))
    if tp > ceiling_db + 1e-6:                       # 최후 안전장치
        factor = lin(ceiling_db) / (10 ** (tp / 20))
        y = (y * factor).astype(np.float32)
        log["true_peak_trim_db"] = round(20 * np.log10(factor), 3)
        tp = 20 * np.log10(max(float(np.abs(
            sig.resample_poly(to_stereo(y).astype(np.float64), 4, 1, axis=-1)).max()), 1e-12))
    log["final_true_peak_dbtp"] = round(float(tp), 2)

    meter = pyln.Meter(sr)
    achieved = meter.integrated_loudness(to_stereo(y).T.astype(np.float64))
    log["achieved_lufs"] = round(float(achieved), 2) if np.isfinite(achieved) else None
    log["lufs_target"] = target_lufs
    if log["achieved_lufs"] is not None:
        miss = log["achieved_lufs"] - target_lufs
        log["lufs_miss_db"] = round(miss, 2)
        if abs(miss) > 0.5:
            log["lufs_note_ko"] = (f"목표 {target_lufs} LUFS 를 {abs(miss):.2f} LU 못 맞췄습니다. "
                                   f"트루피크 천장 {ceiling_db} dBTP 를 지키면서 이 이상 키울 수 없다는 뜻입니다. "
                                   "더 크게 하려면 편곡·믹스에서 다이내믹을 줄이세요.")
    return y.astype(np.float32), log


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
    bridge_piece_index = None
    if bridge is not None and bridge_at is not None:
        cut = max(0, min(int(bridge_at * sr), n))
        pieces += [base[:, :cut], to_stereo(bridge), base[:, cut:]]
        bridge_piece_index = len(pieces) - 2
        timeline["bridge_sec"] = round(bridge.shape[-1] / sr, 3)
    else:
        pieces.append(base)
    out = crossfade_concat(pieces, sr, xfade_ms)
    if bridge_piece_index is not None:
        # 크로스페이드는 이음매마다 길이를 줄이므로 실제 시작 위치를 다시 계산한다
        xn = max(2, int(xfade_ms / 1000.0 * sr))
        pos = 0
        for i in range(bridge_piece_index):
            k = min(xn, pieces[i].shape[1], pieces[i + 1].shape[1])
            pos += pieces[i].shape[1] - (k if k >= 2 else 0)
        timeline["bridge_inserted_at"] = round(pos / sr, 3)
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
