"""Shared audio utilities: loading/saving, metering (LUFS/LRA/true peak/correlation/DC),
20 Hz high-pass, mid/side width, oversampled brick-wall limiter, loudness normalisation.
All processing is float64 internally. Nothing here touches the original file in place."""
from __future__ import annotations
import hashlib, json, re, subprocess, shutil, os
import numpy as np
import soundfile as sf
from scipy import signal, ndimage

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_audio(path: str, sr: int | None = None) -> tuple[np.ndarray, int]:
    """Return (n, 2) float64 array in [-1, 1] and sample rate. Mono is duplicated to stereo."""
    x, fs = sf.read(path, dtype="float64", always_2d=True)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    elif x.shape[1] > 2:
        x = x[:, :2]
    if sr is not None and sr != fs:
        x = resample(x, fs, sr)
        fs = sr
    return x, fs


def resample(x: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return x
    import soxr
    return soxr.resample(x, sr_in, sr_out, quality="VHQ")


def save_wav(path: str, x: np.ndarray, sr: int, subtype: str = "PCM_24", dither: bool = False):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    y = np.asarray(x, dtype=np.float64)
    if dither and subtype == "PCM_16":
        rng = np.random.default_rng(1234)
        lsb = 1.0 / 32768.0
        y = y + (rng.random(y.shape) - rng.random(y.shape)) * lsb  # TPDF dither
    y = np.clip(y, -1.0, 1.0)
    sf.write(path, y, sr, subtype=subtype)


def db(v: float) -> float:
    return 20.0 * np.log10(max(v, 1e-12))


# ---------------------------------------------------------------- metering

def ffmpeg_ebur128(path: str) -> dict:
    """Integrated loudness (LUFS), loudness range (LU) and true peak (dBTP) via ffmpeg ebur128."""
    cmd = [FFMPEG, "-nostats", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"]
    out = subprocess.run(cmd, capture_output=True, text=True).stderr
    out = out.split("Summary:")[-1]  # ignore per-frame log lines, parse only the summary block
    def grab(pattern):
        m = re.search(pattern, out)
        return float(m.group(1)) if m else None
    return {
        "lufs_integrated": grab(r"I:\s+(-?[\d.]+) LUFS"),
        "lra_lu": grab(r"LRA:\s+(-?[\d.]+) LU"),
        "true_peak_dbtp": grab(r"Peak:\s+(-?[\d.]+) dBFS"),
    }


def true_peak_dbtp(x: np.ndarray, sr: int, os_factor: int = 4) -> float:
    up = signal.resample_poly(x, os_factor, 1, axis=0)
    return db(float(np.max(np.abs(up))))


def stereo_stats(x: np.ndarray, sr: int) -> dict:
    l, r = x[:, 0], x[:, 1]
    if np.std(l) < 1e-9 or np.std(r) < 1e-9:
        corr = 1.0
    else:
        corr = float(np.corrcoef(l, r)[0, 1])
    # per-1-second windows on "active" audio (RMS > -50 dBFS): ratio with negative correlation
    n = sr
    neg = 0; act = 0
    for i in range(0, len(x) - n, n):
        seg = x[i:i + n]
        rms = np.sqrt(np.mean(seg ** 2))
        if rms < 10 ** (-50 / 20):
            continue
        act += 1
        if np.std(seg[:, 0]) < 1e-9 or np.std(seg[:, 1]) < 1e-9:
            continue
        c = np.corrcoef(seg[:, 0], seg[:, 1])[0, 1]
        if c < 0:
            neg += 1
    return {"correlation": corr, "neg_corr_ratio_1s": (neg / act) if act else 0.0, "active_seconds": act}


def silence_edges(x: np.ndarray, sr: int, thresh_db: float = -60.0) -> tuple[float, float]:
    a = np.max(np.abs(x), axis=1)
    thr = 10 ** (thresh_db / 20)
    idx = np.where(a > thr)[0]
    if len(idx) == 0:
        return len(x) / sr, len(x) / sr
    return idx[0] / sr, (len(x) - 1 - idx[-1]) / sr


def measure(path: str) -> dict:
    """Full technical QC of a file (used for original and for every render)."""
    x, sr = load_audio(path)
    info = sf.info(path)
    peak = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(x ** 2)))
    head, tail = silence_edges(x, sr)
    ebu = ffmpeg_ebur128(path)
    m = {
        "file": os.path.basename(path),
        "sha256": sha256(path),
        "duration_s": round(len(x) / sr, 3),
        "duration_mmss": f"{int(len(x)/sr//60):02d}:{len(x)/sr%60:05.2f}",
        "sample_rate": sr,
        "channels": info.channels,
        "subtype": info.subtype,
        "sample_peak_dbfs": round(db(peak), 2),
        "true_peak_dbtp_4x": round(true_peak_dbtp(x, sr), 2),
        "rms_dbfs": round(db(rms), 2),
        "crest_factor_db": round(db(peak) - db(rms), 2),
        "dc_offset_max_abs": float(np.max(np.abs(np.mean(x, axis=0)))),
        "clipped_samples_ge_0dbfs": int(np.sum(np.abs(x) >= 0.99997)),
        "head_silence_s": round(head, 2),
        "tail_silence_s": round(tail, 2),
    }
    m.update(ebu)
    m.update(stereo_stats(x, sr))
    return m


# ---------------------------------------------------------------- processing

def highpass(x: np.ndarray, sr: int, fc: float = 20.0, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, fc, btype="highpass", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0)


def lowpass(x: np.ndarray, sr: int, fc: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, min(fc, sr / 2 - 100), btype="lowpass", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0)


def mid_side(x: np.ndarray, side_gain: float) -> np.ndarray:
    m = (x[:, 0] + x[:, 1]) * 0.5
    s = (x[:, 0] - x[:, 1]) * 0.5 * side_gain
    return np.stack([m + s, m - s], axis=1)


def integrated_lufs(x: np.ndarray, sr: int) -> float:
    import pyloudnorm as pyln
    meter = pyln.Meter(sr)
    return float(meter.integrated_loudness(x))


def loudness_normalize(x: np.ndarray, sr: int, target_lufs: float) -> tuple[np.ndarray, float]:
    cur = integrated_lufs(x, sr)
    gain_db = target_lufs - cur
    return x * (10 ** (gain_db / 20)), gain_db


def limiter(x: np.ndarray, sr: int, ceiling_dbtp: float = -1.0, os_factor: int = 4,
            lookahead_ms: float = 5.0, release_ms: float = 80.0) -> np.ndarray:
    """Oversampled brick-wall peak limiter with lookahead (moving-minimum gain) and exponential release."""
    ceiling = 10 ** (ceiling_dbtp / 20)
    up = signal.resample_poly(x, os_factor, 1, axis=0)
    fs = sr * os_factor
    peak = np.max(np.abs(up), axis=1) + 1e-12
    g = np.minimum(1.0, ceiling / peak)
    la = max(1, int(lookahead_ms / 1000 * fs))
    g = ndimage.minimum_filter1d(g, size=la, mode="nearest")
    # attack: smooth downward over lookahead using a short moving average (keeps ceiling because of the min filter)
    g = ndimage.uniform_filter1d(g, size=la, mode="nearest")
    # release: one-pole so gain returns up gradually
    rel = np.exp(-1.0 / (release_ms / 1000 * fs))
    out = np.empty_like(g)
    prev = 1.0
    for i in range(len(g)):
        v = g[i]
        if v < prev:
            prev = v
        else:
            prev = rel * prev + (1 - rel) * v
        out[i] = prev
    up *= out[:, None]
    y = signal.resample_poly(up, 1, os_factor, axis=0)
    # final safety trim for decimation overshoot
    tp = 10 ** (true_peak_dbtp(y, sr) / 20)
    if tp > ceiling:
        y *= ceiling / tp
    return y


def crossfade_gain(n: int, sr: int, start_s: float, end_s: float, ramp_ms: float, level_db: float) -> np.ndarray:
    """Gain curve (linear amplitude) that goes to level_db between start and end with ramps of ramp_ms."""
    g = np.ones(n)
    lvl = 10 ** (level_db / 20)
    r = max(1, int(ramp_ms / 1000 * sr))
    s = int(start_s * sr); e = int(end_s * sr)
    s = max(0, min(n, s)); e = max(0, min(n, e))
    if e <= s:
        return g
    g[s:e] = lvl
    ramp = np.linspace(1.0, lvl, r)
    a = max(0, s - r // 2); g[a:a + len(ramp[:min(r, n - a)])] = ramp[:min(r, n - a)]
    b = max(0, e - r // 2); rr = np.linspace(lvl, 1.0, r); g[b:b + len(rr[:min(r, n - b)])] = rr[:min(r, n - b)]
    return g


def write_json(path: str, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=float)


def tool_versions() -> dict:
    import importlib
    v = {}
    for mod in ["numpy", "scipy", "soundfile", "librosa", "pyloudnorm", "mido", "pretty_midi", "torch", "demucs", "basic_pitch", "soxr"]:
        try:
            m = importlib.import_module(mod)
            v[mod] = getattr(m, "__version__", "installed")
        except Exception:
            v[mod] = None
    try:
        v["ffmpeg"] = subprocess.run([FFMPEG, "-version"], capture_output=True, text=True).stdout.splitlines()[0]
    except Exception:
        v["ffmpeg"] = None
    return v
