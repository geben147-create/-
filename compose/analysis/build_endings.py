# -*- coding: utf-8 -*-
"""Five endings for the first four blocks (the part the composer likes, up to 13.7 s = beat 32).

python3 build_endings.py <their FULL 140bpm .mid> <out folder> <report.json of a build6 run (for the fader gains)>

Everything before beat 32 is the arrangement as it stands. After it, each ending uses ONLY pitches that are already in the
composer's chords (Dm = D F A) or in their own block-1 figures; there is no new melody. The sub follows their bass an
octave down, as in the long version. The five differ in what happens at and after the end of the A7 block:
  1_open     stops on the A7 and lets it ring out: the line feels as if it were still going
  2_linger   resolves to Dm and rings, long and soft, a slow fade
  3_stop     one short Dm hit and silence
  4_fadeout  their own next two blocks keep going and fade away
  5_grand    a crescendo through the A7, then a big Dm with timpani and brass
"""
import os, sys, json, subprocess, shutil
import numpy as np, soundfile as sf
from scipy import signal

A = sys.argv; SRC, OUT, GAINS = A[1], A[2], A[3]
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
sys.argv = ["build6_run.py", SRC, OUT, "77.0", "violin"]
import build6_run as B
F, O, M = B.F, B.O, B.M
SR = 44100; CUT = 32.0
os.makedirs(OUT, exist_ok=True)
gains = {t["midi_name"]: t["gain_db"] for t in json.load(open(GAINS, encoding="utf-8"))["tracks"]}
TR = {t["midi_name"]: t for t in B.TRACKS}
IR = O.hall_ir()
HPF = {"Contrabass (yours)", "Contrabass root"}
V1, V2, HN, BS, RT, CH_, GL, PD = ("Violin I (yours)", "Viola melody -8ve (yours)", "Horns chords (yours)", "Contrabass (yours)",
                                   "Contrabass root", "Choir", "Glockenspiel", "Low strings bed")
LH, TB, TP, TK, RV = "French horns low", "Trombones", "Timpani", "Taiko", "Reverse cymbal swell"
PASS_A = [V1, V2, HN, BS, RT, CH_, GL, PD]

def upto(name, limit, clip=None):
    clip = limit if clip is None else clip
    return [{**n, "end": min(n["end"], clip)} for n in TR[name]["notes"] if n["start"] < limit - 1e-3]
def hold(ps, start, length, vel): return [{"pitch": p, "start": start, "end": start + length, "vel": vel} for p in ps]
def scale(ns, g, lo=CUT - 8): return [{**n, "vel": int(np.clip(round(n["vel"] * (g if n["start"] >= lo - 1e-3 else 1.0)), 1, 127))} for n in ns]

def prep(name, notes, cc=None):
    t = dict(TR[name]); t["notes"] = notes; t["gain_db"] = gains[name]
    if cc is not None: t["cc11"] = cc
    cal = B.CAL[t["program"]]
    t["voices"] = B.split_voices(notes)
    t["vbends"] = []
    for v in t["voices"]:
        bends = [(n["start"] - 0.02, -cal.get(n["pitch"], 0.0)) for n in v]
        t["vbends"].append(bends if any(abs(c) >= 5 for _, c in bends) else [])
    return t

def tri(ph): return 2 / np.pi * np.arcsin(np.sin(ph))
def render(key, tracks, end_s, fade_s):
    stems = []
    for i, t in enumerate(tracks):
        a = B.stem(t, 200 + i)
        if t["midi_name"] in HPF:
            a = signal.sosfiltfilt(signal.butter(4, 90.0, btype="highpass", fs=SR, output="sos"), a)
        stems.append({**t, "audio": a})
    N = len(stems[0]["audio"]); L = int(end_s * SR)
    base = O.mix(stems, IR, wet_bus_db=-6.0)[:L].copy()
    sub = np.zeros(N)
    for n in [n for t in tracks if t["midi_name"] == BS for n in t["notes"]]:     # their bass, one octave down, dry and mono
        f = 440.0 * 2 ** ((n["pitch"] - 12 - 69) / 12.0); s0, s1 = int(F.sec(n["start"]) * SR), min(int(F.sec(n["end"]) * SR), N)
        if s1 - s0 < 100: continue
        ph = 2 * np.pi * f * np.arange(s1 - s0) / SR; env = np.ones(s1 - s0); a = int(0.03 * SR); r = int(0.15 * SR)
        env[:a] = np.linspace(0, 1, a); env[-r:] = np.minimum(env[-r:], np.linspace(1, 0, r))
        sub[s0:s1] += (0.8 * np.sin(ph) + 0.2 * tri(ph)) * env
    sub = sub[:L]; rms = lambda x: float(np.sqrt(np.mean(x ** 2)) + 1e-12)
    g = rms(base.mean(axis=1)) * 10 ** (-3.0 / 20) / rms(sub[sub != 0])
    y = base + (sub * g)[:, None]
    fd = min(int(fade_s * SR), len(y)); y[-fd:] *= (0.5 * (1 + np.cos(np.linspace(0, np.pi, fd))))[:, None]
    y = y / max(1.0, np.max(np.abs(y)) / 0.89)
    raw = f"{OUT}/_{key}.wav"; sf.write(raw, y, SR, subtype="PCM_24")
    rep = M.master(raw, f"{OUT}/{key}_master.wav", target_lufs=-14.0, air_db=2.5, air_hz=7000.0)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{OUT}/{key}_master.wav", "-ac", "2", "-b:a", "128k", f"{OUT}/{key}.mp3"], check=True)
    os.remove(raw)
    B.write_midi(f"{OUT}/{key}_FULL_140bpm.mid", tracks)
    return {"seconds": round(len(y) / SR, 2), "lufs": rep["after"]["lufs"], "tp": float(rep["after"]["true_peak"]), "clipped": rep["after"]["clipped"]}

res = {}
def chord_hold(start, length, vel_scale=1.0, d=None):
    """Dm from the composer's own chord: horns A3 D4 F4, choir the same, bed A3 F4, bass D3, root D2, melody D5 F5 / A3."""
    v = lambda x: int(np.clip(round(x * vel_scale), 1, 127))
    return {V1: hold([74, 77], start, length, v(72)), V2: hold([57], start, length, v(66)),
            HN: hold([57, 62, 65], start + 0.02, length, v(70)), CH_: hold([57, 62, 65], start + 0.04, length, v(46)),
            PD: hold([57, 65], start, length, v(54)), BS: hold([50], start, length, v(90)), RT: hold([38], start, length, v(86))}

# 1 open: stop on the A7 and let it ring
tr = [prep(n, upto(n, CUT)) for n in PASS_A]
res["1_open"] = render("1_open", tr, F.sec(CUT) + 1.5, 1.0)

# 2 linger: resolve to Dm, soft, long ring and a slow fade
ch = chord_hold(CUT, 7.8)
tr = [prep(n, upto(n, CUT) + ch.get(n, [])) for n in PASS_A]
tr = [prep(GL, upto(GL, CUT) + [{"pitch": 86, "start": CUT + 0.02, "end": CUT + 1.6, "vel": 58}, {"pitch": 93, "start": CUT + 3.0, "end": CUT + 4.4, "vel": 46}])
      if t["midi_name"] == GL else t for t in tr]
res["2_linger"] = render("2_linger", tr, F.sec(CUT + 8) + 2.0, 3.4)

# 3 stop: one short Dm hit
ch = chord_hold(CUT, 0.9, 1.25)
tr = [prep(n, upto(n, CUT) + ch.get(n, [])) for n in PASS_A] + [prep(TP, hold([38], CUT, 0.7, 108))]
res["3_stop"] = render("3_stop", tr, F.sec(CUT + 1) + 1.6, 0.7)

# 4 fade-out: their own next two blocks keep going and fade (no added layers)
tr = [prep(n, upto(n, CUT + 16, CUT + 15.9)) for n in PASS_A]
res["4_fadeout"] = render("4_fadeout", tr, F.sec(CUT + 16) + 0.4, F.sec(CUT + 16) + 0.4 - F.sec(CUT))

# 5 grand: crescendo through the A7, then a big Dm with timpani, taiko, low horns and trombones
ch = chord_hold(CUT, 7.8, 1.5)
base5 = {n: scale(upto(n, CUT), 1.25) if n in (V1, V2, HN, CH_) else upto(n, CUT) for n in PASS_A}
tr = [prep(n, base5[n] + ch.get(n, [])) for n in PASS_A]
tr += [prep(LH, hold([57, 62], CUT + 0.02, 7.8, 100), [(0.0, 127)]), prep(TB, hold([45, 53], CUT + 0.02, 7.8, 100), [(0.0, 127)]),
       prep(TP, [{"pitch": 45, "start": 28.0, "end": 28.4, "vel": 84}, {"pitch": 45, "start": 30.0, "end": 30.4, "vel": 96},
                 {"pitch": 45, "start": 31.0, "end": 31.4, "vel": 106}, {"pitch": 38, "start": CUT, "end": CUT + 4.0, "vel": 127}]),
       prep(TK, [{"pitch": 45, "start": CUT, "end": CUT + 3.0, "vel": 120}]),
       prep(RV, [{"pitch": 60, "start": CUT - 8, "end": CUT, "vel": 100}], F.ramp(CUT - 8, CUT, 34, 127, curve=1.5))]
res["5_grand"] = render("5_grand", tr, F.sec(CUT + 8) + 2.6, 2.4)

json.dump(res, open(f"{OUT}/endings_report.json", "w"), indent=1)
shutil.rmtree(B.TMP, ignore_errors=True)
for k, v in res.items(): print(k, v)
