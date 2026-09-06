"""Musical analysis: tempo/beats/downbeats, key (Krumhansl-Schmuckler), chord per beat
(24 triad templates), section segmentation (agglomerative on chroma+MFCC+RMS) and an RMS
envelope for visualisation. All heuristics — every result is written to JSON so a human can
check it, and the arrangement stage uses the *detected beat times* (not a fixed grid) so small
tempo drift does not break alignment."""
from __future__ import annotations
import numpy as np
import librosa

KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def _mono(x):
    return np.mean(x, axis=1) if x.ndim == 2 else x


def estimate_key(chroma_mean: np.ndarray) -> dict:
    scores = []
    for i in range(12):
        for mode, prof in (("major", MAJOR), ("minor", MINOR)):
            r = np.corrcoef(np.roll(prof, i), chroma_mean)[0, 1]
            scores.append((r, KEY_NAMES[i], mode))
    scores.sort(reverse=True)
    best = scores[0]
    return {"key": f"{best[1]} {best[2]}", "tonic": best[1], "mode": best[2],
            "confidence": round(float(best[0]), 3),
            "runner_up": f"{scores[1][1]} {scores[1][2]} ({scores[1][0]:.3f})"}


def chord_templates():
    t = {}
    for i in range(12):
        maj = np.zeros(12); maj[[i, (i + 4) % 12, (i + 7) % 12]] = 1
        mi = np.zeros(12); mi[[i, (i + 3) % 12, (i + 7) % 12]] = 1
        t[f"{KEY_NAMES[i]}"] = maj
        t[f"{KEY_NAMES[i]}m"] = mi
    return t


def sync_no_pad(X: np.ndarray, boundaries: np.ndarray, agg) -> np.ndarray:
    """librosa.util.sync pads a segment in front when boundaries[0] > 0, which shifts every
    column by one. Drop that padded column so column j is the segment STARTING at boundaries[j]."""
    out = librosa.util.sync(X, boundaries, aggregate=agg)
    if len(boundaries) and boundaries[0] > 0 and out.shape[1] == len(boundaries) + 1:
        out = out[:, 1:]
    return out[:, :len(boundaries)]


def regularise_beats(beat_times: np.ndarray, tol_ratio: float = 0.09, win: int = 6) -> tuple[np.ndarray, list[dict]]:
    """The beat tracker occasionally snaps a beat onto a syncopated stab (typically in a drum
    break), which would place a new kick a 16th early. For each beat, fit a local line using the
    window's MEDIAN interval as slope (robust to the outlier itself) and replace the beat when its
    residual exceeds tol_ratio of the beat period. Two passes so consecutive outliers are caught.
    Returns (corrected_times, corrections)."""
    bt = np.asarray(beat_times, dtype=float).copy()
    corrections = []
    if len(bt) < 2 * win + 2:
        return bt, corrections
    for _ in range(2):
        period = float(np.median(np.diff(bt)))
        tol = tol_ratio * period
        fixed = bt.copy()
        for k in range(len(bt)):
            lo, hi = max(0, k - win), min(len(bt), k + win + 1)
            idx = np.arange(lo, hi)
            slope = float(np.median(np.diff(bt[lo:hi]))) if hi - lo > 1 else period
            intercept = float(np.median(bt[lo:hi] - idx * slope))
            fit = intercept + k * slope
            if abs(bt[k] - fit) > tol and 0 < k < len(bt) - 1:
                fixed[k] = fit
        moved = np.where(np.abs(fixed - bt) > 1e-9)[0]
        for k in moved:
            corrections.append({"beat_index": int(k), "raw": round(float(bt[k]), 4),
                                "corrected": round(float(fixed[k]), 4), "shift_ms": round(float(fixed[k] - bt[k]) * 1000, 1)})
        bt = fixed
        if not len(moved):
            break
    bt = np.maximum.accumulate(bt)  # keep it monotonic
    return bt, corrections


def chords_per_beat(chroma: np.ndarray, beat_frames: np.ndarray, key: dict) -> list[dict]:
    """Beat-synchronous chord estimate. Chords inside the detected key are given a small bonus
    so the estimate is stable; the raw best match is stored too."""
    templ = chord_templates()
    names = list(templ.keys())
    T = np.stack([templ[n] / np.linalg.norm(templ[n]) for n in names])
    sync = sync_no_pad(chroma, beat_frames, np.median)
    tonic = KEY_NAMES.index(key["tonic"])
    if key["mode"] == "major":
        diatonic = {KEY_NAMES[(tonic + s) % 12] + q for s, q in [(0, ""), (2, "m"), (4, "m"), (5, ""), (7, ""), (9, "m")]}
    else:
        diatonic = {KEY_NAMES[(tonic + s) % 12] + q for s, q in [(0, "m"), (3, ""), (5, "m"), (7, "m"), (8, ""), (10, "")]}
    out = []
    for b in range(sync.shape[1]):
        v = sync[:, b]
        v = v / (np.linalg.norm(v) + 1e-9)
        sc = T @ v
        bonus = np.array([0.08 if n in diatonic else 0.0 for n in names])
        i = int(np.argmax(sc + bonus)); j = int(np.argmax(sc))
        out.append({"chord": names[i], "raw_best": names[j], "score": round(float(sc[i]), 3)})
    # light smoothing: single-beat islands take the neighbours' chord
    for i in range(1, len(out) - 1):
        if out[i - 1]["chord"] == out[i + 1]["chord"] != out[i]["chord"]:
            out[i]["chord"] = out[i - 1]["chord"]
    return out


def chord_to_midi_root(name: str, octave: int = 2) -> int:
    root = name.rstrip("m")
    return 12 * (octave + 1) + KEY_NAMES.index(root)


def chroma_len_guard(y, sr, hop):
    return int(np.ceil(len(y) / hop)) - 1


def analyze(x: np.ndarray, sr: int, n_sections_hint: int | None = None) -> dict:
    y = _mono(x).astype(np.float32)
    hop = 512
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, hop_length=hop, units="frames", trim=False)
    tempo = float(np.atleast_1d(tempo)[0])
    beat_times_raw = librosa.frames_to_time(beats, sr=sr, hop_length=hop)
    beat_times, beat_corrections = regularise_beats(beat_times_raw)
    beats = librosa.time_to_frames(beat_times, sr=sr, hop_length=hop)
    beats = np.clip(beats, 0, chroma_len_guard(y, sr, hop))
    # downbeat phase: which of the 4 beat offsets carries the most onset energy + low-frequency energy
    y_h, y_p = librosa.effects.hpss(y)
    low = librosa.feature.rms(y=librosa.effects.preemphasis(y_p, coef=-0.97), hop_length=hop)[0]
    ons_at_beats = onset_env[np.clip(beats, 0, len(onset_env) - 1)] + low[np.clip(beats, 0, len(low) - 1)] * 10
    phase_scores = [float(np.sum(ons_at_beats[p::4])) for p in range(4)]
    phase = int(np.argmax(phase_scores))
    downbeats = beat_times[phase::4]
    # key
    chroma = librosa.feature.chroma_cqt(y=y_h, sr=sr, hop_length=hop)
    key = estimate_key(np.mean(chroma, axis=1))
    chords = chords_per_beat(chroma, beats, key)
    # sections: bar-level novelty (checkerboard kernel on a self-similarity matrix of
    # bar-synchronous chroma+MFCC+RMS). Boundaries therefore always fall on downbeats.
    mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop, n_mfcc=13)
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    dur = len(y) / sr
    db_frames = librosa.time_to_frames(downbeats, sr=sr, hop_length=hop)
    db_frames = np.unique(np.clip(db_frames, 0, chroma.shape[1] - 1))
    sections = []
    rms_t = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    if len(db_frames) >= 8:
        F = np.vstack([sync_no_pad(chroma, db_frames, np.median), sync_no_pad(mfcc, db_frames, np.median),
                       sync_no_pad(rms[None, :], db_frames, np.median)])
        F = (F - F.mean(axis=1, keepdims=True)) / (F.std(axis=1, keepdims=True) + 1e-9)
        R = librosa.segment.recurrence_matrix(F, mode="affinity", sym=True, width=1)
        nb = R.shape[0]
        kw = 4  # bars each side of the kernel
        kern = np.kron(np.array([[1, -1], [-1, 1]]), np.ones((kw, kw)))
        nov = np.zeros(nb)
        Rp = np.pad(R, kw, mode="constant")
        for i in range(nb):
            nov[i] = np.sum(Rp[i:i + 2 * kw, i:i + 2 * kw] * kern)
        nov = np.maximum(nov, 0)
        n_target = int(np.clip(round(dur / 18), 4, 9)) - 1
        peaks = librosa.util.peak_pick(nov, pre_max=3, post_max=3, pre_avg=4, post_avg=4, delta=0.0, wait=3)
        peaks = [int(p) for p in peaks if 4 <= p <= nb - 4]
        peaks = sorted(peaks, key=lambda p: -nov[p])[:n_target]
        bound_bars = sorted(set([0] + peaks))
        db_times = librosa.frames_to_time(db_frames, sr=sr, hop_length=hop)
        bar_times = [float(db_times[min(b, len(db_times) - 1)]) for b in bound_bars] + [dur]
        bar_times[0] = 0.0  # first section covers the pickup before the first downbeat
    else:
        bar_times = [0.0, dur]
    for i in range(len(bar_times) - 1):
        s, e = bar_times[i], bar_times[i + 1]
        sel = (rms_t >= s) & (rms_t < e)
        sections.append({"index": len(sections), "start": round(s, 3), "end": round(e, 3),
                         "bars": int(np.sum((downbeats >= s - 1e-3) & (downbeats < e - 1e-3))),
                         "rms_db": round(float(20 * np.log10(np.mean(rms[sel]) + 1e-9)), 2) if sel.any() else -99.0})
    # label sections by energy rank (heuristic: loudest ~ hook/chorus)
    order = sorted(range(len(sections)), key=lambda i: -sections[i]["rms_db"])
    for rank, i in enumerate(order):
        sections[i]["energy_rank"] = rank + 1
    for s in sections:
        s["label"] = ("hook" if s["energy_rank"] <= max(1, len(sections) // 3) else
                      "low" if s["energy_rank"] > len(sections) - max(1, len(sections) // 4) else "verse")
    if sections:
        sections[0]["label"] = "intro" if sections[0]["end"] - sections[0]["start"] < 20 else sections[0]["label"]
        sections[-1]["label"] = "outro" if sections[-1]["end"] - sections[-1]["start"] < 20 else sections[-1]["label"]
    # envelope for the HTML (0.25 s)
    step = int(0.25 * sr)
    env = [float(np.sqrt(np.mean(y[i:i + step] ** 2))) for i in range(0, len(y), step)]
    return {
        "duration_s": round(dur, 3),
        "tempo_bpm": round(tempo, 2),
        "beat_count": int(len(beat_times)),
        "beat_times": [round(float(t), 4) for t in beat_times],
        "beat_times_raw": [round(float(t), 4) for t in beat_times_raw],
        "beat_corrections": beat_corrections,
        "downbeat_phase": phase,
        "downbeat_times": [round(float(t), 4) for t in downbeats],
        "key": key,
        "chords_per_beat": chords,
        "sections": sections,
        "rms_envelope_0p25s": [round(v, 5) for v in env],
    }


def bar_chords(an: dict) -> list[dict]:
    """Collapse per-beat chords to one chord per bar (majority over the 4 beats)."""
    beats = an["beat_times"]; ph = an["downbeat_phase"]; ch = an["chords_per_beat"]
    bars = []
    i = ph
    while i < len(beats):
        names = [ch[j]["chord"] for j in range(i, min(i + 4, len(ch)))]
        if not names:
            break
        # deterministic, musical tie-break: the chord sounding on beat 1 wins a tie, else the first
        top = max(names.count(n) for n in names)
        best = next(n for n in names if names.count(n) == top)
        bars.append({"bar": len(bars), "start": beats[i], "end": beats[i + 4] if i + 4 < len(beats) else an["duration_s"],
                     "chord": best, "beats": [beats[j] for j in range(i, min(i + 4, len(beats)))]})
        i += 4
    return bars
