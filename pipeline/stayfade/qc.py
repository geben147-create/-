"""09 qc — 기술 검사. 수치 통과가 '좋은 음악'을 뜻하지 않습니다.

측정: LUFS-I / LRA / True Peak(4x) / Sample Peak / Crest / Stereo correlation /
      1초 구간 음(-) 상관 비율 / DC / 0 dBFS 이상 샘플 / 앞뒤 무음 / 길이 / 포맷.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import signal as sig

from .common import audio_info, db, load_audio, to_stereo

# 유통사 기본 규격 (제출 직전에 각 사 공식 페이지에서 반드시 재확인)
DISTRIBUTOR_SPECS = {
    "routenote": {"sr": [44100], "bits": [16], "channels": 2, "formats": ["FLAC", "MP3"],
                  "max_edge_silence_sec": 8.0, "min_track_sec": 3.0,
                  "note_ko": "RouteNote는 WAV 업로드 불가 — 16bit/44.1kHz 스테레오 FLAC 또는 MP3 320kbps"},
    "distrokid": {"sr": [44100, 48000], "bits": [16, 24], "channels": 2, "formats": ["WAV", "FLAC"],
                  "max_edge_silence_sec": 8.0, "min_track_sec": 3.0,
                  "note_ko": "DistroKid는 WAV 권장(16/24bit). 제출 전 공식 페이지 확인"},
    "generic": {"sr": [44100, 48000], "bits": [16, 24], "channels": 2, "formats": ["WAV", "FLAC"],
                "max_edge_silence_sec": 8.0, "min_track_sec": 3.0, "note_ko": "일반 기준"},
}


def true_peak_db(y: np.ndarray, sr: int, oversample: int = 4) -> float:
    up = sig.resample_poly(to_stereo(y).astype(np.float64), oversample, 1, axis=-1)
    return float(db(np.abs(up).max()))


def edge_silence(y: np.ndarray, sr: int, threshold_db: float = -60.0) -> tuple[float, float]:
    mono = np.abs(to_stereo(y)).max(axis=0)
    thr = 10 ** (threshold_db / 20)
    idx = np.where(mono > thr)[0]
    if len(idx) == 0:
        return (len(mono) / sr, len(mono) / sr)
    return (float(idx[0] / sr), float((len(mono) - 1 - idx[-1]) / sr))


def correlation_stats(y: np.ndarray, sr: int, win_sec: float = 1.0, active_db: float = -50.0) -> dict:
    y = to_stereo(y)
    if np.allclose(y[0], y[1]):
        return {"overall": 1.0, "negative_window_ratio_active": 0.0, "active_windows": 0,
                "min_window": 1.0, "mono_note_ko": "좌우 동일 (모노)"}
    dead = bool(np.std(y[0]) < 1e-9 or np.std(y[1]) < 1e-9)
    overall = None if dead else float(np.corrcoef(y[0], y[1])[0, 1])
    n = int(win_sec * sr)
    vals, active = [], 0
    thr = 10 ** (active_db / 20)
    for i in range(0, y.shape[1] - n + 1, n):
        a, b = y[0, i:i + n], y[1, i:i + n]
        if max(np.abs(a).max(), np.abs(b).max()) < thr:
            continue
        active += 1
        if np.std(a) < 1e-9 or np.std(b) < 1e-9:
            vals.append(1.0)
        else:
            vals.append(float(np.corrcoef(a, b)[0, 1]))
    neg = sum(1 for v in vals if v < 0)
    if dead:
        return {"overall": None, "dead_or_constant_channel": True,
                "negative_window_ratio_active": round(neg / max(1, len(vals)) * 100, 2),
                "active_windows": active, "min_window": round(min(vals), 4) if vals else None,
                "note_ko": "한쪽 채널이 무음이거나 상수입니다 — 상관을 계산할 수 없습니다. 파일을 확인하세요."}
    return {"overall": round(overall, 4), "dead_or_constant_channel": False,
            "negative_window_ratio_active": round(neg / max(1, len(vals)) * 100, 2),
            "active_windows": active, "min_window": round(min(vals), 4) if vals else None,
            "note_ko": "참고 검사입니다. 모노 청취를 대체하지 않습니다."}


def measure(path: Path | str, sr_target: int | None = None) -> dict:
    import pyloudnorm as pyln
    info = audio_info(path)
    y, sr = load_audio(path)
    y = to_stereo(y)
    y64 = y.astype(np.float64)
    meter = pyln.Meter(sr)
    lufs_i = meter.integrated_loudness(y64.T)
    # LRA (EBU R128 근사: 3초 게이트 블록의 10-95 백분위)
    lra = _loudness_range(y64, sr)
    sample_peak = float(np.abs(y).max())
    tp = true_peak_db(y, sr)
    rms = float(np.sqrt(np.mean(y64 ** 2)))
    crest = round(db(sample_peak) - db(rms), 2)
    head, tail = edge_silence(y, sr)
    dc = [float(np.mean(ch)) for ch in y64]
    over = int(np.sum(np.abs(y) >= 1.0))
    return {
        "file": info,
        "duration_sec": info["duration_sec"],
        "duration_mmss": f"{int(info['duration_sec'] // 60):02d}:{info['duration_sec'] % 60:05.2f}",
        "lufs_i": round(float(lufs_i), 2) if np.isfinite(lufs_i) else None,
        "lra_lu": round(float(lra), 2) if lra is not None else None,
        "lra_note_ko": "LRA 는 3초 블록의 10~95 백분위로 계산한 근사치입니다 (EBU R128 정식 게이팅과 다를 수 있음).",
        "true_peak_dbtp": round(tp, 2),
        "sample_peak_dbfs": round(db(sample_peak), 2),
        "crest_db": crest,
        "stereo": correlation_stats(y, sr),
        "dc_offset_max_abs": round(max(abs(d) for d in dc), 9),
        "dc_per_channel": [round(d, 9) for d in dc],
        "samples_at_or_over_0dbfs": over,
        "silence_head_sec": round(head, 3),
        "silence_tail_sec": round(tail, 3),
    }


def _loudness_range(y64: np.ndarray, sr: int) -> float | None:
    import pyloudnorm as pyln
    block, hop = 3.0, 1.0
    n, h = int(block * sr), int(hop * sr)
    if y64.shape[1] < n:
        return None
    meter = pyln.Meter(sr)
    vals = []
    for i in range(0, y64.shape[1] - n + 1, h):
        try:
            l = meter.integrated_loudness(y64[:, i:i + n].T)
        except Exception:  # noqa: BLE001
            continue
        if np.isfinite(l):
            vals.append(l)
    if len(vals) < 3:
        return None
    v = np.array(vals)
    v = v[v > (np.max(v) - 40)]  # 상대 게이트 근사
    return float(np.percentile(v, 95) - np.percentile(v, 10))


def check_spec(measurement: dict, distributor: str = "routenote") -> dict:
    spec = DISTRIBUTOR_SPECS.get(distributor, DISTRIBUTOR_SPECS["generic"])
    f = measurement["file"]
    checks = []

    def add(name, ok, detail, severity="fail"):
        checks.append({"check": name, "pass": bool(ok), "detail": detail,
                       "severity": "info" if ok else severity})

    add("샘플레이트", f["samplerate"] in spec["sr"], f"{f['samplerate']} Hz (허용 {spec['sr']})")
    bits = {"PCM_16": 16, "PCM_24": 24, "PCM_32": 32, "FLOAT": 32}.get(f["subtype"], None)
    add("비트뎁스", bits in spec["bits"] if bits else False, f"{f['subtype']} (허용 {spec['bits']}bit)")
    add("채널", f["channels"] == spec["channels"], f"{f['channels']}ch (필요 {spec['channels']}ch)")
    add("포맷", f["format"].upper() in spec["formats"], f"{f['format']} (허용 {spec['formats']})")
    add("클리핑(0 dBFS 이상 샘플)", measurement["samples_at_or_over_0dbfs"] == 0,
        f"{measurement['samples_at_or_over_0dbfs']} samples")
    add("True Peak ≤ -1.0 dBTP", measurement["true_peak_dbtp"] <= -1.0,
        f"{measurement['true_peak_dbtp']} dBTP", severity="warn")
    add("앞 무음 ≤ 8초", measurement["silence_head_sec"] <= spec["max_edge_silence_sec"],
        f"{measurement['silence_head_sec']}초")
    add("뒤 무음 ≤ 8초", measurement["silence_tail_sec"] <= spec["max_edge_silence_sec"],
        f"{measurement['silence_tail_sec']}초")
    add("길이 ≥ 3초", measurement["duration_sec"] >= spec["min_track_sec"], f"{measurement['duration_sec']}초")
    add("DC 오프셋 < 0.001", measurement["dc_offset_max_abs"] < 1e-3,
        f"{measurement['dc_offset_max_abs']}", severity="warn")
    stereo = measurement["stereo"]
    corr = stereo.get("overall")
    if stereo.get("dead_or_constant_channel"):
        add("스테레오 상관 > -0.3 (모노 호환)", False, "한쪽 채널이 무음/상수 — 파일 확인 필요", severity="fail")
    else:
        add("스테레오 상관 > -0.3 (모노 호환)", corr is None or corr > -0.3, f"{corr}", severity="warn")
    lufs = measurement.get("lufs_i")
    add("LUFS-I -18 ~ -6 범위", lufs is None or (-18 <= lufs <= -6), f"{lufs} LUFS", severity="warn")
    fails = [c for c in checks if not c["pass"] and c["severity"] == "fail"]
    warns = [c for c in checks if not c["pass"] and c["severity"] == "warn"]
    return {"distributor": distributor, "spec_note_ko": spec["note_ko"], "checks": checks,
            "fail_count": len(fails), "warn_count": len(warns),
            "verdict": "PASS" if not fails else "FAIL",
            "human_gate_ko": "기술 검사 통과는 전체 청취·권리 확인·유통 승인과 별개입니다."}


def compare(before: dict, after: dict) -> dict:
    def d(k):
        a, b = before.get(k), after.get(k)
        if a is None or b is None:
            return None
        return round(b - a, 2)
    return {
        "lufs_i": {"before": before.get("lufs_i"), "after": after.get("lufs_i"), "delta": d("lufs_i")},
        "lra_lu": {"before": before.get("lra_lu"), "after": after.get("lra_lu"), "delta": d("lra_lu")},
        "true_peak_dbtp": {"before": before.get("true_peak_dbtp"), "after": after.get("true_peak_dbtp"),
                           "delta": d("true_peak_dbtp")},
        "crest_db": {"before": before.get("crest_db"), "after": after.get("crest_db"), "delta": d("crest_db")},
        "duration_sec": {"before": before.get("duration_sec"), "after": after.get("duration_sec"),
                         "delta": round((after.get("duration_sec") or 0) - (before.get("duration_sec") or 0), 2)},
        "stereo_correlation": {"before": before.get("stereo", {}).get("overall"),
                               "after": after.get("stereo", {}).get("overall")},
        "negative_corr_ratio_pct": {"before": before.get("stereo", {}).get("negative_window_ratio_active"),
                                    "after": after.get("stereo", {}).get("negative_window_ratio_active")},
        "dc_offset_max_abs": {"before": before.get("dc_offset_max_abs"), "after": after.get("dc_offset_max_abs")},
        "note_ko": "LRA·crest 변화에는 편곡·무음 길이 변화도 함께 영향을 줍니다.",
    }
