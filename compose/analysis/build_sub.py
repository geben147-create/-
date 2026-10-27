# -*- coding: utf-8 -*-
"""Add a mono sine/triangle SUB layer one octave under the composer's own bass, and tune its level by measurement.

python3 build_sub.py <their FULL 140bpm .mid> <out folder> [seconds=77.0] [mode=violin|cello]

No new notes: the sub plays exactly the pitches and timing of the composer's bass track, one octave down
(D3 Bb2 C3 A2 -> D2 Bb1 C2 A1 = 73 / 58 / 65 / 55 Hz). It is synthesised, so it is in tune by construction (no
soundfont calibration), mono, and dry (no hall). The two General-MIDI bass stems are high-passed at 90 Hz so they
stay where a bass is audible on small speakers (about 110-150 Hz) and the sub carries what is below.
The sub's RMS is swept from -15 dB to -3 dB relative to the RMS of the rest of the mix; each step is mastered and
measured, and the report records every step.
"""
import os, sys, json, subprocess
import numpy as np, soundfile as sf
from scipy import signal

A = sys.argv
SRC, OUT = A[1], A[2]; SEC = A[3] if len(A) > 3 else "77.0"; MODE = A[4] if len(A) > 4 else "violin"
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
sys.argv = ["build6_run.py", SRC, OUT, SEC, MODE]
import build6_run as B           # builds TRACKS and calibrates tuning on import; the build itself is under __main__
F, O, M = B.F, B.O, B.M
os.makedirs(OUT, exist_ok=True)
SR = 44100
HPF_NAMES = {"Contrabass (yours)", "Contrabass root"}          # keep the GM bass around 120 Hz
HPF_HZ = 90.0

IR = O.hall_ir()
stems = []
for i, t in enumerate(B.TRACKS):
    a = B.stem(t, i); tgt, b0, b1 = B.AUTO[t["midi_name"]]
    seg = a[int(F.sec(b0) * SR): int(F.sec(b1) * SR)]
    t["gain_db"] = float(np.clip(tgt - 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12), -30.0, 25.0))
    if t["midi_name"] in HPF_NAMES:                              # gain was set from the full-range stem; filter afterwards
        a = signal.sosfiltfilt(signal.butter(4, HPF_HZ, btype="highpass", fs=SR, output="sos"), a)
    stems.append({**t, "audio": a})

# ---- the sub: their bass notes, one octave down, mono sine with a little triangle
BASS = [n for t in B.TRACKS if t["midi_name"] == "Contrabass (yours)" for n in t["notes"]]
N = len(stems[0]["audio"]); sub = np.zeros(N)
def tri(ph): return 2 / np.pi * np.arcsin(np.sin(ph))
for n in BASS:
    f = 440.0 * 2 ** ((n["pitch"] - 12 - 69) / 12.0)
    s0, s1 = int(F.sec(n["start"]) * SR), int(F.sec(n["end"]) * SR)
    s1 = min(s1, N)
    if s1 - s0 < 100: continue
    ph = 2 * np.pi * f * np.arange(s1 - s0) / SR
    w = 0.8 * np.sin(ph) + 0.2 * tri(ph)
    env = np.ones(s1 - s0); a = int(0.03 * SR); r = int(0.15 * SR)
    env[:a] = np.linspace(0, 1, a); env[-r:] = np.minimum(env[-r:], np.linspace(1, 0, r))
    sub[s0:s1] += w * env
subnotes = [{"pitch": n["pitch"] - 12, "start": n["start"], "end": n["end"], "vel": 100} for n in BASS]

END_S = F.sec(B.HOLD_END) + B.TAIL
L = int(END_S * SR)
base = O.mix(stems, IR, wet_bus_db=-6.0)[:L].copy()
sub = sub[:L]
def rms(x): return float(np.sqrt(np.mean(x ** 2)) + 1e-12)
ref = rms(base.mean(axis=1)); sub_rms = rms(sub[sub != 0])
fade = int(1.2 * SR)
def finish(y):
    y = y.copy(); y[-fade:] *= (0.5 * (1 + np.cos(np.linspace(0, np.pi, fade))))[:, None]
    return y / max(1.0, np.max(np.abs(y)) / 0.89)
def share(x, a, b):
    f, P = signal.welch(x, SR, nperseg=16384); tot = np.trapezoid(P, f)
    k = (f >= a) & (f < b); return 100 * np.trapezoid(P[k], f[k]) / tot

def band(x, a, b):
    sos = signal.butter(4, [a, b], btype="bandpass", fs=SR, output="sos")
    return 20 * np.log10(np.sqrt(np.mean(signal.sosfiltfilt(sos, x.mean(axis=1)) ** 2)) + 1e-12)

rows = []
FIXED = os.environ.get("SUB_REL")          # skip the sweep when the level is already known
LEVELS = (None, float(FIXED)) if FIXED else (None, -15.0, -12.0, -9.0, -6.0, -3.0)
for rel in LEVELS:
    if rel is None: y = base
    else:
        g = ref * 10 ** (rel / 20) / sub_rms
        y = base + (sub * g)[:, None]                            # identical in L and R: mono, centred, dry
    y = finish(y); raw = f"{OUT}/_sweep.wav"; sf.write(raw, y, SR, subtype="PCM_24")
    rep = M.master(raw, f"{OUT}/_sweep_m.wav", target_lufs=-14.0, air_db=2.5, air_hz=7000.0)
    m, _ = sf.read(f"{OUT}/_sweep_m.wav", always_2d=True); mm = m.mean(axis=1)
    row = {"sub_rel_db": rel, "lt120_pct": round(share(mm, 20, 120), 1), "sub_band_40_75_pct": round(share(mm, 40, 75), 1),
           "melody_500_1k_pct": round(share(mm, 500, 1000), 1),
           "melody_500_1k_dbfs": round(float(band(m, 500, 1000)), 1), "bass_95_190_dbfs": round(float(band(m, 95, 190)), 1),
           "crest_db": round(float(20 * np.log10(np.max(np.abs(mm)) / rms(mm))), 1),
           "lufs_after": rep["after"]["lufs"], "tp_after": rep["after"]["true_peak"], "clipped": rep["after"]["clipped"],
           "side_mid_db": round(float(20 * np.log10(rms((m[:, 0] - m[:, 1]) / 2) / rms((m[:, 0] + m[:, 1]) / 2))), 1)}
    rows.append(row); print(row, flush=True)
    os.remove(raw)

# the highest step whose master still lands on target and does not squeeze the melody band
base_mel = rows[0]["melody_500_1k_pct"]
ok = [r for r in rows[1:] if abs(r["lufs_after"] + 14.0) <= 0.6 and r["melody_500_1k_pct"] >= 0.6 * base_mel and r["clipped"] == 0]
pick = ok[-1] if ok else rows[1]
rel = pick["sub_rel_db"]; g = ref * 10 ** (rel / 20) / sub_rms
y = finish(base + (sub * g)[:, None]); sf.write(f"{OUT}/_f.wav", y, SR, subtype="PCM_24")
rep = M.master(f"{OUT}/_f.wav", f"{OUT}/sub_master.wav", target_lufs=-14.0, air_db=2.5, air_hz=7000.0)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{OUT}/sub_master.wav", "-ac", "2", "-b:a", "128k", f"{OUT}/sub.mp3"], check=True)

without = O.mix([q for q in stems if q["midi_name"] != "Contrabass (yours)"], IR, wet_bus_db=-6.0)[:L] + (sub * g)[:, None]
bass_worth = round(float(band(base + (sub * g)[:, None], 95, 190) - band(without, 95, 190)), 2)

# MIDI for Studio One: the sub is one more track (the player picks a sine synth for it)
subtrack = dict(name="서브 사인 (당신 베이스 한 옥타브 아래)", midi_name="Sub sine mono (octave below yours)", program=80,
                notes=subnotes, cc11=[], who="당신 음에서 파생", enters=1)
B.write_midi(f"{OUT}/sub_FULL_140bpm.mid", B.TRACKS + [subtrack])
B.write_midi(f"{OUT}/sub_ADD_ONLY_140bpm.mid", [t for t in B.TRACKS if t["who"] not in ("당신", "당신(교정)")] + [subtrack])
json.dump({"mode": MODE, "sweep": rows, "chosen_rel_db": rel, "bass_worth_db": bass_worth, "master": rep,
           "sub_pitches_hz": {str(p): round(440 * 2 ** ((p - 69) / 12), 1) for p in sorted({n["pitch"] for n in subnotes})},
           "hpf_hz": HPF_HZ, "ref_rms_dbfs_premaster": round(20 * np.log10(ref), 1)},
          open(f"{OUT}/sub_report.json", "w"), ensure_ascii=False, indent=1)
for f in ("_f.wav", "_sweep_m.wav"):
    p = f"{OUT}/{f}"
    if os.path.exists(p): os.remove(p)
print("CHOSEN rel dB:", rel, "| bass worth in mix:", bass_worth, "dB | master", rep["after"])
