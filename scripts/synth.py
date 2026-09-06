"""Tiny deterministic synthesiser used to *audition* proposals and to render the new parts.
Sounds are generated from scratch (no samples, no third-party sound library) so the whole
pipeline stays free and reproducible. Every render is also written as a MIDI file so the
same notes can be re-rendered later with better instruments in REAPER or any DAW."""
from __future__ import annotations
import numpy as np
from scipy import signal
import pretty_midi

GM_DRUM = {"kick": 36, "snare": 38, "clap": 39, "hat": 42, "ohat": 46, "shaker": 70, "rim": 37, "tom": 45, "crash": 49}


def _env(n, a, d, s, r, sr):
    a = max(1, int(a * sr)); d = max(1, int(d * sr)); r = max(1, int(r * sr))
    sus = max(0, n - a - d - r)
    e = np.concatenate([np.linspace(0, 1, a), np.linspace(1, s, d), np.full(sus, s), np.linspace(s, 0, r)])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))


def kick(sr, vel=1.0):
    n = int(0.45 * sr); t = np.arange(n) / sr
    f = 150 * np.exp(-t * 22) + 45
    ph = 2 * np.pi * np.cumsum(f) / sr
    body = np.sin(ph) * np.exp(-t * 7)
    click = np.random.default_rng(1).standard_normal(n) * np.exp(-t * 400) * 0.4
    return (body + click) * vel * 0.95


def snare(sr, vel=1.0):
    n = int(0.28 * sr); t = np.arange(n) / sr
    rng = np.random.default_rng(2)
    noise = rng.standard_normal(n)
    sos = signal.butter(2, [1500, 9000], btype="band", fs=sr, output="sos")
    noise = signal.sosfilt(sos, noise) * np.exp(-t * 18)
    tone = (np.sin(2 * np.pi * 190 * t) + 0.5 * np.sin(2 * np.pi * 330 * t)) * np.exp(-t * 30)
    return (noise * 0.8 + tone * 0.6) * vel * 0.8


def clap(sr, vel=1.0):
    n = int(0.25 * sr); t = np.arange(n) / sr
    rng = np.random.default_rng(3)
    sos = signal.butter(2, [900, 6000], btype="band", fs=sr, output="sos")
    out = np.zeros(n)
    for k, off in enumerate([0, 0.011, 0.022, 0.033]):
        o = int(off * sr)
        burst = signal.sosfilt(sos, rng.standard_normal(n - o)) * np.exp(-(t[: n - o]) * (60 if k < 3 else 14))
        out[o:] += burst
    return out * vel * 0.5


def hat(sr, vel=1.0, open_=False):
    n = int((0.35 if open_ else 0.06) * sr); t = np.arange(n) / sr
    rng = np.random.default_rng(4)
    sos = signal.butter(4, 7000, btype="high", fs=sr, output="sos")
    return signal.sosfilt(sos, rng.standard_normal(n)) * np.exp(-t * (9 if open_ else 70)) * vel * 0.35


def shaker(sr, vel=1.0):
    n = int(0.09 * sr); t = np.arange(n) / sr
    rng = np.random.default_rng(5)
    sos = signal.butter(4, [5000, 12000], btype="band", fs=sr, output="sos")
    e = np.minimum(t * 200, 1) * np.exp(-t * 45)
    return signal.sosfilt(sos, rng.standard_normal(n)) * e * vel * 0.3


def rim(sr, vel=1.0):
    n = int(0.05 * sr); t = np.arange(n) / sr
    return np.sin(2 * np.pi * 800 * t) * np.exp(-t * 120) * vel * 0.5


def crash(sr, vel=1.0):
    n = int(1.6 * sr); t = np.arange(n) / sr
    rng = np.random.default_rng(6)
    sos = signal.butter(2, 4000, btype="high", fs=sr, output="sos")
    return signal.sosfilt(sos, rng.standard_normal(n)) * np.exp(-t * 2.2) * vel * 0.3


DRUM_SOUNDS = {"kick": kick, "snare": snare, "clap": clap, "hat": hat, "shaker": shaker, "rim": rim, "crash": crash}


def render_drums(events, sr, length_s, width=0.15):
    """events: list of dict(time, inst, vel). Returns stereo (n,2)."""
    n = int(length_s * sr) + sr
    out = np.zeros((n, 2))
    cache = {}
    pan = {"kick": 0.0, "snare": 0.0, "clap": 0.1, "hat": -0.35, "ohat": -0.35, "shaker": 0.4, "rim": 0.2, "crash": -0.2}
    for ev in events:
        inst = ev["inst"]; vel = float(ev.get("vel", 1.0))
        key = (inst, round(vel, 2))
        if key not in cache:
            if inst == "ohat":
                cache[key] = hat(sr, vel, open_=True)
            else:
                cache[key] = DRUM_SOUNDS[inst](sr, vel)
        s = cache[key]
        i = int(ev["time"] * sr)
        if i < 0 or i >= n:
            continue
        seg = s[: n - i]
        p = pan.get(inst, 0.0) * width / 0.15
        out[i:i + len(seg), 0] += seg * (1 - max(p, 0))
        out[i:i + len(seg), 1] += seg * (1 + min(p, 0))
    return out


def bass_note(freq, dur, sr, vel=1.0, style="warm"):
    n = int(dur * sr); t = np.arange(n) / sr
    saw = 2 * (t * freq - np.floor(t * freq + 0.5))
    sub = np.sin(2 * np.pi * freq * t)
    if style == "warm":
        raw = 0.45 * saw + 0.75 * sub
        cutoff = 350 + 900 * vel
    elif style == "pluck":
        raw = 0.7 * saw + 0.5 * sub
        cutoff = 600 + 2200 * vel
    else:  # "round"
        raw = 0.25 * saw + 0.9 * sub
        cutoff = 300 + 500 * vel
    env = _env(n, 0.004, 0.12, 0.75 if style != "pluck" else 0.35, min(0.06, dur * 0.3), sr)
    sos = signal.butter(2, min(cutoff, sr / 2 - 100), btype="low", fs=sr, output="sos")
    y = signal.sosfilt(sos, raw) * env * vel * 0.6
    return np.tanh(y * 1.5) * 0.8


def pad_chord(freqs, dur, sr, vel=0.5, attack=0.8, release=1.2, detune=0.4):
    n = int(dur * sr); t = np.arange(n) / sr
    out = np.zeros((n, 2))
    for k, f in enumerate(freqs):
        for j, (dt, pan) in enumerate([(-detune, -0.6), (0, 0), (detune, 0.6)]):
            ff = f * (2 ** (dt / 1200))
            saw = 2 * (t * ff - np.floor(t * ff + 0.5))
            lfo = 1 + 0.003 * np.sin(2 * np.pi * (0.13 + 0.05 * j) * t + k)
            saw = 2 * (t * ff * lfo - np.floor(t * ff * lfo + 0.5))
            out[:, 0] += saw * (1 - max(pan, 0)) / 3
            out[:, 1] += saw * (1 + min(pan, 0)) / 3
    env = _env(n, attack, 0.5, 0.85, release, sr)
    sos = signal.butter(2, 1800, btype="low", fs=sr, output="sos")
    out = signal.sosfilt(sos, out, axis=0) * env[:, None] * vel * 0.25 / max(1, len(freqs)) ** 0.5
    return out


def riser(dur, sr, vel=0.5):
    n = int(dur * sr); t = np.arange(n) / sr
    rng = np.random.default_rng(7)
    noise = rng.standard_normal((n, 2))
    fc = 300 * (12000 / 300) ** (t / dur)
    out = np.zeros((n, 2))
    blk = 2048
    for i in range(0, n, blk):
        c = float(np.clip(fc[min(i, n - 1)], 200, sr / 2 - 200))
        sos = signal.butter(2, [c * 0.5, c], btype="band", fs=sr, output="sos")
        out[i:i + blk] = signal.sosfilt(sos, noise[i:i + blk], axis=0)
    env = (t / dur) ** 2.2
    return out * env[:, None] * vel * 0.35


def midi_to_freq(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def write_drum_midi(path, events, tempo):
    pm = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    inst = pretty_midi.Instrument(program=0, is_drum=True, name="New drums")
    for ev in events:
        pitch = GM_DRUM.get(ev["inst"], 38)
        inst.notes.append(pretty_midi.Note(velocity=int(np.clip(ev.get("vel", 0.9) * 127, 1, 127)),
                                           pitch=pitch, start=float(ev["time"]), end=float(ev["time"]) + 0.1))
    pm.instruments.append(inst)
    pm.write(path)


def write_note_midi(path, notes, tempo, program=33, name="New bass"):
    pm = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    inst = pretty_midi.Instrument(program=program, name=name)
    for nt in notes:
        inst.notes.append(pretty_midi.Note(velocity=int(np.clip(nt.get("vel", 0.9) * 127, 1, 127)),
                                           pitch=int(nt["midi"]), start=float(nt["start"]), end=float(nt["end"])))
    pm.instruments.append(inst)
    pm.write(path)


def render_notes(notes, sr, length_s, style="warm"):
    n = int(length_s * sr) + sr
    out = np.zeros(n)
    for nt in notes:
        i = int(nt["start"] * sr)
        if i < 0 or i >= n:
            continue
        d = max(0.05, nt["end"] - nt["start"])
        s = bass_note(midi_to_freq(nt["midi"]), d, sr, nt.get("vel", 0.9), style)
        seg = s[: n - i]
        if i >= 0 and len(seg):
            out[i:i + len(seg)] += seg
    return np.stack([out, out], axis=1)
