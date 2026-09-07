"""MIDI 입출력 — 새 파트(사람 결정 포함)를 .mid 로 저장/로드."""
from __future__ import annotations

from pathlib import Path

import pretty_midi

PROGRAMS = {"bass": 33, "pad": 89, "lead": 81, "keys": 4, "pluck": 45, "melody": 81, "chords": 89}


def events_to_instrument(events: list[dict], name: str, program: int = 0, is_drum: bool = False):
    inst = pretty_midi.Instrument(program=program, is_drum=is_drum, name=name)
    for e in events:
        start = float(e["start"])
        end = float(e.get("end", start + e.get("dur", 0.25)))
        if end <= start:
            end = start + 0.05
        inst.notes.append(pretty_midi.Note(
            velocity=int(max(1, min(127, e.get("velocity", 96)))),
            pitch=int(max(0, min(127, e["pitch"]))), start=start, end=end))
    return inst


def write_midi(parts: dict[str, list[dict]], path: Path, tempo: float = 120.0) -> Path:
    pm = pretty_midi.PrettyMIDI(initial_tempo=float(tempo))
    for name, events in parts.items():
        if not events:
            continue
        is_drum = "drum" in name.lower() or "perc" in name.lower()
        program = PROGRAMS.get(name.split("_")[0], 0)
        pm.instruments.append(events_to_instrument(events, name, program=program, is_drum=is_drum))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pm.write(str(path))
    return path


def read_midi(path: Path) -> dict[str, list[dict]]:
    pm = pretty_midi.PrettyMIDI(str(path))
    out = {}
    for inst in pm.instruments:
        out[inst.name or f"track{len(out)}"] = [
            {"start": n.start, "end": n.end, "dur": n.end - n.start, "pitch": n.pitch, "velocity": n.velocity}
            for n in inst.notes]
    return out


def apply_note_edits(events: list[dict], edits: list[dict]) -> tuple[list[dict], list[dict]]:
    """사람이 지정한 수정 적용.

    edit 형식:
      {"op":"transpose","index":3,"semitones":-1}
      {"op":"delete","index":7}
      {"op":"move","index":2,"delta_sec":0.05}
      {"op":"velocity","index":5,"value":110}
      {"op":"add","start":12.5,"dur":0.5,"pitch":51,"velocity":100}
      {"op":"transpose_range","from":8,"to":12,"semitones":-2}
    반환: (수정된 이벤트, 적용 로그)
    """
    ev = [dict(e) for e in events]
    log = []
    for ed in edits:
        op = ed.get("op")
        try:
            if op == "add":
                ev.append({"start": float(ed["start"]), "dur": float(ed.get("dur", 0.25)),
                           "end": float(ed["start"]) + float(ed.get("dur", 0.25)),
                           "pitch": int(ed["pitch"]), "velocity": int(ed.get("velocity", 96))})
                log.append({**ed, "applied": True})
                continue
            if op == "transpose_range":
                a, b = int(ed["from"]), int(ed["to"])
                moved = 0
                for j in range(a, min(b + 1, len(ev))):
                    if ev[j]:
                        ev[j]["pitch"] = int(ev[j]["pitch"]) + int(ed["semitones"])
                        moved += 1
                log.append({**ed, "applied": moved > 0, "notes_changed": moved,
                            **({} if moved else {"error": "해당 범위에 음이 없습니다"})})
                continue
            i = int(ed["index"])
            if op == "delete":
                ev[i] = None
            elif op == "transpose":
                ev[i]["pitch"] = int(ev[i]["pitch"]) + int(ed["semitones"])
            elif op == "move":
                d = float(ed["delta_sec"])
                ev[i]["start"] += d
                if "end" in ev[i]:
                    ev[i]["end"] += d
            elif op == "velocity":
                ev[i]["velocity"] = int(ed["value"])
            elif op == "length":
                ev[i]["dur"] = float(ed["value"])
                ev[i]["end"] = ev[i]["start"] + float(ed["value"])
            else:
                log.append({**ed, "applied": False, "error": "unknown op"})
                continue
            log.append({**ed, "applied": True})
        except Exception as e:  # noqa: BLE001
            log.append({**ed, "applied": False, "error": f"{type(e).__name__}: {e}"})
    ev = [e for e in ev if e]
    for e in ev:
        e.setdefault("end", e["start"] + e.get("dur", 0.25))
    ev.sort(key=lambda x: (x["start"], x["pitch"]))
    return ev, log
