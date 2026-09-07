"""10 evidence — 해시·도구·결정 로그·AI 공시 초안.

이 패키지는 저작권을 발생시키지 않습니다. '무엇을 누가 언제 했는지'를 기록할 뿐입니다.
자동 생성 결정(decided_by='demo_auto')은 인간 창작 증거가 아니며, 공시 초안에도 그렇게 적힙니다.
"""
from __future__ import annotations

from pathlib import Path

from .common import Project, jdump, now_iso, sha256, tool_versions, write_hashes_csv

AI_DISCLOSURE_TEMPLATE = """{warning_block}AI DISCLOSURE / 제작 공시 초안  ({date})
Track: {title}
Artist: {artist}

1) Source audio
   - {source_desc}
   - Original file SHA-256: {source_hash}
   - Commercial-rights evidence: {rights_evidence}

   - AI-generated audio present in the delivered master: {ai_audio_present}

2) What AI did in this session (tools listed with versions in tool_versions.json)
   - Stem estimation: {separation_engine}
   - Automatic transcription (reference only, not claimed as human composition): {transcription}
   - Generated arrangement CANDIDATES (drums / bass / chords / bridge / structure): {candidates}
   - Rendering, mixing, mastering, loudness normalisation, QC measurement: automated

{section3_title}
   - Decisions recorded in human_decisions.json: {human_decision_count} (decided_by={decided_by})
   - Note edits {edit_actor}: {note_edit_count}
   - New human vocal / instrumental performance in this session: {human_performance}

4) What was NOT done
   - Lead vocal melody was not rewritten by a human unless stated above
   - No manual spectral restoration
   - No attempt to hide or remove AI provenance

5) Status
   - Technical QC: see qc.json
   - Full human listening: {listening_status}
   - Rights review: {rights_status}
   - Distributor submission: {submission_status}

This document does not certify copyright ownership or distributor approval.
공시 항목은 유통사(예: DistroKid의 AI Credits, Symphonic의 AI Disclosure)의 현재 양식에 맞춰 다시 작성하세요.
"""


def build(project: Project, meta: dict, decisions: dict, qc_data: dict, extra: dict | None = None) -> dict:
    ev_dir = project.dir("evidence")
    tv = tool_versions()
    jdump(tv, ev_dir / "tool_versions.json")

    extra = extra or {}
    dec_list = decisions.get("decisions", [])
    requested_edits = sum(len(d.get("note_edits", []) or []) for d in dec_list)
    # 요청한 수정이 아니라 '실제로 오디오에 반영된' 수정만 셉니다 (증빙이 부풀려지면 안 됨)
    edits = extra.get("applied_note_edits", requested_edits)
    failed_edits = extra.get("failed_note_edits", 0)
    decided_by = decisions.get("decided_by", "unknown")
    human_perf = decisions.get("human_performance", {})
    takes = extra.get("human_takes") or []
    perf_desc = "없음 (이번 세션에서 새 인간 실연 없음)"
    if takes:
        perf_desc = "; ".join(f"{Path(t.get('raw') or t.get('processed', '')).name} "
                              f"(raw sha256 {str(t.get('raw_sha256'))[:16]}…)" for t in takes)
    elif human_perf.get("files"):
        # 경로만 적혀 있고 실제로 처리되지 않았다면 '실연 있음' 으로 적으면 안 됩니다
        perf_desc = (f"NONE — human_decisions.json lists {len(human_perf['files'])} path(s) "
                     "but no file was actually processed (path not found). "
                     f"Listed: {', '.join(Path(f).name for f in human_perf['files'])}")

    human_decided = decided_by == "human"
    section3_title = ("3) What a human decided or performed" if human_decided else
                      f"3) Decisions in this session — NOT made by a human (decided_by={decided_by}).\n"
                      "   This document is NOT evidence of human authorship.")
    warning_lines = []
    if not human_decided:
        warning_lines.append(f"!! decided_by = {decided_by} — the choices below were not made by a person.")
    if not takes:
        warning_lines.append("!! No human vocal or instrumental performance was processed in this session.")
    if not (meta.get("rights_evidence") or "").strip():
        warning_lines.append("!! No commercial-rights evidence supplied (receipt / subscription / song URL).")
    if not edits:
        warning_lines.append("!! No note edit was actually applied to the audio.")
    warning_block = ("" if not warning_lines else
                     "=== READ FIRST — this draft is not submission-ready ===\n"
                     + "\n".join(warning_lines)
                     + "\nFix these before sending this text to a distributor.\n\n")

    disclosure = AI_DISCLOSURE_TEMPLATE.format(
        warning_block=warning_block,
        section3_title=section3_title,
        ai_audio_present=extra.get(
            "ai_audio_present",
            "YES — the source audio is retained in the master; stems are only attenuated, not removed. "
            "Set to NO only if you rebuilt the master without any of the source audio."),
        date=now_iso()[:10],
        title=meta.get("title") or "(untitled)",
        artist=meta.get("artist") or "(unset)",
        source_desc=meta.get("source_description") or "AI music generator output (fill in service, plan, date)",
        source_hash=meta.get("source_hash") or "(unknown)",
        rights_evidence=(meta.get("rights_evidence") or
                         "NOT YET SUPPLIED — receipt / subscription record / song URL / generation date"),
        separation_engine=extra.get("separation_engine", "?"),
        transcription=extra.get("transcription", "Basic Pitch"),
        candidates=extra.get("candidates", "generated locally, seeded"),
        human_decision_count=len(dec_list),
        decided_by=decided_by,
        edit_actor=("made by hand" if human_decided else f"recorded in the decision file ({decided_by})"),
        note_edit_count=(f"{edits} applied" + (f", {failed_edits} requested but NOT applied" if failed_edits else "")),
        human_performance=perf_desc,
        listening_status=meta.get("listening_status") or "PENDING",
        rights_status=meta.get("rights_status") or "UNVERIFIED",
        submission_status=meta.get("submission_status") or "NOT SUBMITTED",
    )
    (ev_dir / "AI_DISCLOSURE.txt").write_text(disclosure, encoding="utf-8")

    warnings = []
    if decided_by != "human":
        warnings.append("decided_by 가 'human' 이 아닙니다 — 이 산출물은 인간 창작 증거로 쓸 수 없습니다.")
    if not takes:
        if human_perf.get("files"):
            warnings.append("human_decisions.json 에 녹음 파일 경로가 있지만 실제로 처리된 파일이 없습니다 — "
                            "경로를 확인하세요. 지금 상태의 실연 기여는 0 입니다.")
        else:
            warnings.append("새 인간 실연(보컬/연주) 파일이 없습니다 — 실연 기여 0.")
    if not (meta.get("rights_evidence") or "").strip():
        warnings.append("생성 서비스 영수증·구독 증빙이 비어 있습니다 — 유통 심사에서 1순위 요구 항목입니다.")
    if edits == 0:
        warnings.append("실제로 반영된 노트 수정이 0개입니다 — 후보 선택만으로는 창작 기여가 약합니다.")
    if failed_edits:
        warnings.append(f"요청했지만 반영되지 않은 노트 수정이 {failed_edits}개 있습니다 — "
                        "arrangement_manifest.json 의 note_edits_failed 를 확인하세요.")

    manifest = {
        "generated_at": now_iso(),
        "project": str(project.root),
        "meta": meta,
        "tooling": {"packages": tv["packages"], "binaries": {k: (v or {}).get("path") if v else None
                                                             for k, v in tv["binaries"].items()}},
        "decisions_summary": {"count": len(dec_list), "decided_by": decided_by,
                              "note_edits_requested": requested_edits, "note_edits_applied": edits,
                              "note_edits_failed": failed_edits},
        "qc_verdict": qc_data.get("spec_check", {}).get("verdict"),
        "warnings_ko": warnings,
        "not_certified_ko": "이 파일은 저작권 소유나 유통 승인을 증명하지 않습니다.",
    }
    jdump(manifest, ev_dir / "manifest.json")
    n = write_hashes_csv(project.root, ev_dir / "file_hashes.csv")
    manifest["hashed_files"] = n
    jdump(manifest, ev_dir / "manifest.json")
    return {"manifest": str(ev_dir / "manifest.json"), "disclosure": str(ev_dir / "AI_DISCLOSURE.txt"),
            "tool_versions": str(ev_dir / "tool_versions.json"), "hashes_csv": str(ev_dir / "file_hashes.csv"),
            "hashed_files": n, "warnings_ko": warnings}


SUBMISSION_CHECKLIST = [
    {"id": "rights_receipt", "ko": "생성 서비스 영수증 / 당시 구독 상태 캡처", "required": True,
     "why_ko": "유료 구독 중 생성된 출력만 상업 이용권이 인정됩니다."},
    {"id": "song_url_id", "ko": "원곡 URL·곡 ID·생성일", "required": True,
     "why_ko": "RouteNote는 사용한 AI 플랫폼 링크 제출을 요구합니다."},
    {"id": "original_download", "ko": "원본 다운로드 파일 + SHA-256", "required": True, "why_ko": "동일성 증명"},
    {"id": "lyrics_provenance", "ko": "가사 초안 → AI 제안 → 최종본 변경 이력", "required": False,
     "why_ko": "가사에 대한 인간 기여를 보여주는 가장 쉬운 자료"},
    {"id": "human_raw_takes", "ko": "사람이 녹음한 원본(dry) 보컬/연주 테이크", "required": False,
     "why_ko": "실연 기여의 직접 증거. 보정본과 함께 보관"},
    {"id": "human_decisions", "ko": "human_decisions.json (선택·수정 이력)", "required": False,
     "why_ko": "무엇을 사람이 정했는지 남기는 기록"},
    {"id": "qc_json", "ko": "qc.json (기술 측정)", "required": False, "why_ko": "기술 문제로 인한 반려 예방"},
    {"id": "ai_disclosure", "ko": "AI 공시 문안 (유통사 양식에 맞춰 재작성)", "required": True,
     "why_ko": "DistroKid AI Credits / Symphonic AI Disclosure 등에서 필수"},
    {"id": "artwork", "ko": "커버 아트 3000x3000, 텍스트·상표 규정 확인", "required": True, "why_ko": "메타데이터 반려 사유 1순위"},
    {"id": "metadata", "ko": "아티스트명·C/P line·언어·explicit·발매일·ISRC/UPC", "required": True, "why_ko": "제출 폼 필수 항목"},
    {"id": "full_listening", "ko": "전체 인간 청취 (박자·불협화음·발음·분리 아티팩트)", "required": True,
     "why_ko": "수치 검사로는 절대 대체되지 않습니다."},
]


def checklist(status: dict | None = None) -> list[dict]:
    status = status or {}
    return [{**item, "status": status.get(item["id"], "PENDING")} for item in SUBMISSION_CHECKLIST]
