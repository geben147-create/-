"""06 human_gate — 사람이 고르기 전에는 진행하지 않는 관문.

동작:
  1. candidates.json 을 읽어 human_decisions.json 템플릿을 만든다 (status=PENDING).
  2. status 가 PENDING 이면 파이프라인을 여기서 멈춘다.
  3. 사람이 choice 를 채우고 note_edits 를 적고 status=DECIDED, decided_by=human 으로 바꾸면 진행.

decided_by 값:
  human      — 사람이 실제로 듣고 골랐음
  demo_auto  — 데모/테스트 목적의 자동 선택. 인간 창작 증거가 아님 (증빙에 그대로 표시됨)
"""
from __future__ import annotations

from pathlib import Path

from .common import jdump, jload, now_iso


def make_template(candidates: dict, path: Path) -> dict:
    groups = []
    for key, group in candidates.get("groups", {}).items():
        groups.append({
            "id": key,
            "question_ko": group.get("question_ko", f"{key} 후보 중 하나를 고르세요"),
            "options": [{"id": o["id"], "label_ko": o.get("label_ko", o["id"]),
                         "preview": o.get("preview")} for o in group["options"]],
            "choice": None,
            "note_edits": [],
            "comment_ko": "",
        })
    tmpl = {
        "schema": "stayfade/human_decisions/1",
        "status": "PENDING",
        "decided_by": None,
        "decided_at": None,
        "instructions_ko": [
            "1. 04_render 폴더의 미리듣기 WAV를 전부 들어보세요.",
            "2. 각 항목의 choice 에 고른 옵션 id 를 적으세요.",
            "3. 최소 한 군데는 note_edits 로 직접 음을 고치세요. 고르기만 한 것보다 훨씬 강한 기록이 됩니다.",
            "   예: {\"op\":\"transpose\",\"index\":12,\"semitones\":-1}",
            "       {\"op\":\"delete\",\"index\":3}  {\"op\":\"move\",\"index\":7,\"delta_sec\":0.03}",
            "4. 다 정했으면 status 를 DECIDED, decided_by 를 human 으로 바꾸고 저장하세요.",
        ],
        "decisions": groups,
        "human_performance": {"files": [], "description_ko": "직접 녹음한 보컬/연주 파일 경로를 넣으세요 (없으면 비워둠)"},
        "created_at": now_iso(),
    }
    jdump(tmpl, path)
    return tmpl


def load_or_create(candidates: dict, path: Path) -> tuple[dict, bool]:
    path = Path(path)
    if not path.exists():
        return make_template(candidates, path), False
    d = jload(path)
    decisions = d.get("decisions") or []
    covered = {g.get("id") for g in decisions if g.get("choice")}
    needed = set(candidates.get("groups", {}))
    ready = (d.get("status") == "DECIDED" and bool(decisions) and needed.issubset(covered))
    return d, ready


def validate(decisions: dict, candidates: dict) -> list[str]:
    problems = []
    valid = {k: {o["id"] for o in g["options"]} for k, g in candidates.get("groups", {}).items()}
    entries = decisions.get("decisions") or []
    if not entries:
        problems.append("decisions 가 비어 있습니다 — 후보를 하나도 고르지 않았습니다")
    answered = {g.get("id") for g in entries if g.get("choice")}
    for missing in sorted(set(valid) - answered):
        problems.append(f"{missing}: 아직 고르지 않았습니다 (가능: {sorted(valid[missing])})")
    for g in entries:
        if not g.get("choice"):
            problems.append(f"{g['id']}: choice 가 비어 있습니다")
        elif g["id"] in valid and g["choice"] not in valid[g["id"]]:
            problems.append(f"{g['id']}: '{g['choice']}' 는 없는 옵션입니다 (가능: {sorted(valid[g['id']])})")
    if decisions.get("status") == "DECIDED" and decisions.get("decided_by") not in ("human", "demo_auto"):
        problems.append("decided_by 는 'human' 또는 'demo_auto' 여야 합니다")
    return problems
