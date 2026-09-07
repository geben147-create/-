"""의존성 없는 numpy 신스 엔진 (미리듣기·후보 렌더용).

- 멜로디 악기: saw/square/tri/sine 오실레이터 + ADSR + 2차 LPF
- 드럼: 킥/스네어/클랩/하이햇/오픈햇/셰이커/톰/라이드 합성 (샘플 불필요)
- MIDI(pretty_midi) → 스테레오 float32 렌더

품질은 '후보 비교용'입니다. 최종 음색은 REAPER/VSTi 또는 fluidsynth+사운드폰트로 다시 렌더하세요.
"""
from __future__ import annotations

import math
import zlib
from dataclasses import dataclass, field

import numpy as np
from scipy import signal

GM_DRUMS = {
    36: "kick", 35: "kick", 38: "snare", 40: "snare", 39: "clap", 37: "rim",
    42: "hat_closed", 44: "hat_closed", 46: "hat_open", 70: "shaker", 82: "shaker",
    45: "tom_low", 41: "tom_low", 47: "tom_mid", 48: "tom_mid", 50: "tom_high",
    51: "ride", 49: "crash", 57: "crash", 56: "cowbell", 75: "clave",
}


@dataclass
class Preset:
    name: str
    oscs: list = field(default_factory=lambda: [("saw", 0.0, 1.0)])  # (kind, detune_cents, gain)
    sub: float = 0.0            # sub sine 1 octave below, gain
    attack: float = 0.01
    decay: float = 0.1
    sustain: float = 0.7
    release: float = 0.1
    cutoff: float = 2000.0      # Hz at velocity 1.0
    cutoff_vel: float = 0.6     # how much velocity opens filter
    q: float = 0.9
    vibrato_hz: float = 0.0
    vibrato_cents: float = 0.0
    vibrato_delay: float = 0.15
    width: float = 0.0          # 0 = mono center, 1 = wide (Haas + detune)
    gain: float = 0.5
    filter_env: float = 0.0     # extra cutoff (Hz) decaying with 'decay'


PRESETS = {
    "bass": Preset("bass", oscs=[("saw", 0.0, 0.8), ("square", 0.0, 0.3)], sub=0.6,
                   attack=0.004, decay=0.18, sustain=0.55, release=0.08, cutoff=900, cutoff_vel=0.8,
                   filter_env=900, gain=0.55),
    "bass_soft": Preset("bass_soft", oscs=[("tri", 0.0, 0.9)], sub=0.7, attack=0.008, decay=0.25,
                        sustain=0.6, release=0.12, cutoff=500, filter_env=300, gain=0.6),
    "pad": Preset("pad", oscs=[("saw", -8.0, 0.5), ("saw", 0.0, 0.5), ("saw", 8.0, 0.5)],
                  attack=0.45, decay=0.6, sustain=0.85, release=0.7, cutoff=1400, cutoff_vel=0.3,
                  width=0.8, gain=0.22),
    "pad_warm": Preset("pad_warm", oscs=[("tri", -5.0, 0.6), ("saw", 5.0, 0.35)], attack=0.6,
                       decay=0.8, sustain=0.9, release=0.9, cutoff=900, width=0.9, gain=0.24),
    "lead": Preset("lead", oscs=[("square", 0.0, 0.5), ("saw", 3.0, 0.5)], attack=0.012, decay=0.12,
                   sustain=0.7, release=0.16, cutoff=3200, vibrato_hz=5.4, vibrato_cents=14,
                   vibrato_delay=0.18, width=0.25, gain=0.32),
    "lead_soft": Preset("lead_soft", oscs=[("tri", 0.0, 0.7), ("sine", 0.0, 0.5)], attack=0.02,
                        decay=0.15, sustain=0.75, release=0.2, cutoff=2600, vibrato_hz=5.0,
                        vibrato_cents=10, width=0.2, gain=0.36),
    "pluck": Preset("pluck", oscs=[("tri", 0.0, 0.6), ("saw", 0.0, 0.5)], attack=0.002, decay=0.28,
                    sustain=0.0, release=0.12, cutoff=2600, filter_env=2500, width=0.35, gain=0.35),
    "keys": Preset("keys", oscs=[("sine", 0.0, 0.8), ("tri", 0.0, 0.35)], attack=0.004, decay=0.9,
                   sustain=0.25, release=0.25, cutoff=3500, filter_env=1500, width=0.5, gain=0.4),
    "voice_like": Preset("voice_like", oscs=[("saw", 0.0, 0.5), ("tri", -3.0, 0.5)], attack=0.03,
                         decay=0.2, sustain=0.8, release=0.18, cutoff=1800, cutoff_vel=0.4,
                         vibrato_hz=5.6, vibrato_cents=20, vibrato_delay=0.25, width=0.1, gain=0.4),
}


def midi_to_hz(m: float) -> float:
    return 440.0 * 2.0 ** ((m - 69.0) / 12.0)


def _osc(kind: str, freq: np.ndarray | float, n: int, sr: int, phase0: float = 0.0) -> np.ndarray:
    freq = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,))
    ph = (phase0 + np.cumsum(freq) / sr) % 1.0
    if kind == "sine":
        return np.sin(2 * np.pi * ph)
    if kind == "saw":
        return 2.0 * ph - 1.0
    if kind == "square":
        return np.where(ph < 0.5, 1.0, -1.0)
    if kind == "tri":
        return 4.0 * np.abs(ph - 0.5) - 1.0
    raise ValueError(kind)


def _adsr(n: int, sr: int, a: float, d: float, s: float, r: float, gate_n: int) -> np.ndarray:
    env = np.zeros(n)
    a_n = max(1, int(a * sr)); d_n = max(1, int(d * sr)); r_n = max(1, int(r * sr))
    gate_n = max(1, min(gate_n, n))
    t = np.arange(gate_n)
    seg = np.ones(gate_n) * s
    seg[:a_n] = np.linspace(0, 1, a_n)[:gate_n]
    if gate_n > a_n:
        dd = np.minimum(d_n, gate_n - a_n)
        seg[a_n:a_n + dd] = np.linspace(1, s, d_n)[:dd]
    env[:gate_n] = seg
    if n > gate_n:
        tail = min(r_n, n - gate_n)
        env[gate_n:gate_n + tail] = seg[-1] * np.linspace(1, 0, r_n)[:tail]
    return env


def _lpf(x: np.ndarray, cutoff: float, sr: int, q: float = 0.9) -> np.ndarray:
    cutoff = float(np.clip(cutoff, 40.0, sr * 0.45))
    sos = signal.butter(2, cutoff / (sr / 2), btype="low", output="sos")
    return signal.sosfilt(sos, x)


def render_note(preset: Preset, pitch: float, velocity: float, dur: float, sr: int, seed: int = 0):
    """returns stereo (2, n) array for one note incl. release tail."""
    vel = float(np.clip(velocity, 0.05, 1.0))
    n_gate = max(4, int(dur * sr))
    n = n_gate + int(preset.release * sr) + 64
    t = np.arange(n) / sr
    f0 = midi_to_hz(pitch)
    freq = np.full(n, f0)
    if preset.vibrato_hz > 0 and preset.vibrato_cents > 0:
        ramp = np.clip((t - preset.vibrato_delay) / 0.25, 0, 1)
        freq = f0 * 2 ** (preset.vibrato_cents / 1200 * ramp * np.sin(2 * np.pi * preset.vibrato_hz * t))
    rng = np.random.default_rng(seed)
    phases = [rng.random() for _ in preset.oscs]   # 채널마다 새로 뽑으면 width=0 프리셋도 좌우가 어긋나 모노에서 깎임
    chans = []
    for ch in range(2):
        x = np.zeros(n)
        for (kind, det, g), ph0 in zip(preset.oscs, phases):
            det_ch = det + (preset.width * 4.0 * (1 if ch else -1))
            x += g * _osc(kind, freq * 2 ** (det_ch / 1200), n, sr, phase0=ph0)
        if preset.sub > 0:
            x += preset.sub * _osc("sine", freq / 2, n, sr)
        env = _adsr(n, sr, preset.attack, preset.decay, preset.sustain, preset.release, n_gate)
        cutoff = preset.cutoff * (1 - preset.cutoff_vel + preset.cutoff_vel * vel)
        if preset.filter_env > 0:
            # simple 2-stage: bright start then darker
            n_half = max(8, int(preset.decay * sr))
            y1 = _lpf(x[:n_half], cutoff + preset.filter_env * vel, sr, preset.q)
            y2 = _lpf(x, cutoff, sr, preset.q)
            fade = np.linspace(1, 0, n_half)
            x = y2.copy()
            x[:n_half] = y1 * fade + y2[:n_half] * (1 - fade)
        else:
            x = _lpf(x, cutoff, sr, preset.q)
        x = x * env * vel * preset.gain
        chans.append(x)
    out = np.vstack(chans)
    if preset.width > 0:
        d = int(preset.width * 0.012 * sr)
        if d > 0:
            out[1] = np.concatenate([np.zeros(d), out[1][:-d]])
    return out.astype(np.float32)


# ---------- drums ----------

def _noise(n: int, rng) -> np.ndarray:
    return rng.standard_normal(n)


def _bpf(x: np.ndarray, lo: float, hi: float, sr: int) -> np.ndarray:
    lo = max(20.0, lo); hi = min(hi, sr * 0.48)
    sos = signal.butter(2, [lo / (sr / 2), hi / (sr / 2)], btype="band", output="sos")
    return signal.sosfilt(sos, x)


def _hpf(x: np.ndarray, fc: float, sr: int) -> np.ndarray:
    sos = signal.butter(2, min(fc, sr * 0.48) / (sr / 2), btype="high", output="sos")
    return signal.sosfilt(sos, x)


def _kind_offset(kind: str) -> int:
    """프로세스마다 달라지는 hash() 대신 고정된 값. (PEP 456 이후 str hash 는 실행마다 다름)"""
    return zlib.crc32(kind.encode("utf-8")) % 1000


def drum_hit(kind: str, sr: int, velocity: float = 1.0, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed + _kind_offset(kind))
    v = float(np.clip(velocity, 0.05, 1.0))
    if kind == "kick":
        n = int(0.42 * sr); t = np.arange(n) / sr
        f = 42 + 130 * np.exp(-t / 0.045)
        ph = 2 * np.pi * np.cumsum(f) / sr
        body = np.sin(ph) * np.exp(-t / 0.20)
        click = _hpf(_noise(n, rng), 2500, sr) * np.exp(-t / 0.004) * 0.5
        x = (body * 1.0 + click) * (0.6 + 0.4 * v)
        x = np.tanh(x * 1.6)
        return (x * 0.9).astype(np.float32)
    if kind == "snare":
        n = int(0.28 * sr); t = np.arange(n) / sr
        tone = (np.sin(2 * np.pi * 185 * t) + 0.5 * np.sin(2 * np.pi * 330 * t)) * np.exp(-t / 0.07)
        noise = _bpf(_noise(n, rng), 900, 9000, sr) * np.exp(-t / 0.12)
        x = (0.55 * tone + 0.9 * noise) * (0.5 + 0.5 * v)
        return (np.tanh(x * 1.3) * 0.7).astype(np.float32)
    if kind == "rim":
        n = int(0.08 * sr); t = np.arange(n) / sr
        x = (np.sin(2 * np.pi * 800 * t) * np.exp(-t / 0.01) + _bpf(_noise(n, rng), 2000, 8000, sr) * np.exp(-t / 0.02)) * v
        return (x * 0.5).astype(np.float32)
    if kind == "clap":
        n = int(0.32 * sr); t = np.arange(n) / sr
        x = np.zeros(n)
        for k, off in enumerate([0.0, 0.011, 0.021, 0.032]):
            o = int(off * sr)
            burst = _bpf(_noise(n - o, rng), 1100, 4500, sr) * np.exp(-np.arange(n - o) / sr / (0.012 if k < 3 else 0.11))
            x[o:] += burst
        return (x * 0.45 * (0.5 + 0.5 * v)).astype(np.float32)
    if kind in ("hat_closed", "hat_open"):
        dur = 0.055 if kind == "hat_closed" else 0.32
        n = int((dur + 0.05) * sr); t = np.arange(n) / sr
        metal = sum(np.sign(np.sin(2 * np.pi * f * t)) for f in (3180, 4790, 6410, 8123, 9560)) / 5
        x = _hpf(_noise(n, rng) * 0.8 + metal * 0.3, 6500, sr) * np.exp(-t / (dur / 3))
        return (x * 0.28 * (0.4 + 0.6 * v)).astype(np.float32)
    if kind == "shaker":
        n = int(0.09 * sr); t = np.arange(n) / sr
        env = np.exp(-t / 0.025) * (1 - np.exp(-t / 0.004))
        x = _bpf(_noise(n, rng), 3800, 10000, sr) * env
        return (x * 0.22 * (0.4 + 0.6 * v)).astype(np.float32)
    if kind in ("tom_low", "tom_mid", "tom_high"):
        f0 = {"tom_low": 95, "tom_mid": 140, "tom_high": 190}[kind]
        n = int(0.4 * sr); t = np.arange(n) / sr
        f = f0 * (1 + 0.6 * np.exp(-t / 0.03))
        x = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t / 0.16) + 0.2 * _bpf(_noise(n, rng), 500, 3000, sr) * np.exp(-t / 0.02)
        return (np.tanh(x * 1.2) * 0.6 * (0.5 + 0.5 * v)).astype(np.float32)
    if kind in ("ride", "crash"):
        dur = 0.9 if kind == "ride" else 1.6
        n = int(dur * sr); t = np.arange(n) / sr
        metal = sum(np.sin(2 * np.pi * f * t) for f in (2100, 3300, 5200, 7100, 9900)) / 5
        x = _hpf(_noise(n, rng) * 0.7 + metal * 0.5, 3000, sr) * np.exp(-t / (dur / 3))
        return (x * (0.18 if kind == "ride" else 0.3) * (0.4 + 0.6 * v)).astype(np.float32)
    if kind in ("cowbell", "clave"):
        n = int(0.15 * sr); t = np.arange(n) / sr
        x = (np.sign(np.sin(2 * np.pi * 800 * t)) + np.sign(np.sin(2 * np.pi * 540 * t))) * np.exp(-t / 0.04)
        return (x * 0.2 * v).astype(np.float32)
    # fallback: short noise tick
    n = int(0.05 * sr); t = np.arange(n) / sr
    return (_hpf(_noise(n, rng), 4000, sr) * np.exp(-t / 0.01) * 0.2 * v).astype(np.float32)


_DRUM_CACHE: dict = {}


def drum_sample(kind: str, sr: int, velocity: float) -> np.ndarray:
    vb = int(round(velocity * 8))  # 8 velocity buckets
    key = (kind, sr, vb)
    if key not in _DRUM_CACHE:
        _DRUM_CACHE[key] = drum_hit(kind, sr, velocity=vb / 8.0, seed=vb)
    return _DRUM_CACHE[key]


# ---------- MIDI rendering ----------

def render_events(events: list[dict], sr: int, total_sec: float | None = None, preset: str | Preset = "lead",
                  drums: bool = False, pan: float = 0.0) -> np.ndarray:
    """events: [{start, end, pitch, velocity(0-127 or 0-1)}]. returns stereo (2, n)."""
    if not events:
        return np.zeros((2, int((total_sec or 1.0) * sr)), dtype=np.float32)
    if total_sec is None:
        total_sec = max(e["end"] for e in events) + 1.5
    n_total = int(total_sec * sr) + int(2.0 * sr)
    out = np.zeros((2, n_total), dtype=np.float32)
    pr = PRESETS[preset] if isinstance(preset, str) else preset
    for i, e in enumerate(events):
        vel = e.get("velocity", 100)
        vel = vel / 127.0 if vel > 1.0 else vel
        start = int(e["start"] * sr)
        if start >= n_total:
            continue
        head = 0
        if start < 0:            # 미리듣기 오프셋 등으로 음이 0초 앞에서 시작하는 경우: 앞부분을 잘라낸다
            head = -start
            start = 0
        if drums:
            kind = GM_DRUMS.get(int(e["pitch"]), "tick")
            smp = drum_sample(kind, sr, vel)[head:]
            m = max(0, min(len(smp), n_total - start))
            if m:
                out[0, start:start + m] += smp[:m]
                out[1, start:start + m] += smp[:m]
        else:
            dur = max(0.03, e["end"] - e["start"])
            smp = render_note(pr, e["pitch"], vel, dur, sr, seed=i)[:, head:]
            m = max(0, min(smp.shape[1], n_total - start))
            if m:
                out[:, start:start + m] += smp[:, :m]
    if pan:
        # 표준 등파워 팬 (센터에서 -3 dB). 1.414 로 정규화하면 옆으로 보낸 소리가 오히려 커집니다
        l = math.cos((pan + 1) * math.pi / 4); r = math.sin((pan + 1) * math.pi / 4)
        out[0] *= l; out[1] *= r
    return out[:, : int(total_sec * sr)]


def render_pretty_midi(pm, sr: int, total_sec: float | None = None, preset_map: dict | None = None) -> np.ndarray:
    """render each instrument; preset chosen by instrument name keyword, drums by is_drum."""
    preset_map = preset_map or {}
    if total_sec is None:
        total_sec = max([pm.get_end_time(), 1.0]) + 1.0
    mix = np.zeros((2, int(total_sec * sr)), dtype=np.float32)
    for inst in pm.instruments:
        events = [{"start": n.start, "end": n.end, "pitch": n.pitch, "velocity": n.velocity} for n in inst.notes]
        if not events:
            continue
        name = (inst.name or "").lower()
        if inst.is_drum:
            part = render_events(events, sr, total_sec, drums=True)
        else:
            preset = preset_map.get(inst.name) or next((v for k, v in {
                "bass": "bass", "pad": "pad", "lead": "lead", "melody": "lead", "pluck": "pluck",
                "keys": "keys", "piano": "keys", "voice": "voice_like", "vocal": "voice_like", "chord": "pad",
            }.items() if k in name), "keys")
            part = render_events(events, sr, total_sec, preset=preset)
        m = min(part.shape[1], mix.shape[1])
        mix[:, :m] += part[:, :m]
    return mix


def soft_clip(x: np.ndarray, drive: float = 1.0) -> np.ndarray:
    return np.tanh(x * drive) / np.tanh(drive)
