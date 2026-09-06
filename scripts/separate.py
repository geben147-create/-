"""Stem separation with two backends and one file layout:
   01_stems/<backend>/original/{vocals,drums,bass,other}.wav

Backend 1 (preferred): Demucs htdemucs (facebookresearch/demucs). Needs the checkpoint
  955717e8-8726e21a.th in the torch hub cache. If the download host is blocked, copy the
  file manually to ~/.cache/torch/hub/checkpoints/ (see docs).
Backend 2 (fallback, no weights needed): classical signal processing —
  HPSS (percussive -> drums), low-band of the harmonic part -> bass,
  nearest-neighbour (REPET-style) foreground of the harmonic mid channel -> vocals,
  remainder -> other. Quality is far below Demucs; it exists so the *pipeline* can run
  anywhere and so that a later Demucs run can drop into the same folders.
Every run records which backend produced the stems in 01_stems/separation.json."""
from __future__ import annotations
import os, sys, json, time, shutil, subprocess
import numpy as np
from audiolib import load_audio, save_wav, write_json

DEMUCS_CKPT = "955717e8-8726e21a.th"


def demucs_available() -> bool:
    cache = os.path.expanduser("~/.cache/torch/hub/checkpoints")
    return os.path.exists(os.path.join(cache, DEMUCS_CKPT))


def run_demucs(track_dir: str) -> str | None:
    out = os.path.join(track_dir, "01_stems")
    cmd = [sys.executable, "-m", "demucs", "-n", "htdemucs", "-d", "cpu", "--float32", "-o", out,
           os.path.join(track_dir, "00_original", "original.wav")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    stems = os.path.join(out, "htdemucs", "original")
    if r.returncode == 0 and os.path.exists(os.path.join(stems, "vocals.wav")):
        return stems
    return None


def classical_separation(x: np.ndarray, sr: int) -> dict[str, np.ndarray]:
    import librosa
    n_fft, hop = 4096, 1024
    out = {}
    S = [librosa.stft(x[:, c], n_fft=n_fft, hop_length=hop) for c in range(2)]
    H, P = [], []
    for c in range(2):
        h, p = librosa.decompose.hpss(S[c], margin=(1.0, 3.0))
        H.append(h); P.append(p)
    drums = np.stack([librosa.istft(P[c], hop_length=hop, length=len(x)) for c in range(2)], axis=1)
    harm = np.stack([librosa.istft(H[c], hop_length=hop, length=len(x)) for c in range(2)], axis=1)
    # bass: harmonic content below 160 Hz (with a soft crossover)
    from scipy import signal
    sos = signal.butter(4, 160, btype="low", fs=sr, output="sos")
    bass = signal.sosfiltfilt(sos, harm, axis=0)
    harm_hi = harm - bass
    # vocals: REPET-style nearest-neighbour filtering on the harmonic (non-bass) part, mid channel weighted
    mid = np.mean(harm_hi, axis=1)
    Sm = librosa.stft(mid, n_fft=n_fft, hop_length=hop)
    mag, phase = np.abs(Sm), np.exp(1j * np.angle(Sm))
    filt = librosa.decompose.nn_filter(mag, aggregate=np.median, metric="cosine", width=int(librosa.time_to_frames(2, sr=sr, hop_length=hop)))
    filt = np.minimum(mag, filt)
    margin_v, power = 6, 2
    mask_v = librosa.util.softmask(mag - filt, margin_v * filt, power=power)
    # restrict the vocal mask to the 120 Hz .. 9 kHz band
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    band = ((freqs >= 120) & (freqs <= 9000)).astype(float)[:, None]
    mask_v = mask_v * band
    vocals_mid = librosa.istft(mask_v * Sm, hop_length=hop, length=len(x))
    vocals = np.stack([vocals_mid, vocals_mid], axis=1)
    # 'other' is the exact residual so that vocals+drums+bass+other == original sample-for-sample
    other = x - drums - bass - vocals
    return {"drums": drums, "bass": bass, "vocals": vocals, "other": other}


def separate(track_dir: str) -> dict:
    t0 = time.time()
    src = os.path.join(track_dir, "00_original", "original.wav")
    info = {"backend": None, "stems_dir": None, "seconds": None, "note": ""}
    pre = os.path.join(track_dir, "01_stems", "htdemucs", "original", "vocals.wav")
    if os.path.exists(pre):  # stems already produced by an earlier Demucs run
        info.update(backend="demucs-htdemucs", stems_dir=os.path.relpath(os.path.dirname(pre), track_dir))
    elif demucs_available():
        stems = run_demucs(track_dir)
        if stems:
            info.update(backend="demucs-htdemucs", stems_dir=os.path.relpath(stems, track_dir))
    if info["backend"] is None:
        x, sr = load_audio(src)
        st = classical_separation(x, sr)
        stems = os.path.join(track_dir, "01_stems", "classical", "original")
        for k, v in st.items():
            save_wav(os.path.join(stems, f"{k}.wav"), v, sr, subtype="FLOAT")
        info.update(backend="classical-hpss-nnfilter", stems_dir=os.path.relpath(stems, track_dir),
                    note="Demucs checkpoint not reachable in this environment; classical fallback used. "
                         "Re-run with Demucs on a machine with internet access for far better stems.")
    # residual check: stems must sum back to the original
    x, sr = load_audio(src)
    s = sum(load_audio(os.path.join(track_dir, info["stems_dir"], f"{k}.wav"), sr)[0] for k in ("vocals", "drums", "bass", "other"))
    n = min(len(x), len(s))
    corr = float(np.corrcoef(x[:n].ravel(), s[:n].ravel())[0, 1])
    rel_rms = float(np.sqrt(np.mean((x[:n] - s[:n]) ** 2)) / (np.sqrt(np.mean(x[:n] ** 2)) + 1e-12))
    info.update(sum_correlation=round(corr, 6), sum_relative_rms_error=round(rel_rms, 6), seconds=round(time.time() - t0, 1))
    write_json(os.path.join(track_dir, "01_stems", "separation.json"), info)
    return info


if __name__ == "__main__":
    print(json.dumps(separate(sys.argv[1]), indent=2))
