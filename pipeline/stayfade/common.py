from __future__ import annotations
import csv
import datetime as _dt
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

STEP_DIRS = {
    "original": "00_original",
    "stems": "01_stems",
    "midi": "02_midi",
    "variants": "03_variants",
    "human": "03_human_raw",
    "render": "04_render",
    "edit": "05_edit",
    "mix": "06_mix",
    "master": "07_master",
    "qc": "08_qc",
    "evidence": "09_evidence",
}


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path | str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def jdump(obj, path: Path | str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=_json_default)


def _json_default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    return str(o)


def jload(path: Path | str):
    """JSON 읽기. 손으로 고치다 깨뜨리는 일이 잦으므로 어느 파일의 몇 줄인지 한국어로 알려준다."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:   # utf-8-sig: 메모장이 넣는 BOM 을 그대로 처리
            return json.load(f)
    except json.JSONDecodeError as e:
        raise SystemExit(
            f"⛔ JSON 형식이 깨졌습니다: {path}\n"
            f"   {e.lineno}번째 줄 {e.colno}번째 글자 근처 — {e.msg}\n"
            "   자주 나는 실수: 마지막 항목 뒤의 쉼표, 큰따옴표 대신 작은따옴표, 한글 따옴표(“ ”), 괄호 짝 안 맞음\n"
            "   고치기 어려우면 그 파일을 지우고 해당 단계를 다시 실행하면 새로 만들어집니다.") from None
    except UnicodeDecodeError:
        raise SystemExit(
            f"⛔ 파일 인코딩을 읽을 수 없습니다: {path}\n"
            "   메모장에서 [다른 이름으로 저장] → 인코딩을 'UTF-8' 로 선택해 저장하세요.") from None


def db(x: float) -> float:
    return 20.0 * np.log10(max(abs(float(x)), 1e-12))


def lin(db_value: float) -> float:
    return float(10.0 ** (db_value / 20.0))


class Project:
    """프로젝트 폴더 = 한 곡의 모든 산출물. root/ 아래 STEP_DIRS 구조."""

    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()
        if self.root.exists() and not self.root.is_dir():
            raise SystemExit(f"⛔ --project 에는 폴더 경로를 넣어야 합니다. 지금 값은 파일입니다: {self.root}\n"
                             "   예: --project ./work/mysong  (원본 파일 경로는 init 뒤에 씁니다)")
        self.root.mkdir(parents=True, exist_ok=True)
        self.log_path = self.root / "pipeline.log"
        self.state_path = self.root / "pipeline_state.json"

    def dir(self, key: str) -> Path:
        p = self.root / STEP_DIRS[key]
        p.mkdir(parents=True, exist_ok=True)
        return p

    def log(self, msg: str) -> None:
        line = f"[{now_iso()}] {msg}"
        print(line, flush=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def state(self) -> dict:
        if self.state_path.exists():
            return jload(self.state_path)
        return {"steps": {}, "created": now_iso()}

    def set_state(self, step: str, status: str, **extra) -> None:
        st = self.state()
        st["steps"][step] = {"status": status, "time": now_iso(), **extra}
        st["updated"] = now_iso()
        jdump(st, self.state_path)

    def info(self) -> dict:
        p = self.root / "project.json"
        return jload(p) if p.exists() else {}

    def resolve(self, stored: str | Path) -> Path:
        """저장된 경로를 이 프로젝트 안에서 다시 찾는다.

        프로젝트 폴더를 복사하거나 이름을 바꾸면 절대경로가 남의 폴더를 가리켜
        엉뚱한 파일을 측정하게 됩니다. 프로젝트 안에 같은 이름이 있으면 그쪽을 씁니다.
        """
        p = Path(stored)
        try:
            rel = p.relative_to(self.root)
            return self.root / rel
        except ValueError:
            pass
        for step in STEP_DIRS.values():                    # 같은 단계 폴더 안의 같은 이름
            cand = self.root / step / p.name
            if cand.exists():
                return cand
        cand = self.root / p.name
        if cand.exists():
            return cand
        return p


# ---------- audio io ----------

def load_audio(path: Path | str, sr: int | None = None, mono: bool = False):
    """returns (y[channels, n] float32, sr). always 2-D."""
    y, file_sr = sf.read(str(path), dtype="float32", always_2d=True)
    y = y.T  # (channels, n)
    if sr is not None and sr != file_sr:
        import librosa
        y = librosa.resample(y, orig_sr=file_sr, target_sr=sr, res_type="soxr_hq")
        file_sr = sr
    if mono:
        y = y.mean(axis=0, keepdims=True)
    return np.ascontiguousarray(y, dtype=np.float32), int(file_sr)


def to_stereo(y: np.ndarray) -> np.ndarray:
    y = np.atleast_2d(y)
    if y.shape[0] == 1:
        y = np.vstack([y, y])
    return y[:2]


def save_wav(path: Path | str, y: np.ndarray, sr: int, subtype: str = "PCM_24") -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    y = np.atleast_2d(y)
    sf.write(str(path), np.clip(y.T, -1.0, 1.0), sr, subtype=subtype)
    return path


def save_flac16(path: Path | str, y: np.ndarray, sr: int, dither: bool = True, seed: int = 7) -> Path:
    y = np.atleast_2d(np.asarray(y, dtype=np.float64))
    if dither:
        rng = np.random.default_rng(seed)
        lsb = 1.0 / 32768.0
        tpdf = (rng.random(y.shape) - rng.random(y.shape)) * lsb
        y = y + tpdf
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.clip(y.T, -1.0, 1.0), sr, subtype="PCM_16", format="FLAC")
    return path


def audio_info(path: Path | str) -> dict:
    i = sf.info(str(path))
    return {
        "path": str(path),
        "samplerate": i.samplerate,
        "channels": i.channels,
        "frames": i.frames,
        "duration_sec": round(i.frames / i.samplerate, 3),
        "subtype": i.subtype,
        "format": i.format,
        "bytes": os.path.getsize(path),
    }


def fmt_time(sec: float) -> str:
    m = int(sec // 60)
    s = sec - 60 * m
    return f"{m:02d}:{s:05.2f}"


# ---------- tools ----------

def which(name: str) -> str | None:
    return shutil.which(name)


def run_cmd(cmd: list[str], timeout: int = 3600) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return 1, f"{type(e).__name__}: {e}"


def tool_versions() -> dict:
    out = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "time": now_iso(),
        "packages": {},
        "binaries": {},
    }
    for mod in ["numpy", "scipy", "librosa", "soundfile", "pyloudnorm", "mido", "pretty_midi",
                "basic_pitch", "onnxruntime", "tensorflow", "torch", "demucs", "matchering", "yaml", "jsonschema"]:
        try:
            m = __import__(mod)
            out["packages"][mod] = getattr(m, "__version__", "installed")
        except Exception:  # noqa: BLE001
            out["packages"][mod] = None
    for b, args in {"ffmpeg": ["-version"], "fluidsynth": ["--version"], "demucs": ["--help"]}.items():
        path = which(b)
        if path:
            rc, txt = run_cmd([path] + args, timeout=60)
            out["binaries"][b] = {"path": path, "version_line": (txt.strip().splitlines() or [""])[0][:120]}
        else:
            out["binaries"][b] = None
    return out


def write_hashes_csv(root: Path, out_csv: Path, skip_dirs: tuple[str, ...] = ()) -> int:
    rows = []
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(root)
        if any(str(rel).startswith(s) for s in skip_dirs):
            continue
        if p == out_csv:
            continue
        rows.append((str(rel), os.path.getsize(p), sha256(p)))
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["relative_path", "bytes", "sha256"])
        w.writerows(rows)
    return len(rows)


NOTE_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_NAMES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def pc_name(pc: int, flats: bool = True) -> str:
    return (NOTE_NAMES_FLAT if flats else NOTE_NAMES_SHARP)[pc % 12]


def midi_name(m: int, flats: bool = True) -> str:
    return f"{pc_name(m % 12, flats)}{m // 12 - 1}"
