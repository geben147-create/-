"""Arrangement stage. Builds the *pre-master* arrangement from the separated stems plus newly
programmed parts, following the priority list agreed in the brief:
  1. structure re-edit  : new intro (2 bars), 1-bar breakdown before the 2nd changed section,
                          long tail silence trimmed
  2. stem re-arrangement: in 2 chosen sections the original drums/bass are ducked and new
                          drums + bass + pad (chosen A/B/C variant) are layered on the detected
                          beat grid
  3. transitions        : 180 ms gain ramps, riser + hat pick-up into the original start
Everything the human still has to decide is read from human_decisions.json (variant choice,
note edits, bridge, vocal) and defaults are used only so a preview exists.
Output time = original time + intro length (see arrangement_manifest.json for the map)."""
from __future__ import annotations
import os, json
import numpy as np
from audiolib import load_audio, save_wav, write_json, crossfade_gain, db
from analysis import bar_chords, chord_to_midi_root
from proposals import beat_grid, drums_variant, bass_variant, chord_freqs, DRUM_DESCRIPTIONS, BASS_DESCRIPTIONS
from synth import render_drums, render_notes, pad_chord, riser, write_drum_midi, write_note_midi

DEFAULT_DECISIONS = {
    "drums": {"choice": "A", "edits": []},
    "bass": {"choice": "A", "edits": []},
    "pad": {"enabled": True, "level_db": -20.0},
    "original_drums_db": -1.5,
    "original_bass_db": -3.0,
    "intro_bars": 2,
    "breakdown": True,
    "bridge": {"choice": "none"},
    "vocal": {"lead_takes": []},
}


def load_decisions(track_dir: str) -> dict:
    p = os.path.join(track_dir, "human_decisions.json")
    d = json.loads(json.dumps(DEFAULT_DECISIONS))
    if os.path.exists(p):
        user = json.load(open(p, encoding="utf-8"))
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(d.get(k), dict):
                d[k].update(v)
            else:
                d[k] = v
        d["_source"] = "human_decisions.json"
    else:
        d["_source"] = "defaults (no human_decisions.json yet)"
    return d


def apply_note_edits(notes: list[dict], edits: list[dict]) -> list[dict]:
    """edits: [{"index": 12, "action": "transpose", "semitones": -1} | {"index": 4, "action": "remove"}
              | {"index": 7, "action": "shift_ms", "ms": 20} | {"index": 7, "action": "velocity", "vel": 0.6}]"""
    out = [dict(n) for n in notes]
    remove = set()
    for e in edits:
        i = e.get("index")
        if i is None or i < 0 or i >= len(out):
            continue
        a = e.get("action")
        if a == "remove":
            remove.add(i)
        elif a == "transpose":
            out[i]["midi"] = int(out[i]["midi"] + e.get("semitones", 0))
        elif a == "shift_ms":
            d = e.get("ms", 0) / 1000.0
            out[i]["start"] += d; out[i]["end"] += d
        elif a == "velocity":
            out[i]["vel"] = float(e.get("vel", out[i].get("vel", 0.8)))
    return [n for i, n in enumerate(out) if i not in remove]


def apply_drum_edits(events: list[dict], edits: list[dict]) -> list[dict]:
    """edits: [{"index": 40, "action": "remove"} | {"index": 40, "action": "velocity", "vel": 0.5}
              | {"bar": 12, "beat": 2.5, "inst": "kick", "action": "remove_at"}]"""
    out = [dict(e) for e in events]
    remove = set()
    for e in edits:
        a = e.get("action")
        if a in ("remove", "velocity") and e.get("index") is not None and 0 <= e["index"] < len(out):
            if a == "remove":
                remove.add(e["index"])
            else:
                out[e["index"]]["vel"] = float(e.get("vel", 0.5))
        elif a == "remove_at":
            for i, ev in enumerate(out):
                if ev.get("bar") == e.get("bar") and abs(ev.get("beat", -9) - e.get("beat", -1)) < 0.01 and ev["inst"] == e.get("inst"):
                    remove.add(i)
    return [ev for i, ev in enumerate(out) if i not in remove]


def choose_change_sections(sections: list[dict], min_bars: int = 6) -> list[dict]:
    dur = sections[-1]["end"] if sections else 0
    cands = [s for s in sections if s["bars"] >= min_bars and s["label"] not in ("intro", "outro")]
    def pick(lo, hi, prefer="hook"):
        pool = [s for s in cands if lo * dur <= (s["start"] + s["end"]) / 2 <= hi * dur]
        if not pool:
            return None
        pool.sort(key=lambda s: (s["label"] != prefer, s["energy_rank"]))
        return pool[0]
    first = pick(0.30, 0.62)
    second = pick(0.62, 0.95)
    if second is first:
        second = None
    chosen = [s for s in (first, second) if s]
    if not chosen and cands:
        chosen = [max(cands, key=lambda s: s["bars"])]
    return chosen


def rms_db(x):
    return db(float(np.sqrt(np.mean(x ** 2)) + 1e-12))


def arrange(track_dir: str, analysis: dict, stems_dir: str) -> dict:
    dec = load_decisions(track_dir)
    src = os.path.join(track_dir, "00_original", "original.wav")
    x, sr = load_audio(src)
    stems = {k: load_audio(os.path.join(track_dir, stems_dir, f"{k}.wav"), sr)[0] for k in ("vocals", "drums", "bass", "other")}
    n_orig = len(x)
    tempo = analysis["tempo_bpm"]
    bar_len = 60.0 / tempo * 4
    bars = beat_grid(analysis["beat_times"], analysis["downbeat_phase"])
    bchords = [b["chord"] for b in bar_chords(analysis)]
    while len(bchords) < len(bars):
        bchords.append(bchords[-1] if bchords else analysis["key"]["tonic"] + ("m" if analysis["key"]["mode"] == "minor" else ""))
    sections = analysis["sections"]
    changed = choose_change_sections(sections)
    sec_end_bars = {b["bar"] for b in bars for s in sections if abs(b["end"] - s["end"]) < 0.1}

    # ---- 1. structure: intro length, tail trim
    intro_bars = int(dec.get("intro_bars", 2))
    intro_len = intro_bars * bar_len
    off = int(round(intro_len * sr))
    tail = 0.0
    a = np.max(np.abs(x), axis=1); idx = np.where(a > 10 ** (-60 / 20))[0]
    tail_sil = (n_orig - 1 - idx[-1]) / sr if len(idx) else 0
    trim = 0
    if tail_sil > 3.0:
        trim = int((tail_sil - 1.5) * sr)
    n_out = off + n_orig - trim
    T = n_out / sr

    # ---- 2. original bed with gain automation (ducking in changed sections, breakdown)
    g_dr = np.ones(n_orig); g_bs = np.ones(n_orig)
    events_log = []
    for s in changed:
        g_dr *= crossfade_gain(n_orig, sr, s["start"], s["end"], 180, dec["original_drums_db"])
        g_bs *= crossfade_gain(n_orig, sr, s["start"], s["end"], 180, dec["original_bass_db"])
        events_log.append({"type": "stem_duck", "orig_start": s["start"], "orig_end": s["end"],
                           "drums_db": dec["original_drums_db"], "bass_db": dec["original_bass_db"], "ramp_ms": 180})
    breakdown = None
    if dec.get("breakdown", True) and len(changed) >= 2:
        s2 = changed[1]
        bd_start = max(0.0, s2["start"] - bar_len); bd_end = s2["start"]
        g_dr *= crossfade_gain(n_orig, sr, bd_start, bd_end, 120, -14.0)
        g_bs *= crossfade_gain(n_orig, sr, bd_start, bd_end, 120, -8.0)
        breakdown = {"orig_start": round(bd_start, 3), "orig_end": round(bd_end, 3)}
        events_log.append({"type": "breakdown", "orig_start": round(bd_start, 3), "orig_end": round(bd_end, 3), "drums_db": -14, "bass_db": -8})
    bed = (stems["vocals"] + stems["other"] + stems["drums"] * g_dr[:, None] + stems["bass"] * g_bs[:, None])
    bed_out = np.zeros((n_out, 2)); bed_out[off:off + n_orig - trim] = bed[: n_orig - trim]

    # ---- 3. new parts on the beat grid of the changed sections
    parts = {}
    dv, bv = dec["drums"]["choice"], dec["bass"]["choice"]
    drum_events, bass_notes, pad_chunks = [], [], []
    for s in changed:
        sb = [b for b in bars if b["beats"][0] >= s["start"] - 0.05 and b["beats"][0] < s["end"] - 0.05]
        if not sb:
            continue
        ev = drums_variant(dv, sb, sec_end_bars)
        for e in ev:  # tag bar/beat so a human can refer to hits
            bi = max((b for b in sb if b["beats"][0] <= e["time"] + 1e-6), key=lambda b: b["beats"][0], default=sb[0])
            e["bar"] = bi["bar"]; e["beat"] = round(1 + (e["time"] - bi["beats"][0]) / max(1e-6, (bi["end"] - bi["beats"][0])) * 4, 2)
        drum_events += ev
        bass_notes += bass_variant(bv, sb, [bchords[b["bar"]] for b in sb])
        if dec["pad"]["enabled"]:
            for b in sb:
                pad_chunks.append((b["beats"][0], b["end"] - b["beats"][0] + 0.3, bchords[b["bar"]]))
    drum_events = apply_drum_edits(drum_events, dec["drums"].get("edits", []))
    bass_notes = apply_note_edits(bass_notes, dec["bass"].get("edits", []))
    for i, nt in enumerate(bass_notes):
        nt["index"] = i
    for i, e in enumerate(drum_events):
        e["index"] = i

    drums_new = render_drums(drum_events, sr, n_orig / sr)[:n_orig]
    bass_new = render_notes(bass_notes, sr, n_orig / sr, style="warm")[:n_orig]
    pad_new = np.zeros((n_orig, 2))
    for (t0, d, ch) in pad_chunks:
        seg = pad_chord(chord_freqs(ch, 3), d, sr, vel=0.6, attack=0.05, release=0.25)
        i = int(t0 * sr); seg = seg[: n_orig - i]
        if i >= 0 and len(seg):
            pad_new[i:i + len(seg)] += seg

    # level matching against the original stems inside the changed sections
    def sect_mask():
        m = np.zeros(n_orig, dtype=bool)
        for s in changed:
            m[int(s["start"] * sr):int(s["end"] * sr)] = True
        return m
    m = sect_mask()
    levels = {}
    if m.any():
        tgt_dr = rms_db(stems["drums"][m]); tgt_bs = rms_db(stems["bass"][m]); tgt_mix = rms_db(x[m])
        tgt_dr = min(tgt_dr, tgt_mix - 6); tgt_bs = min(tgt_bs, tgt_mix - 8)  # never louder than the mix minus headroom
        if np.any(drums_new[m]):
            g = 10 ** ((tgt_dr - 1.0 - rms_db(drums_new[m])) / 20); drums_new *= g; levels["drums_gain_db"] = round(db(g), 2)
        if np.any(bass_new[m]):
            g = 10 ** ((tgt_bs - 1.5 - rms_db(bass_new[m])) / 20); bass_new *= g; levels["bass_gain_db"] = round(db(g), 2)
        if np.any(pad_new[m]):
            g = 10 ** ((tgt_mix + dec["pad"]["level_db"] - rms_db(pad_new[m])) / 20); pad_new *= g; levels["pad_gain_db"] = round(db(g), 2)
        levels.update(target_drums_rms_db=round(tgt_dr, 2), target_bass_rms_db=round(tgt_bs, 2), section_mix_rms_db=round(tgt_mix, 2))

    # ---- 4. intro: pad on the tonic chord, riser over the last bar, hat pick-up
    key = analysis["key"]
    tonic_chord = key["tonic"] + ("m" if key["mode"] == "minor" else "")
    first_chord = bchords[0] if bchords else tonic_chord
    intro = np.zeros((off, 2))
    if off > 0:
        pd = pad_chord(chord_freqs(first_chord, 3), intro_len, sr, vel=0.7, attack=0.9, release=0.6)[:off]
        intro[: len(pd)] += pd
        rz = riser(bar_len, sr, vel=0.5)[: off]
        intro[off - len(rz):] += rz
        pick = [{"time": intro_len - (60 / tempo) * (1 - k / 4), "inst": "hat", "vel": 0.35 + 0.12 * k} for k in range(4)]
        intro += render_drums(pick, sr, intro_len)[:off]
        peak = float(np.max(np.abs(intro)) + 1e-9)
        intro *= min(1.0, 10 ** (-9 / 20) / peak)  # intro peaks at -9 dBFS
        # match the intro pad level to the start of the original so it doesn't jump
        ref = rms_db(x[: int(2 * sr)]) if n_orig > 2 * sr else -20
        cur = rms_db(intro[int(off * 0.3): int(off * 0.8)]) if off > sr else rms_db(intro)
        intro *= 10 ** (min(0.0, (ref - 4 - cur)) / 20) if cur > ref - 4 else 1.0

    # riser into the second changed section (breakdown)
    riser_track = np.zeros((n_orig, 2))
    if breakdown:
        rz = riser(bar_len, sr, vel=0.45)
        i = int(breakdown["orig_start"] * sr); rz = rz[: n_orig - i]
        riser_track[i:i + len(rz)] += rz * (10 ** ((rms_db(x[m]) - 10 - rms_db(rz) ) / 20) if m.any() else 0.2)

    # ---- 5. place everything on the output timeline
    def place(sig):
        o = np.zeros((n_out, 2)); L = min(len(sig), n_orig - trim); o[off:off + L] = sig[:L]; return o
    parts = {
        "intro_new": np.pad(intro, ((0, n_out - off), (0, 0))),
        f"drums_{dv}": place(drums_new),
        f"bass_{bv}": place(bass_new),
        "pad": place(pad_new),
        "riser": place(riser_track),
    }
    premaster = bed_out + sum(parts.values())
    peak = float(np.max(np.abs(premaster)))
    if peak > 0.98:  # keep 0.2 dB below full scale before mastering
        premaster *= 0.98 / peak
        bed_out *= 0.98 / peak
        for k in parts:
            parts[k] *= 0.98 / peak

    # ---- 6. write files
    ed = os.path.join(track_dir, "04_edits")
    os.makedirs(os.path.join(ed, "new_parts"), exist_ok=True)
    save_wav(os.path.join(ed, "bed_original_stems_automated.wav"), bed_out, sr, subtype="FLOAT")
    for k, v in parts.items():
        if np.any(v):
            save_wav(os.path.join(ed, "new_parts", f"{k}.wav"), v, sr, subtype="FLOAT")
    save_wav(os.path.join(track_dir, "05_mix", "premaster.wav"), premaster, sr, subtype="FLOAT")
    os.makedirs(os.path.join(ed, "midi"), exist_ok=True)
    shifted_ev = [dict(e, time=e["time"] + intro_len) for e in drum_events]
    shifted_nt = [dict(nn, start=nn["start"] + intro_len, end=nn["end"] + intro_len) for nn in bass_notes]
    write_drum_midi(os.path.join(ed, "midi", f"new_drums_{dv}_output_time.mid"), shifted_ev, tempo)
    write_note_midi(os.path.join(ed, "midi", f"new_bass_{bv}_output_time.mid"), shifted_nt, tempo)
    write_json(os.path.join(ed, "midi", "new_notes.json"), {"time_reference": "original time (add intro_len for output time)",
               "intro_len_s": round(intro_len, 4), "drum_events": drum_events, "bass_notes": bass_notes,
               "pad_chords": [{"orig_start": round(t, 3), "dur": round(d, 3), "chord": c} for t, d, c in pad_chunks]})

    manifest = {
        "decisions_used": dec,
        "variant_descriptions": {"drums": DRUM_DESCRIPTIONS[dv], "bass": BASS_DESCRIPTIONS[bv]},
        "tempo_bpm": tempo, "key": key["key"], "bar_len_s": round(bar_len, 4), "bars_total": len(bars),
        "intro": {"bars": intro_bars, "len_s": round(intro_len, 3), "chord": first_chord,
                  "output_range": [0.0, round(intro_len, 3)], "content": "pad + riser + hat pick-up (new)"},
        "original_offset_in_output_s": round(intro_len, 3),
        "tail_trimmed_s": round(trim / sr, 3),
        "changed_sections": [{"section_index": s["index"], "label": s["label"], "bars": s["bars"],
                              "orig_range": [s["start"], s["end"]],
                              "output_range": [round(s["start"] + intro_len, 3), round(s["end"] + intro_len, 3)]} for s in changed],
        "breakdown": ({**breakdown, "output_range": [round(breakdown["orig_start"] + intro_len, 3), round(breakdown["orig_end"] + intro_len, 3)]} if breakdown else None),
        "events": events_log,
        "new_midi_counts": {"drum_events": len(drum_events), "bass_notes": len(bass_notes), "pad_chords": len(pad_chunks)},
        "levels": levels,
        "sections_output_time": [{**s, "start": round(s["start"] + intro_len, 3), "end": round(s["end"] + intro_len, 3)} for s in sections],
        "duration_out_s": round(T, 3), "duration_in_s": round(n_orig / sr, 3),
        "human_still_needed": [
            "Choose drums/bass variant (A/B/C) and edit notes -> human_decisions.json, re-run: python scripts/pipeline.py <track> --from arrange",
            "Hum/sing a new melody for the bridge or hook -> 03_human_raw/, convert with scripts/hum_to_midi.py",
            "Record lead/harmony vocal takes -> 03_human_raw/TAKE_xx.wav, then scripts/vocal_prep.py",
            "Full listening pass of LISTEN_arranged.mp3 and the A/B file",
        ],
    }
    write_json(os.path.join(ed, "arrangement_manifest.json"), manifest)
    return manifest
