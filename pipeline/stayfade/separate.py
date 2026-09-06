"""01 separate — 스템 분리.

우선순위:
  1) demucs (htdemucs) — 설치되어 있고 모델 가중치를 받을 수 있을 때. 품질 최상.
  2) HPSS + 대역 분할 폴백 — 인터넷/모델 없이도 항상 동작. 품질은 낮고
     '참고용 근사 스템'입니다. 최종 마스터의 감산 편집에 쓰기 전에 반드시 청취하세요.
분리물은 원본 멀티트랙이 아닙니다.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

from .common import Project, load_audio, run_cmd, save_wav, to_stereo, which

STEM_NAMES = ["vocals", "drums", "bass", "other"]


def demucs_available() -> bool:
    if which("demucs"):
        return True
    try:
        import demucs  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def separate_demucs(src: Path, out_dir: Path, model: str = "htdemucs", timeout: int = 5400) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    exe = which("demucs")
    cmd = ([exe] if exe else ["python", "-m", "demucs.separate"]) + \
          ["-n", model, "-o", str(out_dir), "--filename", "{stem}.{ext}", str(src)]
    rc, log = run_cmd(cmd, timeout=timeout)
    produced = {}
    for p in out_dir.rglob("*.wav"):
        produced[p.stem] = p
    if rc == 0 and produced:
        for name, p in list(produced.items()):
            dest = out_dir / f"{name}.wav"
            if p != dest:
                shutil.move(str(p), str(dest))
                produced[name] = dest
        return {"engine": "demucs", "model": model, "ok": True,
                "stems": {k: str(v) for k, v in produced.items()}, "log_tail": log[-600:]}
    return {"engine": "demucs", "model": model, "ok": False, "log_tail": log[-1500:]}


def separate_fallback(src: Path, out_dir: Path) -> dict:
    """librosa HPSS + 대역 분할로 4스템 근사.

    vocals : harmonic 성분 중 200-6000 Hz + 중앙(mid) 우세 성분
    drums  : percussive 성분
    bass   : 30-180 Hz (harmonic 위주)
    other  : 나머지 (원본 - 위 3개)
    """
    import librosa
    from scipy import signal as sig

    out_dir.mkdir(parents=True, exist_ok=True)
    y, sr = load_audio(src)
    y = to_stereo(y)
    mono = y.mean(axis=0)

    S = librosa.stft(mono, n_fft=4096, hop_length=1024)
    H, P = librosa.decompose.hpss(S, margin=(2.0, 2.5))
    harm = librosa.istft(H, hop_length=1024, length=mono.shape[-1])
    perc = librosa.istft(P, hop_length=1024, length=mono.shape[-1])

    def band(x, lo, hi):
        nyq = sr / 2
        if lo <= 0:
            sos = sig.butter(4, min(hi / nyq, 0.99), btype="low", output="sos")
        elif hi >= nyq:
            sos = sig.butter(4, lo / nyq, btype="high", output="sos")
        else:
            sos = sig.butter(4, [lo / nyq, min(hi / nyq, 0.99)], btype="band", output="sos")
        return sig.sosfiltfilt(sos, x)

    bass = band(harm, 0, 180)
    mid = band(harm, 180, 6000)
    # side/mid: 보컬은 보통 중앙 → mid 성분에서 center-ish 추출
    m = (y[0] + y[1]) / 2
    s = (y[0] - y[1]) / 2
    center_ratio = np.clip(1.0 - np.abs(s) / (np.abs(m) + 1e-6), 0.0, 1.0)
    vocals = mid * (0.35 + 0.65 * center_ratio[: len(mid)])
    drums = perc
    other = mono - (bass + vocals + drums)

    stems = {}
    for name, mono_sig in [("vocals", vocals), ("drums", drums), ("bass", bass), ("other", other)]:
        st = np.vstack([mono_sig, mono_sig]).astype(np.float32)
        p = save_wav(out_dir / f"{name}.wav", st, sr, subtype="PCM_24")
        stems[name] = str(p)
    return {"engine": "hpss_fallback", "ok": True, "stems": stems,
            "quality_note": "근사 분리입니다. demucs 대비 품질이 낮고 누설(bleed)이 큽니다. 감산 편집 전 반드시 청취하세요."}


def check_recombination(src: Path, stems: dict[str, str]) -> dict:
    """스템 합산이 원본을 얼마나 재현하는지."""
    y, sr = load_audio(src)
    y = to_stereo(y).mean(axis=0)
    acc = None
    for p in stems.values():
        s, _ = load_audio(p, sr=sr)
        s = to_stereo(s).mean(axis=0)
        n = min(len(y), len(s))
        acc = s[:n] if acc is None else acc[:n] + s[:n]
    n = min(len(y), len(acc))
    a, b = y[:n], acc[:n]
    corr = float(np.corrcoef(a, b)[0, 1]) if n > 8 else 0.0
    rms_a = float(np.sqrt(np.mean(a ** 2))) + 1e-12
    rel_err = float(np.sqrt(np.mean((a - b) ** 2)) / rms_a)
    return {"sum_correlation": round(corr, 5), "relative_rms_error": round(rel_err, 5),
            "note": "상관이 1에 가까워도 분리가 완벽하다는 뜻은 아닙니다."}


def run(project: Project, src: Path, prefer: str = "auto") -> dict:
    out_dir = project.dir("stems")
    res = None
    if prefer in ("auto", "demucs") and demucs_available():
        project.log("스템 분리: demucs 시도")
        res = separate_demucs(Path(src), out_dir)
        if not res.get("ok"):
            project.log(f"demucs 실패 → 폴백 사용. tail: {res.get('log_tail','')[:200]}")
            res = None
    if res is None:
        project.log("스템 분리: HPSS 폴백 사용 (근사)")
        res = separate_fallback(Path(src), out_dir)
    res["recombination"] = check_recombination(Path(src), res["stems"])
    if res["engine"] == "hpss_fallback":
        res["recombination"]["meaningless_ko"] = (
            "폴백 엔진에서는 other = 원본 - (bass+vocals+drums) 로 만들기 때문에 "
            "합산 상관이 1.0 이 나오는 것이 당연합니다. 분리 품질의 근거가 아닙니다.")
    return res
