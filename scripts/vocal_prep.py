"""Human step helper: prepare a phone-recorded vocal take for the arrangement.
   python scripts/vocal_prep.py 03_human_raw/TAKE_01.wav --track tracks/01_xxx --start 45.7 [--key "D minor"] [--tune]
Steps (the RAW file is never modified; a *_prepped.wav copy is written next to it):
  1. high-pass 80 Hz, DC removal            4. optional pitch snap to the song key (crude; use MAutoPitch/Graillon in REAPER for real tuning)
  2. simple noise gate (-45 dBFS)           5. peak normalise to -6 dBFS
  3. de-ess-ish 6-9 kHz dynamic dip         6. place at --start seconds (output time) as 04_edits/new_parts/vocal_<take>.wav
Then re-run:  python scripts/pipeline.py <track> --from master   (the mix picks up every file in new_parts/)"""
from __future__ import annotations
import argparse, os, sys, json
import numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audiolib import load_audio, save_wav, highpass, sha256, write_json, db
from analysis import KEY_NAMES

SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}


def gate(x, sr, thresh_db=-45.0, hold_ms=120, ramp_ms=20):
    env = np.sqrt(signal.fftconvolve(np.mean(x ** 2, axis=1), np.ones(int(0.02 * sr)) / int(0.02 * sr), mode="same"))
    on = env > 10 ** (thresh_db / 20)
    hold = int(hold_ms / 1000 * sr)
    on = np.convolve(on.astype(float), np.ones(hold), mode="same") > 0
    g = signal.fftconvolve(on.astype(float), np.ones(int(ramp_ms / 1000 * sr)) / int(ramp_ms / 1000 * sr), mode="same")
    return x * np.clip(g, 0, 1)[:, None]


def deess(x, sr):
    sos = signal.butter(2, [6000, 9500], btype="band", fs=sr, output="sos")
    s = signal.sosfiltfilt(sos, x, axis=0)
    env = np.sqrt(signal.fftconvolve(np.mean(s ** 2, axis=1), np.ones(int(0.005 * sr)) / int(0.005 * sr), mode="same"))
    thr = 10 ** (-28 / 20)
    red = np.where(env > thr, thr / (env + 1e-9), 1.0) ** 0.5
    return x - s * (1 - red)[:, None]


def pitch_snap(x, sr, key):
    import librosa
    tonic, mode = key.split(); tonic = KEY_NAMES.index(tonic)
    pcs = [(tonic + s) % 12 for s in SCALES[mode]]
    y = np.mean(x, axis=1).astype(np.float32)
    f0, voiced, _ = librosa.pyin(y, fmin=70, fmax=1000, sr=sr, frame_length=2048, hop_length=512)
    out = np.zeros_like(y)
    hop = 512
    # segment by voiced runs, shift each run by the median correction so vibrato/phrasing survives
    i = 0
    frames = len(f0)
    while i < frames:
        if not voiced[i] or np.isnan(f0[i]):
            i += 1; continue
        k = i
        while k < frames and voiced[k] and not np.isnan(f0[k]):
            k += 1
        seg = y[i * hop:k * hop + 2048]
        midi = librosa.hz_to_midi(np.nanmedian(f0[i:k]))
        target = min(range(int(midi) - 2, int(midi) + 3), key=lambda m: (0 if m % 12 in pcs else 1, abs(m - midi)))
        shift = float(target - midi)
        if abs(shift) > 0.05 and len(seg) > 2048:
            seg = librosa.effects.pitch_shift(seg, sr=sr, n_steps=shift)
        out[i * hop:i * hop + len(seg)] += seg[: len(out) - i * hop]
        i = k
    unv = np.ones_like(y)
    for i in range(frames):
        if voiced[i] and not np.isnan(f0[i]):
            unv[i * hop:(i + 1) * hop] = 0
    out += y * unv
    return np.stack([out, out], axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("take")
    ap.add_argument("--track", required=True)
    ap.add_argument("--start", type=float, required=True, help="output-time position (s) where the take begins")
    ap.add_argument("--key", default=None)
    ap.add_argument("--tune", action="store_true")
    ap.add_argument("--gain_db", type=float, default=-3.0)
    a = ap.parse_args()
    man = json.load(open(os.path.join(a.track, "04_edits", "arrangement_manifest.json")))
    ref, sr = load_audio(os.path.join(a.track, "05_mix", "premaster.wav"))
    x, _ = load_audio(a.take, sr)
    x = highpass(x, sr, 80.0, order=2)
    x = gate(x, sr)
    x = deess(x, sr)
    if a.tune and a.key:
        x = pitch_snap(x, sr, a.key)
    x *= 10 ** (-6 / 20) / (np.max(np.abs(x)) + 1e-9)
    x *= 10 ** (a.gain_db / 20)
    out = np.zeros_like(ref)
    i = int(a.start * sr); seg = x[: len(out) - i]
    out[i:i + len(seg)] = seg
    name = os.path.splitext(os.path.basename(a.take))[0]
    dst = os.path.join(a.track, "04_edits", "new_parts", f"vocal_{name}.wav")
    save_wav(dst, out, sr, subtype="FLOAT")
    # rebuild the premaster = bed + all new parts (so the master stage sees the vocal)
    bed, _ = load_audio(os.path.join(a.track, "04_edits", "bed_original_stems_automated.wav"))
    total = bed.copy()
    for f in sorted(os.listdir(os.path.join(a.track, "04_edits", "new_parts"))):
        if f.endswith(".wav"):
            p, _ = load_audio(os.path.join(a.track, "04_edits", "new_parts", f), sr)
            n = min(len(total), len(p)); total[:n] += p[:n]
    pk = float(np.max(np.abs(total)))
    if pk > 0.98:
        total *= 0.98 / pk
    save_wav(os.path.join(a.track, "05_mix", "premaster.wav"), total, sr, subtype="FLOAT")
    write_json(os.path.join(a.track, "03_human_raw", f"{name}_prep.json"), {
        "raw_take": os.path.basename(a.take), "raw_sha256": sha256(a.take), "origin": "HUMAN performance (user)",
        "processing": ["hpf80", "gate-45dB", "deess", "pitch_snap" if a.tune and a.key else "no tuning", f"peak -6 dBFS, gain {a.gain_db} dB"],
        "placed_at_output_s": a.start, "placed_file": os.path.relpath(dst, a.track)})
    print("placed", dst, "-> now run: python scripts/pipeline.py", a.track, "--from master")


if __name__ == "__main__":
    main()
