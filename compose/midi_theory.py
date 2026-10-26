"""Music theory on MIDI notes — no audio, no heavy dependencies.

Everything here works on the notes the HUMAN played. Nothing is generated from a
reference recording, so whatever this module reports describes the user's own material.

Provides: key estimation, chord naming per bar, scale/mode fitting, range and density
statistics, and instrument suggestions driven by those statistics.
"""
from __future__ import annotations
import numpy as np

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NAMES_KO = {"C": "도", "C#": "도#", "D": "레", "D#": "레#", "E": "미", "F": "파",
            "F#": "파#", "G": "솔", "G#": "솔#", "A": "라", "A#": "라#", "B": "시"}

# Krumhansl-Schmuckler key profiles
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

SCALES = {
    "major":            [0, 2, 4, 5, 7, 9, 11],
    "natural minor":    [0, 2, 3, 5, 7, 8, 10],
    "harmonic minor":   [0, 2, 3, 5, 7, 8, 11],
    "dorian":           [0, 2, 3, 5, 7, 9, 10],
    "mixolydian":       [0, 2, 4, 5, 7, 9, 10],
    "lydian":           [0, 2, 4, 6, 7, 9, 11],
    "phrygian":         [0, 1, 3, 5, 7, 8, 10],
    "major pentatonic": [0, 2, 4, 7, 9],
    "minor pentatonic": [0, 3, 5, 7, 10],
}

# chord templates: name suffix -> intervals from root
CHORDS = {
    "":      [0, 4, 7],        # major
    "m":     [0, 3, 7],        # minor
    "dim":   [0, 3, 6],
    "aug":   [0, 4, 8],
    "sus2":  [0, 2, 7],
    "sus4":  [0, 5, 7],
    "7":     [0, 4, 7, 10],
    "maj7":  [0, 4, 7, 11],
    "m7":    [0, 3, 7, 10],
    "m7b5":  [0, 3, 6, 10],
    "6":     [0, 4, 7, 9],
    "m6":    [0, 3, 7, 9],
    "add9":  [0, 2, 4, 7],
}


def pitch_name(midi: int) -> str:
    return f"{NAMES[midi % 12]}{midi // 12 - 1}"


def estimate_key(pitches: list[int], durations: list[float] | None = None) -> dict:
    """Duration-weighted pitch-class histogram matched against the 24 key profiles."""
    if not pitches:
        return {"key": "unknown", "tonic": "C", "mode": "major", "confidence": 0.0, "runner_up": ""}
    w = durations if durations is not None and len(durations) == len(pitches) else [1.0] * len(pitches)
    hist = np.zeros(12)
    for p, d in zip(pitches, w):
        hist[p % 12] += max(d, 1e-3)
    if hist.sum() <= 0:
        hist[:] = 1.0
    hist = hist / hist.sum()
    scores = []
    for i in range(12):
        for mode, prof in (("major", MAJOR), ("minor", MINOR)):
            p = np.roll(prof, i)
            r = float(np.corrcoef(p, hist)[0, 1]) if np.std(hist) > 1e-9 else 0.0
            scores.append((r, NAMES[i], mode))
    scores.sort(reverse=True)
    best = scores[0]
    return {"key": f"{best[1]} {best[2]}", "tonic": best[1], "mode": best[2],
            "confidence": round(float(best[0]), 3),
            "runner_up": f"{scores[1][1]} {scores[1][2]} ({scores[1][0]:.3f})",
            "histogram": {NAMES[i]: round(float(hist[i]), 4) for i in range(12)}}


def best_scales(pitches: list[int], top: int = 3) -> list[dict]:
    """Which scales contain the most of the played notes. Tells the user which notes are 'safe'."""
    if not pitches:
        return []
    pcs = [p % 12 for p in pitches]
    out = []
    for tonic in range(12):
        for name, steps in SCALES.items():
            members = {(tonic + s) % 12 for s in steps}
            inside = sum(1 for p in pcs if p in members)
            out.append({"scale": f"{NAMES[tonic]} {name}", "tonic": NAMES[tonic], "type": name,
                        "fit_percent": round(100 * inside / len(pcs), 1),
                        "notes": [NAMES[(tonic + s) % 12] for s in steps],
                        "outside_notes": sorted({NAMES[p] for p in pcs if p not in members})})
    out.sort(key=lambda d: (-d["fit_percent"], len(d["notes"])))
    seen, uniq = set(), []
    for d in out:
        if d["scale"] in seen:
            continue
        seen.add(d["scale"]); uniq.append(d)
        if len(uniq) >= top:
            break
    return uniq


def name_chord(pcs: set[int], bass_pc: int | None = None, weights: dict | None = None) -> dict:
    """Best chord name for a set of pitch classes.
    The bass note dominates: on a piano the left hand states the root, so a chord whose root
    matches the bass wins over a rootless reading that happens to share notes (the classic
    Am vs Fmaj7 mix-up). Simpler chords are preferred unless the extra tone is really held."""
    if not pcs:
        return {"chord": "N.C.", "score": 0.0, "missing": [], "extra": []}
    w = weights or {}
    total_w = sum(w.values()) or 1.0
    best = None
    for root in range(12):
        for suffix, ivs in CHORDS.items():
            tones = {(root + i) % 12 for i in ivs}
            # weight matches by how long each pitch class actually sounds
            hit = sum(w.get(t, 0.0) for t in (pcs & tones)) / total_w * len(pcs) if w else len(pcs & tones)
            extra = sum(w.get(e, 0.0) for e in (pcs - tones)) / total_w * len(pcs) if w else len(pcs - tones)
            missing = len(tones - pcs)
            score = hit - 0.8 * extra - 0.6 * missing
            score -= 0.25 * (len(ivs) - 3)        # prefer triads over 7th chords
            if bass_pc is not None:
                if bass_pc == root:
                    score += 1.8                  # root in the bass: strongest cue there is
                elif bass_pc in tones:
                    score += 0.2                  # an inversion is still plausible
                else:
                    score -= 1.0                  # bass note outside the chord: unlikely
            if best is None or score > best[0]:
                best = (score, root, suffix, sorted(tones - pcs), sorted(pcs - tones))
    score, root, suffix, missing, extra = best
    return {"chord": NAMES[root] + suffix, "root": NAMES[root], "quality": suffix or "major",
            "score": round(float(score), 2),
            "missing": [NAMES[m] for m in missing], "extra": [NAMES[e] for e in extra]}


def roman_numeral(chord_root: str, quality: str, tonic: str, mode: str) -> str:
    """Where the chord sits in the key — this is the part a human uses to decide what comes next."""
    try:
        deg = (NAMES.index(chord_root) - NAMES.index(tonic)) % 12
    except ValueError:
        return "?"
    major_map = {0: "I", 2: "II", 4: "III", 5: "IV", 7: "V", 9: "VI", 11: "VII"}
    minor_map = {0: "I", 2: "II", 3: "III", 5: "IV", 7: "V", 8: "VI", 10: "VII"}
    m = major_map if mode == "major" else minor_map
    base = m.get(deg)
    if base is None:
        flat = {1: "bII", 3: "bIII", 6: "bV", 8: "bVI", 10: "bVII", 4: "bIV", 9: "bVI"}
        base = flat.get(deg, f"({deg})")
    minorish = quality.startswith("m") and not quality.startswith("maj")
    return base.lower() if minorish else base


def stats(pitches: list[int], starts: list[float], ends: list[float], total_s: float) -> dict:
    if not pitches:
        return {}
    durs = [max(1e-3, e - s) for s, e in zip(starts, ends)]
    # polyphony: how many notes sound at the same time, sampled on a fine grid
    grid = np.arange(0, max(total_s, 1e-3), 0.05)
    poly = np.zeros(len(grid), dtype=int)
    for s, e in zip(starts, ends):
        poly[(grid >= s) & (grid < e)] += 1
    sounding = poly[poly > 0]
    return {
        "note_count": len(pitches),
        "lowest": pitch_name(min(pitches)), "highest": pitch_name(max(pitches)),
        "lowest_midi": int(min(pitches)), "highest_midi": int(max(pitches)),
        "range_semitones": int(max(pitches) - min(pitches)),
        "mean_duration_s": round(float(np.mean(durs)), 3),
        "median_duration_s": round(float(np.median(durs)), 3),
        "notes_per_second": round(len(pitches) / max(total_s, 1e-3), 2),
        "max_polyphony": int(poly.max()) if len(poly) else 0,
        "mean_polyphony_when_sounding": round(float(np.mean(sounding)), 2) if len(sounding) else 0.0,
        "rest_ratio": round(float(np.mean(poly == 0)), 3) if len(poly) else 0.0,
        "distinct_pitch_classes": len({p % 12 for p in pitches}),
    }


# ---------------------------------------------------------------- instrument suggestions

# General MIDI programs that actually sound good in FluidR3_GM, grouped by role
GM = {
    "piano_bright": (1, "Bright Acoustic Piano"), "piano_electric": (4, "Electric Piano 1"),
    "piano_rhodes": (5, "Electric Piano 2"), "harpsichord": (6, "Harpsichord"),
    "celesta": (8, "Celesta"), "music_box": (10, "Music Box"), "vibraphone": (11, "Vibraphone"),
    "marimba": (12, "Marimba"), "church_organ": (19, "Church Organ"), "drawbar_organ": (16, "Drawbar Organ"),
    "nylon_guitar": (24, "Nylon Guitar"), "steel_guitar": (25, "Steel Guitar"),
    "clean_electric": (27, "Clean Electric Guitar"), "overdrive_guitar": (29, "Overdriven Guitar"),
    "acoustic_bass": (32, "Acoustic Bass"), "finger_bass": (33, "Fingered Bass"),
    "pick_bass": (34, "Picked Bass"), "fretless_bass": (35, "Fretless Bass"),
    "synth_bass": (38, "Synth Bass 1"),
    "violin": (40, "Violin"), "cello": (42, "Cello"), "strings": (48, "String Ensemble 1"),
    "slow_strings": (49, "Slow Strings"), "synth_strings": (50, "Synth Strings 1"),
    "choir": (52, "Choir Aahs"), "voice_oohs": (53, "Voice Oohs"),
    "trumpet": (56, "Trumpet"), "french_horn": (60, "French Horn"), "brass": (61, "Brass Section"),
    "soprano_sax": (64, "Soprano Sax"), "alto_sax": (65, "Alto Sax"), "tenor_sax": (66, "Tenor Sax"),
    "oboe": (68, "Oboe"), "clarinet": (71, "Clarinet"), "flute": (73, "Flute"), "pan_flute": (75, "Pan Flute"),
    "square_lead": (80, "Square Lead"), "saw_lead": (81, "Saw Lead"),
    "warm_pad": (89, "Warm Pad"), "poly_pad": (90, "Polysynth Pad"), "halo_pad": (94, "Halo Pad"),
    "sweep_pad": (95, "Sweep Pad"), "kalimba": (108, "Kalimba"),
}

# which roles suit which pitch range (in MIDI note numbers) and texture
ROLE_RULES = [
    # (key, role, lo, hi, best_polyphony, why in Korean)
    ("strings",        "받침(패드)",  40, 96, "chord", "길게 끄는 화음에 가장 안정적입니다. 보컬이나 리드를 가리지 않습니다."),
    ("slow_strings",   "받침(패드)",  40, 96, "chord", "어택이 느려서 잔잔한 곡에 어울립니다. 빠른 패시지에는 안 맞습니다."),
    ("warm_pad",       "받침(패드)",  36, 96, "chord", "신스 패드. 전자/발라드 계열에 넓게 깔립니다."),
    ("choir",          "받침(패드)",  48, 84, "chord", "사람 목소리 질감. 후렴을 크게 들리게 만듭니다."),
    ("rhodes",         "코드 반주",   40, 88, "chord", "로즈 피아노. 재즈·알앤비·시티팝 반주에 잘 맞습니다."),
    ("piano_electric", "코드 반주",   40, 88, "chord", "일렉 피아노. 피아노보다 부드럽고 보컬과 덜 부딪힙니다."),
    ("nylon_guitar",   "코드 반주",   40, 84, "chord", "나일론 기타. 어쿠스틱·보사노바 느낌."),
    ("clean_electric", "코드 반주",   40, 88, "chord", "클린 일렉. 아르페지오에 좋습니다."),
    ("vibraphone",     "장식",        53, 96, "both",  "비브라폰. 짧은 장식음·아르페지오에 반짝입니다."),
    ("celesta",        "장식",        60, 108, "both", "첼레스타. 높은 음역의 반짝이는 장식."),
    ("music_box",      "장식",        72, 108, "mono", "오르골. 아주 높은 음역에서만 쓰세요."),
    ("marimba",        "장식",        45, 96, "both",  "마림바. 통통 튀는 리듬 패시지."),
    ("kalimba",        "장식",        60, 96, "both",  "칼림바. 소박하고 따뜻한 반복 음형."),
    ("flute",          "멜로디",      60, 96, "mono",  "플루트. 높은 음역의 가벼운 멜로디."),
    ("violin",         "멜로디",      55, 100, "mono", "바이올린. 표현력 있는 선율선."),
    ("cello",          "멜로디/저음", 36, 72, "mono",  "첼로. 낮은 멜로디나 대선율에 좋습니다."),
    ("alto_sax",       "멜로디",      49, 81, "mono",  "알토 색소폰. 중음역 멜로디에 두껍게."),
    ("clarinet",       "멜로디",      50, 84, "mono",  "클라리넷. 부드러운 중음역."),
    ("trumpet",        "멜로디",      55, 86, "mono",  "트럼펫. 밝고 뚫고 나오는 선율."),
    ("square_lead",    "멜로디",      48, 96, "mono",  "스퀘어 리드. 게임/신스팝 느낌."),
    ("saw_lead",       "멜로디",      48, 96, "mono",  "소 리드. 강한 전자 리드."),
    ("finger_bass",    "베이스",      28, 55, "mono",  "핑거 베이스. 대부분의 장르에 기본."),
    ("acoustic_bass",  "베이스",      28, 55, "mono",  "어쿠스틱 베이스. 재즈·발라드."),
    ("synth_bass",     "베이스",      24, 52, "mono",  "신스 베이스. 전자 장르."),
    ("church_organ",   "받침(패드)",  36, 96, "chord", "파이프 오르간. 웅장한 느낌."),
]


def suggest_instruments(st: dict, key: dict, top: int = 6, prefer_role: str | None = None) -> list[dict]:
    """Rank GM instruments for the part the user played, from its range and texture.
    Returns reasons in Korean so the user can judge the suggestion rather than trust it."""
    if not st:
        return []
    lo, hi = st["lowest_midi"], st["highest_midi"]
    poly = st.get("mean_polyphony_when_sounding", 1)
    nps = st.get("notes_per_second", 1)
    texture = "chord" if poly >= 2.2 else ("mono" if poly < 1.4 else "both")
    out = []
    for gmkey, role, rlo, rhi, want, why in ROLE_RULES:
        if gmkey not in GM:
            continue
        prog, gmname = GM[gmkey]
        # how much of the played range the instrument covers
        overlap = max(0, min(hi, rhi) - max(lo, rlo))
        span = max(1, hi - lo)
        cover = overlap / span
        score = cover * 3.0
        if want == texture or want == "both" or texture == "both":
            score += 1.2
        else:
            score -= 0.8
        if lo < rlo:
            score -= 0.9  # played notes fall below the instrument
        if hi > rhi:
            score -= 0.9
        if nps > 4 and want == "chord":
            score -= 0.7   # fast passages do not suit slow pads
        if nps < 1.2 and want == "mono" and role == "멜로디":
            score -= 0.3
        if prefer_role:
            # the caller knows what this voice is for (top line vs. the harmony underneath)
            if role.startswith(prefer_role):
                score += 2.5
            elif prefer_role == "멜로디" and role == "장식":
                score += 0.4      # decorative instruments can carry a line, just not first choice
            else:
                score -= 0.6
        out.append({"gm_program": prog, "gm_name": gmname, "key": gmkey, "role": role,
                    "score": round(float(score), 2), "range_fit_percent": round(100 * cover, 1),
                    "why": why,
                    "warning": ("연주한 음이 이 악기 음역보다 낮습니다" if lo < rlo else
                                "연주한 음이 이 악기 음역보다 높습니다" if hi > rhi else "")})
    out.sort(key=lambda d: -d["score"])
    return out[:top]
