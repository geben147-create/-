# -*- coding: utf-8 -*-
"""Mastering for a rendered mix: 20 Hz high-pass, mid/side width, loudness target,
oversampled true-peak limiting. Mastering is production, not composition — it changes
nothing about who wrote the notes."""
from __future__ import annotations
import numpy as np, soundfile as sf
from scipy import signal, ndimage


def _db(v): return 20 * np.log10(max(float(v), 1e-12))


def read(p):
    x, sr = sf.read(p, dtype="float64", always_2d=True)
    if x.shape[1] == 1: x = np.repeat(x, 2, axis=1)
    return x[:, :2], sr


def highpass(x, sr, fc=20.0):
    return signal.sosfiltfilt(signal.butter(2, fc, btype="highpass", fs=sr, output="sos"), x, axis=0)


def width(x, g):
    m = (x[:, 0] + x[:, 1]) * .5; s = (x[:, 0] - x[:, 1]) * .5 * g
    return np.stack([m + s, m - s], axis=1)


def true_peak(x, sr, os_=4):
    return _db(np.max(np.abs(signal.resample_poly(x, os_, 1, axis=0))))


def lufs(x, sr):
    import pyloudnorm as pyln
    return float(pyln.Meter(sr).integrated_loudness(x))


def limit(x, sr, ceil_db=-1.0, os_=4, look_ms=5.0, rel_ms=80.0):
    """Detector runs oversampled; the gain curve is applied to the original samples so the
    top octave is not filtered away by the resampler."""
    ceil = 10 ** (ceil_db / 20)
    w = signal.firwin(os_ * 64 + 1, 1.0 / os_, window=("kaiser", 14.0))
    up = signal.resample_poly(x, os_, 1, axis=0, window=w)
    fs = sr * os_
    g = np.minimum(1.0, ceil / (np.max(np.abs(up), axis=1) + 1e-12))
    la = max(1, int(look_ms / 1000 * fs))
    g = ndimage.uniform_filter1d(ndimage.minimum_filter1d(g, size=la, mode="nearest"), size=la, mode="nearest")
    rel = np.exp(-1.0 / (rel_ms / 1000 * fs)); out = np.empty_like(g); prev = 1.0
    for i, v in enumerate(g):
        prev = v if v < prev else rel * prev + (1 - rel) * v
        out[i] = prev
    n = len(x); pad = n * os_ - len(out)
    if pad > 0: out = np.concatenate([out, np.full(pad, out[-1])])
    y = x * out[: n * os_].reshape(n, os_).min(axis=1)[:, None]
    tp = 10 ** (true_peak(y, sr) / 20)
    return y * (ceil / tp) if tp > ceil else y


def master(src, dst, target_lufs=-14.0, ceil=-1.0, side=0.95):
    x, sr = read(src)
    before = {"lufs": round(lufs(x, sr), 2), "true_peak": round(true_peak(x, sr), 2),
              "peak": round(_db(np.max(np.abs(x))), 2),
              "clipped": int(np.sum(np.abs(x) >= 0.99997))}
    y = width(highpass(x, sr), side)
    y = y * 10 ** ((target_lufs - lufs(y, sr)) / 20)
    y = limit(y, sr, ceil)
    l = lufs(y, sr)
    if abs(l - target_lufs) > 0.3:
        y = limit(y * 10 ** ((target_lufs - l) / 20), sr, ceil)
    sf.write(dst, np.clip(y, -1, 1), sr, subtype="PCM_24")
    after = {"lufs": round(lufs(y, sr), 2), "true_peak": round(true_peak(y, sr), 2),
             "peak": round(_db(np.max(np.abs(y))), 2),
             "clipped": int(np.sum(np.abs(y) >= 0.99997)),
             "dc": float(np.max(np.abs(np.mean(y, axis=0))))}
    return {"before": before, "after": after, "settings":
            {"highpass_hz": 20, "side_gain": side, "target_lufs": target_lufs, "ceiling_dbtp": ceil,
             "limiter_oversampling": 4}}
