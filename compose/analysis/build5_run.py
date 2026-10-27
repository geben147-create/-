# -*- coding: utf-8 -*-
"""Build the progressive-orchestra version (10 blocks + held final chord).

python3 build5_run.py <their FULL 140bpm .mid> <out folder>
"""
import os, sys, json, subprocess, shutil
import numpy as np, pretty_midi, soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import finale as F
import orchestra as O
import master_simple as M

SRC, OUT = sys.argv[1], sys.argv[2]
TMP = os.path.join(OUT, "_stems"); os.makedirs(TMP, exist_ok=True)
S = F.load_beats(SRC)
END_B = 9 * F.BLK + 6 + 8 + 0       # final chord lands at beat 78 and is held to 86
CUT = 9 * F.BLK + 6                 # beat 78: the last ostinato note must start before this
HOLD_END = CUT + 8

def get(name): return [dict(n) for n in S[name]]
def ext(tr, blocks=(8, 9)):
    """Blocks 9 and 10 repeat the composer's own block-1 material."""
    base = F.in_block(tr, 0)
    return tr + [n for b in blocks for n in F.shift(base, b * F.BLK)]

V1, V2 = ext(get("Violin I (your melody)")), ext(get("Violin II (your melody, doubled)"))
HORN, BASS = ext(get("Horns (your chords)")), ext(get("Contrabass (your bass)"))
ROOT, CHOIR = ext(get("Contrabass (root, retuned)")), ext(get("Choir"))
GLOCK = ext(get("Glockenspiel"))

# crescendo through the closing blocks (velocity only)
def crescendo(ns, g8, g9):
    out = []
    for n in ns:
        b = int(n["start"] // F.BLK)
        g = g8 if b == 8 else (g9 if b == 9 else 1.0)
        out.append({**n, "vel": int(np.clip(round(n["vel"] * g), 1, 127))})
    return out
V1, V2 = crescendo(V1, 1.15, 1.32), crescendo(V2, 1.15, 1.32)
HORN, CHOIR = crescendo(HORN, 1.25, 1.5), crescendo(CHOIR, 1.2, 1.5)
GLOCK = [{**n, "vel": min(127, n["vel"] + (10 if n["start"] >= 8 * F.BLK else 0))} for n in GLOCK]

# the last ostinato note must stop before the held chord
violin_notes = {}
for nm, tr, v in (("V1", V1, 86), ("V2", V2, 78)):
    kept = [n for n in tr if n["start"] < CUT]
    held = [{"pitch": p, "start": CUT, "end": HOLD_END - 0.1, "vel": v} for p in (74, 69, 77)]  # D5 A4 F5, their cell's pitches
    violin_notes[nm] = kept + held
V1, V2 = violin_notes["V1"], violin_notes["V2"]
OCT = F.scale_vel([ {**n, "pitch": n["pitch"] + 12} for n in V1
                    if 9 * F.BLK <= n["start"] < CUT and n["end"] - n["start"] < 1.5], 0.85)   # derived octave, b10 only

# sustained layers ring on into the held chord
def ring(ns):
    return [{**n, "end": HOLD_END - 0.1} if n["start"] >= 9 * F.BLK else n for n in ns]
HORN, BASS, ROOT, CHOIR = ring(HORN), ring(BASS), ring(ROOT), ring(CHOIR)

PADN = [n for b in range(10) for n in F.sustained(F.PAD[F.CH[b]], b, 60)]
PADN = ring(PADN)
PADCC = [c for b in range(10) for c in F.ramp(b * F.BLK, (b + 1) * F.BLK - 0.01, 72, 100)]

CELLO = sum([F.cello_ostinato([b], 48 + 5 * (b - 4)) for b in range(4, 8)], []) + F.cello_ostinato((8, 9), 70, drive=True)
CELLO = [n for n in CELLO if n["start"] < CUT] + [{"pitch": 38, "start": CUT, "end": HOLD_END - 0.1, "vel": 92}]

LH = [n for b in range(5, 10) for n in F.sustained(F.LHORN[F.CH[b]], b, 64)]
LH = ring(LH)
LHCC = (F.ramp(5*8, 6*8-.01, 62, 92) + F.ramp(6*8, 7*8-.01, 70, 100)
        + F.ramp(7*8, 8*8-.01, 56, 122, curve=2.0)                     # the breath swell into the driving bar
        + F.ramp(8*8, 9*8-.01, 90, 127) + F.ramp(9*8, CUT, 100, 127) + [(CUT, 127), (HOLD_END - 4, 127), (HOLD_END, 100)])

TB = [n for b in (8, 9) for n in F.sustained(F.TBONE, b, 72)]
TB = ring(TB)
TBCC = F.ramp(8*8, 9*8-.01, 74, 120) + F.ramp(9*8, CUT, 90, 127) + [(CUT, 127), (HOLD_END - 4, 127), (HOLD_END, 100)]

TIMP = F.timpani_pass2(6, 7)
t8, k8 = F.rock_bar(8); t9, k9 = F.rock_bar(9)
t9 = [n for n in t9 if n["start"] < CUT - 2]; k9 = [n for n in k9 if n["start"] < CUT - 2]
TIMP += t8 + t9 + F.finale_roll(CUT - 2, CUT) + [{"pitch": 38, "start": CUT, "end": CUT + 4.0, "vel": 127}]
TAIKO = k8 + k9 + [{"pitch": 43, "start": CUT, "end": CUT + 3.0, "vel": 122}]
REV = [{"pitch": 60, "start": 9 * F.BLK, "end": CUT, "vel": 100}]
REVCC = F.ramp(9 * F.BLK, CUT, 34, 127, curve=1.5)

def T(name, mn, prog, notes, pan, gain, send, who, enters, cc=None):
    return dict(name=name, midi_name=mn, program=prog, notes=notes, cc11=cc or [], pan=pan,
                gain_db=gain, send_db=send, who=who, enters=enters)

TRACKS = [
    T("제1바이올린 — 당신 멜로디", "Violin I (yours)", 48, V1, -0.38, 0.0, -10.0, "당신", 1),
    T("제2바이올린 — 당신 멜로디 겹침", "Violin II (yours)", 49, V2, -0.10, -5.0, -8.0, "당신", 1),
    T("호른 — 당신 화음", "Horns chords (yours)", 60, HORN, -0.30, -7.0, -4.0, "당신(교정)", 1),
    T("콘트라베이스 — 당신 베이스", "Contrabass (yours)", 43, BASS, 0.40, -2.0, -9.0, "당신", 1),
    T("콘트라베이스 — 저음 루트", "Contrabass root", 43, ROOT, 0.30, -4.0, -9.0, "당신(교정)", 1),
    T("합창", "Choir", 52, CHOIR, 0.0, -9.0, -2.0, "제가 만든 반주", 1),
    T("글로켄슈필", "Glockenspiel", 9, GLOCK, 0.55, -5.0, -3.0, "제가 만든 반주", 1),
    T("저음 현악 베드", "Low strings bed", 48, PADN, -0.20, -3.0, -5.0, "당신 화음에서 파생", 1, PADCC),
    T("첼로 오스티나토", "Cello ostinato", 42, CELLO, 0.35, +3.0, -8.0, "당신 화음에서 파생", 5),
    T("프렌치 호른 (저음)", "French horns low", 60, LH, -0.45, +3.0, -4.0, "당신 화음에서 파생", 6, LHCC),
    T("트롬본", "Trombones", 57, TB, 0.45, -1.0, -4.0, "당신 화음에서 파생", 9, TBCC),
    T("팀파니", "Timpani", 47, TIMP, 0.05, 0.0, -4.0, "제가 만든 반주", 7),
    T("타이코", "Taiko", 116, TAIKO, 0.0, -2.0, -5.0, "제가 만든 반주", 9),
    T("리버스 심벌 스웰", "Reverse cymbal swell", 119, REV, 0.0, 6.0, -2.0, "제가 만든 반주", 10, REVCC),
    T("바이올린 옥타브 (최종 합창)", "Violins +8ve (final)", 48, OCT, -0.25, -7.0, -8.0, "당신 음에서 파생", 10),
]

# ------------------------------------------------------------------ MIDI out + stems
def write_midi(path, tracks):
    pm = pretty_midi.PrettyMIDI(initial_tempo=F.TEMPO)
    for t in tracks:
        inst = pretty_midi.Instrument(program=int(t["program"]), is_drum=False, name=t["midi_name"])
        for n in t["notes"]:
            inst.notes.append(pretty_midi.Note(int(np.clip(n["vel"], 1, 127)), int(n["pitch"]),
                                               F.sec(n["start"]), F.sec(max(n["end"], n["start"] + 0.05))))
        for b, v in t["cc11"]:
            inst.control_changes.append(pretty_midi.ControlChange(11, int(np.clip(v, 0, 127)), F.sec(b)))
        pm.instruments.append(inst)
    pm.write(path)

def stem(t, i, tail_s=3.8):
    mid, wav = f"{TMP}/s{i}.mid", f"{TMP}/s{i}.wav"
    write_midi(mid, [{**t, "cc11": ([(0.0, 127)] if not t["cc11"] else t["cc11"])}])
    r = subprocess.run([F.FLUID, "-ni", "-g", "0.7", "-F", wav, "-r", "44100", "-R", "0", "-C", "0", F.SF2, mid],
                       capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(r.stderr[:200])
    x, sr = sf.read(wav, dtype="float64", always_2d=True)
    return np.concatenate([x.mean(axis=1), np.zeros(int(tail_s * sr))])

IR = O.hall_ir()
report = {"tempo": F.TEMPO, "blocks": 10, "hold_end_beat": HOLD_END, "tracks": []}

# Faders are set from measurement, not guessed. Each stem is rendered at unity, its RMS is read
# over the blocks where it is meant to be heard, and the gain that lands it on its target is
# applied. (Guessed faders left Violin II 20 dB under Violin I and the choir inaudible.)
# target dB RMS, window in beats
AUTO = {
    "Violin I (yours)": (-28.0, 0, 32), "Violin II (yours)": (-34.0, 0, 32),
    "Horns chords (yours)": (-35.0, 0, 32), "Contrabass (yours)": (-24.5, 0, 32),
    "Contrabass root": (-35.0, 0, 32), "Choir": (-41.0, 0, 32), "Glockenspiel": (-50.0, 0, 32),
    "Low strings bed": (-35.0, 0, 32), "Cello ostinato": (-33.0, 32, 64),
    "French horns low": (-29.0, 40, 64), "Timpani": (-41.0, 48, 64),
    "Trombones": (-28.0, 64, 72), "Taiko": (-31.0, 64, 72),
    "Reverse cymbal swell": (-34.0, 72, 78), "Violins +8ve (final)": (-31.0, 72, 78),
}
stems = []
for i, t in enumerate(TRACKS):
    a = stem(t, i)
    tgt, b0, b1 = AUTO[t["midi_name"]]
    seg = a[int(F.sec(b0) * 44100): int(F.sec(b1) * 44100)]
    meas = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12)
    t["gain_db"] = float(np.clip(tgt - meas, -30.0, 25.0))
    stems.append({**t, "audio": a})
    print(f"  fader {t['midi_name']:<24} measured {meas:6.1f} dB -> target {tgt:6.1f} => {t['gain_db']:+6.1f} dB")
y = O.mix(stems, IR, wet_bus_db=-6.0)
n = len(y)
full_rms = np.sqrt(np.mean(y ** 2))
# what each added layer is worth, by removal; whole-file RMS and its loudest 200 ms
W = int(0.2 * 44100); worth = {}
for s_ in stems:
    if s_["who"] == "당신":
        continue
    y2 = O.mix([q for q in stems if q is not s_], IR, wet_bus_db=-6.0)
    m = min(len(y), len(y2)); d = y[:m] - y2[:m]
    nb = m // W
    dw = np.sqrt((d[:nb * W] ** 2).reshape(nb, -1).mean(axis=1)); mw = np.sqrt((y[:nb * W] ** 2).reshape(nb, -1).mean(axis=1))
    worth[s_["name"]] = {"avg_db": round(float(20 * np.log10(np.sqrt(np.mean(d ** 2)) / full_rms + 1e-12)), 1),
                         "peak_db": round(float(np.max(20 * np.log10(dw / (mw + 1e-12) + 1e-12))), 1)}
# the synth renders ~7 s of silence after the last note: end 3.2 s after the held chord, fading
END_S = F.sec(HOLD_END) + 3.2
y = y[: int(END_S * 44100)].copy()
fade = int(2.2 * 44100)
y[-fade:] *= (0.5 * (1 + np.cos(np.linspace(0, np.pi, fade))))[:, None]
n = len(y)
# Bass audibility measured inside the real mix: remove their bass (and, separately, bass + root)
# and see how much of the 95-190 Hz band disappears.
from scipy import signal as _sg
def _band(x, a, b):
    sos = _sg.butter(4, [a, b], btype="bandpass", fs=44100, output="sos")
    return 20 * np.log10(np.sqrt(np.mean(_sg.sosfiltfilt(sos, x.mean(axis=1)) ** 2)) + 1e-12)
def _without(names):
    z = O.mix([q for q in stems if q["midi_name"] not in names], IR, wet_bus_db=-6.0)[: len(y)]
    return z
_full = _band(y, 95, 190)
report["bass_worth_db"] = {
    "yours_only": round(float(_full - _band(_without({"Contrabass (yours)"}), 95, 190)), 2),
    "yours_plus_root": round(float(_full - _band(_without({"Contrabass (yours)", "Contrabass root"}), 95, 190)), 2)}
y = y / max(1.0, np.max(np.abs(y)) / 0.89)
raw = f"{OUT}/finale_raw.wav"; sf.write(raw, y, 44100, subtype="PCM_24")
rep = M.master(raw, f"{OUT}/finale_master.wav", target_lufs=-14.0, air_db=2.5, air_hz=7000.0)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{OUT}/finale_master.wav", "-ac", "2",
                "-b:a", "128k", f"{OUT}/finale.mp3"], check=True)
os.remove(raw)

write_midi(f"{OUT}/finale_FULL_140bpm.mid", TRACKS)
write_midi(f"{OUT}/finale_ADD_ONLY_140bpm.mid", [t for t in TRACKS if t["who"] != "당신" and t["who"] != "당신(교정)"])
mm, _sr = sf.read(f"{OUT}/finale_master.wav", always_2d=True); mm = mm.mean(axis=1)
bl = 8 * 60 / F.TEMPO
report["block_rms_db"] = [round(float(20 * np.log10(np.sqrt(np.mean(mm[int(b*bl*_sr):int(min((b+1)*bl, len(mm)/_sr)*_sr)] ** 2)) + 1e-12)), 1)
                          for b in range(11) if int(b*bl*_sr) < len(mm)]
report["master"] = rep; report["layer_worth_db"] = worth
report["length_sec"] = round(n / 44100, 2)
report["tracks"] = [{"name": t["name"], "midi_name": t["midi_name"], "who": t["who"], "enters_block": t["enters"],
                     "notes": len(t["notes"]), "pan": t["pan"], "gain_db": t["gain_db"], "send_db": t["send_db"]}
                    for t in TRACKS]
shutil.rmtree(TMP, ignore_errors=True)
json.dump(report, open(f"{OUT}/report.json", "w"), ensure_ascii=False, indent=1)
print(f"{report['length_sec']} s, master {rep['before']['lufs']:+.2f} -> {rep['after']['lufs']:+.2f} LUFS, "
      f"TP {rep['after']['true_peak']:+.2f}, clipped {rep['after']['clipped']}")
for t in report["tracks"]:
    print(f"  b{t['enters_block']:>2}+ {t['name']:<28} {t['notes']:>4} notes  pan{t['pan']:+.2f} {t['gain_db']:+5.1f}dB  [{t['who']}]")
print("block RMS dB:", report["block_rms_db"])
print("bass worth in the real mix (95-190 Hz):", report["bass_worth_db"])
print("layer worth (avg / loudest 200ms):")
for k, v in sorted(worth.items(), key=lambda kv: -kv[1]["peak_db"]):
    print(f"  {k:<28} {v['avg_db']:+6.1f} / {v['peak_db']:+6.1f} dB")
