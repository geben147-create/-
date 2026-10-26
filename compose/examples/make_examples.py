"""세 가지 예시곡을 만듭니다 — 뼈대(사람이 치는 것)와 완성본(반주가 붙은 것)을 쌍으로.

이 예시는 '참고용'입니다. 사용자가 그대로 쓰라는 것이 아니라,
같은 자리에 자기 연주를 넣었을 때 무엇이 가능한지 보여주기 위한 것입니다.
코드 진행은 널리 쓰이는 관용적 진행(I-V-vi-IV 등)이라 특정 곡의 복제가 아닙니다.
"""
from __future__ import annotations
import os, sys, subprocess, shutil, json
import pretty_midi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from midi_theory import GM, NAMES
from compose import (bar_grid, chords_per_bar, drum_options, bass_options, pad_option,
                     drum_notes, write_midi, render, to_mp3, chord_tones)
from midi_theory import estimate_key

N = {n: i for i, n in enumerate(NAMES)}


def note(pc_name: str, octave: int) -> int:
    return 12 * (octave + 1) + N[pc_name]


def build_skeleton(prog, mel, bpm, beats_per_bar=4, chord_octave=3, mel_octave=5, repeats=2):
    """prog: [(chord_name, [pitch-class names of the voicing])] per bar
       mel : [(scale-degree-name, beat_position, duration_in_beats)] per bar, list per bar"""
    beat = 60.0 / bpm
    bar = beat * beats_per_bar
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    piano = pretty_midi.Instrument(program=0, name="Piano (you)")
    b = 0
    for _ in range(repeats):
        for i, (chname, voicing) in enumerate(prog):
            t = b * bar
            for j, pcn in enumerate(voicing):
                oct_ = chord_octave if j == 0 else chord_octave + (1 if N[pcn] < N[voicing[0]] else 0)
                piano.notes.append(pretty_midi.Note(velocity=70, pitch=note(pcn, oct_),
                                                    start=t, end=t + bar * 0.96))
            for (pcn, pos, dur) in mel[i % len(mel)]:
                s = t + (pos - 1) * beat
                o = mel_octave if N[pcn] >= 0 else mel_octave
                piano.notes.append(pretty_midi.Note(velocity=96, pitch=note(pcn, o),
                                                    start=s, end=s + dur * beat * 0.92))
            b += 1
    pm.instruments.append(piano)
    return pm


EXAMPLES = [
    {
        "id": "1_ballad", "title": "예시 1 · 발라드",
        "bpm": 76, "feel": "느리고 넓게. 피아노 + 스트링 + 조용한 드럼",
        "progression_text": "C – G – Am – F  (I – V – vi – IV)",
        "why": "대중음악에서 가장 많이 쓰이는 진행입니다. 어떤 멜로디를 얹어도 잘 받쳐 줍니다. 처음 작곡할 때 안전한 출발점입니다.",
        "melody_instrument": "strings", "drums": "B", "bass": "A", "pad": True,
        "prog": [("C", ["C", "E", "G"]), ("G", ["G", "B", "D"]),
                 ("Am", ["A", "C", "E"]), ("F", ["F", "A", "C"])],
        "mel": [[("E", 1, 2), ("G", 3, 1.5)],
                [("D", 1, 1.5), ("B", 2.5, 1.5), ("G", 4, 1)],
                [("C", 1, 2), ("A", 3, 2)],
                [("A", 1, 1), ("G", 2, 1), ("F", 3, 2)]],
        "repeats": 2, "chord_octave": 3, "mel_octave": 5,
    },
    {
        "id": "2_citypop", "title": "예시 2 · 시티팝 / R&B",
        "bpm": 100, "feel": "로즈 피아노 + 움직이는 베이스 + 셔플 느낌 드럼",
        "progression_text": "Fmaj7 – Em7 – Dm7 – G7  (IVmaj7 – iii7 – ii7 – V7)",
        "why": "7화음을 쓰면 같은 진행도 훨씬 세련되게 들립니다. 한 음만 더 얹으면 되는데 분위기가 크게 바뀝니다.",
        "melody_instrument": "piano_rhodes", "drums": "C", "bass": "C", "pad": False,
        "prog": [("Fmaj7", ["F", "A", "C", "E"]), ("Em7", ["E", "G", "B", "D"]),
                 ("Dm7", ["D", "F", "A", "C"]), ("G7", ["G", "B", "D", "F"])],
        "mel": [[("A", 1, 1), ("C", 2, 1), ("A", 3, 1.5)],
                [("B", 1, 1.5), ("G", 2.5, 1.5)],
                [("A", 1, 1), ("F", 2, 1), ("D", 3, 2)],
                [("F", 1, 1), ("D", 2, 1), ("B", 3, 1), ("G", 4, 1)]],
        "repeats": 2, "chord_octave": 3, "mel_octave": 5,
    },
    {
        "id": "3_synthpop", "title": "예시 3 · 신스팝",
        "bpm": 122, "feel": "신스 리드 + 통통 튀는 베이스 + 16분 하이햇",
        "progression_text": "Am – F – C – G  (i – VI – III – VII)",
        "why": "같은 네 코드라도 템포를 올리고 8분 베이스를 깔면 완전히 다른 장르가 됩니다. 코드보다 리듬이 장르를 결정한다는 예입니다.",
        "melody_instrument": "square_lead", "drums": "C", "bass": "B", "pad": True,
        "prog": [("Am", ["A", "C", "E"]), ("F", ["F", "A", "C"]),
                 ("C", ["C", "E", "G"]), ("G", ["G", "B", "D"])],
        "mel": [[("A", 1, 0.5), ("C", 1.5, 0.5), ("E", 2, 1), ("C", 3, 1)],
                [("F", 1, 0.5), ("A", 1.5, 0.5), ("C", 2, 1), ("A", 3, 1)],
                [("G", 1, 0.5), ("E", 1.5, 0.5), ("C", 2, 1), ("G", 3, 1)],
                [("B", 1, 0.5), ("D", 1.5, 0.5), ("G", 2, 1), ("D", 3, 1)]],
        "repeats": 2, "chord_octave": 3, "mel_octave": 5,
    },
]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
    os.makedirs(out, exist_ok=True)
    manifest = []
    for ex in EXAMPLES:
        d = os.path.join(out, ex["id"])
        os.makedirs(d, exist_ok=True)
        bpm = ex["bpm"]
        pm = build_skeleton(ex["prog"], ex["mel"], bpm, chord_octave=ex["chord_octave"],
                            mel_octave=ex["mel_octave"], repeats=ex["repeats"])
        skel = os.path.join(d, "뼈대_피아노만.mid")
        pm.write(skel)
        notes = [{"pitch": int(n.pitch), "start": float(n.start), "end": float(n.end),
                  "velocity": int(n.velocity)} for n in pm.instruments[0].notes]
        end_s = max(n["end"] for n in notes)
        bars = bar_grid(bpm, end_s)
        key = estimate_key([n["pitch"] for n in notes], [n["end"] - n["start"] for n in notes])
        chords = chords_per_bar(notes, bars, key)
        dopt = drum_options(bars, bpm)
        bopt = bass_options(bars, chords, bpm)
        popt = pad_option(bars, chords)
        mel_prog = GM[ex["melody_instrument"]][0]

        # 뼈대 미리듣기 (피아노 그대로)
        w = render(skel, os.path.join(d, "뼈대_피아노만.wav"))
        skel_mp3 = to_mp3(w, os.path.join(d, "뼈대_피아노만.mp3"), "96k") if w else None

        # 완성본
        tracks = [{"program": mel_prog, "notes": notes, "name": "Your part"},
                  {"program": GM["finger_bass"][0], "notes": bopt[ex["bass"]]["notes"], "name": "Bass"},
                  {"is_drum": True, "notes": drum_notes(dopt[ex["drums"]]["events"]), "name": "Drums"}]
        if ex["pad"]:
            tracks.insert(2, {"program": GM["warm_pad"][0], "notes": popt["notes"], "name": "Pad"})
        full = write_midi(os.path.join(d, "완성본.mid"), bpm, tracks)
        w = render(full, os.path.join(d, "완성본.wav"))
        full_mp3 = to_mp3(w, os.path.join(d, "완성본.mp3"), "96k") if w else None

        manifest.append({**{k: ex[k] for k in ("id", "title", "bpm", "feel", "progression_text", "why",
                                               "melody_instrument", "drums", "bass", "pad")},
                         "key": key["key"], "bars": len(bars), "length_s": round(end_s, 1),
                         "chords": [c["chord"] for c in chords],
                         "skeleton_mp3": skel_mp3, "full_mp3": full_mp3,
                         "skeleton_mid": skel, "full_mid": full,
                         "melody_gm": GM[ex["melody_instrument"]][1]})
        print(f"{ex['title']}: {key['key']}, {len(bars)}마디, {round(end_s,1)}초")
    with open(os.path.join(out, "examples.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return manifest


if __name__ == "__main__":
    main()
