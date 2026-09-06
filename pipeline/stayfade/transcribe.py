"""03 transcribe — 스템 → MIDI (Basic Pitch).

주의: 여기서 나온 노트는 '원곡을 자동 채보한 참고 데이터'입니다.
사람이 만든 창작물이 아니며, 그대로 쓰면 원곡 멜로디를 그대로 복제하는 셈이 됩니다.
용도는 (1) 코드/베이스 진행 파악, (2) 새 파트를 만들 때 충돌 검사입니다.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def transcribe_file(src: Path, out_dir: Path, onset_threshold: float = 0.5,
                    frame_threshold: float = 0.3, min_note_len_ms: float = 58,
                    min_freq: float | None = None, max_freq: float | None = None) -> dict:
    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import predict

    out_dir.mkdir(parents=True, exist_ok=True)
    model_out, midi_data, note_events = predict(
        str(src), ICASSP_2022_MODEL_PATH,
        onset_threshold=onset_threshold, frame_threshold=frame_threshold,
        minimum_note_length=min_note_len_ms, minimum_frequency=min_freq, maximum_frequency=max_freq,
    )
    mid_path = out_dir / f"{Path(src).stem}.mid"
    midi_data.write(str(mid_path))
    events = [{"start": round(float(s), 4), "end": round(float(e), 4), "pitch": int(p),
               "amplitude": round(float(a), 4)} for s, e, p, a, *_ in note_events]
    return {"source": str(src), "midi": str(mid_path), "note_count": len(events), "events": events}


def run(project, stems: dict[str, str]) -> dict:
    out_dir = project.dir("midi")
    results = {}
    plan = {
        "bass": dict(min_freq=30.0, max_freq=400.0, onset_threshold=0.5, frame_threshold=0.3, min_note_len_ms=80),
        "vocals": dict(min_freq=80.0, max_freq=1200.0, onset_threshold=0.6, frame_threshold=0.35, min_note_len_ms=90),
        "other": dict(min_freq=60.0, max_freq=3000.0, onset_threshold=0.6, frame_threshold=0.4, min_note_len_ms=90),
    }
    for name, kw in plan.items():
        p = stems.get(name)
        if not p or not Path(p).exists():
            continue
        try:
            project.log(f"채보: {name}")
            results[name] = transcribe_file(Path(p), out_dir, **kw)
        except Exception as e:  # noqa: BLE001
            project.log(f"채보 실패 {name}: {type(e).__name__}: {e}")
            results[name] = {"error": f"{type(e).__name__}: {e}"}
    return results


def quantize_events(events: list[dict], beat_times: list[float], subdiv: int = 4, strength: float = 1.0) -> list[dict]:
    """비트 그리드에 스냅. strength=1 완전 퀀타이즈, 0.6 정도면 사람 느낌 유지."""
    if not events or len(beat_times) < 2:
        return events
    grid = []
    bt = list(beat_times)
    for i in range(len(bt) - 1):
        for k in range(subdiv):
            grid.append(bt[i] + (bt[i + 1] - bt[i]) * k / subdiv)
    grid.append(bt[-1])
    grid = np.array(grid)
    out = []
    for e in events:
        j = int(np.argmin(np.abs(grid - e["start"])))
        target = float(grid[j])
        new_start = e["start"] + (target - e["start"]) * strength
        dur = e["end"] - e["start"]
        out.append({**e, "start": round(new_start, 4), "end": round(new_start + dur, 4)})
    return out
