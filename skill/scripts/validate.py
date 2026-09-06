#!/usr/bin/env python3
"""프로젝트 폴더의 산출물을 스키마로 검증한다.

    python skill/scripts/validate.py ./work/mysong
종료코드 0 = 통과, 1 = 실패.
"""
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    sys.exit("jsonschema 가 필요합니다:  pip install jsonschema")

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"
PAIRS = {
    "project.json": "project.schema.json",
    "analysis.json": "analysis.schema.json",
    "candidates.json": "candidates.schema.json",
    "human_decisions.json": "human_decisions.schema.json",
    "arrangement_manifest.json": "arrangement_manifest.schema.json",
    "qc.json": "qc.schema.json",
}


def main(project: str) -> int:
    root = Path(project)
    if not root.exists():
        print(f"❌ 프로젝트 폴더가 없습니다: {root}")
        return 1
    failed = 0
    for fname, sname in PAIRS.items():
        f = root / fname
        if not f.exists():
            print(f"⏭  {fname}: 아직 없음 (해당 단계 미실행)")
            continue
        schema = json.loads((SCHEMA_DIR / sname).read_text(encoding="utf-8"))
        data = json.loads(f.read_text(encoding="utf-8"))
        errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(data), key=lambda e: e.path)
        if errors:
            failed += 1
            print(f"❌ {fname}: {len(errors)}개 오류")
            for e in errors[:8]:
                loc = "/".join(str(x) for x in e.path) or "(root)"
                print(f"     - {loc}: {e.message[:160]}")
        else:
            print(f"✅ {fname}")

    hd = root / "human_decisions.json"
    if hd.exists():
        d = json.loads(hd.read_text(encoding="utf-8"))
        if d.get("status") == "DECIDED" and d.get("decided_by") != "human":
            print(f"⚠  decided_by='{d.get('decided_by')}' — 이 산출물은 인간 창작 증거로 쓸 수 없습니다.")
        edits = sum(len(g.get("note_edits") or []) for g in d.get("decisions", []))
        if edits == 0:
            print("⚠  직접 고친 노트가 0개입니다 — 선택만으로는 창작 기여가 약합니다.")
        if not (d.get("human_performance") or {}).get("files"):
            print("⚠  사람이 녹음한 파일이 없습니다 — 실연 기여 0.")
    an = root / "analysis.json"
    if an.exists():
        a = json.loads(an.read_text(encoding="utf-8"))
        k = a.get("key", {})
        if k.get("ambiguous") and not k.get("manual"):
            print(f"⚠  조성 모호: {k.get('relative_pair')} — 귀로 확인하고 `analyze --key` 로 지정하세요.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "./work/project"))
