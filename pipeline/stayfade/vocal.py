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


def _smooth_asym(target: np.ndarray, attack_samples: int, release_samples: int,
                 release_db: float = 60.0) -> np.ndarray:
    """엔벌로프 추종기: 즉시 상승 + 선형 dB 하강, 그다음 어택 시상수로 평활.

    하강부는 재귀식  v[i] = max(x_db[i], v[i-1] - step)  의 닫힌 형태
        w[i] = x_db[i] + i*step,  v[i] = cummax(w)[i] - i*step
    로 계산하므로 파이썬 루프 없이 정확합니다.
    """
    x = np.asarray(target, dtype=np.float64)
    if x.size == 0:
        return x.astype(np.float32)
    step = release_db / max(release_samples, 1)
    x_db = 20.0 * np.log10(np.maximum(np.abs(x), 1e-9))
    idx = np.arange(x.size, dtype=np.float64)
    v = np.maximum.accumulate(x_db + idx * step) - idx * step
    env = 10.0 ** (v / 20.0)
    if attack_samples > 1:
        ca = float(np.exp(-1.0 / attack_samples))
        env = sig.lfilter([1 - ca], [1.0, -ca], env, zi=[env[0] * ca])[0]
    return np.minimum(env, np.maximum(np.abs(x).max(), 1e-9)).astype(np.float64)


def gate(y: np.ndarray, sr: int, threshold_db: float = -48.0, attack_ms: float = 5,
         release_ms: float = 120) -> np.ndarray:
    x = _mono(y)
    env = np.abs(sig.hilbert(x)) if len(x) < 3_000_000 else np.abs(x)
    thr = lin(threshold_db)
    target = (env > thr).astype(np.float64)
    sm = _smooth_asym(target, int(sr * attack_ms / 1000), int(sr * release_ms / 1000))
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
                  max_shift_ms: float = 90.0, fade_ms: float = 8.0) -> tuple[np.ndarray, dict]:
    """온셋을 가장 가까운 그리드로 옮기는 타이밍 정렬.

    설계상 지켜야 하는 것:
      * 첫 온셋 앞의 소리를 잃지 않는다 (들숨·시작 자음이 잘리면 안 됨)
      * 구간을 옮겨서 생기는 빈 자리를 만들지 않는다 (뚝 끊기는 구멍 방지)
      * 겹치는 구간을 그냥 더하지 않는다 (이중으로 들리는 것 방지)
      * 이음매마다 짧은 페이드를 넣는다 (딱 소리 방지)
    """
    import librosa

    x = _mono(y).astype(np.float64)
    if len(beat_times) < 2 or len(x) == 0:
        return x.astype(np.float32), {"moved": 0, "reason_ko": "비트 그리드가 없어 정렬하지 않았습니다"}
    grid = []
    bt = list(beat_times)
    for i in range(len(bt) - 1):
        for k in range(subdiv):
            grid.append(bt[i] + (bt[i + 1] - bt[i]) * k / subdiv)
    grid = np.array(grid + [bt[-1]])

    env = librosa.onset.onset_strength(y=x.astype(np.float32), sr=sr)
    frames = librosa.onset.onset_detect(onset_envelope=env, sr=sr, backtrack=True)
    onsets = list(librosa.frames_to_time(frames, sr=sr))
    if not onsets:
        return x.astype(np.float32), {"moved": 0, "reason_ko": "온셋을 찾지 못해 정렬하지 않았습니다"}

    duration = len(x) / sr
    if len(onsets) / max(duration, 1e-6) > 4.0:
        # 지속음처럼 온셋이 불분명한 소재에서는 검출이 신뢰할 수 없다.
        # 이런 자료를 잘라 옮기면 위상이 어긋나 '딱' 소리와 빈 구간이 생기므로 건드리지 않는다.
        return x.astype(np.float32), {
            "moved": 0, "onsets": len(onsets),
            "reason_ko": f"초당 온셋이 {len(onsets)/duration:.1f}개로 너무 많습니다 — "
                         "타이밍 정렬을 건너뛰었습니다 (지속음이거나 검출이 불안정한 소재)"}
    if len(frames) and len(env):
        strengths = env[np.clip(frames, 0, len(env) - 1)]
        keep = strengths >= np.median(strengths) * 0.5      # 약한 온셋은 옮기지 않는다
        onsets = [t for t, k in zip(onsets, keep) if k]
        if not onsets:
            return x.astype(np.float32), {"moved": 0, "reason_ko": "뚜렷한 온셋이 없어 정렬하지 않았습니다"}

    bounds = [0.0] + [o for o in onsets if o > 0.001] + [len(x) / sr]
    fade = max(2, int(fade_ms / 1000.0 * sr))
    out = np.zeros(len(x) + int(max_shift_ms / 1000.0 * sr) + 2 * fade, dtype=np.float64)
    written_until = 0
    moved = 0
    max_shift = max_shift_ms / 1000.0

    for i in range(len(bounds) - 1):
        a0, b0 = max(0, int(bounds[i] * sr)), min(len(x), int(bounds[i + 1] * sr))
        if b0 <= a0:
            continue
        if i == 0:
            shift = 0.0                      # 첫 조각(첫 온셋 이전)은 옮기지 않는다
        else:
            j = int(np.argmin(np.abs(grid - bounds[i])))
            shift = float(np.clip(grid[j] - bounds[i], -max_shift, max_shift))
        # 이음매를 부드럽게 하려고 조각 앞에서 fade 만큼 원본을 더 가져온다
        lead = min(fade, a0)
        seg = x[a0 - lead:b0].copy()
        dst = int(round(a0 + shift * sr)) - lead
        dst = max(0, min(dst, len(out) - len(seg)))
        if written_until > 0 and dst < written_until:
            dst = max(dst, written_until - lead) if lead else written_until
            dst = max(0, min(dst, len(out) - len(seg)))
        if dst > written_until and written_until > 0:
            # 옮기면서 생긴 빈 자리는 원본에서 이어지는 소리로 메우고, 조각 앞에 붙여 한 덩어리로 쓴다
            # (따로 쓰면 '이미 쓴 소리 → 채운 소리' 이음매에 크로스페이드가 걸리지 않아 딱 소리가 납니다)
            gap = dst - written_until
            filler = x[max(0, a0 - lead - gap):max(0, a0 - lead)]
            if len(filler) < gap:
                filler = (np.pad(filler, (gap - len(filler), 0), mode="edge")
                          if len(filler) else np.zeros(gap))
            seg = np.concatenate([filler[-gap:], seg])
            dst = written_until
        ov = max(0, min(written_until - dst, len(seg)))
        if ov < 2 and written_until > 0:
            # 딱 붙는 이음매도 그냥 이어붙이면 '딱' 소리가 납니다 — fade 만큼 뒤로 물려 겹치게 만든다
            back = int(min(fade, written_until, len(seg) - 1))
            if back >= 2:
                dst -= back
                ov = back
        if ov >= 2:
            w = np.linspace(0.0, 1.0, ov)                       # 겹치는 만큼 크로스페이드
            out[dst:dst + ov] = out[dst:dst + ov] * (1 - w) + seg[:ov] * w
            out[dst + ov:dst + len(seg)] = seg[ov:]
        else:
            out[dst:dst + len(seg)] = seg
        written_until = dst + len(seg)
        if abs(shift) > 0.003:
            moved += 1

    out = out[: max(written_until, len(x))]
    if len(out) < len(x):
        out = np.pad(out, (0, len(x) - len(out)))
    return out[: len(x)].astype(np.float32), {
        "onsets": len(onsets), "moved": moved, "max_shift_ms": max_shift_ms,
        "fade_ms": fade_ms, "note_ko": "첫 온셋 이전 구간은 옮기지 않고 그대로 둡니다."}


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
    env = np.abs(x).astype(np.float64)
    sm = _smooth_asym(env, int(sr * attack_ms / 1000), int(sr * release_ms / 1000))
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
        # 표준 등파워 팬. 1.414 로 정규화하면 옆으로 보낸 성부가 요청한 gain_db 보다 커집니다
        l = float(np.cos((pan + 1) * np.pi / 4)); r = float(np.sin((pan + 1) * np.pi / 4))
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
    stereo = np.vstack([x, x]).astype(np.float32)
    if do_harmony:
        stereo = stereo + harmony(x, sr)
        steps["harmony"] = "3도/5도 자동 생성 (인간 실연 아님)"
    # 레벨 정리는 하모니를 더한 뒤에 — 그 전에 하면 합쳐지면서 클리핑이 납니다
    peak = float(np.abs(stereo).max())
    if peak > 0:
        stereo = (stereo * (lin(-3.0) / peak)).astype(np.float32)
    steps["output_peak_dbfs"] = -3.0
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{Path(src).stem}_processed.wav"
    save_wav(out_path, stereo, sr, subtype="PCM_24")
    return {"source": str(src), "output": str(out_path), "sr": sr, "steps": steps,
            "raw_preserved_ko": "원본 RAW 파일은 수정하지 않았습니다."}
