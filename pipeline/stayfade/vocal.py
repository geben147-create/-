"""07 vocal — 사람이 부른 보컬 정리 (컴핑·튠·타이밍·노이즈·디에서·EQ·컴프·하모니).

전제: 원본 RAW 테이크는 절대 덮어쓰지 않습니다 (03_human_raw 보존 + 해시).
보정은 '실연'을 지우지 않습니다. 다만 실연 기여이지 작곡 기여는 아닙니다.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import signal as sig

from .common import db, lin, load_audio, save_wav, to_stereo


def _mono(y):
    return to_stereo(np.atleast_2d(y)).mean(axis=0)


# ---------- noise ----------
def denoise(y: np.ndarray, sr: int, strength: float = 1.0, n_fft: int = 2048) -> np.ndarray:
    """가장 조용한 구간에서 노이즈 프로파일을 뽑아 스펙트럼 차감."""
    x = _mono(y)
    f, t, Z = sig.stft(x, sr, nperseg=n_fft, noverlap=n_fft * 3 // 4)
    mag, phase = np.abs(Z), np.angle(Z)
    frame_energy = mag.mean(axis=0)
    k = max(3, int(len(frame_energy) * 0.05))
    quiet = np.argsort(frame_energy)[:k]
    profile = np.median(mag[:, quiet], axis=1, keepdims=True)
    cleaned = np.maximum(mag - profile * (1.5 * strength), mag * 0.08)
    _, out = sig.istft(cleaned * np.exp(1j * phase), sr, nperseg=n_fft, noverlap=n_fft * 3 // 4)
    return out[: len(x)].astype(np.float32)


def gate(y: np.ndarray, sr: int, threshold_db: float = -48.0, attack_ms: float = 5,
         release_ms: float = 120) -> np.ndarray:
    x = _mono(y)
    env = np.abs(sig.hilbert(x)) if len(x) < 3_000_000 else np.abs(x)
    thr = lin(threshold_db)
    target = (env > thr).astype(np.float32)
    a = int(sr * attack_ms / 1000); r = int(sr * release_ms / 1000)
    sm = np.copy(target)
    coef_a = np.exp(-1 / max(a, 1)); coef_r = np.exp(-1 / max(r, 1))
    cur = 0.0
    for i in range(len(sm)):
        t = target[i]
        cur = coef_a * cur + (1 - coef_a) * t if t > cur else coef_r * cur + (1 - coef_r) * t
        sm[i] = cur
    return (x * sm).astype(np.float32)


# ---------- pitch ----------
def detect_notes(y: np.ndarray, sr: int, fmin: float = 65.0, fmax: float = 1000.0) -> dict:
    import librosa
    x = _mono(y)
    f0, voiced, vprob = librosa.pyin(x, fmin=fmin, fmax=fmax, sr=sr, frame_length=2048)
    times = librosa.times_like(f0, sr=sr)
    midi = librosa.hz_to_midi(np.where(np.isnan(f0), np.nan, f0))
    segs = []
    cur = None
    for i, (m, v) in enumerate(zip(midi, voiced)):
        if v and np.isfinite(m):
            if cur is None:
                cur = {"start_i": i, "pitches": [m]}
            elif abs(m - np.median(cur["pitches"])) > 1.6:  # 새 음으로 판단
                segs.append(cur); cur = {"start_i": i, "pitches": [m]}
            else:
                cur["pitches"].append(m)
        else:
            if cur is not None and len(cur["pitches"]) > 3:
                segs.append(cur)
            cur = None
    if cur is not None and len(cur["pitches"]) > 3:
        segs.append(cur)
    notes = []
    for s in segs:
        i0 = s["start_i"]; i1 = i0 + len(s["pitches"])
        med = float(np.median(s["pitches"]))
        notes.append({"start": float(times[i0]), "end": float(times[min(i1, len(times) - 1)]),
                      "midi_median": round(med, 3), "nearest": int(round(med)),
                      "cents_off": round((med - round(med)) * 100, 1)})
    return {"notes": notes, "f0_voiced_ratio": round(float(np.mean(voiced)), 3),
            "median_abs_cents_off": round(float(np.median([abs(n["cents_off"]) for n in notes])) if notes else 0.0, 1)}


def autotune(y: np.ndarray, sr: int, scale_pcs: list[int] | None = None, strength: float = 0.85,
             max_correction_semitones: float = 2.0) -> tuple[np.ndarray, dict]:
    """노트 단위 리튠. scale_pcs 를 주면 스케일 음으로, 없으면 가장 가까운 반음으로."""
    import librosa
    x = _mono(y).astype(np.float32)
    info = detect_notes(x, sr)
    out = np.copy(x)
    applied = []
    for n in info["notes"]:
        a, b = int(n["start"] * sr), int(n["end"] * sr)
        if b - a < int(0.04 * sr):
            continue
        med = n["midi_median"]
        if scale_pcs:
            cands = [p for p in range(int(med) - 2, int(med) + 3) if p % 12 in scale_pcs]
            target = min(cands, key=lambda p: abs(p - med)) if cands else round(med)
        else:
            target = round(med)
        delta = (target - med) * strength
        if abs(delta) < 0.02 or abs(delta) > max_correction_semitones:
            continue
        seg = x[a:b]
        try:
            shifted = librosa.effects.pitch_shift(y=seg, sr=sr, n_steps=float(delta), bins_per_octave=12)
            m = min(len(shifted), b - a)
            win = np.ones(m)
            f = min(int(0.005 * sr), m // 2)
            if f > 1:
                win[:f] = np.linspace(0, 1, f); win[-f:] = np.linspace(1, 0, f)
            out[a:a + m] = out[a:a + m] * (1 - win) + shifted[:m] * win
            applied.append({"start": round(n["start"], 3), "semitones": round(float(delta), 3),
                            "target_midi": int(target)})
        except Exception:  # noqa: BLE001
            continue
    return out.astype(np.float32), {"notes_detected": len(info["notes"]), "notes_corrected": len(applied),
                                    "median_abs_cents_off_before": info["median_abs_cents_off"],
                                    "corrections": applied[:200],
                                    "note_ko": "반음(100 cents) 이상 어긋난 음은 보정보다 재녹음이 낫습니다."}


def align_to_grid(y: np.ndarray, sr: int, beat_times: list[float], subdiv: int = 2,
                  max_shift_ms: float = 90.0) -> tuple[np.ndarray, dict]:
    """온셋을 가장 가까운 그리드로 당기고 미는 간단한 타이밍 정렬 (구간 단위 시프트)."""
    import librosa
    x = _mono(y)
    if len(beat_times) < 2:
        return x, {"moved": 0, "reason": "beat grid 없음"}
    grid = []
    for i in range(len(beat_times) - 1):
        for k in range(subdiv):
            grid.append(beat_times[i] + (beat_times[i + 1] - beat_times[i]) * k / subdiv)
    grid = np.array(grid + [beat_times[-1]])
    onsets = librosa.onset.onset_detect(y=x, sr=sr, units="time", backtrack=True)
    out = np.zeros_like(x)
    moved = 0
    bounds = list(onsets) + [len(x) / sr]
    prev_end = 0
    for i, on in enumerate(onsets):
        j = int(np.argmin(np.abs(grid - on)))
        shift = float(grid[j] - on)
        if abs(shift) > max_shift_ms / 1000.0:
            shift = np.sign(shift) * max_shift_ms / 1000.0
        a = int(on * sr); b = int(bounds[i + 1] * sr)
        a = max(a, prev_end); b = min(b, len(x))
        if b <= a:
            continue
        dst = int(a + shift * sr)
        dst = max(0, min(dst, len(out) - (b - a)))
        out[dst:dst + (b - a)] += x[a:b]
        prev_end = b
        if abs(shift) > 0.003:
            moved += 1
    if prev_end < len(x):
        out[prev_end:] += x[prev_end:]
    return out.astype(np.float32), {"onsets": len(onsets), "moved": moved, "max_shift_ms": max_shift_ms}


# ---------- tone ----------
def deesser(y: np.ndarray, sr: int, freq: float = 6500.0, threshold_db: float = -28.0, ratio: float = 4.0):
    x = _mono(y)
    sos = sig.butter(2, min(freq / (sr / 2), 0.99), btype="high", output="sos")
    hi = sig.sosfilt(sos, x)
    env = np.abs(sig.lfilter([0.02], [1, -0.98], np.abs(hi)))
    thr = lin(threshold_db)
    over = np.maximum(env / max(thr, 1e-9), 1.0)
    g = over ** (1 / ratio - 1)
    return (x - hi + hi * g).astype(np.float32), {"freq": freq, "min_gain_db": round(float(db(g.min())), 2)}


def eq(y: np.ndarray, sr: int, hpf_hz: float = 90.0, presence_db: float = 2.0, mud_db: float = -2.0):
    x = _mono(y)
    sos = sig.butter(2, hpf_hz / (sr / 2), btype="high", output="sos")
    x = sig.sosfilt(sos, x)
    x = _peaking(x, sr, 300.0, mud_db, q=1.0)
    x = _peaking(x, sr, 3500.0, presence_db, q=0.9)
    return x.astype(np.float32)


def _peaking(x, sr, f0, gain_db, q=1.0):
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / sr
    alpha = np.sin(w0) / (2 * q)
    b = [1 + alpha * A, -2 * np.cos(w0), 1 - alpha * A]
    a = [1 + alpha / A, -2 * np.cos(w0), 1 - alpha / A]
    return sig.lfilter(np.array(b) / a[0], np.array(a) / a[0], x)


def compress(y: np.ndarray, sr: int, threshold_db: float = -20.0, ratio: float = 3.0,
             attack_ms: float = 8, release_ms: float = 120, makeup_db: float | None = None):
    x = _mono(y)
    env = np.abs(x)
    a = np.exp(-1 / max(sr * attack_ms / 1000, 1)); r = np.exp(-1 / max(sr * release_ms / 1000, 1))
    sm = np.empty_like(env); cur = 0.0
    for i in range(len(env)):
        e = env[i]
        cur = a * cur + (1 - a) * e if e > cur else r * cur + (1 - r) * e
        sm[i] = cur
    thr = lin(threshold_db)
    over_db = 20 * np.log10(np.maximum(sm / thr, 1e-9))
    gain_db_arr = np.where(over_db > 0, -over_db * (1 - 1 / ratio), 0.0)
    out = x * 10 ** (gain_db_arr / 20)
    if makeup_db is None:
        makeup_db = float(-np.percentile(gain_db_arr, 5)) * 0.7
    out = out * lin(makeup_db)
    return out.astype(np.float32), {"makeup_db": round(makeup_db, 2),
                                    "max_reduction_db": round(float(gain_db_arr.min()), 2)}


def harmony(y: np.ndarray, sr: int, intervals: list[int] = (3, 7), gain_db: float = -9.0,
            delay_ms: float = 12.0, spread: float = 0.6) -> np.ndarray:
    """스케일 간격으로 하모니 생성 (자동 생성물이며 인간 실연이 아닙니다)."""
    import librosa
    x = _mono(y)
    out = np.zeros((2, len(x)), dtype=np.float32)
    for k, iv in enumerate(intervals):
        h = librosa.effects.pitch_shift(y=x, sr=sr, n_steps=float(iv))
        d = int(sr * delay_ms / 1000 * (k + 1))
        h = np.concatenate([np.zeros(d), h])[: len(x)]
        pan = spread * (1 if k % 2 == 0 else -1)
        l = np.cos((pan + 1) * np.pi / 4) * 1.414; r = np.sin((pan + 1) * np.pi / 4) * 1.414
        out[0] += h * lin(gain_db) * l
        out[1] += h * lin(gain_db) * r
    return out


def process_take(src: Path, out_dir: Path, sr_target: int = 44100, scale_pcs: list[int] | None = None,
                 beat_times: list[float] | None = None, do_harmony: bool = False) -> dict:
    """RAW 테이크 → 보정본. 원본은 건드리지 않습니다."""
    y, sr = load_audio(src, sr=sr_target, mono=True)
    x = y[0]
    steps = {}
    x = denoise(x, sr, strength=0.8); steps["denoise"] = "spectral subtraction (0.8)"
    x = gate(x, sr, threshold_db=-50); steps["gate"] = "-50 dB"
    x, tinfo = autotune(x, sr, scale_pcs=scale_pcs, strength=0.85)
    steps["autotune"] = tinfo
    if beat_times:
        x, ainfo = align_to_grid(x, sr, beat_times)
        steps["timing"] = ainfo
    x, dinfo = deesser(x, sr); steps["deesser"] = dinfo
    x = eq(x, sr); steps["eq"] = "HPF 90 Hz / 300 Hz -2 dB / 3.5 kHz +2 dB"
    x, cinfo = compress(x, sr); steps["compressor"] = cinfo
    peak = float(np.abs(x).max())
    if peak > 0:
        x = x * (lin(-3.0) / peak)
    stereo = np.vstack([x, x]).astype(np.float32)
    if do_harmony:
        stereo = stereo + harmony(x, sr)
        steps["harmony"] = "3도/5도 자동 생성 (인간 실연 아님)"
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{Path(src).stem}_processed.wav"
    save_wav(out_path, stereo, sr, subtype="PCM_24")
    return {"source": str(src), "output": str(out_path), "sr": sr, "steps": steps,
            "raw_preserved_ko": "원본 RAW 파일은 수정하지 않았습니다."}
