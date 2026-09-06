"""04 variants — 드럼 / 베이스 / 코드 / 브리지 / 구조 A·B·C 후보 생성.

원칙:
  * 여기서 나오는 것은 전부 '후보'입니다. 자동 확정하지 않습니다.
  * 시드 고정 → 같은 입력이면 같은 결과 (재현 가능, 증빙에 유리).
  * 사람이 고른 뒤 노트를 직접 고치는 것을 전제로 설계했습니다
    (human_decisions.json 의 note_edits).
"""
from __future__ import annotations

import numpy as np

from .common import pc_name

# ---------- scales ----------
NAT_MINOR = [0, 2, 3, 5, 7, 8, 10]
HARM_MINOR = [0, 2, 3, 5, 7, 8, 11]
DORIAN = [0, 2, 3, 5, 7, 9, 10]
MAJOR = [0, 2, 4, 5, 7, 9, 11]
PENT_MINOR = [0, 3, 5, 7, 10]
PENT_MAJOR = [0, 2, 4, 7, 9]

DRUM = {"kick": 36, "snare": 38, "clap": 39, "rim": 37, "hat": 42, "ohat": 46,
        "shaker": 70, "tom_l": 45, "tom_m": 47, "tom_h": 50, "ride": 51, "crash": 49}


def _rng(seed: int):
    return np.random.default_rng(seed)


def bar_grid(bar_start: float, bar_end: float, steps: int = 16) -> list[float]:
    return [bar_start + (bar_end - bar_start) * i / steps for i in range(steps)]


# ---------- drums ----------
DRUM_PATTERNS = {
    "A_straight": {
        "label_ko": "A · 정박 팝/발라드 (킥 1·3, 스네어 2·4, 8비트 하이햇)",
        "kick": [0, 8], "snare": [4, 12], "hat": list(range(0, 16, 2)), "shaker": [],
        "ghost": [7, 15], "swing": 0.0, "energy": 0.8,
    },
    "B_halftime": {
        "label_ko": "B · 하프타임 (스네어 3박, 싱코페이션 킥, 16비트 셰이커)",
        "kick": [0, 6, 10], "snare": [8], "hat": [0, 4, 8, 12], "shaker": list(range(0, 16, 1)),
        "ghost": [11, 14], "swing": 0.0, "energy": 0.65,
    },
    "C_broken": {
        "label_ko": "C · 브로큰비트 (스윙 하이햇, 당김 킥, 클랩 백비트)",
        "kick": [0, 3, 8, 11, 14], "snare": [4, 12], "hat": [0, 2, 3, 5, 6, 8, 10, 11, 13, 14],
        "shaker": [2, 6, 10, 14], "ghost": [7], "swing": 0.16, "energy": 0.9,
    },
}


def make_drums(variant: str, bars: list[tuple[float, float]], seed: int = 11,
               humanize_ms: float = 9.0, fill_every: int = 8) -> list[dict]:
    spec = DRUM_PATTERNS[variant]
    rng = _rng(seed)
    ev = []
    for bi, (b0, b1) in enumerate(bars):
        g = bar_grid(b0, b1, 16)
        step = (b1 - b0) / 16
        swing = spec["swing"]

        def t_at(i):
            base = g[i % 16]
            if swing and i % 2 == 1:
                base += step * swing
            return base + rng.normal(0, humanize_ms / 1000.0)

        for i in spec["kick"]:
            ev.append({"start": t_at(i), "dur": step * 0.9, "pitch": DRUM["kick"],
                       "velocity": int(np.clip(rng.normal(108, 6), 70, 127))})
        for i in spec["snare"]:
            ev.append({"start": t_at(i), "dur": step * 0.9, "pitch": DRUM["snare"],
                       "velocity": int(np.clip(rng.normal(104, 7), 70, 127))})
            if variant == "C_broken":
                ev.append({"start": t_at(i), "dur": step * 0.9, "pitch": DRUM["clap"],
                           "velocity": int(np.clip(rng.normal(92, 7), 60, 120))})
        for i in spec["ghost"]:
            if rng.random() < 0.6:
                ev.append({"start": t_at(i), "dur": step * 0.5, "pitch": DRUM["snare"],
                           "velocity": int(np.clip(rng.normal(42, 8), 20, 70))})
        for i in spec["hat"]:
            open_hat = (i == 14 and bi % 2 == 1)
            ev.append({"start": t_at(i), "dur": step * 0.6,
                       "pitch": DRUM["ohat"] if open_hat else DRUM["hat"],
                       "velocity": int(np.clip(rng.normal(78 if i % 4 == 0 else 62, 9), 30, 110))})
        for i in spec["shaker"]:
            ev.append({"start": t_at(i), "dur": step * 0.4, "pitch": DRUM["shaker"],
                       "velocity": int(np.clip(rng.normal(58, 10), 25, 95))})
        # fill at the end of each phrase
        if fill_every and (bi + 1) % fill_every == 0:
            for k, i in enumerate([10, 12, 13, 14, 15]):
                ev.append({"start": t_at(i), "dur": step * 0.8,
                           "pitch": [DRUM["tom_h"], DRUM["tom_m"], DRUM["tom_m"], DRUM["tom_l"], DRUM["snare"]][k],
                           "velocity": int(np.clip(80 + k * 8 + rng.normal(0, 5), 60, 127))})
        if bi % fill_every == 0 and bi > 0:
            ev.append({"start": g[0], "dur": step * 4, "pitch": DRUM["crash"],
                       "velocity": int(np.clip(rng.normal(96, 6), 70, 120))})
    ev = [e for e in ev if e["start"] >= 0]
    ev.sort(key=lambda e: (e["start"], e["pitch"]))
    return ev


# ---------- bass ----------
BASS_STYLES = {
    "A_root_sustain": "A · 루트 지속음 (한 마디에 한 음, 안정적·간섭 적음)",
    "B_octave_passing": "B · 옥타브 + 경과음 (8비트, 코드 전환에 경과음)",
    "C_syncopated": "C · 싱코페이션 16비트 (당김음 중심, 그루브 강함)",
}


def make_bass(variant: str, bars: list[tuple[float, float]], chord_roots: list[int],
              scale: list[int], tonic_pc: int, seed: int = 23, base_octave: int = 2,
              humanize_ms: float = 7.0) -> list[dict]:
    rng = _rng(seed)
    ev = []
    scale_pcs = [(tonic_pc + s) % 12 for s in scale]
    for bi, (b0, b1) in enumerate(bars):
        step = (b1 - b0) / 16
        root_pc = chord_roots[bi % len(chord_roots)] if chord_roots else tonic_pc
        nxt_pc = chord_roots[(bi + 1) % len(chord_roots)] if chord_roots else tonic_pc
        root = 12 * (base_octave + 1) + root_pc  # MIDI: C2 = 36
        while root < 28:
            root += 12
        while root > 52:
            root -= 12
        def hum():
            return rng.normal(0, humanize_ms / 1000.0)
        if variant == "A_root_sustain":
            ev.append({"start": b0 + hum(), "dur": (b1 - b0) * 0.92, "pitch": root,
                       "velocity": int(np.clip(rng.normal(96, 5), 70, 120))})
        elif variant == "B_octave_passing":
            pattern = [(0, root), (4, root), (8, root + 12), (10, root), (14, None)]
            for i, p in pattern:
                if p is None:
                    # 경과음: 다음 코드 루트로 향하는 스케일 음
                    cands = [12 * (base_octave + 1) + pc for pc in scale_pcs]
                    target = 12 * (base_octave + 1) + nxt_pc
                    p = min(cands, key=lambda c: abs(c - (root + target) / 2))
                ev.append({"start": b0 + step * i + hum(), "dur": step * 1.7, "pitch": int(p),
                           "velocity": int(np.clip(rng.normal(92 if i else 104, 7), 60, 120))})
        else:  # C_syncopated
            hits = [0, 3, 6, 7, 10, 13, 14]
            for i in hits:
                pitch = root
                if i in (6, 13) and rng.random() < 0.6:
                    pitch = root + 12
                if i == 10 and rng.random() < 0.5:
                    pitch = 12 * (base_octave + 1) + ((root_pc + 7) % 12)
                ev.append({"start": b0 + step * i + hum(), "dur": step * (2.2 if i in (0, 6) else 1.3),
                           "pitch": int(pitch),
                           "velocity": int(np.clip(rng.normal(100 if i in (0, 6) else 84, 8), 55, 122))})
    ev.sort(key=lambda e: e["start"])
    return ev


# ---------- chords / reharmonization ----------
def reharmonize(chord_roots: list[int], tonic_pc: int, mode: str, variant: str) -> list[dict]:
    """원곡 추정 코드를 기반으로 한 재화성 후보. 원곡 코드를 지우지 않고 '대안'만 제시."""
    minor = mode == "minor"
    out = []
    for i, r in enumerate(chord_roots):
        deg = (r - tonic_pc) % 12
        if variant == "A_diatonic_sub":
            # 상대/대리코드: i↔III, iv↔VI, v↔VII
            table = {0: 3, 3: 0, 5: 8, 8: 5, 7: 10, 10: 7} if minor else {0: 9, 9: 0, 5: 2, 2: 5, 7: 4, 4: 7}
            nd = table.get(deg, deg)
            qual = "m" if (minor and nd in (0, 5, 7)) or (not minor and nd in (2, 4, 9)) else ""
        elif variant == "B_borrowed":
            # 차용화음: VI / VII / IV(major) 삽입, v→V (도미넌트화)
            if deg == 7 and minor:
                nd, qual = 7, ""      # v → V (화성단음계)
            elif deg == 0:
                nd, qual = 0, "m" if minor else ""
            elif deg in (5,):
                nd, qual = 5, "" if minor else "m"   # iv → IV / IV → iv
            else:
                nd, qual = (deg + 1) % 12 if deg in (8, 10) else deg, "" if minor else "m"
        else:  # C_pedal_sus
            nd = deg
            qual = "sus4" if i % 2 == 1 else ("m" if minor and deg in (0, 5, 7) else "")
        root = (tonic_pc + nd) % 12
        out.append({"bar": i, "chord": f"{pc_name(root)}{qual}", "root_pc": int(root), "quality": qual})
    return out


def chord_pitches(root_pc: int, quality: str, octave: int = 4) -> list[int]:
    offs = {"": [0, 4, 7], "m": [0, 3, 7], "dim": [0, 3, 6], "aug": [0, 4, 8],
            "sus4": [0, 5, 7], "sus2": [0, 2, 7], "7": [0, 4, 7, 10], "m7": [0, 3, 7, 10],
            "maj7": [0, 4, 7, 11]}.get(quality, [0, 4, 7])
    base = 12 * (octave + 1) + root_pc
    return [base + o for o in offs]


def make_pad(chords: list[dict], bars: list[tuple[float, float]], seed: int = 31,
             octave: int = 4, voicing: str = "close") -> list[dict]:
    rng = _rng(seed)
    ev = []
    for bi, (b0, b1) in enumerate(bars):
        c = chords[bi % len(chords)]
        ps = chord_pitches(c["root_pc"], c.get("quality", ""), octave)
        if voicing == "spread":
            ps = [ps[0] - 12] + ps[1:]
        for k, p in enumerate(ps):
            ev.append({"start": b0 + rng.normal(0, 0.008) + k * 0.012, "dur": (b1 - b0) * 0.98,
                       "pitch": int(p), "velocity": int(np.clip(rng.normal(64, 6), 40, 90))})
    return ev


# ---------- bridge (new section) ----------
BRIDGE_SHAPES = {
    "A_arch": ("A · 아치형 (올라갔다 내려오는 8마디, 안정적)", [0, 2, 4, 5, 4, 2, 1, 0]),
    "B_descend": ("B · 하행형 (높은 데서 시작해 내려오는 8마디, 애절함)", [6, 5, 4, 3, 2, 1, 0, -1]),
    "C_call_response": ("C · 콜앤리스폰스 (짧은 동기 + 응답, 리듬감)", [0, 2, 0, 4, 2, 5, 4, 0]),
}
BRIDGE_CHORDS = {
    "A_arch": [(5, "m"), (8, ""), (3, ""), (7, "m")],
    "B_descend": [(8, ""), (7, ""), (5, "m"), (0, "m")],
    "C_call_response": [(0, "m"), (10, ""), (8, ""), (7, "")],
}


def make_bridge(variant: str, start: float, bpm: float, bars_count: int, tonic_pc: int,
                scale: list[int], seed: int = 47, beats_per_bar: int = 4,
                melody_octave: int = 5) -> dict:
    """새 브리지 후보: 코드 진행 + 멜로디 동기(motif) + 베이스.

    멜로디는 스케일 degree 시퀀스를 리듬에 배치한 '초안'입니다.
    사람이 허밍한 멜로디로 대체하는 것을 권장합니다 (그게 인간 창작 증거가 됩니다).
    """
    rng = _rng(seed)
    spb = 60.0 / bpm
    bar_len = spb * beats_per_bar
    bars = [(start + i * bar_len, start + (i + 1) * bar_len) for i in range(bars_count)]
    label, degrees = BRIDGE_SHAPES[variant]
    prog = BRIDGE_CHORDS[variant]
    chords = [{"bar": i, "root_pc": (tonic_pc + prog[i % len(prog)][0]) % 12,
               "quality": prog[i % len(prog)][1],
               "chord": f"{pc_name((tonic_pc + prog[i % len(prog)][0]) % 12)}{prog[i % len(prog)][1]}"}
              for i in range(bars_count)]
    melody = []
    rhythms = {"A_arch": [0, 1.5, 2.5], "B_descend": [0, 2], "C_call_response": [0, 0.75, 1.5, 2.5, 3]}[variant]
    for bi, (b0, b1) in enumerate(bars):
        deg = degrees[bi % len(degrees)]
        for k, beat in enumerate(rhythms):
            d = deg + (1 if k % 2 and rng.random() < 0.5 else 0)
            octv = melody_octave + (d // len(scale))
            pitch = 12 * (octv + 1) + (tonic_pc + scale[d % len(scale)]) % 12
            dur = spb * (1.2 if k == 0 else 0.7)
            melody.append({"start": b0 + beat * spb + rng.normal(0, 0.01), "dur": dur,
                           "pitch": int(pitch), "velocity": int(np.clip(rng.normal(92, 7), 60, 118))})
    bass = make_bass("A_root_sustain" if variant == "B_descend" else "B_octave_passing",
                     bars, [c["root_pc"] for c in chords], scale, tonic_pc, seed=seed + 5)
    pad = make_pad(chords, bars, seed=seed + 9)
    return {"variant": variant, "label_ko": label, "start": round(start, 3),
            "end": round(bars[-1][1], 3), "bars": bars_count, "chords": chords,
            "melody": melody, "bass": bass, "pad": pad,
            "note_ko": "이 멜로디는 자동 초안입니다. 직접 허밍한 멜로디로 바꾸면 인간 창작 증거가 훨씬 강해집니다."}


# ---------- structure ----------
def structure_options(sections: list[dict], intro_sec: float, bpm: float, beats_per_bar: int = 4) -> list[dict]:
    bar_len = 60.0 / bpm * beats_per_bar
    labels = [s["label"] for s in sections]
    return [
        {"variant": "A_minimal", "label_ko": "A · 최소 변경 (새 인트로 + 브리지 1개 삽입, 원곡 순서 유지)",
         "intro_bars": max(1, round(intro_sec / bar_len)), "insert_bridge_before_last": True,
         "reorder": list(range(len(sections))), "risk_ko": "가장 안전. 편곡 변화량은 작음"},
        {"variant": "B_extended", "label_ko": "B · 확장 (긴 인트로 + 브리지 + 후반 브레이크다운)",
         "intro_bars": max(2, round(intro_sec / bar_len) + 2), "insert_bridge_before_last": True,
         "breakdown_section": max(0, len(sections) - 2), "reorder": list(range(len(sections))),
         "risk_ko": "보컬 흐름 확인 필요"},
        {"variant": "C_rebuilt", "label_ko": "C · 재조립 (구간 순서 변경 + 브리지 + 새 아웃트로)",
         "intro_bars": max(2, round(intro_sec / bar_len) + 1), "insert_bridge_before_last": True,
         "reorder": _reorder(labels), "risk_ko": "가사 문맥이 깨질 수 있음 — 반드시 전체 청취"},
    ]


def _reorder(labels: list[str]) -> list[int]:
    """후렴을 앞으로 한 번 끌어오는 보수적 재배치 (cold open)."""
    idx = list(range(len(labels)))
    chorus = [i for i, l in enumerate(labels) if "chorus" in l]
    if len(idx) > 3 and chorus and chorus[0] > 1:
        c = chorus[0]
        idx.remove(c)
        idx.insert(1, c)
    return idx
