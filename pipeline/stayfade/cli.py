"""stayfade CLI — 단계별 실행기.

  python -m stayfade --project DIR init <audio> [--title T --artist A --target-lufs -14]
  python -m stayfade analyze      # 01 분리 + 02 분석 + 03 채보
  python -m stayfade candidates   # 04 후보 생성 + 05 미리듣기 렌더
  python -m stayfade gate         # 06 사람 결정 관문 (템플릿 생성 / 검증)
  python -m stayfade build        # 07 보컬 + 08 믹스·마스터
  python -m stayfade qc           # 09 측정 + A/B
  python -m stayfade evidence     # 10 증빙
  python -m stayfade all          # 위를 순서대로 (gate 에서 멈춤)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from . import analyze as A
from . import evidence as EV
from . import human_gate as HG
from . import midiio, mix, qc, render, separate, transcribe, variants as V, vocal
from .common import (Project, fmt_time, jdump, jload, load_audio, now_iso, save_flac16, save_wav,
                     sha256, to_stereo)

SCALES = {"minor": V.NAT_MINOR, "major": V.MAJOR, "dorian": V.DORIAN, "harmonic_minor": V.HARM_MINOR}


def _proj(args) -> Project:
    return Project(args.project)


STEP_HINT = {
    "project.json": ("init", "python -m stayfade --project {p} init <원본.wav>"),
    "separation.json": ("analyze", "python -m stayfade --project {p} analyze"),
    "analysis.json": ("analyze", "python -m stayfade --project {p} analyze"),
    "candidates.json": ("candidates", "python -m stayfade --project {p} candidates"),
    "human_decisions.json": ("gate", "python -m stayfade --project {p} gate"),
    "arrangement_manifest.json": ("build", "python -m stayfade --project {p} build"),
    "qc.json": ("qc", "python -m stayfade --project {p} qc"),
}


def require(project: Project, *files: str) -> None:
    """이전 단계 산출물이 없으면 무엇을 먼저 해야 하는지 알려주고 종료한다."""
    missing = [f for f in files if not (project.root / f).exists()]
    if not missing:
        return
    lines = [f"⛔ 아직 실행하지 않은 단계가 있습니다: {project.root}"]
    for f in missing:
        step, cmd = STEP_HINT.get(f, ("?", "?"))
        lines.append(f"   · {f} 없음 → 먼저 실행하세요:  {cmd.format(p=project.root)}")
    if not (project.root / "project.json").exists():
        lines.append("   (프로젝트 폴더 경로가 맞는지도 확인하세요. --project 로 지정합니다)")
    sys.exit("\n".join(lines))


# ---------- 00 ----------
def cmd_init(args):
    p = Project(args.project)
    src = Path(args.audio).resolve()
    if not src.exists():
        sys.exit(f"입력 파일이 없습니다: {src}")
    dest = p.dir("original") / src.name
    if not dest.exists() or sha256(src) != sha256(dest):
        dest.write_bytes(src.read_bytes())
    h = sha256(dest)
    from .common import audio_info
    info = audio_info(dest)
    existing = p.info() if (p.root / "project.json").exists() else {}
    meta = {
        "schema": "stayfade/project/1",
        "title": args.title or src.stem,
        "artist": args.artist or "(unset)",
        "created_at": now_iso(),
        "source_file": str(dest),
        "source_original_path": str(src),
        "source_hash": h,
        "source_info": info,
        "target_lufs": args.target_lufs,
        "side_gain": args.side_gain,
        "ceiling_dbtp": args.ceiling,
        "distributor_spec": args.distributor,
        "source_description": args.source_description,
        "rights_evidence": args.rights_evidence,
        "seed": args.seed,
        "listening_status": "PENDING",
        "rights_status": "UNVERIFIED",
        "submission_status": "NOT SUBMITTED",
        "warning_ko": "원본 파일은 00_original 에서 수정하지 마세요. 모든 작업은 사본에서 합니다.",
    }
    if existing:
        # 같은 프로젝트에 init 을 다시 돌려도 사람이 채워 넣은 값(권리 증빙·청취 상태 등)을 지우지 않는다
        explicit = {a.split("=")[0].lstrip("-").replace("-", "_") for a in sys.argv[1:] if a.startswith("--")}
        keep = {"artist", "rights_evidence", "source_description", "listening_status", "rights_status",
                "submission_status", "target_lufs", "side_gain", "ceiling_dbtp", "distributor_spec", "seed",
                "title"}
        flag_for = {"target_lufs": "target_lufs", "side_gain": "side_gain", "ceiling_dbtp": "ceiling",
                    "distributor_spec": "distributor"}
        for k in keep:
            if k in existing and existing[k] not in (None, "") and flag_for.get(k, k) not in explicit:
                meta[k] = existing[k]
        meta["created_at"] = existing.get("created_at", meta["created_at"])
        meta["reinitialised_at"] = now_iso()
        p.log("기존 project.json 의 사용자 입력값(권리 증빙·상태 등)을 유지했습니다.")
    jdump(meta, p.root / "project.json")
    p.set_state("00_init", "ok", source_hash=h)
    p.log(f"init 완료 · {info['duration_sec']}초 · {info['samplerate']}Hz · {info['channels']}ch · sha256={h[:16]}…")
    print(f"프로젝트: {p.root}")
    return meta


# ---------- 01-03 ----------
def cmd_analyze(args):
    p = _proj(args)
    require(p, "project.json")
    meta = p.info()
    src = Path(meta["source_file"])
    sep = separate.run(p, src, prefer=args.separator)
    jdump(sep, p.root / "separation.json")
    p.set_state("01_separate", "ok", engine=sep["engine"])

    y, sr = load_audio(src, mono=True)
    mono = y[0]
    p.log("분석: BPM/키/섹션/코드")
    tempo = A.estimate_tempo_beats(mono, sr)
    bass_mono = None
    bass_path = sep["stems"].get("bass")
    if bass_path and Path(bass_path).exists():
        by, _ = load_audio(bass_path, sr=sr, mono=True)
        bass_mono = by[0]
    key = A.estimate_key(mono, sr, bass_mono=bass_mono)
    if getattr(args, "key", None):
        try:
            key = A.override_key(key, args.key)
        except ValueError:
            sys.exit(f"⛔ 조성을 해석할 수 없습니다: {args.key}\n"
                     "   이렇게 적어주세요:  Ebm  Gb  C#m  A  Fm  (m 이 붙으면 단조)\n"
                     f"   자동 추정값은 {key['key']} 입니다. 그대로 쓰려면 --key 를 빼세요.")
        p.log(f"조성 수동 지정: {key['key']}")
    bars = A.downbeats_from_beats(tempo["beat_times"], args.beats_per_bar,
                                  duration=len(mono) / sr)
    sections = A.estimate_sections(mono, sr, bars)
    chords = A.estimate_chords(mono, sr, bars, key["tonic_pc"], key["mode"])
    analysis = {"schema": "stayfade/analysis/1", "sr": sr, "duration_sec": round(len(mono) / sr, 3),
                "tempo": tempo, "key": key, "beats_per_bar": args.beats_per_bar,
                "bar_times": bars, "bar_count": len(bars), "sections": sections, "chords": chords,
                "caveat_ko": "BPM·키·코드·섹션은 모두 자동 추정입니다. 미리듣기로 확인하세요."}
    jdump(analysis, p.root / "analysis.json")
    p.set_state("02_analyze", "ok", bpm=tempo["bpm"], key=key["key"])
    if len(bars) < 8 or analysis["duration_sec"] < 20:
        print(f"⚠ 곡이 짧거나({analysis['duration_sec']}초) 마디를 적게 찾았습니다({len(bars)}마디). "
              "편곡 후보가 빈약해집니다. 20초 이상, 8마디 이상 되는 파일을 권합니다.")

    tr = {}
    if not args.no_transcribe:
        tr = transcribe.run(p, sep["stems"])
        jdump({k: {kk: vv for kk, vv in v.items() if kk != "events"} for k, v in tr.items()},
              p.root / "transcription_summary.json")
        for k, v in tr.items():
            if "events" in v:
                jdump(v["events"], p.dir("midi") / f"{k}_events.json")
        p.set_state("03_transcribe", "ok", stems=list(tr))
    print(f"BPM {tempo['bpm']} · 키 {key['key']} (신뢰도 {key['confidence']}"
          f"{', 나란한조 모호 → 귀로 확인 필요' if key.get('ambiguous') and not key.get('manual') else ''})"
          f" · 마디 {len(bars)} · 섹션 {len(sections)}")
    if key.get("ambiguous") and not key.get("manual"):
        print(f"  ⚠ {key['relative_pair'][0]} / {key['relative_pair'][1]} 중 하나입니다. "
              f"틀리면 편곡이 전부 불협이 됩니다 → `analyze --key {key['relative_pair'][1]}` 로 지정 가능")
    for s in sections:
        print(f"  [{s['index']}] {fmt_time(s['start'])}–{fmt_time(s['end'])} {s['label']} ({s['bars']}마디)")
    return analysis


# ---------- 04-05 ----------
def cmd_candidates(args):
    p = _proj(args)
    require(p, "project.json", "analysis.json")
    meta, an = p.info(), jload(p.root / "analysis.json")
    sr = an["sr"]
    seed = meta.get("seed", 7)
    bar_times = an["bar_times"]
    if len(bar_times) < 3:
        sys.exit("마디를 3개 이상 찾지 못했습니다. --beats-per-bar 를 조정하거나 다른 곡으로 시도하세요.")
    bar_len = float(np.median(np.diff(bar_times)))
    bars = [(bar_times[i], bar_times[i] + bar_len) for i in range(len(bar_times))]
    tonic, mode = an["key"]["tonic_pc"], an["key"]["mode"]
    scale = SCALES["minor" if mode == "minor" else "major"]
    chord_roots = [c["root_pc"] for c in an["chords"]] or [tonic]

    # 미리듣기 구간: 가장 에너지가 높은 섹션 중심 8마디
    focus_start = 0
    if an["sections"]:
        best = max(an["sections"], key=lambda s: s.get("rms", 0))
        focus_start = next((i for i, t in enumerate(bar_times) if t >= best["start"]), 0)
    focus = bars[focus_start: focus_start + 8] or bars[:8]
    preview_sec = (focus[-1][1] - focus[0][0]) + 1.0

    render_dir = p.dir("render")
    var_dir = p.dir("variants")
    groups, previews = {}, []

    def preview(name, parts, offset):
        shifted = {k: [{**e, "start": e["start"] - offset,
                        "end": e.get("end", e["start"] + e.get("dur", .25)) - offset} for e in v]
                   for k, v in parts.items()}
        layers = render.render_parts(shifted, sr, preview_sec)
        y = render.mixdown(layers, int(preview_sec * sr))
        peak = float(np.abs(y).max()) or 1.0
        y = y * (0.7 / peak)
        path = save_wav(render_dir / f"{name}.wav", y, sr)
        previews.append(str(path))
        return str(path)

    # 드럼
    opts = []
    for key_ in V.DRUM_PATTERNS:
        ev = V.make_drums(key_, focus, seed=seed + 11)
        midiio.write_midi({f"drums_{key_}": ev}, var_dir / f"drums_{key_}.mid", an["tempo"]["bpm"])
        opts.append({"id": key_, "label_ko": V.DRUM_PATTERNS[key_]["label_ko"],
                     "note_count": len(ev), "midi": str(var_dir / f"drums_{key_}.mid"),
                     "preview": preview(f"drums_{key_}", {"drums": ev}, focus[0][0])})
    groups["drums"] = {"question_ko": "드럼 패턴 A/B/C 중 어느 것이 곡에 맞습니까?", "options": opts}

    # 베이스
    opts = []
    for key_ in V.BASS_STYLES:
        ev = V.make_bass(key_, focus, chord_roots[focus_start:] or chord_roots, scale, tonic, seed=seed + 23)
        midiio.write_midi({f"bass_{key_}": ev}, var_dir / f"bass_{key_}.mid", an["tempo"]["bpm"])
        opts.append({"id": key_, "label_ko": V.BASS_STYLES[key_], "note_count": len(ev),
                     "midi": str(var_dir / f"bass_{key_}.mid"),
                     "preview": preview(f"bass_{key_}", {"bass": ev}, focus[0][0])})
    groups["bass"] = {"question_ko": "베이스 A/B/C 중 어느 것이 좋습니까? 음 하나라도 직접 고쳐보세요.", "options": opts}

    # 코드 재화성
    opts = []
    for key_ in ["A_diatonic_sub", "B_borrowed", "C_pedal_sus"]:
        ch = V.reharmonize(chord_roots[:8] or [tonic], tonic, mode, key_)
        pad = V.make_pad(ch, focus, seed=seed + 31)
        midiio.write_midi({f"chords_{key_}": pad}, var_dir / f"chords_{key_}.mid", an["tempo"]["bpm"])
        opts.append({"id": key_, "label_ko": {"A_diatonic_sub": "A · 대리코드 (i↔III, iv↔VI)",
                                              "B_borrowed": "B · 차용화음 (v→V, IV/iv 교체)",
                                              "C_pedal_sus": "C · 페달 + sus (긴장 유지)"}[key_],
                     "progression": [c["chord"] for c in ch], "midi": str(var_dir / f"chords_{key_}.mid"),
                     "preview": preview(f"chords_{key_}", {"pad": pad}, focus[0][0])})
    groups["chords"] = {"question_ko": "재화성 후보 — 원곡 보컬과 부딪히지 않는지 꼭 들어보세요.", "options": opts}

    # 브리지
    opts = []
    bridge_bars = args.bridge_bars
    for key_ in V.BRIDGE_SHAPES:
        br = V.make_bridge(key_, 0.0, an["tempo"]["bpm"], bridge_bars, tonic, scale, seed=seed + 47)
        midiio.write_midi({f"bridge_melody_{key_}": br["melody"], f"bridge_bass_{key_}": br["bass"],
                           f"bridge_pad_{key_}": br["pad"]}, var_dir / f"bridge_{key_}.mid", an["tempo"]["bpm"])
        jdump(br, var_dir / f"bridge_{key_}.json")
        opts.append({"id": key_, "label_ko": br["label_ko"], "bars": bridge_bars,
                     "progression": [c["chord"] for c in br["chords"]],
                     "midi": str(var_dir / f"bridge_{key_}.mid"),
                     "preview": preview(f"bridge_{key_}", {"melody": br["melody"], "bass": br["bass"],
                                                           "pad": br["pad"]}, 0.0)})
    groups["bridge"] = {"question_ko": f"새 브리지 {bridge_bars}마디 후보 — 직접 허밍한 멜로디로 바꾸면 더 좋습니다.",
                        "options": opts}

    # 구조
    struct = V.structure_options(an["sections"], args.intro_sec, an["tempo"]["bpm"], an["beats_per_bar"])
    groups["structure"] = {"question_ko": "구조 변경 폭을 고르세요.",
                           "options": [{"id": s["variant"], "label_ko": s["label_ko"],
                                        "risk_ko": s["risk_ko"], "spec": s} for s in struct]}

    cands = {"schema": "stayfade/candidates/1", "created_at": now_iso(), "seed": seed,
             "preview_window": {"start": round(focus[0][0], 3), "end": round(focus[-1][1], 3),
                                "bars": len(focus)},
             "groups": groups,
             "note_ko": "여기 있는 것은 전부 자동 생성 후보입니다. 고르고 고치는 것은 사람이 합니다."}
    jdump(cands, p.root / "candidates.json")
    p.set_state("04_candidates", "ok", previews=len(previews))
    print(f"후보 {sum(len(g['options']) for g in groups.values())}개 · 미리듣기 {len(previews)}개 → {render_dir}")
    return cands


# ---------- 06 ----------
def cmd_gate(args):
    p = _proj(args)
    require(p, "candidates.json")
    cands = jload(p.root / "candidates.json")
    path = p.root / "human_decisions.json"
    dec, ready = HG.load_or_create(cands, path)
    problems = HG.validate(dec, cands) if dec.get("status") == "DECIDED" else []
    if not ready or problems:
        print(f"⏸  사람 결정 대기: {path}")
        for g in dec["decisions"]:
            gid = g.get("id", "?")
            question = g.get("question_ko") or (cands.get("groups", {}).get(gid, {}).get("question_ko", ""))
            print(f"  - {gid}: {question}")
            options = g.get("options") or cands.get("groups", {}).get(gid, {}).get("options", [])
            for o in options:
                print(f"      {o.get('id','?')}  {o.get('label_ko','')}")
        if problems:
            print("문제: " + "; ".join(problems))
        p.set_state("06_gate", "waiting")
        return {"ready": False, "path": str(path), "problems": problems}
    p.set_state("06_gate", "ok", decided_by=dec.get("decided_by"))
    print(f"✅ 결정 확인됨 (decided_by={dec.get('decided_by')})")
    return {"ready": True, "decisions": dec}


# ---------- 07-08 ----------
def cmd_build(args):
    p = _proj(args)
    require(p, "project.json", "analysis.json", "candidates.json", "separation.json", "human_decisions.json")
    meta, an = p.info(), jload(p.root / "analysis.json")
    cands = jload(p.root / "candidates.json")
    sep = jload(p.root / "separation.json")
    dec, ready = HG.load_or_create(cands, p.root / "human_decisions.json")
    problems = HG.validate(dec, cands)
    if not ready or problems:
        lines = ["⛔ human_decisions.json 을 아직 쓸 수 없습니다:"]
        if dec.get("status") != "DECIDED":
            lines.append("   · status 가 DECIDED 가 아닙니다")
        lines += [f"   · {m}" for m in problems]
        lines.append(f"   파일: {p.root / 'human_decisions.json'}")
        sys.exit("\n".join(lines))
    choice = {g["id"]: g["choice"] for g in dec["decisions"]}
    edits = {g["id"]: g.get("note_edits", []) for g in dec["decisions"]}
    sr = an["sr"]
    src = Path(meta["source_file"])
    y, _ = load_audio(src, sr=sr)
    y = to_stereo(y)
    total = y.shape[1] / sr

    bar_times = an["bar_times"]
    bar_len = float(np.median(np.diff(bar_times)))
    bars = [(t, t + bar_len) for t in bar_times]
    tonic, mode = an["key"]["tonic_pc"], an["key"]["mode"]
    scale = SCALES["minor" if mode == "minor" else "major"]
    chord_roots = [c["root_pc"] for c in an["chords"]] or [tonic]

    # 새 파트를 곡 전체 길이로 생성 (선택된 변형)
    parts, edit_log = {}, {}
    drum_ev = V.make_drums(choice["drums"], bars, seed=meta.get("seed", 7) + 11)
    bass_ev = V.make_bass(choice["bass"], bars, chord_roots, scale, tonic, seed=meta.get("seed", 7) + 23)
    ch = V.reharmonize(chord_roots, tonic, mode, choice["chords"])
    pad_ev = V.make_pad(ch, bars, seed=meta.get("seed", 7) + 31)
    for name, ev, key_ in [("drums", drum_ev, "drums"), ("bass", bass_ev, "bass"), ("pad", pad_ev, "chords")]:
        if edits.get(key_):
            ev, log = midiio.apply_note_edits(ev, edits[key_])
            edit_log[name] = log
        parts[name] = ev

    bridge_opt = next((o for o in cands["groups"]["bridge"]["options"] if o["id"] == choice["bridge"]), None)
    bridge_bars = args.bridge_bars if getattr(args, "bridge_bars", None) else (bridge_opt or {}).get("bars", 8)
    if bridge_opt and args.bridge_bars and args.bridge_bars != bridge_opt.get("bars"):
        p.log(f"⚠ --bridge-bars {args.bridge_bars} 는 미리듣기({bridge_opt.get('bars')}마디)와 다릅니다. "
              "들어본 것과 다른 길이가 최종본에 들어갑니다.")
    struct_spec = next(o["spec"] for o in cands["groups"]["structure"]["options"] if o["id"] == choice["structure"])
    intro_bars = struct_spec["intro_bars"]
    intro_sec = intro_bars * bar_len
    br = V.make_bridge(choice["bridge"], 0.0, an["tempo"]["bpm"], bridge_bars, tonic, scale,
                       seed=meta.get("seed", 7) + 47)
    if edits.get("bridge"):
        br["melody"], log = midiio.apply_note_edits(br["melody"], edits["bridge"])
        edit_log["bridge_melody"] = log

    # 사람이 녹음한 파트가 있으면 브리지 멜로디 대신 사용
    human_files = (dec.get("human_performance") or {}).get("files") or []
    processed_vocals = []
    for f in human_files:
        src_take = Path(f)
        if not src_take.exists():
            p.log(f"⚠ 녹음 파일을 찾을 수 없습니다: {src_take}")
            continue
        # 원본 테이크를 프로젝트 안에 보존하고 해시를 남긴 뒤, 사본을 처리합니다
        kept = p.dir("human") / src_take.name
        if not kept.exists() or sha256(src_take) != sha256(kept):
            kept.write_bytes(src_take.read_bytes())
        take_hash = sha256(kept)
        scale_pcs = [(tonic + s) % 12 for s in scale]
        r = vocal.process_take(kept, p.dir("edit") / "vocal", sr_target=sr,
                               scale_pcs=scale_pcs, beat_times=an["tempo"]["beat_times"],
                               do_harmony=args.harmony)
        r["raw_kept"] = str(kept)
        r["raw_sha256"] = take_hash
        r["raw_source"] = str(src_take)
        processed_vocals.append(r)
    jdump(processed_vocals, p.root / "vocal_processing.json")

    # 렌더
    new_layers = render.render_parts(parts, sr, total,
                                     gains_db={"drums": -3.0, "bass": -4.0, "pad": -9.0})
    for name, ylayer in new_layers.items():
        save_wav(p.dir("edit") / f"new_{name}.wav", ylayer, sr)

    # 마디 시각은 곡 전체 기준(절대 시각)이라 인트로 버퍼(0초부터)에 쓰려면 오프셋을 빼야 합니다.
    # 빼지 않으면 인트로 앞부분이 통째로 무음이 됩니다.
    intro_offset = bars[0][0] if bars else 0.0

    def _shift(events, offset):
        return [{**e, "start": e["start"] - offset,
                 "end": e.get("end", e["start"] + e.get("dur", 0.25)) - offset} for e in events]

    intro_layers = render.render_parts(
        {"pad": _shift(V.make_pad(ch[:intro_bars] or ch[:1], bars[:intro_bars], seed=meta.get("seed", 7) + 5),
                       intro_offset),
         "drums": _shift(V.make_drums(choice["drums"], bars[max(0, intro_bars - 1):intro_bars],
                                      seed=meta.get("seed", 7) + 3),
                         intro_offset + max(0, intro_bars - 1) * bar_len)},
        sr, intro_sec, gains_db={"pad": -8.0, "drums": -6.0})
    intro = render.mixdown(intro_layers, int(intro_sec * sr))
    intro = intro * np.linspace(0.2, 1.0, intro.shape[1], dtype=np.float32)

    bridge_layers = render.render_parts({"melody": br["melody"], "bass": br["bass"], "pad": br["pad"]},
                                        sr, br["end"] - br["start"] + 0.5,
                                        gains_db={"melody": -6.0, "bass": -4.0, "pad": -9.0})
    bridge = render.mixdown(bridge_layers, int((br["end"] - br["start"]) * sr))
    if processed_vocals:
        vy, _ = load_audio(processed_vocals[0]["output"], sr=sr)
        vy = to_stereo(vy)
        m = min(vy.shape[1], bridge.shape[1])
        bridge[:, :m] += vy[:, :m] * 0.9

    # 원곡 바탕에서 기존 드럼/베이스 부분 감산
    stems = {k: load_audio(v, sr=sr)[0] for k, v in sep["stems"].items() if Path(v).exists()}
    regions = [{"start": s["start"], "end": s["end"]} for s in an["sections"]
               if s["label"] in ("chorus?", "verse?")][: args.max_regions] or None
    base = mix.subtract_stems(y, stems, {"drums": args.drum_reduce_db, "bass": args.bass_reduce_db},
                              sr, regions=regions)

    bridge_at = an["sections"][-1]["start"] if len(an["sections"]) > 1 else total * 0.75
    arranged, timeline = mix.assemble(base, sr, new_layers, intro=intro, bridge=bridge,
                                      bridge_at=bridge_at, xfade_ms=args.xfade_ms)
    save_wav(p.dir("mix") / "arranged_premaster.wav", arranged, sr)
    mastered, mlog = mix.master_chain(arranged, sr, target_lufs=meta["target_lufs"],
                                      side_gain=meta["side_gain"], ceiling_db=meta["ceiling_dbtp"])
    master_wav = save_wav(p.dir("master") / "arranged_master_44k1_24bit.wav", mastered, sr, subtype="PCM_24")
    flac = save_flac16(p.dir("master") / "distributor_candidate_44k1_16bit.flac", mastered, sr)
    midiio.write_midi({**{f"new_{k}": v for k, v in parts.items()},
                       "bridge_melody": br["melody"], "bridge_bass": br["bass"], "bridge_pad": br["pad"]},
                      p.dir("edit") / "new_parts.mid", an["tempo"]["bpm"])

    failed_edits = [(name, e) for name, log in edit_log.items() for e in log if not e.get("applied")]
    for name, e in failed_edits:
        p.log(f"⚠ 적용되지 않은 노트 수정 ({name}): {e} — 증빙에는 '적용됨'으로 세지 않습니다")

    manifest = {"schema": "stayfade/arrangement/1", "created_at": now_iso(), "choices": choice,
                "decided_by": dec.get("decided_by"), "note_edits_applied": edit_log,
                "intro": {"bars": intro_bars, "seconds": round(intro_sec, 3)},
                "bridge": {"variant": choice["bridge"], "bars": bridge_bars,
                           "inserted_at_sec": round(bridge_at, 3)},
                "stem_reduction_db": {"drums": args.drum_reduce_db, "bass": args.bass_reduce_db},
                "reduction_regions": regions, "transition_ms": args.xfade_ms,
                "new_note_counts": {k: len(v) for k, v in parts.items()} | {"bridge_melody": len(br["melody"])},
                "human_vocal_takes": [{"raw": r.get("raw_kept"), "raw_sha256": r.get("raw_sha256"),
                                       "processed": r["output"]} for r in processed_vocals],
                "note_edits_failed": [{"part": n, **e} for n, e in failed_edits],
                "timeline": timeline, "master_chain": mlog,
                "outputs": {"premaster": str(p.dir("mix") / "arranged_premaster.wav"),
                            "master_wav": str(master_wav), "flac16": str(flac),
                            "new_parts_midi": str(p.dir("edit") / "new_parts.mid")},
                "caveat_ko": "새 MIDI 는 자동 생성·편집 데이터입니다. 인간 실연이 아닙니다."}
    jdump(manifest, p.root / "arrangement_manifest.json")
    p.set_state("08_mixmaster", "ok", master=str(master_wav))
    print(f"마스터: {master_wav}\nFLAC: {flac}\n길이 {timeline['total_sec']}초")
    return manifest


# ---------- 09 ----------
def cmd_qc(args):
    p = _proj(args)
    require(p, "project.json", "analysis.json", "arrangement_manifest.json")
    meta, an = p.info(), jload(p.root / "analysis.json")
    arr = jload(p.root / "arrangement_manifest.json")
    src = Path(meta["source_file"])
    master = Path(arr["outputs"]["master_wav"])
    flac = Path(arr["outputs"]["flac16"])
    before = qc.measure(src)
    after = qc.measure(master)
    after_flac = qc.measure(flac)
    spec = qc.check_spec(after_flac, meta.get("distributor_spec", "routenote"))
    ab_at_src = min(an["sections"][1]["start"] if len(an["sections"]) > 1 else 30.0,
                    max(0.0, before["duration_sec"] - 30))
    ab = render.ab_preview(src, master, p.dir("qc") / "AB_original_vs_arranged.wav",
                           at_original=ab_at_src,
                           at_arranged=ab_at_src + arr["intro"]["seconds"], seconds=args.ab_seconds)
    out = {"schema": "stayfade/qc/1", "measured_at": now_iso(), "before": before, "after": after,
           "after_flac16": after_flac, "comparison": qc.compare(before, after), "spec_check": spec,
           "ab_preview": ab,
           "needs_human_check_ko": ["전체 청취 (박자/불협화음/발음/분리 아티팩트)", "모노 청취",
                                    "가사·보컬·샘플 권리", "커버·메타데이터"]}
    jdump(out, p.root / "qc.json")
    p.set_state("09_qc", "ok", verdict=spec["verdict"])
    print(f"QC {spec['verdict']} · 원본 {before['lufs_i']} LUFS → 편곡 {after['lufs_i']} LUFS · "
          f"TP {after['true_peak_dbtp']} dBTP · 상관 {after['stereo']['overall']}")
    for c in spec["checks"]:
        if not c["pass"]:
            print(f"  ⚠ {c['check']}: {c['detail']}")
    return out


# ---------- 10 ----------
def cmd_evidence(args):
    p = _proj(args)
    require(p, "project.json")
    meta = p.info()
    dec = jload(p.root / "human_decisions.json") if (p.root / "human_decisions.json").exists() else {}
    qcd = jload(p.root / "qc.json") if (p.root / "qc.json").exists() else {}
    sep = jload(p.root / "separation.json") if (p.root / "separation.json").exists() else {}
    arr = jload(p.root / "arrangement_manifest.json") if (p.root / "arrangement_manifest.json").exists() else {}
    applied_edits = sum(1 for log in (arr.get("note_edits_applied") or {}).values()
                        for e in log if e.get("applied"))
    failed_edits = len(arr.get("note_edits_failed") or [])
    res = EV.build(p, meta, dec, qcd,
                   extra={"separation_engine": sep.get("engine"), "transcription": "Basic Pitch (참고용)",
                          "candidates": f"drums/bass/chords/bridge/structure, seed={meta.get('seed')}",
                          "applied_note_edits": applied_edits, "failed_note_edits": failed_edits,
                          "human_takes": arr.get("human_vocal_takes") or []})
    jdump({"checklist": EV.checklist(), "arrangement_choices": arr.get("choices")},
          p.dir("evidence") / "submission_checklist.json")
    p.set_state("10_evidence", "ok", files=res["hashed_files"])
    print(f"증빙 {res['hashed_files']}개 파일 해시 · {res['manifest']}")
    for w in res["warnings_ko"]:
        print(f"  ⚠ {w}")
    return res


def cmd_all(args):
    cmd_analyze(args)
    cmd_candidates(args)
    g = cmd_gate(args)
    if not g["ready"]:
        print("\n👉 human_decisions.json 을 채운 뒤 `build → qc → evidence` 를 실행하세요.")
        return g
    cmd_build(args)
    cmd_qc(args)
    return cmd_evidence(args)


def build_parser():
    ap = argparse.ArgumentParser(prog="stayfade", description="AI 파생곡 재편곡·QC·증빙 파이프라인")
    ap.add_argument("--project", default="./work/project", help="프로젝트 폴더")
    ap.add_argument("--debug", action="store_true", help="오류가 나면 전체 추적 정보를 그대로 보여줍니다")
    sub = ap.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init"); i.add_argument("audio")
    i.add_argument("--title"); i.add_argument("--artist")
    i.add_argument("--target-lufs", type=float, default=-14.0)
    i.add_argument("--side-gain", type=float, default=1.0)
    i.add_argument("--ceiling", type=float, default=-1.0)
    i.add_argument("--distributor", default="routenote", choices=list(qc.DISTRIBUTOR_SPECS))
    i.add_argument("--source-description", default="AI music generator output (fill in service, plan, date)")
    i.add_argument("--rights-evidence", default="")
    i.add_argument("--seed", type=int, default=7)
    i.set_defaults(func=cmd_init)

    a = sub.add_parser("analyze")
    a.add_argument("--separator", default="auto", choices=["auto", "demucs", "fallback"])
    a.add_argument("--beats-per-bar", type=int, default=4)
    a.add_argument("--no-transcribe", action="store_true")
    a.add_argument("--key", help="조성 수동 지정 (예: Ebm, Gb, C#m). 자동 추정을 덮어씁니다.")
    a.set_defaults(func=cmd_analyze)

    c = sub.add_parser("candidates")
    c.add_argument("--bridge-bars", type=int, default=8)
    c.add_argument("--intro-sec", type=float, default=4.0)
    c.set_defaults(func=cmd_candidates)

    g = sub.add_parser("gate"); g.set_defaults(func=cmd_gate)

    b = sub.add_parser("build")
    b.add_argument("--bridge-bars", type=int, default=None,
                   help="기본값은 미리듣기에서 들은 브리지 길이입니다. 지정하면 그 값으로 덮어씁니다")
    b.add_argument("--drum-reduce-db", type=float, default=-1.5)
    b.add_argument("--bass-reduce-db", type=float, default=-3.0)
    b.add_argument("--xfade-ms", type=float, default=180.0)
    b.add_argument("--max-regions", type=int, default=3)
    b.add_argument("--harmony", action="store_true")
    b.set_defaults(func=cmd_build)

    q = sub.add_parser("qc"); q.add_argument("--ab-seconds", type=float, default=24.0); q.set_defaults(func=cmd_qc)
    e = sub.add_parser("evidence"); e.set_defaults(func=cmd_evidence)

    al = sub.add_parser("all")
    al.add_argument("--separator", default="auto", choices=["auto", "demucs", "fallback"])
    al.add_argument("--beats-per-bar", type=int, default=4)
    al.add_argument("--no-transcribe", action="store_true")
    al.add_argument("--key", help="조성 수동 지정 (예: Ebm)")
    al.add_argument("--bridge-bars", type=int, default=8)
    al.add_argument("--intro-sec", type=float, default=4.0)
    al.add_argument("--drum-reduce-db", type=float, default=-1.5)
    al.add_argument("--bass-reduce-db", type=float, default=-3.0)
    al.add_argument("--xfade-ms", type=float, default=180.0)
    al.add_argument("--max-regions", type=int, default=3)
    al.add_argument("--harmony", action="store_true")
    al.add_argument("--ab-seconds", type=float, default=24.0)
    al.set_defaults(func=cmd_all)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    if getattr(args, "debug", False):
        args.func(args)
        return
    try:
        args.func(args)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit("\n중단했습니다. 지금까지 만든 파일은 프로젝트 폴더에 남아 있습니다.")
    except FileNotFoundError as e:
        sys.exit(f"⛔ 파일을 찾을 수 없습니다: {e.filename or e}\n"
                 "   경로를 확인하세요. 경로에 공백이 있으면 따옴표로 감싸야 합니다.")
    except MemoryError:
        sys.exit("⛔ 메모리가 부족합니다. 곡을 짧게 자르거나 --no-transcribe 로 다시 시도하세요.")
    except Exception as e:  # noqa: BLE001
        sys.exit(f"⛔ {type(e).__name__}: {e}\n"
                 "   자세한 내용을 보려면 같은 명령에 --debug 를 붙여 다시 실행하세요.\n"
                 "   실행 기록은 프로젝트 폴더의 pipeline.log 에 있습니다.")


if __name__ == "__main__":
    main()
