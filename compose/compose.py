"""Manual composition assistant — you play the notes, this builds around them.

    /opt/mc/bin/python compose/compose.py 내피아노.mid --out work/곡1

What it does, in order:
  1. reads YOUR MIDI (piano part) and never changes it
  2. works out key, usable scales, chord per bar, range and texture
  3. suggests General MIDI instruments that fit what you actually played, with reasons
  4. writes drum / bass / pad options (A, B, C) locked to your bar grid
  5. renders every option to audio with FluidSynth so you can hear it before choosing
  6. writes a report you can read, and MIDI files you can drag into any DAW

Nothing here invents a melody. The melody stays yours; only accompaniment is proposed,
and you pick which proposal (or none) in decisions.json.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, shutil
import numpy as np
import pretty_midi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from midi_theory import (estimate_key, best_scales, name_chord, roman_numeral, stats,
                         suggest_instruments, pitch_name, GM, NAMES, NAMES_KO)

SF2 = os.environ.get("GM_SOUNDFONT", "/usr/share/sounds/sf2/FluidR3_GM.sf2")
FLUID = shutil.which("fluidsynth")
FFMPEG = shutil.which("ffmpeg")

# General MIDI percussion key numbers (channel 10)
DRUM = {"kick": 36, "snare": 38, "clap": 39, "rim": 37, "hat": 42, "ohat": 46,
        "ride": 51, "crash": 49, "tom_lo": 45, "tom_hi": 50, "shaker": 70, "tamb": 54}


# ---------------------------------------------------------------- read the human's part

def read_part(path: str) -> dict:
    pm = pretty_midi.PrettyMIDI(path)
    notes = []
    for inst in pm.instruments:
        if inst.is_drum:
            continue
        for n in inst.notes:
            notes.append({"pitch": int(n.pitch), "start": float(n.start), "end": float(n.end),
                          "velocity": int(n.velocity)})
    notes.sort(key=lambda n: (n["start"], n["pitch"]))
    if not notes:
        raise SystemExit("이 MIDI에 (드럼이 아닌) 음이 하나도 없습니다. 연주한 파트를 확인해 주세요.")
    try:
        tempi = pm.get_tempo_changes()[1]
        tempo = float(tempi[0]) if len(tempi) else 120.0
    except Exception:
        tempo = 120.0
    end = max(n["end"] for n in notes)
    return {"notes": notes, "tempo": round(tempo, 2), "end_s": round(end, 3),
            "source_file": os.path.basename(path), "instrument_count": len(pm.instruments)}


def split_voices(notes: list[dict], bars: list[dict]) -> dict:
    """Separate the top line from what is underneath. On a two-hand piano part the top voice is
    usually the melody and the lower notes are the harmony — suggesting one instrument for both
    is useless, so each gets its own suggestions."""
    melody, accomp = [], []
    for n in notes:
        # a note is 'melody' when nothing higher is sounding at the same moment
        higher = any(o["pitch"] > n["pitch"] and o["start"] < n["end"] - 1e-6 and o["end"] > n["start"] + 1e-6
                     for o in notes)
        (accomp if higher else melody).append(n)
    return {"melody": melody, "accompaniment": accomp}


def bar_grid(tempo: float, end_s: float, beats_per_bar: int = 4, start: float = 0.0) -> list[dict]:
    beat = 60.0 / tempo
    bar_len = beat * beats_per_bar
    bars = []
    t = start
    while t < end_s + 1e-6:
        bars.append({"bar": len(bars), "start": round(t, 4), "end": round(t + bar_len, 4),
                     "beats": [round(t + i * beat, 4) for i in range(beats_per_bar)]})
        t += bar_len
    return bars


def chords_per_bar(notes: list[dict], bars: list[dict], key: dict) -> list[dict]:
    out = []
    for b in bars:
        inside = [n for n in notes if n["start"] < b["end"] and n["end"] > b["start"]]
        if not inside:
            out.append({"bar": b["bar"], "start": b["start"], "chord": "N.C.", "roman": "-",
                        "notes_played": [], "confidence": 0.0})
            continue
        # weight each pitch class by how long it sounds inside this bar
        weight = {}
        for n in inside:
            dur = min(n["end"], b["end"]) - max(n["start"], b["start"])
            weight[n["pitch"] % 12] = weight.get(n["pitch"] % 12, 0.0) + max(dur, 1e-3)
        keep = {pc for pc, w in weight.items() if w >= 0.25 * max(weight.values())}
        # the bass is the lowest note sounding ON the downbeat — that is what the left hand states
        on_downbeat = [n for n in inside if n["start"] <= b["start"] + 0.12]
        bass_src = on_downbeat or inside
        bass_pc = min(bass_src, key=lambda n: n["pitch"])["pitch"] % 12
        ch = name_chord(keep, bass_pc, weight)
        out.append({"bar": b["bar"], "start": b["start"], "chord": ch["chord"],
                    "roman": roman_numeral(ch["root"], ch["quality"], key["tonic"], key["mode"]),
                    "quality": ch["quality"], "confidence": ch["score"],
                    "bass_note": NAMES[bass_pc],
                    "notes_played": sorted({NAMES[n["pitch"] % 12] for n in inside}),
                    "extra_notes": ch["extra"], "missing_chord_tones": ch["missing"]})
    return out


# ---------------------------------------------------------------- accompaniment proposals

def drum_options(bars: list[dict], tempo: float) -> dict:
    """Three grooves. Each is plain data so you can read it before you hear it."""
    beat = 60.0 / tempo
    def pos(b, p):   # p = 1.0 .. 4.99 within the bar
        return b["start"] + (p - 1) * beat
    opts = {}
    for name, desc in [("A", "기본 8비트 — 킥 1·3, 스네어 2·4, 8분 하이햇. 어떤 곡에도 안전합니다."),
                       ("B", "하프타임 — 킥 1, 스네어 3. 느리고 무게감 있게 들립니다."),
                       ("C", "싱코페이션 — 킥 1·2.5·3.5, 클랩 2·4, 16분 하이햇. 추진력이 생깁니다.")]:
        ev = []
        for i, b in enumerate(bars):
            last = (i == len(bars) - 1) or (i % 4 == 3)
            if name == "A":
                for p, inst, v in [(1, "kick", 100), (3, "kick", 92), (2, "snare", 96), (4, "snare", 100)]:
                    ev.append({"t": pos(b, p), "inst": inst, "vel": v, "bar": i, "beat": p})
                for k in range(8):
                    p = 1 + k * 0.5
                    ev.append({"t": pos(b, p), "inst": "hat", "vel": 70 if k % 2 == 0 else 48, "bar": i, "beat": p})
            elif name == "B":
                ev.append({"t": pos(b, 1), "inst": "kick", "vel": 104, "bar": i, "beat": 1})
                ev.append({"t": pos(b, 3), "inst": "snare", "vel": 100, "bar": i, "beat": 3})
                ev.append({"t": pos(b, 4.5), "inst": "rim", "vel": 55, "bar": i, "beat": 4.5})
                for k in range(8):
                    p = 1 + k * 0.5
                    ev.append({"t": pos(b, p), "inst": "hat", "vel": 62 if k % 2 == 0 else 42, "bar": i, "beat": p})
            else:
                for p, v in [(1, 102), (2.5, 88), (3.5, 94)]:
                    ev.append({"t": pos(b, p), "inst": "kick", "vel": v, "bar": i, "beat": p})
                for p in (2, 4):
                    ev.append({"t": pos(b, p), "inst": "snare", "vel": 92, "bar": i, "beat": p})
                    ev.append({"t": pos(b, p), "inst": "clap", "vel": 80, "bar": i, "beat": p})
                for k in range(16):
                    p = 1 + k * 0.25
                    v = 72 if k % 4 == 0 else (52 if k % 2 == 0 else 36)
                    ev.append({"t": pos(b, p), "inst": "hat", "vel": v, "bar": i, "beat": p})
                ev.append({"t": pos(b, 4.5), "inst": "ohat", "vel": 70, "bar": i, "beat": 4.5})
            if last:
                ev.append({"t": pos(b, 4.5), "inst": "tom_lo", "vel": 80, "bar": i, "beat": 4.5})
                ev.append({"t": pos(b, 4.75), "inst": "tom_hi", "vel": 90, "bar": i, "beat": 4.75})
        opts[name] = {"description": desc, "events": ev, "hit_count": len(ev)}
    return opts


def chord_tones(chord: str) -> list[int]:
    """pitch classes of a chord name like 'Am7' -> [9,0,4,7]"""
    from midi_theory import CHORDS
    root = None
    for i, nm in enumerate(NAMES):
        if chord.startswith(nm) and (root is None or len(nm) > len(NAMES[root])):
            root = i
    if root is None:
        return []
    suffix = chord[len(NAMES[root]):]
    ivs = CHORDS.get(suffix, CHORDS.get("", [0, 4, 7]))
    return [(root + i) % 12 for i in ivs]


def bass_options(bars: list[dict], chords: list[dict], tempo: float, octave: int = 2) -> dict:
    beat = 60.0 / tempo
    def pos(b, p):
        return b["start"] + (p - 1) * beat
    opts = {}
    for name, desc in [("A", "온음표 루트 — 마디마다 근음 하나. 가장 안전하고 멜로디를 안 가립니다."),
                       ("B", "8분음표 펄스 — 계속 통통 움직입니다. 곡에 추진력을 줍니다."),
                       ("C", "루트–5도 + 경과음 — 다음 코드로 걸어 들어갑니다. 가장 음악적입니다.")]:
        notes = []
        for i, b in enumerate(bars):
            ch = chords[i]["chord"] if i < len(chords) else "N.C."
            tones = chord_tones(ch)
            if not tones:
                continue
            root = 12 * (octave + 1) + tones[0]
            fifth = root + 7
            nxt_tones = chord_tones(chords[i + 1]["chord"]) if i + 1 < len(chords) else tones
            nroot = 12 * (octave + 1) + (nxt_tones[0] if nxt_tones else tones[0])
            if name == "A":
                notes.append({"pitch": root, "start": pos(b, 1), "end": b["end"] - 0.02, "vel": 88, "bar": i, "beat": 1})
            elif name == "B":
                for k in range(8):
                    p = 1 + k * 0.5
                    pitch = root + 12 if k == 7 else root
                    notes.append({"pitch": pitch, "start": pos(b, p), "end": pos(b, p) + beat * 0.45,
                                  "vel": 86 if k % 2 == 0 else 70, "bar": i, "beat": p})
            else:
                notes.append({"pitch": root,  "start": pos(b, 1),   "end": pos(b, 2),   "vel": 92, "bar": i, "beat": 1})
                notes.append({"pitch": fifth, "start": pos(b, 2.5), "end": pos(b, 3),   "vel": 74, "bar": i, "beat": 2.5})
                notes.append({"pitch": root,  "start": pos(b, 3),   "end": pos(b, 4),   "vel": 88, "bar": i, "beat": 3})
                step = -1 if nroot > root else 1
                notes.append({"pitch": nroot + step, "start": pos(b, 4.5), "end": b["end"] - 0.02,
                              "vel": 70, "bar": i, "beat": 4.5})
        opts[name] = {"description": desc, "notes": notes, "note_count": len(notes)}
    return opts


def pad_option(bars: list[dict], chords: list[dict], octave: int = 4) -> dict:
    notes = []
    for i, b in enumerate(bars):
        ch = chords[i]["chord"] if i < len(chords) else "N.C."
        tones = chord_tones(ch)
        if not tones:
            continue
        for t in tones[:4]:
            notes.append({"pitch": 12 * (octave + 1) + t, "start": b["start"], "end": b["end"] + 0.25,
                          "vel": 56, "bar": i})
    return {"description": "코드를 길게 받쳐 주는 패드. 빈 공간을 메우고 곡을 넓게 들리게 합니다.",
            "notes": notes, "note_count": len(notes)}


# ---------------------------------------------------------------- MIDI + audio output

def write_midi(path: str, tempo: float, tracks: list[dict]):
    """tracks: [{'program':int,'is_drum':bool,'name':str,'notes':[{pitch,start,end,vel}]}]"""
    pm = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    for t in tracks:
        inst = pretty_midi.Instrument(program=int(t.get("program", 0)),
                                      is_drum=bool(t.get("is_drum", False)), name=t.get("name", ""))
        for n in t["notes"]:
            inst.notes.append(pretty_midi.Note(velocity=int(np.clip(n.get("vel", 90), 1, 127)),
                                               pitch=int(n["pitch"]), start=float(n["start"]),
                                               end=float(max(n["end"], n["start"] + 0.03))))
        pm.instruments.append(inst)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    pm.write(path)
    return path


def render(mid: str, wav: str, gain: float = 0.8) -> str | None:
    if not FLUID or not os.path.exists(SF2):
        return None
    os.makedirs(os.path.dirname(wav) or ".", exist_ok=True)
    r = subprocess.run([FLUID, "-ni", "-g", str(gain), "-F", wav, "-r", "44100", SF2, mid],
                       capture_output=True, text=True)
    return wav if r.returncode == 0 and os.path.exists(wav) else None


def to_mp3(wav: str, mp3: str, bitrate: str = "192k") -> str | None:
    if not FFMPEG or not wav or not os.path.exists(wav):
        return None
    r = subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", wav, "-codec:a", "libmp3lame",
                        "-b:a", bitrate, mp3], capture_output=True, text=True)
    if r.returncode == 0:
        os.remove(wav)
        return mp3
    return None


def drum_notes(events: list[dict]) -> list[dict]:
    return [{"pitch": DRUM.get(e["inst"], 38), "start": e["t"], "end": e["t"] + 0.12, "vel": e["vel"]}
            for e in events]


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="당신이 연주한 MIDI 위에 반주를 제안합니다")
    ap.add_argument("midi", help="당신이 연주한 .mid 파일")
    ap.add_argument("--out", required=True, help="결과 폴더")
    ap.add_argument("--tempo", type=float, default=None, help="BPM 직접 지정 (MIDI 값이 틀릴 때)")
    ap.add_argument("--beats-per-bar", type=int, default=4)
    ap.add_argument("--melody-instrument", default=None,
                    help=f"당신 파트를 이 악기로 렌더 (예: strings, nylon_guitar). 목록: {', '.join(sorted(GM))}")
    ap.add_argument("--no-render", action="store_true", help="오디오 렌더 건너뛰기 (MIDI만)")
    a = ap.parse_args()

    out = a.out
    os.makedirs(out, exist_ok=True)
    for sub in ("01_당신파트", "02_악기후보", "03_반주후보", "04_합본"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)

    part = read_part(a.midi)
    tempo = a.tempo or part["tempo"]
    notes = part["notes"]
    pitches = [n["pitch"] for n in notes]
    durs = [n["end"] - n["start"] for n in notes]
    key = estimate_key(pitches, durs)
    scales = best_scales(pitches)
    st = stats(pitches, [n["start"] for n in notes], [n["end"] for n in notes], part["end_s"])
    bars = bar_grid(tempo, part["end_s"], a.beats_per_bar)
    chords = chords_per_bar(notes, bars, key)
    instruments = suggest_instruments(st, key)
    voices = split_voices(notes, bars)
    voice_suggestions = {}
    for vname, vlabel, vrole in (("melody", "윗선율(오른손)", "멜로디"),
                                 ("accompaniment", "아랫화음(왼손)", "받침")):
        vn = voices[vname]
        if len(vn) < 3:
            continue
        vst = stats([n["pitch"] for n in vn], [n["start"] for n in vn], [n["end"] for n in vn], part["end_s"])
        voice_suggestions[vname] = {"label": vlabel, "note_count": len(vn), "stats": vst,
                                    "suggestions": suggest_instruments(vst, key, top=4, prefer_role=vrole)}

    # keep an untouched copy of what the human played
    shutil.copy(a.midi, os.path.join(out, "01_당신파트", "원본_" + os.path.basename(a.midi)))

    # your part rendered with each suggested instrument, so you can compare timbres
    inst_files = []
    if not a.no_render:
        for s in instruments:
            tag = f"{s['key']}_{s['gm_name'].replace(' ', '')}"
            mid = write_midi(os.path.join(out, "02_악기후보", f"내파트_{tag}.mid"), tempo,
                             [{"program": s["gm_program"], "notes": notes, "name": s["gm_name"]}])
            w = render(mid, os.path.join(out, "02_악기후보", f"내파트_{tag}.wav"))
            m = to_mp3(w, os.path.join(out, "02_악기후보", f"내파트_{tag}.mp3")) if w else None
            inst_files.append({**s, "midi": os.path.basename(mid), "preview": os.path.basename(m) if m else None})

    # each hand rendered with its own best-fitting instrument
    voice_files = {}
    if not a.no_render:
        for vname, vs in voice_suggestions.items():
            vn = voices[vname]
            items = []
            for s2 in vs["suggestions"][:3]:
                tag = f"{vname}_{s2['key']}"
                m2 = write_midi(os.path.join(out, "02_악기후보", f"{vs['label']}_{s2['gm_name'].replace(' ','')}.mid"),
                                tempo, [{"program": s2["gm_program"], "notes": vn, "name": s2["gm_name"]}])
                w2 = render(m2, os.path.join(out, "02_악기후보", f"{vs['label']}_{s2['gm_name'].replace(' ','')}.wav"))
                p2 = to_mp3(w2, os.path.join(out, "02_악기후보", f"{vs['label']}_{s2['gm_name'].replace(' ','')}.mp3")) if w2 else None
                items.append({**s2, "midi": os.path.basename(m2), "preview": os.path.basename(p2) if p2 else None})
            voice_files[vname] = {"label": vs["label"], "note_count": vs["note_count"],
                                  "range": f"{vs['stats']['lowest']} ~ {vs['stats']['highest']}", "options": items}

    # accompaniment proposals
    dopt = drum_options(bars, tempo)
    bopt = bass_options(bars, chords, tempo)
    popt = pad_option(bars, chords)
    melody_prog = GM.get(a.melody_instrument, (0, "Acoustic Grand Piano"))[0] if a.melody_instrument else 0

    prop = {"drums": {}, "bass": {}, "pad": {}}
    for nm, d in dopt.items():
        mid = write_midi(os.path.join(out, "03_반주후보", f"드럼_{nm}.mid"), tempo,
                         [{"is_drum": True, "notes": drum_notes(d["events"]), "name": f"Drums {nm}"}])
        prev = None
        if not a.no_render:
            mix = write_midi(os.path.join(out, "03_반주후보", f"_mix_드럼_{nm}.mid"), tempo,
                             [{"program": melody_prog, "notes": notes, "name": "Your part"},
                              {"is_drum": True, "notes": drum_notes(d["events"]), "name": "Drums"}])
            w = render(mix, os.path.join(out, "03_반주후보", f"드럼_{nm}_내파트와함께.wav"))
            prev = to_mp3(w, os.path.join(out, "03_반주후보", f"드럼_{nm}_내파트와함께.mp3")) if w else None
            os.remove(mix)
        prop["drums"][nm] = {"description": d["description"], "hits": d["hit_count"],
                             "midi": os.path.basename(mid), "preview": os.path.basename(prev) if prev else None}
    for nm, d in bopt.items():
        mid = write_midi(os.path.join(out, "03_반주후보", f"베이스_{nm}.mid"), tempo,
                         [{"program": GM["finger_bass"][0], "notes": d["notes"], "name": f"Bass {nm}"}])
        prev = None
        if not a.no_render:
            mix = write_midi(os.path.join(out, "03_반주후보", f"_mix_베이스_{nm}.mid"), tempo,
                             [{"program": melody_prog, "notes": notes, "name": "Your part"},
                              {"program": GM["finger_bass"][0], "notes": d["notes"], "name": "Bass"}])
            w = render(mix, os.path.join(out, "03_반주후보", f"베이스_{nm}_내파트와함께.wav"))
            prev = to_mp3(w, os.path.join(out, "03_반주후보", f"베이스_{nm}_내파트와함께.mp3")) if w else None
            os.remove(mix)
        prop["bass"][nm] = {"description": d["description"], "notes": d["note_count"],
                            "midi": os.path.basename(mid), "preview": os.path.basename(prev) if prev else None}
    mid = write_midi(os.path.join(out, "03_반주후보", "패드.mid"), tempo,
                     [{"program": GM["warm_pad"][0], "notes": popt["notes"], "name": "Pad"}])
    prop["pad"]["A"] = {"description": popt["description"], "notes": popt["note_count"],
                        "midi": os.path.basename(mid), "preview": None}

    # one full demo: your part + drums A + bass A + pad, so you hear the whole idea at once
    full = None
    if not a.no_render:
        fmid = write_midi(os.path.join(out, "04_합본", "전체_드럼A_베이스A_패드.mid"), tempo,
                          [{"program": melody_prog, "notes": notes, "name": "Your part"},
                           {"program": GM["finger_bass"][0], "notes": bopt["A"]["notes"], "name": "Bass A"},
                           {"program": GM["warm_pad"][0], "notes": popt["notes"], "name": "Pad"},
                           {"is_drum": True, "notes": drum_notes(dopt["A"]["events"]), "name": "Drums A"}])
        w = render(fmid, os.path.join(out, "04_합본", "전체_드럼A_베이스A_패드.wav"))
        full = to_mp3(w, os.path.join(out, "04_합본", "전체_드럼A_베이스A_패드.mp3")) if w else None

    report = {
        "당신이_연주한_것": {**part, "tempo_used": tempo, "bars": len(bars), **st},
        "조성": key, "어울리는_스케일": scales,
        "마디별_코드": chords,
        "악기_추천": inst_files if inst_files else instruments,
        "손별_악기_추천": voice_files if voice_files else voice_suggestions,
        "반주_후보": prop,
        "합본_미리듣기": os.path.basename(full) if full else None,
        "렌더_엔진": f"FluidSynth + {os.path.basename(SF2)}" if FLUID else "없음",
        "원칙": "멜로디는 당신 것입니다. 이 도구는 반주 후보만 제안하고, 무엇을 쓸지는 당신이 정합니다.",
    }
    with open(os.path.join(out, "리포트.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    write_text_report(out, report)
    print(f"완료 → {out}/읽어보기.txt")
    return report


def write_text_report(out: str, r: dict):
    p = r["당신이_연주한_것"]; k = r["조성"]
    L = []
    L.append("=" * 64)
    L.append("  당신이 연주한 것을 분석한 결과")
    L.append("=" * 64)
    L.append(f"파일            : {p['source_file']}")
    L.append(f"음 개수         : {p['note_count']}개   길이 {p['end_s']}초   {p['bars']}마디")
    L.append(f"템포            : {p['tempo_used']} BPM")
    L.append(f"음역            : {p['lowest']} ~ {p['highest']}  ({p['range_semitones']}반음)")
    L.append(f"동시에 울리는 음 : 평균 {p['mean_polyphony_when_sounding']}개, 최대 {p['max_polyphony']}개")
    L.append(f"초당 음 수      : {p['notes_per_second']}개")
    L.append("")
    L.append(f"조성 추정       : {k['key']}  (신뢰도 {k['confidence']}, 다음 후보 {k['runner_up']})")
    L.append("")
    L.append("- 어울리는 스케일 (여기 안의 음을 쓰면 안전합니다)")
    for s in r["어울리는_스케일"]:
        extra = f"  / 벗어난 음: {', '.join(s['outside_notes'])}" if s["outside_notes"] else ""
        L.append(f"   {s['scale']:<22} 일치 {s['fit_percent']}%   구성음 {' '.join(s['notes'])}{extra}")
    L.append("")
    L.append("- 마디별 코드 (자동 추정이라 틀릴 수 있습니다. 귀로 확인하세요)")
    for c in r["마디별_코드"][:32]:
        L.append(f"   {c['bar']+1:>3}마디  {c['chord']:<8} {c['roman']:<5} 연주한 음: {' '.join(c['notes_played'])}")
    if len(r["마디별_코드"]) > 32:
        L.append(f"   ... 외 {len(r['마디별_코드'])-32}마디 (리포트.json 참고)")
    L.append("")
    L.append("- 이 파트에 어울리는 악기 (02_악기후보 폴더에서 직접 들어보세요)")
    for i, s in enumerate(r["악기_추천"], 1):
        warn = f"  [!] {s['warning']}" if s.get("warning") else ""
        L.append(f"   {i}. {s['gm_name']} (GM {s['gm_program']}) · {s['role']} · 음역적합 {s['range_fit_percent']}%{warn}")
        L.append(f"      {s['why']}")
    L.append("")
    if r.get("손별_악기_추천"):
        L.append("- 양손을 나눠서 본 악기 추천 (각 손을 다른 악기로 바꿀 수 있습니다)")
        for vname, v in r["손별_악기_추천"].items():
            rng = v.get("range", "")
            L.append(f"   [{v['label']}] {v['note_count']}음  {rng}")
            for s2 in v.get("options", v.get("suggestions", []))[:3]:
                L.append(f"      - {s2['gm_name']} (GM {s2['gm_program']}) · {s2['role']}")
        L.append("")
    L.append("- 반주 후보 (03_반주후보 폴더, 전부 당신 파트와 섞어서 들려줍니다)")
    for kind, label in (("drums", "드럼"), ("bass", "베이스"), ("pad", "패드")):
        for nm, d in r["반주_후보"][kind].items():
            L.append(f"   {label} {nm}: {d['description']}")
    L.append("")
    L.append(f"- 전체 합본: 04_합본/{r['합본_미리듣기']}" if r["합본_미리듣기"] else "- 전체 합본: 렌더 안 함")
    L.append("")
    L.append("다음에 할 일")
    L.append("  1) 02_악기후보 를 들어보고 당신 파트를 어떤 악기로 할지 고르세요")
    L.append("  2) 03_반주후보 에서 드럼 1개, 베이스 1개를 고르세요")
    L.append("  3) 고른 것과 바꾸고 싶은 부분을 알려주세요. 그대로 다시 만들어 드립니다")
    L.append("")
    L.append(f"렌더 엔진: {r['렌더_엔진']}")
    L.append(r["원칙"])
    with open(os.path.join(out, "읽어보기.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))


if __name__ == "__main__":
    main()
