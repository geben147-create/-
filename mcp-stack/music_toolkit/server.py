#!/usr/bin/env python3
"""
music_toolkit MCP server.

Audio analysis, stem separation, audio->MIDI, distribution mastering and
provenance recording — the parts of the production pipeline that do not need a
DAW, so they run identically under Claude Code, Codex, Cursor, Claude Desktop
and any other MCP client.

Every optional dependency is probed at call time, never at import time: a
missing extra degrades to a clear error message instead of a server that
refuses to start and shows up as a red dot in the client with no explanation.
"""
from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

_raw_mcp = FastMCP("music-toolkit")


class _Mcp:
    """FastMCP wrapper that sanitises every tool result through _py()."""

    def __init__(self, inner):
        self._inner = inner

    def tool(self, *d_args, **d_kwargs):
        import functools

        def deco(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                return _py(fn(*args, **kwargs))

            return self._inner.tool(*d_args, **d_kwargs)(wrapper)

        return deco

    def run(self, *a, **k):
        return self._inner.run(*a, **k)


mcp = _Mcp(_raw_mcp)

# --------------------------------------------------------------------------
# capability probing
# --------------------------------------------------------------------------

def _try_import(name: str):
    try:
        __import__(name)
        return sys.modules[name]
    except Exception:
        return None


def _ffmpeg() -> str | None:
    """Prefer a system ffmpeg; fall back to the wheel-bundled binary."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    iio = _try_import("imageio_ffmpeg")
    if iio:
        try:
            return iio.get_ffmpeg_exe()
        except Exception:
            return None
    return None


def _need(*mods: str) -> str | None:
    missing = [m for m in mods if _try_import(m) is None]
    if missing:
        return (
            f"Missing dependency: {', '.join(missing)}. "
            f"Install with: {sys.executable} -m pip install {' '.join(missing)}"
        )
    return None


def _resolve(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    return p


def _py(obj: Any) -> Any:
    """Convert numpy scalars/arrays to builtins, recursively.

    numpy comparisons yield numpy.bool_ and numpy math yields numpy.float64;
    neither is JSON-serialisable, and the MCP layer turns that into an opaque
    "Unable to serialize unknown type" string instead of the tool's result.
    Every tool return goes through here so a numpy value can never leak.
    """
    if isinstance(obj, dict):
        return {k: _py(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_py(v) for v in obj]
    if hasattr(obj, "item") and getattr(obj, "shape", None) == ():
        return obj.item()
    if hasattr(obj, "tolist") and hasattr(obj, "shape"):
        return obj.tolist()
    return obj


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# tools
# --------------------------------------------------------------------------

@mcp.tool()
def list_capabilities() -> dict[str, Any]:
    """Report which parts of the toolkit are usable on this machine.

    Call this first when something fails — it says exactly which optional
    dependency is missing rather than making you guess from a stack trace.
    """
    mods = {m: _try_import(m) is not None
            for m in ("numpy", "soundfile", "librosa", "pyloudnorm",
                      "basic_pitch", "demucs", "torch")}
    return {
        "python": sys.executable,
        "python_version": sys.version.split()[0],
        "modules": mods,
        "ffmpeg": _ffmpeg(),
        "ready": {
            "audio_qc": mods["soundfile"] and mods["numpy"],
            "loudness": mods["pyloudnorm"],
            "detect_tempo_key": mods["librosa"],
            "detect_sections": mods["librosa"],
            "audio_to_midi": mods["basic_pitch"],
            "split_stems": mods["demucs"],
            "make_distribution_master": _ffmpeg() is not None,
            "provenance_manifest": True,
        },
    }


def _audio_qc_impl(path: str, silence_db: float = -60.0) -> dict[str, Any]:
    err = _need("numpy", "soundfile")
    if err:
        return {"error": err}
    import numpy as np
    import soundfile as sf

    p = _resolve(path)
    if not p.exists():
        return {"error": f"file not found: {p}"}

    info = sf.info(str(p))
    data, sr = sf.read(str(p), always_2d=True, dtype="float64")
    mono = data.mean(axis=1)

    peak = float(np.max(np.abs(data))) if data.size else 0.0
    peak_db = 20 * np.log10(peak) if peak > 0 else -np.inf

    # True peak: 4x zero-stuffed FFT resample per channel, the cheap standard
    # approximation of the ITU-R BS.1770 intersample-peak measurement.
    try:
        up = np.fft.irfft(np.fft.rfft(data, axis=0), n=len(data) * 4, axis=0) * 4
        tp = float(np.max(np.abs(up)))
    except Exception:
        tp = peak
    tp_db = 20 * np.log10(tp) if tp > 0 else -np.inf

    lufs = None
    pl = _try_import("pyloudnorm")
    if pl is not None and len(mono) > sr:  # meter needs >= 400ms of audio
        try:
            lufs = float(pl.Meter(sr).integrated_loudness(data))
        except Exception:
            lufs = None

    clipped = int(np.sum(np.abs(data) >= 0.99999))
    dc = [float(np.mean(data[:, c])) for c in range(data.shape[1])]

    thr = 10 ** (silence_db / 20)
    loud = np.where(np.abs(mono) > thr)[0]
    if loud.size:
        lead, trail = loud[0] / sr, (len(mono) - 1 - loud[-1]) / sr
    else:
        lead = trail = len(mono) / sr

    checks = {
        "sample_rate_44100": info.samplerate == 44100,
        "stereo": info.channels == 2,
        "bit_depth_16": "16" in (info.subtype or ""),
        "no_clipping": clipped == 0,
        "true_peak_under_-1dBTP": tp_db <= -1.0,
        "dc_offset_ok": all(abs(v) < 1e-3 for v in dc),
        "lead_silence_under_8s": lead < 8.0,
        "trail_silence_under_8s": trail < 8.0,
    }
    return {
        "file": str(p),
        "sha256": _sha256(p),
        "duration_sec": round(info.frames / info.samplerate, 3),
        "sample_rate": info.samplerate,
        "channels": info.channels,
        "subtype": info.subtype,
        "format": info.format,
        "peak_dbfs": round(peak_db, 3) if np.isfinite(peak_db) else None,
        "true_peak_dbtp": round(tp_db, 3) if np.isfinite(tp_db) else None,
        "integrated_lufs": round(lufs, 2) if lufs is not None else None,
        "clipped_samples": clipped,
        "dc_offset_per_channel": [round(v, 8) for v in dc],
        "lead_silence_sec": round(float(lead), 3),
        "trail_silence_sec": round(float(trail), 3),
        "checks": checks,
        "passed": all(checks.values()),
        "failed_checks": [k for k, v in checks.items() if not v],
    }


@mcp.tool()
def audio_qc(path: str, silence_db: float = -60.0) -> dict[str, Any]:
    """Run the pre-upload QC pass on an audio file.

    Reports duration, sample rate, channels, sample peak, true peak (4x
    oversampled), integrated LUFS, DC offset, clipped-sample count and
    leading/trailing silence — then flags each against typical distributor
    requirements (16-bit/44.1kHz stereo, no clipping, under 8s of edge silence).
    """
    return _audio_qc_impl(path, silence_db)


# Krumhansl-Schmuckler key profiles, the standard published weights.
_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


@mcp.tool()
def detect_tempo_key(path: str) -> dict[str, Any]:
    """Estimate BPM and musical key of an audio file.

    BPM comes from librosa beat tracking; key from correlating the mean
    chroma vector against the Krumhansl-Schmuckler profiles. Both are
    estimates — the confidence margin is returned so you can tell a
    clear answer from a coin flip.
    """
    err = _need("librosa", "numpy")
    if err:
        return {"error": err}
    import librosa
    import numpy as np

    p = _resolve(path)
    if not p.exists():
        return {"error": f"file not found: {p}"}

    y, sr = librosa.load(str(p), sr=None, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    scores = {}
    for i in range(12):
        rolled = np.roll(chroma, -i)
        scores[f"{_NOTES[i]} major"] = float(np.corrcoef(rolled, _MAJOR)[0, 1])
        scores[f"{_NOTES[i]} minor"] = float(np.corrcoef(rolled, _MINOR)[0, 1])
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

    return {
        "file": str(p),
        "bpm": round(tempo, 2),
        "beat_count": int(len(beats)),
        "duration_sec": round(len(y) / sr, 3),
        "key": ranked[0][0],
        "key_confidence": round(ranked[0][1], 4),
        "key_margin_over_runner_up": round(ranked[0][1] - ranked[1][1], 4),
        "key_candidates": [{"key": k, "score": round(v, 4)} for k, v in ranked[:5]],
    }


@mcp.tool()
def detect_sections(path: str, n_sections: int = 8) -> dict[str, Any]:
    """Split a track into structural sections (intro / verse / chorus / bridge).

    Returns timecoded boundaries from librosa's recurrence-matrix
    segmentation. Labels are positional, not semantic — use the timecodes
    and listen; the tool tells you where the song changes, not what to call it.
    """
    err = _need("librosa", "numpy")
    if err:
        return {"error": err}
    import librosa
    import numpy as np

    p = _resolve(path)
    if not p.exists():
        return {"error": f"file not found: {p}"}

    y, sr = librosa.load(str(p), sr=22050, mono=True)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    bounds = librosa.segment.agglomerative(chroma, max(2, int(n_sections)))
    times = librosa.frames_to_time(bounds, sr=sr)
    total = len(y) / sr
    edges = list(times) + [total]

    def _mmss(t: float) -> str:
        return f"{int(t // 60)}:{t % 60:05.2f}"

    return {
        "file": str(p),
        "duration_sec": round(total, 3),
        "sections": [
            {
                "index": i,
                "start_sec": round(float(edges[i]), 3),
                "end_sec": round(float(edges[i + 1]), 3),
                "start": _mmss(float(edges[i])),
                "length_sec": round(float(edges[i + 1] - edges[i]), 3),
            }
            for i in range(len(edges) - 1)
        ],
    }


@mcp.tool()
def audio_to_midi(path: str, out_dir: str = "", min_note_len_ms: float = 127.7,
                  onset_threshold: float = 0.5) -> dict[str, Any]:
    """Convert a hummed or sung melody to MIDI with Spotify Basic Pitch.

    This is the humming-to-composition step: sing a melody, get a MIDI file
    you can render with any instrument. The source audio is never modified.
    """
    err = _need("basic_pitch")
    if err:
        return {"error": err}

    p = _resolve(path)
    if not p.exists():
        return {"error": f"file not found: {p}"}
    out = _resolve(out_dir) if out_dir else p.parent / "midi_out"
    out.mkdir(parents=True, exist_ok=True)

    from basic_pitch.inference import predict_and_save
    from basic_pitch import ICASSP_2022_MODEL_PATH

    predict_and_save(
        [str(p)], str(out),
        save_midi=True, sonify_midi=False, save_model_outputs=False, save_notes=True,
        model_or_model_path=ICASSP_2022_MODEL_PATH,
        onset_threshold=onset_threshold, minimum_note_length=min_note_len_ms,
    )
    produced = sorted(str(f) for f in out.iterdir()
                      if f.suffix.lower() in (".mid", ".midi", ".csv"))
    return {
        "source": str(p),
        "source_sha256": _sha256(p),
        "out_dir": str(out),
        "files": produced,
        "note": "Source audio untouched. Keep both the raw hum and this MIDI as provenance.",
    }


@mcp.tool()
def split_stems(path: str, out_dir: str = "", model: str = "htdemucs",
                two_stems: str = "", timeout_sec: int = 3600) -> dict[str, Any]:
    """Separate a mix into stems (vocals / drums / bass / other) with Demucs.

    Set two_stems to e.g. "vocals" for a fast vocals + accompaniment split.
    Runs on CPU unless a GPU-enabled torch is installed; a full track takes
    minutes, so raise timeout_sec for long files.
    """
    err = _need("demucs", "torch")
    if err:
        return {"error": err}

    p = _resolve(path)
    if not p.exists():
        return {"error": f"file not found: {p}"}
    out = _resolve(out_dir) if out_dir else p.parent / "stems"
    out.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "demucs", "-n", model, "-o", str(out)]
    if two_stems:
        cmd += ["--two-stems", two_stems]
    cmd.append(str(p))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
    if r.returncode != 0:
        tail = r.stderr[-2000:]
        # Demucs fetches model weights from dl.fbaipublicfiles.com on first use.
        # Behind a restrictive egress policy that download is the failure, not
        # the separation itself — say so rather than showing a torch traceback.
        if "urlopen" in tail or "URLError" in tail or "Tunnel" in tail:
            return {"error": "demucs model weights could not be downloaded",
                    "cause": "network blocked dl.fbaipublicfiles.com",
                    "fix": "Run `music-mcp-prefetch` (or the prefetch_models tool) "
                           "once on a machine with open internet access; weights "
                           "cache under ~/.cache/torch/hub/checkpoints.",
                    "stderr": tail}
        return {"error": "demucs failed", "returncode": r.returncode, "stderr": tail}
    stems = sorted(str(f) for f in out.rglob("*.wav"))
    return {"source": str(p), "model": model, "out_dir": str(out),
            "stems": stems, "stem_count": len(stems)}


@mcp.tool()
def prefetch_models(demucs_model: str = "htdemucs") -> dict[str, Any]:
    """Download the model weights Demucs and Basic Pitch need, once, up front.

    Both fetch weights on first use. Doing it deliberately here means the first
    real separation does not fail halfway through on a network error, and it
    surfaces a blocked-egress problem immediately instead of mid-session.
    """
    out: dict[str, Any] = {}

    if _try_import("demucs") and _try_import("torch"):
        r = subprocess.run(
            [sys.executable, "-c",
             f"from demucs.pretrained import get_model; get_model('{demucs_model}')"],
            capture_output=True, text=True, timeout=3600)
        out["demucs"] = ({"ok": True, "model": demucs_model} if r.returncode == 0
                         else {"ok": False, "stderr": r.stderr[-800:]})
    else:
        out["demucs"] = {"ok": False, "reason": "demucs/torch not installed"}

    if _try_import("basic_pitch"):
        r = subprocess.run(
            [sys.executable, "-c",
             "from basic_pitch import ICASSP_2022_MODEL_PATH; print(ICASSP_2022_MODEL_PATH)"],
            capture_output=True, text=True, timeout=900)
        out["basic_pitch"] = ({"ok": True, "model_path": r.stdout.strip()}
                              if r.returncode == 0
                              else {"ok": False, "stderr": r.stderr[-800:]})
    else:
        out["basic_pitch"] = {"ok": False, "reason": "basic-pitch not installed"}

    out["all_ok"] = all(v.get("ok") for v in out.values() if isinstance(v, dict))
    return out


@mcp.tool()
def make_distribution_master(path: str, out_path: str = "",
                             target_lufs: float = -14.0,
                             true_peak_db: float = -1.0,
                             normalize: bool = True) -> dict[str, Any]:
    """Render a distributor-ready master: stereo FLAC, 16-bit, 44.1 kHz.

    With normalize=True it also applies EBU R128 loudness normalisation to
    target_lufs with a true-peak ceiling. Returns the QC report of the file
    it produced, so you see immediately whether it passes.
    """
    ff = _ffmpeg()
    if ff is None:
        return {"error": "ffmpeg not found. Install ffmpeg, or pip install imageio-ffmpeg."}

    p = _resolve(path)
    if not p.exists():
        return {"error": f"file not found: {p}"}
    out = _resolve(out_path) if out_path else p.with_name(p.stem + "_MASTER.flac")
    out.parent.mkdir(parents=True, exist_ok=True)

    af = ["aformat=sample_fmts=s16:sample_rates=44100:channel_layouts=stereo"]
    if normalize:
        af.insert(0, f"loudnorm=I={target_lufs}:TP={true_peak_db}:LRA=11")
    cmd = [ff, "-y", "-i", str(p), "-af", ",".join(af),
           "-ac", "2", "-ar", "44100", "-sample_fmt", "s16", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"error": "ffmpeg failed", "returncode": r.returncode,
                "stderr": r.stderr[-2000:]}
    return {"source": str(p), "master": str(out),
            "target_lufs": target_lufs, "true_peak_ceiling_db": true_peak_db,
            "qc": _audio_qc_impl(str(out))}


@mcp.tool()
def provenance_manifest(paths: list[str], out_dir: str = "",
                        decisions: list[str] | None = None,
                        notes: str = "") -> dict[str, Any]:
    """Write the provenance record for a release: hashes, timestamps, tools.

    Produces provenance.json and provenance.csv listing every file with its
    SHA-256, size and modification time, plus the toolchain versions and any
    creative decisions you pass in. This is what you keep to show which audio
    a human made and which a tool only processed.
    """
    out = _resolve(out_dir) if out_dir else Path.cwd()
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for raw in paths:
        p = _resolve(raw)
        if not p.exists():
            rows.append({"file": str(p), "error": "not found"})
            continue
        st = p.stat()
        rows.append({
            "file": str(p),
            "sha256": _sha256(p),
            "bytes": st.st_size,
            "modified_utc": _dt.datetime.fromtimestamp(
                st.st_mtime, _dt.timezone.utc).isoformat(),
        })

    tools = {"python": sys.version.split()[0], "music_toolkit": "1.0.0"}
    for m in ("numpy", "soundfile", "librosa", "demucs", "torch", "basic_pitch"):
        mod = _try_import(m)
        tools[m] = getattr(mod, "__version__", "present") if mod else "absent"
    ff = _ffmpeg()
    if ff:
        try:
            tools["ffmpeg"] = subprocess.run(
                [ff, "-version"], capture_output=True, text=True
            ).stdout.splitlines()[0]
        except Exception:
            tools["ffmpeg"] = ff

    manifest = {
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "host": os.uname().nodename if hasattr(os, "uname") else "unknown",
        "tools": tools,
        "human_decisions": decisions or [],
        "notes": notes,
        "files": rows,
    }

    jpath = out / "provenance.json"
    jpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    cpath = out / "provenance.csv"
    with cpath.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "sha256", "bytes", "modified_utc", "error"])
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in w.fieldnames})

    return {"json": str(jpath), "csv": str(cpath),
            "file_count": len(rows), "tools": tools}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
