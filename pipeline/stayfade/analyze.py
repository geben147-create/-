"""02 analyze — BPM / 마디 / 키 / 섹션 / 코드 추정.

모든 결과는 '추정'입니다. 사람이 들어서 확인해야 합니다 (qc.json 의 needs_human_check).
"""
from __future__ import annotations

import numpy as np

from .common import NOTE_NAMES_FLAT, NOTE_NAMES_SHARP, midi_name, pc_name

MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

# chord templates: (suffix, semitone offsets)
CHORD_TEMPLATES = [
    ("", [0, 4, 7]),        # major
    ("m", [0, 3, 7]),       # minor
    ("dim", [0, 3, 6]),
    ("aug", [0, 4, 8]),
    ("sus4", [0, 5, 7]),
    ("sus2", [0, 2, 7]),
    ("7", [0, 4, 7, 10]),
    ("m7", [0, 3, 7, 10]),
    ("maj7", [0, 4, 7, 11]),
]

DIATONIC_MINOR = {  # scale degree -> (offset, quality) for natural minor
    "i": (0, "m"), "iidim": (2, "dim"), "III": (3, ""), "iv": (5, "m"),
    "v": (7, "m"), "V": (7, ""), "VI": (8, ""), "VII": (10, ""),
}
DIATONIC_MAJOR = {
    "I": (0, ""), "ii": (2, "m"), "iii": (4, "m"), "IV": (5, ""),
    "V": (7, ""), "vi": (9, "m"), "viidim": (11, "dim"),
}


def estimate_key(y_mono: np.ndarray, sr: int, bass_mono: np.ndarray | None = None) -> dict:
    """조성 추정 + 나란한조 모호성 처리.

    화성 프로파일(Krumhansl)만으로는 Ebm 과 Gb 처럼 구성음이 같은 짝을 자주 혼동합니다.
    그래서 (1) 저역 크로마(으뜸음은 베이스에 많이 나옴), (2) 곡 마지막 부분 크로마
    (대개 으뜸음으로 끝남) 를 함께 봅니다. 그래도 애매하면 ambiguous=True 로 표시하고
    사람에게 넘깁니다 — 틀린 조성으로 편곡하면 전부 불협이 됩니다.
    """
    import librosa
    chroma = librosa.feature.chroma_cqt(y=y_mono, sr=sr, bins_per_octave=36)
    prof = chroma.mean(axis=1)
    prof = prof / (prof.sum() + 1e-12)
    scores = {}
    for pc in range(12):
        for name, tmpl in (("major", MAJ), ("minor", MIN)):
            t = np.roll(tmpl, pc)
            t = t / t.sum()
            scores[(pc, name)] = float(np.corrcoef(prof, t)[0, 1])
    (best_pc, best_mode), best = max(scores.items(), key=lambda kv: kv[1])
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:4]

    tonic_ev = tonic_evidence(y_mono, sr, bass_mono)
    alt_pc = (best_pc - 3) % 12 if best_mode == "major" else (best_pc + 3) % 12
    alt_mode = "minor" if best_mode == "major" else "major"
    alt_score = scores[(alt_pc, alt_mode)]
    ambiguous = (best - alt_score) < 0.15
    switch_note = None
    if ambiguous and tonic_ev is not None and tonic_ev[alt_pc] > tonic_ev[best_pc] * 1.15:
        switch_note = (f"화성 프로파일은 {pc_name(best_pc)}{'m' if best_mode == 'minor' else ''} 이지만 "
                       f"저역·엔딩 근거가 {pc_name(alt_pc)}{'m' if alt_mode == 'minor' else ''} 를 가리켜 바꿨습니다.")
        best_pc, best_mode, best = alt_pc, alt_mode, alt_score
        alt_pc, alt_mode = (best_pc - 3) % 12 if best_mode == "major" else (best_pc + 3) % 12, \
                           "minor" if best_mode == "major" else "major"

    def kname(pc, mode):
        return f"{pc_name(pc)}{'m' if mode == 'minor' else ''}"

    return {
        "key": kname(best_pc, best_mode),
        "tonic_pc": int(best_pc),
        "mode": best_mode,
        "confidence": round(best, 3),
        "ambiguous": bool(ambiguous),
        "relative_pair": [kname(best_pc, best_mode), kname(alt_pc, alt_mode)],
        "switch_note_ko": switch_note,
        "tonic_evidence": None if tonic_ev is None else {pc_name(i): round(float(v), 3) for i, v in enumerate(tonic_ev)},
        "alternatives": [{"key": kname(p, m), "score": round(sc, 3)} for (p, m), sc in ranked],
        "caveat_ko": ("나란한조(예: Ebm ↔ Gb)는 구성음이 같아 자동 판별이 자주 틀립니다. "
                      "ambiguous=true 면 반드시 귀로 확인하고 analyze --key 로 지정하세요."),
        "chroma_profile": [round(float(v), 4) for v in prof],
    }


def tonic_evidence(y_mono: np.ndarray, sr: int, bass_mono: np.ndarray | None = None) -> np.ndarray | None:
    """으뜸음 근거: 저역 크로마 + 곡 마지막 8초 크로마 + (있으면) 베이스 스템 크로마."""
    import librosa
    from scipy import signal as _sig
    try:
        nyq = sr / 2
        sos = _sig.butter(4, min(250.0 / nyq, 0.99), btype="low", output="sos")
        low = _sig.sosfiltfilt(sos, y_mono)
        c_low = librosa.feature.chroma_cqt(y=low, sr=sr, fmin=librosa.note_to_hz("C1"),
                                           n_octaves=4, bins_per_octave=36).mean(axis=1)
        tail = y_mono[-int(min(len(y_mono), 8 * sr)):]
        c_end = librosa.feature.chroma_cqt(y=tail, sr=sr, bins_per_octave=36).mean(axis=1)
        parts = [c_low / (c_low.sum() + 1e-12), c_end / (c_end.sum() + 1e-12)]
        if bass_mono is not None and len(bass_mono) > sr:
            c_b = librosa.feature.chroma_cqt(y=bass_mono, sr=sr, fmin=librosa.note_to_hz("C1"),
                                             n_octaves=4, bins_per_octave=36).mean(axis=1)
            parts.append(c_b / (c_b.sum() + 1e-12))
        ev = np.mean(parts, axis=0)
        return ev / (ev.sum() + 1e-12)
    except Exception:  # noqa: BLE001
        return None


def bass_pitch_class_histogram(bass_mono: np.ndarray, sr: int) -> np.ndarray | None:
    """베이스 스템의 음 높이 분포 (에너지 가중). 으뜸음 판별 보조."""
    import librosa
    try:
        chroma = librosa.feature.chroma_cqt(y=bass_mono, sr=sr, fmin=librosa.note_to_hz("C1"),
                                            n_octaves=4, bins_per_octave=36)
    except Exception:  # noqa: BLE001
        return None
    rms = librosa.feature.rms(y=bass_mono)[0]
    n = min(chroma.shape[1], len(rms))
    w = rms[:n]
    if w.sum() <= 0:
        return None
    hist = (chroma[:, :n] * w).sum(axis=1)
    return hist / (hist.sum() + 1e-12)


def estimate_tempo_beats(y_mono: np.ndarray, sr: int) -> dict:
    import librosa
    onset_env = librosa.onset.onset_strength(y=y_mono, sr=sr, aggregate=np.median)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr, trim=False)
    tempo = float(np.atleast_1d(tempo)[0])
    beat_times = librosa.frames_to_time(beats, sr=sr)
    # candidate tempi for half/double-time confusion
    cands = librosa.feature.tempo(onset_envelope=onset_env, sr=sr, aggregate=None)
    cand_list = sorted({round(float(c), 2) for c in np.atleast_1d(cands)})[:8]
    return {
        "bpm": round(tempo, 3),
        "bpm_candidates": cand_list,
        "beat_times": [round(float(t), 4) for t in beat_times],
        "beat_count": int(len(beat_times)),
        "note": "BPM은 추정값입니다. 절반/두 배 오인식 가능 — 미리듣기에서 확인하세요.",
    }


def downbeats_from_beats(beat_times: list[float], beats_per_bar: int = 4,
                         extend_to_zero: bool = True, duration: float | None = None) -> list[float]:
    """비트에서 마디 시작점을 뽑고, 곡 처음(0초)과 끝까지 그리드를 연장한다.

    첫 비트가 늦게 잡히는 경우(드럼 없는 인트로 등)에도 0초부터 마디가 생기도록 한다.
    """
    if not beat_times:
        return []
    bt = np.asarray(beat_times, dtype=float)
    bars = list(bt[::beats_per_bar])
    if len(bars) < 2:
        return [round(float(t), 4) for t in bars]
    bar_len = float(np.median(np.diff(bars)))
    if extend_to_zero and bars[0] > bar_len * 0.5:
        pre = []
        t = bars[0] - bar_len
        while t > -bar_len * 0.25:
            pre.append(max(0.0, t))
            t -= bar_len
        bars = sorted(set(round(x, 4) for x in pre)) + bars
    if duration is not None:
        t = bars[-1] + bar_len
        while t < duration - bar_len * 0.25:
            bars.append(t)
            t += bar_len
    return [round(float(t), 4) for t in bars]


def estimate_sections(y_mono: np.ndarray, sr: int, bar_times: list[float], max_sections: int = 9) -> list[dict]:
    """bar 단위로 정렬된 구간 분할 (자기유사도 + agglomerative)."""
    import librosa
    if len(bar_times) < 4:
        dur = len(y_mono) / sr
        return [{"index": 0, "start": 0.0, "end": round(dur, 3), "label": "full", "bars": 0}]
    mfcc = librosa.feature.mfcc(y=y_mono, sr=sr, n_mfcc=20)
    chroma = librosa.feature.chroma_cqt(y=y_mono, sr=sr)
    rms = librosa.feature.rms(y=y_mono)
    feat = np.vstack([librosa.util.normalize(mfcc, axis=1),
                      librosa.util.normalize(chroma, axis=1),
                      librosa.util.normalize(rms, axis=1)])
    frame_times = librosa.frames_to_time(np.arange(feat.shape[1]), sr=sr)
    # aggregate per bar
    idx = np.searchsorted(frame_times, bar_times)
    idx = np.clip(idx, 0, feat.shape[1] - 1)
    segs = []
    for i in range(len(idx)):
        a = idx[i]
        b = idx[i + 1] if i + 1 < len(idx) else feat.shape[1]
        if b <= a:
            b = min(a + 1, feat.shape[1])
        segs.append(feat[:, a:b].mean(axis=1))
    X = np.vstack(segs)
    n_seg = int(min(max_sections, max(3, len(bar_times) // 4)))
    try:
        bounds = librosa.segment.agglomerative(X.T, n_seg)
    except Exception:  # noqa: BLE001
        bounds = np.linspace(0, len(bar_times) - 1, n_seg + 1).astype(int)[:-1]
    bounds = sorted(set([0] + [int(b) for b in bounds]))
    total = len(y_mono) / sr
    out = []
    for i, b in enumerate(bounds):
        start = bar_times[b]
        end = bar_times[bounds[i + 1]] if i + 1 < len(bounds) else total
        if end - start < 1.0:
            continue
        nbars = (bounds[i + 1] if i + 1 < len(bounds) else len(bar_times)) - b
        out.append({"index": len(out), "start": round(float(start), 3), "end": round(float(end), 3),
                    "bars": int(nbars), "label": "?"})
    return _label_sections(out, y_mono, sr)


def _label_sections(sections: list[dict], y_mono: np.ndarray, sr: int) -> list[dict]:
    """에너지·위치 기반 러프 라벨. 사람이 고쳐야 하는 값입니다."""
    if not sections:
        return sections
    energies = []
    for s in sections:
        a, b = int(s["start"] * sr), int(s["end"] * sr)
        seg = y_mono[a:b]
        energies.append(float(np.sqrt(np.mean(seg ** 2)) if len(seg) else 0.0))
    e = np.array(energies)
    hi = np.percentile(e, 70) if len(e) > 2 else e.max()
    lo = np.percentile(e, 30) if len(e) > 2 else e.min()
    n = len(sections)
    for i, s in enumerate(sections):
        if i == 0 and e[i] <= np.median(e):
            lab = "intro"
        elif i == n - 1 and e[i] <= np.median(e):
            lab = "outro"
        elif e[i] >= hi:
            lab = "chorus?"
        elif e[i] <= lo:
            lab = "breakdown?"
        else:
            lab = "verse?"
        s["label"] = lab
        s["rms"] = round(float(e[i]), 5)
        s["label_note"] = "자동 추정 라벨 — 들어보고 human_decisions.json 에서 고치세요"
    return sections


def estimate_chords(y_mono: np.ndarray, sr: int, bar_times: list[float], tonic_pc: int, mode: str,
                    subdiv: int = 1) -> list[dict]:
    """마디(또는 마디/subdiv) 단위 코드 추정 — 다이어토닉 가중치 포함."""
    import librosa
    if len(bar_times) < 2:
        return []
    chroma = librosa.feature.chroma_cqt(y=y_mono, sr=sr, bins_per_octave=36)
    times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr)
    grid = []
    for i in range(len(bar_times)):
        a = bar_times[i]
        b = bar_times[i + 1] if i + 1 < len(bar_times) else a + (bar_times[-1] - bar_times[-2] if len(bar_times) > 1 else 2.0)
        for k in range(subdiv):
            grid.append((a + (b - a) * k / subdiv, a + (b - a) * (k + 1) / subdiv, i))
    diatonic = set()
    table = DIATONIC_MINOR if mode == "minor" else DIATONIC_MAJOR
    for off, qual in table.values():
        diatonic.add(((tonic_pc + off) % 12, qual))
    out = []
    for start, end, bar_i in grid:
        a = int(np.searchsorted(times, start))
        b = int(np.searchsorted(times, end))
        if b <= a:
            continue
        v = chroma[:, a:b].mean(axis=1)
        v = v / (np.linalg.norm(v) + 1e-12)
        best, best_score = None, -9
        for root in range(12):
            for suffix, offs in CHORD_TEMPLATES:
                t = np.zeros(12)
                for o in offs:
                    t[(root + o) % 12] = 1.0
                t = t / np.linalg.norm(t)
                score = float(np.dot(v, t))
                if (root, suffix.replace("7", "").replace("maj", "")) in diatonic or (root, suffix) in diatonic:
                    score += 0.06
                if score > best_score:
                    best_score, best = score, (root, suffix)
        root, suffix = best
        out.append({"bar": int(bar_i), "start": round(float(start), 3), "end": round(float(end), 3),
                    "chord": f"{pc_name(root)}{suffix}", "root_pc": int(root), "quality": suffix,
                    "confidence": round(float(best_score), 3)})
    return out


def bass_note_stats(events: list[dict]) -> dict:
    if not events:
        return {"count": 0}
    pitches = [e["pitch"] for e in events]
    return {
        "count": len(events),
        "min": midi_name(int(min(pitches))),
        "max": midi_name(int(max(pitches))),
        "median": midi_name(int(np.median(pitches))),
    }


def parse_key(text: str) -> tuple[int, str]:
    """'Ebm', 'C#', 'Gb major', 'F#m' → (tonic_pc, mode)."""
    t = text.strip().replace("minor", "m").replace("major", "").replace(" ", "")
    mode = "minor" if t.endswith("m") else "major"
    root = t[:-1] if t.endswith("m") else t
    names = {**{n: i for i, n in enumerate(NOTE_NAMES_SHARP)}, **{n: i for i, n in enumerate(NOTE_NAMES_FLAT)}}
    root = root[0].upper() + root[1:].replace("B", "b").replace("S", "#")
    if root not in names:
        raise ValueError(f"조성을 해석할 수 없습니다: {text}")
    return names[root], mode


def override_key(key_dict: dict, text: str) -> dict:
    pc, mode = parse_key(text)
    return {**key_dict, "key": f"{pc_name(pc)}{'m' if mode == 'minor' else ''}", "tonic_pc": pc,
            "mode": mode, "manual": True, "ambiguous": False,
            "auto_estimate": {"key": key_dict.get("key"), "confidence": key_dict.get("confidence")},
            "note_ko": "사용자가 직접 지정한 조성입니다."}
