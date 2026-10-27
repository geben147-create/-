# -*- coding: utf-8 -*-
"""80-second progressive orchestra: 22 blocks + a held final chord.

python3 build6_run.py <their FULL 140bpm .mid> <out folder>

Structure (a block is 8 beats; the harmony cycles Dm | Bb | F/C | A7 every four blocks):
  pass A  b1-4    their parts + low strings bed
  pass B  b5-8    + cello ostinato (b5), low horns (b6), timpani (b7), brass swell into b9 (b8)
  pass C  b9-12   + trombones
  pass D  b13-16  fuller swells, timpani on every downbeat
  pass E  b17-20  the driving cinematic-rock bars (timpani/taiko/low strings, no drum kit), octave violins
  b21     driving bar on the tonic the A7 resolves to
  b22     final chorus: everything, reverse-cymbal swell, one last hit and a held Dm
"""
import os, sys, json, subprocess, shutil
import numpy as np, pretty_midi, soundfile as sf
from scipy import signal as _sg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import finale as F
import orchestra as O
import master_simple as M
import tuning as TU

SRC, OUT = sys.argv[1], sys.argv[2]
TARGET_S = float(sys.argv[3]) if len(sys.argv) > 3 else 77.0     # cut at 1:17
MODE = sys.argv[4] if len(sys.argv) > 4 else "violin"           # "violin": solo violin leads; "cello": a cello leads
TMP = os.path.join(OUT, "_stems"); os.makedirs(TMP, exist_ok=True)
S = F.load_beats(SRC)
N = F.N_BLOCKS
BLK = F.BLK
CUT = (N - 1) * BLK + 6                                   # beat where the last chord lands
TAIL = 0.2                                                # the file ends right after the held chord
HOLD_END = TARGET_S / 60.0 * F.TEMPO - TAIL / 60.0 * F.TEMPO   # so the file is TARGET_S long
HOLD_END = round(HOLD_END, 2)

def get(name): return [dict(n) for n in S[name]]
def repeat(tr):
    """Their 8 blocks, then the same figures again; the last two blocks repeat block 1 (Dm)."""
    out = list(tr)
    for b in range(8, N):
        src = 0 if b >= N - 2 else b % 8
        out += F.shift(F.in_block(tr, src), (b - src) * BLK)
    return out

V1, V2 = repeat(get("Violin I (your melody)")), repeat(get("Violin II (your melody, doubled)"))
HORN, BASS = repeat(get("Horns (your chords)")), repeat(get("Contrabass (your bass)"))
ROOT, CHOIR = repeat(get("Contrabass (root, retuned)")), repeat(get("Choir"))
GLOCK = repeat(get("Glockenspiel"))

# Block 3 (F over their C bass): the retuned root went to F2, which fought their C3. Back to C2.
def blk_of(n):
    """Block index of a note. The composer's block starts sit a hair under the boundary (15.9999 beats instead
    of 16), so a plain floor put them in the previous block - which is how the first pass's block 3 kept its F2."""
    return int((n["start"] + 1e-3) // BLK)

def fix_f_over_c(ns):
    return [{**n, "pitch": 36} if (blk_of(n) % 4 == 2 and n["pitch"] == 41) else n for n in ns]
ROOT = fix_f_over_c(ROOT)

# the whole piece swells pass by pass (velocity only)
GAIN = [1.0]*8 + [1.05]*4 + [1.12]*4 + [1.22]*4 + [1.32, 1.45]
def crescendo(ns):
    return [{**n, "vel": int(np.clip(round(n["vel"] * GAIN[min(blk_of(n), N - 1)]), 1, 127))} for n in ns]
V1, V2, HORN, CHOIR = map(crescendo, (V1, V2, HORN, CHOIR))
GLOCK = [{**n, "vel": min(127, n["vel"] + (10 if n["start"] >= 16 * BLK else 0))} for n in GLOCK]

# ---- the final chord: violins DIVIDED, not doubled. Two ensemble patches holding the same three
# notes beat against each other (that was the shake in the last seconds of the previous version).
# The melody was rendered with ensemble-string patches, whose soft attack on short notes sounds like a
# synth or a piano. It is a solo violin now, and the notes are cut to a staccato length.
STACCATO = 0.30                                              # beats; their notes were about 0.45
def staccato(ns):
    return [{**n, "end": n["start"] + min(n["end"] - n["start"], STACCATO)} if n["end"] - n["start"] < 1.5 else n for n in ns]
V1, V2 = staccato(V1), staccato(V2)
V1 = [n for n in V1 if n["start"] < CUT] + [{"pitch": p, "start": CUT, "end": HOLD_END - 0.1, "vel": 90} for p in (74, 77)]   # D5 F5
# Their second take of the melody is now a VIOLA, one octave down (D4 A3 D4 F4 ...): the heavier, darker
# "alto violin" line under the solo violin. Same notes and timing as the take they played, an octave lower.
# Exception: their A#4 (the b9 over A7) stays at A#4. An octave down it lands a minor 9th above the A2 bass.
V2 = [{**n, "pitch": n["pitch"] if n["pitch"] == 70 else n["pitch"] - 12} for n in V2 if n["start"] < CUT] + [{"pitch": 57, "start": CUT, "end": HOLD_END - 0.1, "vel": 84}]  # A3
OCT = F.scale_vel([{**n, "pitch": n["pitch"] + 12} for n in V1
                   if 16 * BLK <= n["start"] < CUT and n["end"] - n["start"] < 1.5], 0.78)

def ring(ns):          # let a sustained layer run into the hold
    return [{**n, "end": HOLD_END - 0.1} if n["start"] >= (N - 1) * BLK else n for n in ns]
HORN, BASS, ROOT, CHOIR = ring(HORN), ring(BASS), ring(ROOT), ring(CHOIR)

def stop_at_cut(ns):   # layers that would only double the held chord end as it lands
    return [{**n, "end": min(n["end"], CUT + 0.3)} for n in ns]

PADN = [n for b in range(N) for n in F.sustained(F.PAD[F.CH[b]], b, 60)]
PADN = stop_at_cut(PADN)
def lvl(b, lo, hi): return (lo + (hi - lo) * min(1.0, b / (N - 1)))
PADCC = [c for b in range(N) for c in F.ramp(b * BLK, (b + 1) * BLK - 0.01, 70 + b, 96 + b * 0.6)]

# Two string lines under the melody: a viola (low) and a violin (upper), quarter notes that follow each block's chord.
# Block 4 (A7) leaves out the root A: their own A#4 rings above it and a root underneath makes a minor 9th.
#            viola (3 notes per 4 beats: root root fifth root)   violin (third fifth third fifth)
PULSE_V = {0: ([50, 50, 57, 50], [65, 69, 65, 69]),    # Dm   D3 D3 A3 D3     F4 A4 F4 A4
           1: ([46, 46, 53, 46], [62, 65, 62, 65]),    # Bb   Bb2 Bb2 F3 Bb2  D4 F4 D4 F4
           2: ([53, 53, 60, 53], [69, 72, 69, 72]),    # F/C  F3 F3 C4 F3     A4 C5 A4 C5
           3: ([52, 52, 55, 52], [61, 64, 61, 64])}    # A7   E3 E3 G3 E3     C#4 E4 C#4 E4
def pulse_vel(b): return 50 if b < 8 else 60 if b < 12 else 66 if b < 16 else 74 if b < 20 else 82
VPULSE, UPULSE = [], []
for b in range(4, N):
    lo, hi = PULSE_V[F.CH[b]]
    for k in range(8):
        t0 = b * BLK + k
        if t0 >= CUT: continue
        acc = 12 if k % 4 == 0 else 0
        VPULSE.append({"pitch": lo[k % 4], "start": t0, "end": t0 + 0.85, "vel": pulse_vel(b) + acc})
        UPULSE.append({"pitch": hi[k % 4], "start": t0, "end": t0 + 0.85, "vel": pulse_vel(b) - 4 + acc})

# cello: enters block 5, rising; drives eighths from pass E
def cello_vel(b): return 48 + 5 * (b - 4) if b < 8 else (62 if b < 12 else 66 if b < 16 else 72)
# Passes B-D: the cello plays quarter notes, in step with the viola and violin lines, so the three are one
# string trio ("딴 딴 딴 딴"). In the driving passes it goes to eighths.
def cello_quarters(b):
    root, alt = F.OST[F.CH[b]]
    return [{"pitch": alt if k % 4 == 3 else root, "start": b * BLK + k, "end": b * BLK + k + 0.85,
             "vel": cello_vel(b) + (12 if k % 4 == 0 else 0)} for k in range(8)]
CELLO = sum([cello_quarters(b) if b < 16 else F.cello_ostinato([b], cello_vel(b), drive=True) for b in range(4, N)], [])
CELLO = [n for n in CELLO if n["start"] < CUT]

# low French horns: enter block 6, breath swell at the end of each pass
LH = [n for b in range(5, N) for n in F.sustained(F.LHORN[F.CH[b]], b, 64)]
LH = stop_at_cut(LH)
LHCC = []
for b in range(5, N):
    swell_end = (b % 4 == 3)                                   # last block of each pass: a real swell
    lo = 60 + 2 * b; hi = 90 + 2 * b
    if swell_end: lo, hi = 56 + b, 122
    LHCC += F.ramp(b * BLK, (b + 1) * BLK - 0.01, min(lo, 110), min(hi, 127), curve=2.0 if swell_end else 1.6)

# trombones: enter block 9 and get louder each pass; they follow the chord of each block
TB = []
for b in range(8, N):
    if b >= N - 1: continue
    v = 60 if b < 12 else 68 if b < 16 else 76
    for p in F.TBONE_V[F.CH[b]]:
        TB.append({"pitch": p, "start": b * BLK + 0.02, "end": (b + 1) * BLK - 0.12, "vel": v})
TB = [n for n in TB if n["start"] < CUT]
# final hold for trombones (A2 F3 again)
TB += [{"pitch": p, "start": CUT, "end": HOLD_END - 0.1, "vel": 80} for p in (45, 53)]
TBCC = []
for b in range(8, N):
    swell_end = (b % 4 == 3)
    lo, hi = (70, 118) if swell_end else (72 + (b - 8) * 2, 98 + (b - 8) * 2)
    TBCC += F.ramp(b * BLK, (b + 1) * BLK - 0.01, min(lo, 110), min(hi, 127), curve=2.0 if swell_end else 1.6)
TBCC += [(CUT, 127), (HOLD_END - 4, 127), (HOLD_END, 100)]

# timpani: downbeat + beat 5 from block 7, a fill into each pass, the rock figure in pass E and b21
TIMP, TAIKO = [], []
def tp(pitch, t, dur, vel): TIMP.append({"pitch": pitch, "start": t, "end": t + dur, "vel": int(np.clip(vel, 1, 127))})
for b in range(6, N):
    if b >= 16: continue                                        # rock bars take over
    root = {0: 50, 1: 46, 2: 48, 3: 45}[F.CH[b]]
    base = 60 + (b - 6) * 2
    tp(root, b * BLK, 1.5, base + 6); tp(root, b * BLK + 4, 1.2, base - 8)
    if b % 4 == 3:                                              # the fill into the next pass (rising, short)
        for t, v in [(6.0, base), (6.5, base + 8), (7.0, base + 16)]:
            tp(45, b * BLK + t, 0.4, v)
for b in range(16, N):
    t, k = F.rock_bar(b)
    if b == N - 1:                                              # last block: first half only, then the build
        t = [n for n in t if n["start"] < CUT - 2]; k = [n for n in k if n["start"] < CUT - 2]
    TIMP += t; TAIKO += k
# no timpani roll: it is the same machine-gun texture as the tremolo that was taken out.
# Two rising hits, then the last chord.
tp(38, CUT - 2, 0.6, 96); tp(38, CUT - 1, 0.6, 108)
TIMP += [{"pitch": 38, "start": CUT, "end": CUT + 4.0, "vel": 127}]
TAIKO += [{"pitch": 45, "start": CUT, "end": CUT + 3.0, "vel": 122}]               # A2, the fifth - not G
REV = [{"pitch": 60, "start": (N - 1) * BLK, "end": CUT, "vel": 100}]
REVCC = F.ramp((N - 1) * BLK, CUT, 34, 127, curve=1.5)

def T(name, mn, prog, notes, pan, gain, send, who, enters, cc=None):
    return dict(name=name, midi_name=mn, program=prog, notes=notes, cc11=cc or [], pan=pan,
                gain_db=gain, send_db=send, who=who, enters=enters)
TRACKS = [
    T("제1바이올린 — 당신 멜로디", "Violin I (yours)", 40, V1, -0.38, 0.0, -10.0, "당신", 1),
    T("비올라 — 당신 멜로디 한 옥타브 아래", "Viola melody -8ve (yours)", 41, V2, -0.10, -5.0, -8.0, "당신(옥타브 아래)", 1),
    T("호른 — 당신 화음", "Horns chords (yours)", 60, HORN, -0.30, -7.0, -4.0, "당신(교정)", 1),
    T("콘트라베이스 — 당신 베이스", "Contrabass (yours)", 43, BASS, 0.40, -2.0, -9.0, "당신", 1),
    T("콘트라베이스 — 저음 루트", "Contrabass root", 43, ROOT, 0.30, -4.0, -9.0, "당신(교정)", 1),
    T("합창", "Choir", 52, CHOIR, 0.0, -9.0, -2.0, "제가 만든 반주", 1),
    T("글로켄슈필", "Glockenspiel", 9, GLOCK, 0.55, -5.0, -3.0, "제가 만든 반주", 1),
    T("저음 현악 베드", "Low strings bed", 48, PADN, -0.20, -3.0, -5.0, "당신 화음에서 파생", 1, PADCC),
    T("첼로 오스티나토", "Cello ostinato", 42, CELLO, 0.35, 0.0, -8.0, "당신 화음에서 파생", 5),
    T("비올라 펄스 (딴딴딴딴)", "Viola pulse", 41, VPULSE, -0.25, 0.0, -6.0, "당신 화음에서 파생", 5),
    T("바이올린 펄스 (딴딴딴딴)", "Violin pulse", 40, UPULSE, 0.15, 0.0, -6.0, "당신 화음에서 파생", 5),
    T("프렌치 호른 (저음)", "French horns low", 60, LH, -0.45, 0.0, -4.0, "당신 화음에서 파생", 6, LHCC),
    T("트롬본", "Trombones", 57, TB, 0.45, 0.0, -4.0, "당신 화음에서 파생", 9, TBCC),
    T("팀파니", "Timpani", 47, TIMP, 0.05, 0.0, -4.0, "제가 만든 반주", 7),
    T("타이코", "Taiko", 116, TAIKO, 0.0, 0.0, -5.0, "제가 만든 반주", 17),
    T("리버스 심벌 스웰", "Reverse cymbal swell", 119, REV, 0.0, 6.0, -2.0, "제가 만든 반주", N, REVCC),
    T("바이올린 옥타브", "Violins +8ve", 40, OCT, -0.25, -7.0, -8.0, "당신 음에서 파생", 17),
]
# fader targets: dB RMS over the beats where the layer is meant to carry (measured, not guessed)
AUTO = {
    "Violin I (yours)": (-28.0, 0, 32), "Viola melody -8ve (yours)": (-31.0, 0, 32),
    "Horns chords (yours)": (-35.0, 0, 32), "Contrabass (yours)": (-24.5, 0, 32),
    "Contrabass root": (-35.0, 0, 32), "Choir": (-41.0, 0, 32), "Glockenspiel": (-50.0, 0, 32),
    "Low strings bed": (-35.0, 0, 32), "Cello ostinato": (-33.0, 32, 64), "Viola pulse": (-33.0, 32, 64), "Violin pulse": (-35.0, 32, 64),
    "French horns low": (-29.0, 40, 64), "Timpani": (-41.0, 48, 64),
    "Trombones": (-31.0, 64, 96), "Taiko": (-31.0, 128, 160),
    "Reverse cymbal swell": (-34.0, (N - 1) * BLK, CUT), "Violins +8ve": (-33.0, 128, 160),
}

if MODE == "cello":
    # The cello leads the melody (their second take, an octave down, staccato); the violin keeps the original octave but steps back.
    for t in TRACKS:
        if t["midi_name"] == "Viola melody -8ve (yours)":
            t.update(name="첼로 — 당신 멜로디 한 옥타브 아래", midi_name="Cello melody -8ve (yours)", program=42, pan=-0.15, send_db=-8.0)
    AUTO.pop("Viola melody -8ve (yours)", None)
    AUTO["Cello melody -8ve (yours)"] = (-27.0, 0, 32)
    AUTO["Violin I (yours)"] = (-34.0, 0, 32)

# ---- tuning: General MIDI patches are not all at concert pitch, and the error depends on the note
# (the solo-violin patch is 29 cents flat on A5 and 3 cents sharp on D5; the timpani is 40 sharp above D2).
# A flat A5 against an in-tune A3 horn is heard as a dissonance in a chord whose written notes are all
# right. Each track is split into voices so every note can carry its own pitch correction.
PERC = {"Taiko", "Reverse cymbal swell"}                 # not pitched enough for a bend to mean anything
EXTRA = {}
NMS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
def _nn(p): return f"{NMS[p % 12]}{p // 12 - 1}"

def split_voices(notes):
    """k-th lowest note of each chord goes to voice k, so each voice is one line."""
    voices, cluster, last = {}, [], None
    for n in sorted(notes, key=lambda q: (round(q["start"], 2), q["pitch"])):
        if last is not None and abs(n["start"] - last) > 0.02:
            for k, m in enumerate(cluster): voices.setdefault(k, []).append(m)
            cluster = []
        cluster.append(n); last = n["start"]
    for k, m in enumerate(cluster): voices.setdefault(k, []).append(m)
    return [voices[k] for k in sorted(voices)]

CAL = {}
for prog in sorted({t["program"] for t in TRACKS if t["midi_name"] not in PERC}):
    pitches = [n["pitch"] for t in TRACKS if t["program"] == prog and t["midi_name"] not in PERC for n in t["notes"]]
    CAL[prog] = TU.calibrate(prog, pitches, TMP)
TUNING = {}
for t in TRACKS:
    t["voices"], t["vbends"] = split_voices(t["notes"]), []
    if t["midi_name"] in PERC:
        t["vbends"] = [[] for _ in t["voices"]]; continue
    extra = EXTRA.get(t["midi_name"], 0.0); cal = CAL[t["program"]]
    for v in t["voices"]:
        bends = [(n["start"] - 0.02, -cal.get(n["pitch"], 0.0) + extra) for n in v]
        t["vbends"].append(bends if any(abs(c) >= 5 for _, c in bends) else [])
    TUNING[t["midi_name"]] = {_nn(p): round(cal[p]) for p in sorted({n["pitch"] for n in t["notes"]})}

def write_midi(path, tracks, bend=False):
    pm = pretty_midi.PrettyMIDI(initial_tempo=F.TEMPO)
    for t in tracks:
        inst = pretty_midi.Instrument(program=int(t["program"]), is_drum=False, name=t["midi_name"])
        for n in t["notes"]:
            inst.notes.append(pretty_midi.Note(int(np.clip(n["vel"], 1, 127)), int(n["pitch"]),
                                               F.sec(n["start"]), F.sec(max(n["end"], n["start"] + 0.05))))
        for b, v in t["cc11"]:
            inst.control_changes.append(pretty_midi.ControlChange(11, int(np.clip(v, 0, 127)), F.sec(b)))
        if bend:
            for b, c in t.get("bends", []):
                inst.pitch_bends.append(pretty_midi.PitchBend(TU.bend_value(c), max(0.0, F.sec(b))))
        pm.instruments.append(inst)
    pm.write(path)

def _render(t, tag, tail_s):
    mid, wav = f"{TMP}/{tag}.mid", f"{TMP}/{tag}.wav"
    write_midi(mid, [t], bend=True)
    r = subprocess.run([F.FLUID, "-ni", "-g", "0.7", "-F", wav, "-r", "44100", "-R", "0", "-C", "0", F.SF2, mid],
                       capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(r.stderr[:200])
    x, sr = sf.read(wav, dtype="float64", always_2d=True)
    return np.concatenate([x.mean(axis=1), np.zeros(int(tail_s * sr))])

def stem(t, i, tail_s=3.8):
    parts = []
    for k, v in enumerate(t["voices"]):
        tv = {**t, "notes": v, "cc11": t["cc11"] or [(0.0, 127)], "bends": t["vbends"][k]}
        parts.append(_render(tv, f"s{i}_{k}", tail_s))
    out = np.zeros(max(len(p) for p in parts))
    for p in parts: out[: len(p)] += p
    return out

if __name__ == "__main__":
    IR = O.hall_ir()
    report = {"tempo": F.TEMPO, "blocks": N, "cut_beat": CUT, "hold_end_beat": HOLD_END}
    stems = []
    for i, t in enumerate(TRACKS):
        a = stem(t, i); tgt, b0, b1 = AUTO[t["midi_name"]]
        seg = a[int(F.sec(b0) * 44100): int(F.sec(b1) * 44100)]
        meas = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12)
        t["gain_db"] = float(np.clip(tgt - meas, -30.0, 25.0)); stems.append({**t, "audio": a})
    y = O.mix(stems, IR, wet_bus_db=-6.0)
    END_S = F.sec(HOLD_END) + TAIL
    y = y[: int(END_S * 44100)].copy(); fade = int(1.2 * 44100)
    y[-fade:] *= (0.5 * (1 + np.cos(np.linspace(0, np.pi, fade))))[:, None]
    n = len(y)
    def band(x, a, b):
        sos = _sg.butter(4, [a, b], btype="bandpass", fs=44100, output="sos")
        return 20 * np.log10(np.sqrt(np.mean(_sg.sosfiltfilt(sos, x.mean(axis=1)) ** 2)) + 1e-12)
    def without(names): return O.mix([q for q in stems if q["midi_name"] not in names], IR, wet_bus_db=-6.0)[:n]
    full = band(y, 95, 190)
    report["bass_worth_db"] = {"yours_only": round(float(full - band(without({"Contrabass (yours)"}), 95, 190)), 2),
                               "yours_plus_root": round(float(full - band(without({"Contrabass (yours)", "Contrabass root"}), 95, 190)), 2)}
    y = y / max(1.0, np.max(np.abs(y)) / 0.89)
    raw = f"{OUT}/p6_raw.wav"; sf.write(raw, y, 44100, subtype="PCM_24")
    rep = M.master(raw, f"{OUT}/p6_master.wav", target_lufs=-14.0, air_db=2.5, air_hz=7000.0)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{OUT}/p6_master.wav", "-ac", "2", "-b:a", "128k",
                    f"{OUT}/p6.mp3"], check=True)
    os.remove(raw)
    write_midi(f"{OUT}/p6_FULL_140bpm.mid", TRACKS)
    write_midi(f"{OUT}/p6_ADD_ONLY_140bpm.mid", [t for t in TRACKS if t["who"] not in ("당신", "당신(교정)")])
    mm, sr = sf.read(f"{OUT}/p6_master.wav", always_2d=True); mm = mm.mean(axis=1)
    bl = F.sec(BLK)
    report["block_rms_db"] = [round(float(20 * np.log10(np.sqrt(np.mean(mm[int(b*bl*sr):int(min((b+1)*bl, len(mm)/sr)*sr)] ** 2)) + 1e-12)), 1)
                              for b in range(N + 1) if int(b * bl * sr) < len(mm)]
    report["tuning_measured_cents"] = TUNING
    report["master"] = rep; report["length_sec"] = round(n / 44100, 2)
    report["tracks"] = [{"name": t["name"], "midi_name": t["midi_name"], "who": t["who"], "enters_block": t["enters"],
                         "notes": len(t["notes"]), "gain_db": round(t["gain_db"], 1)} for t in TRACKS]
    shutil.rmtree(TMP, ignore_errors=True)
    json.dump(report, open(f"{OUT}/report.json", "w"), ensure_ascii=False, indent=1)
    print(f"{report['length_sec']} s, master {rep['before']['lufs']:+.2f} -> {rep['after']['lufs']:+.2f} LUFS, "
          f"TP {rep['after']['true_peak']:+.2f}, clipped {rep['after']['clipped']}")
    print("block RMS dB:", report["block_rms_db"])
    print("bass worth:", report["bass_worth_db"])
    for t in report["tracks"]: print(f"  b{t['enters_block']:>2}+ {t['name']:<26}{t['notes']:>4} notes  {t['gain_db']:+5.1f} dB  [{t['who']}]")
