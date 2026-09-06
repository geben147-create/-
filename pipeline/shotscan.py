#!/usr/bin/env python3
"""
shotscan.py — genre-agnostic shot/scene analyser for short-form video.

Pipeline per video:
  1. download            (yt-dlp; skipped with --no-download)
  2. probe               duration / fps / resolution
  3. cut detection       two-pass (coarse, then low-threshold rescan of long shots)
  4. still extraction    first + middle frame of every shot
  5. contact sheet       tiled grid of shot-middle frames
  6. colour + motion     per-shot signalstats (luma, saturation) and motion proxy
  7. metrics.json        machine-readable record consumed by the playbook HTML

Nothing here is Instagram-specific or genre-specific: give it any list of URLs
or local files. Instagram saved collections need --cookies-from-browser.

Requires: yt-dlp >= 2026.08.19, ffmpeg >= 6 (ffprobe optional).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path

# ---------------------------------------------------------------- constants --

# Pass 1 catches obvious hard cuts. Pass 2 re-scans anything still longer than
# LONG_SHOT_S at a much lower threshold, because soft/graded cuts and matched
# cuts inside a held shot do not clear the coarse threshold. Single-pass
# detection systematically under-counts and inflates the mean shot length.
PASS1_THRESHOLD = 0.40     # a score at or above this is a cut, no argument
PASS2_THRESHOLD = 0.18     # fallback detector only (ffmpeg without scdet)
ADAPTIVE_K = 6.0           # stage-1 level = median + K x MAD of all frame scores
MIN_ADAPTIVE = 0.15        # never go below this, however calm the footage
MAX_ADAPTIVE = 1.20        # ...and never above this, however violent
SOFT_RATIO = 0.55          # stage-2 bar, as a fraction of the stage-1 level
MIN_SOFT = 0.10
# Dissolve detection. scdet scores frame-to-frame difference, so a crossfade
# is NOT a plateau of high scores -- each step of a linear blend is tiny. It
# shows up as two modest spikes (blend start, blend end) with an unusually
# quiet interval between them. Two hard cuts around a brief static shot give
# the same spike pair, so the interval content is checked too: mid-dissolve the
# picture is still changing, inside a held shot it is not.
DISSOLVE_MIN_S = 0.20
DISSOLVE_MAX_S = 1.50
DISSOLVE_QUIET_RATIO = 0.60   # interior peak must stay below this share of the spikes
DISSOLVE_CONTENT_DELTA = 10.0  # mean luma change across the interval (0-255)
DISSOLVE_COMPANION_RATIO = 0.50  # the closing spike may sit below the cut bar
LONG_SHOT_S = 4.0
MIN_SHOT_S = 0.25          # below this a "cut" is flash/strobe, not a shot
CONTACT_COLS = 5
CONTACT_TILE_W = 480


def which(name: str) -> str | None:
    return shutil.which(name)


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True,
                          errors="replace", **kw)


def ffmpeg_bin() -> str:
    exe = which("ffmpeg")
    if exe:
        return exe
    try:                                   # pip install imageio-ffmpeg
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ffmpeg not found. Install ffmpeg or `pip install imageio-ffmpeg`.")


FFMPEG = ffmpeg_bin()
FFPROBE = which("ffprobe")


# -------------------------------------------------------------------- probe --

@dataclass
class Probe:
    duration: float = 0.0
    fps: float = 0.0
    width: int = 0
    height: int = 0
    has_audio: bool = False

    @property
    def aspect(self) -> str:
        if not self.width or not self.height:
            return "unknown"
        r = self.width / self.height
        for label, val in (("9:16", 0.5625), ("1:1", 1.0),
                           ("4:5", 0.8), ("16:9", 1.7778)):
            if abs(r - val) < 0.04:
                return label
        return f"{r:.3f}"


def probe(path: Path) -> Probe:
    """ffprobe when available, otherwise parse `ffmpeg -i` stderr."""
    if FFPROBE:
        cp = run([FFPROBE, "-v", "error", "-print_format", "json",
                  "-show_format", "-show_streams", str(path)])
        if cp.returncode == 0:
            try:
                data = json.loads(cp.stdout)
            except json.JSONDecodeError:
                data = {}
            p = Probe()
            p.duration = float(data.get("format", {}).get("duration", 0) or 0)
            for st in data.get("streams", []):
                if st.get("codec_type") == "video" and not p.width:
                    p.width = int(st.get("width") or 0)
                    p.height = int(st.get("height") or 0)
                    num, _, den = (st.get("avg_frame_rate") or "0/1").partition("/")
                    try:
                        p.fps = float(num) / float(den) if float(den) else 0.0
                    except (ValueError, ZeroDivisionError):
                        p.fps = 0.0
                elif st.get("codec_type") == "audio":
                    p.has_audio = True
            if p.duration and p.width:
                return p

    cp = run([FFMPEG, "-hide_banner", "-i", str(path)])
    err = cp.stderr
    p = Probe()
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", err)
    if m:
        h, mi, s = m.groups()
        p.duration = int(h) * 3600 + int(mi) * 60 + float(s)
    m = re.search(r"(\d{2,5})x(\d{2,5})", err)
    if m:
        p.width, p.height = int(m.group(1)), int(m.group(2))
    m = re.search(r"([\d.]+)\s*fps", err)
    if m:
        p.fps = float(m.group(1))
    p.has_audio = "Audio:" in err
    return p


# ----------------------------------------------------------- cut detection --

def _frame_scores(path: Path) -> list[tuple[float, float]]:
    """(time, scene_score) for EVERY frame, via the scdet filter.

    One decode pass. Returns [] if scdet is unavailable (ffmpeg < 5), which
    makes the caller fall back to threshold scanning.
    """
    cp = run([FFMPEG, "-hide_banner", "-nostats", "-i", str(path),
              "-vf", "scdet=threshold=0,metadata=print:file=-",
              "-fps_mode", "passthrough", "-an", "-f", "null", "-"])
    blob = cp.stdout + cp.stderr
    times = [float(m) for m in re.findall(r"lavfi\.scd\.time=([\d.]+)", blob)]
    scores = [float(m) for m in re.findall(r"lavfi\.scd\.score=([\d.]+)", blob)]
    if not times or len(times) != len(scores):
        return []
    return list(zip(times, scores))


def _scene_times(path: Path, threshold: float,
                 start: float | None = None,
                 length: float | None = None) -> list[float]:
    """Fallback detector: frame times whose scene score exceeds `threshold`."""
    cmd = [FFMPEG, "-hide_banner", "-nostats"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    if length is not None:
        cmd += ["-t", f"{length:.3f}"]
    cmd += ["-i", str(path),
            "-vf", f"select='gt(scene,{threshold})',metadata=print:file=-",
            "-fps_mode", "passthrough",        # -vsync is gone in ffmpeg >= 7
            "-an", "-f", "null", "-"]
    cp = run(cmd)
    out = cp.stdout + cp.stderr
    return sorted({float(m) + (start or 0.0)
                   for m in re.findall(r"pts_time:([\d.]+)", out)})


def _mad(values: list[float], centre: float) -> float:
    """Median absolute deviation, scaled to be comparable to a std-dev."""
    if not values:
        return 0.0
    return 1.4826 * statistics.median([abs(v - centre) for v in values])


def _pick_peaks(cands: list[tuple[float, float]]) -> list[float]:
    """Greedy non-maximum suppression: within MIN_SHOT_S keep the best score."""
    kept: list[tuple[float, float]] = []
    for t, s in sorted(cands):
        if kept and t - kept[-1][0] < MIN_SHOT_S:
            if s > kept[-1][1]:               # this frame is the better cut
                kept[-1] = (t, s)
            continue
        kept.append((t, s))
    return [t for t, _ in kept]


def _frame_delta(path: Path, t_a: float, t_b: float) -> float:
    """Mean absolute luma difference between the frames at t_a and t_b (0-255).

    Near zero means the two moments look the same -- a held shot. A large value
    means the picture moved on, which inside a candidate transition interval is
    the signature of a dissolve rather than two adjacent hard cuts.
    """
    cp = run([FFMPEG, "-hide_banner", "-nostats",
              "-ss", f"{max(t_a, 0):.3f}", "-i", str(path),
              "-ss", f"{max(t_b, 0):.3f}", "-i", str(path),
              "-filter_complex",
              "[0:v]trim=end_frame=1,scale=320:-2,format=gray,setpts=0[a];"
              "[1:v]trim=end_frame=1,scale=320:-2,format=gray,setpts=0[b];"
              "[a][b]blend=all_mode=difference,signalstats,metadata=print:file=-",
              "-frames:v", "1", "-f", "null", "-"])
    blob = cp.stdout + cp.stderr
    m = re.search(r"lavfi\.signalstats\.YAVG=([\d.]+)", blob)
    return float(m.group(1)) if m else 0.0


def detect_cuts(path: Path, duration: float) -> tuple[list[dict], dict]:
    """Adaptive two-stage boundary detection.

    Returns (boundaries, diagnostics) where each boundary is
    {"t", "kind": "hard"|"soft", "ramp", "score"}.

    Stage 1 thresholds the whole per-frame score timeline at a level derived
    from the footage itself (median + K*MAD). This matters more than any fixed
    number: a locked-off talking head sits near zero, while a rotating drone
    shot can hold 0.3-0.6 indefinitely without a single cut. A constant
    threshold either shreds the second or misses everything in the first.

    Stage 2 lowers the bar, but only inside shots still longer than
    LONG_SHOT_S, where soft/graded/matched cuts hide. Restricting the low bar
    to long held passages is what keeps it from spraying false positives
    through already fast-cut sections.

    Each accepted boundary is then classified by how many consecutive frames
    stay elevated around it: a one- or two-frame spike is a hard cut, a run of
    RAMP_MIN_FRAMES or more is a dissolve/soft transition, reported with its
    duration. Peaks inside one ramp collapse to a single boundary.
    """
    frames = _frame_scores(path)

    if not frames:                                  # ---- legacy fallback ----
        coarse = [t for t in _scene_times(path, PASS1_THRESHOLD) if t > MIN_SHOT_S]
        bounds = [0.0] + coarse + [duration]
        refined, rescanned = [], 0
        for a, b in zip(bounds, bounds[1:]):
            if b - a <= LONG_SHOT_S:
                continue
            rescanned += 1
            refined += [t for t in _scene_times(path, PASS2_THRESHOLD,
                                                start=a + 0.15, length=b - a - 0.30)
                        if a + MIN_SHOT_S < t < b - MIN_SHOT_S]
        cuts = _pick_peaks([(t, 1.0) for t in set(coarse + refined)])
        return ([{"t": t, "kind": "unknown", "ramp": 0.0, "score": None}
                 for t in cuts],
                {"mode": "fallback_select", "adaptive_threshold": None,
                 "stage1_cuts": len(coarse), "stage2_added": len(refined),
                 "long_shots_rescanned": rescanned, "frames_scored": 0,
                 "soft_transitions": 0})

    scores = [s for _, s in frames]
    centre = statistics.median(scores)
    spread = _mad(scores, centre)
    adaptive = min(MAX_ADAPTIVE, max(MIN_ADAPTIVE, centre + ADAPTIVE_K * spread))

    stage1 = [(t, s) for t, s in frames if s >= adaptive and t >= MIN_SHOT_S]

    # ---- stage 2: lower the bar inside long held shots only ----
    # The bar is recomputed from the frames *inside* each long shot. A held,
    # quiet shot has a near-zero local baseline, so the bar drops and a soft cut
    # surfaces; a continuous moving take has a high local baseline, so the bar
    # stays high and its motion is not mistaken for cutting. A single global
    # fraction cannot do both -- it shreds the moving take.
    prelim = _pick_peaks(stage1)
    bounds = [0.0] + prelim + [duration]
    extra, rescanned, soft_levels = [], 0, []
    for a, b in zip(bounds, bounds[1:]):
        if b - a <= LONG_SHOT_S:
            continue
        rescanned += 1
        window = [(t, s) for t, s in frames
                  if a + MIN_SHOT_S < t < b - MIN_SHOT_S]
        if not window:
            continue
        w_scores = [s for _, s in window]
        w_centre = statistics.median(w_scores)
        w_level = max(MIN_SOFT, w_centre + ADAPTIVE_K * _mad(w_scores, w_centre))
        soft_levels.append(round(w_level, 4))
        extra += [(t, s) for t, s in window if w_level <= s < adaptive]
    soft_level = min(soft_levels) if soft_levels else None

    peaks = _pick_peaks(stage1 + extra)

    # ---- classify each boundary: hard cut, or a dissolve spike pair ----
    fps_dt = ((frames[-1][0] - frames[0][0]) / max(len(frames) - 1, 1)) or 0.033

    def score_at(t: float) -> float:
        return min(frames, key=lambda f: abs(f[0] - t))[1]

    def interior_peak(a: float, b: float) -> float:
        inner = [s for t, s in frames if a + fps_dt < t < b - fps_dt]
        return max(inner) if inner else 0.0

    companion_bar = adaptive * DISSOLVE_COMPANION_RATIO
    boundaries: list[dict] = []
    i = 0
    while i < len(peaks):
        t1 = peaks[i]
        s1 = score_at(t1)

        # The closing spike of a dissolve is often weaker than the opening one
        # and can sit below the cut threshold, so look for it on a lower bar.
        window = [(t, s) for t, s in frames
                  if t1 + DISSOLVE_MIN_S <= t <= t1 + DISSOLVE_MAX_S
                  and s >= companion_bar]
        dissolved = False
        if window:
            t2, s2 = max(window, key=lambda f: f[1])
            if interior_peak(t1, t2) < DISSOLVE_QUIET_RATIO * min(s1, s2):
                # Is the picture still changing between the two spikes? Mid
                # dissolve it is; inside a brief held shot bracketed by two
                # hard cuts it is not. This is the only thing separating them.
                delta = _frame_delta(path, t1 + fps_dt * 1.5, t2 - fps_dt * 1.5)
                if delta >= DISSOLVE_CONTENT_DELTA:
                    boundaries.append({"t": round(t1 + (t2 - t1) / 2, 3),
                                       "kind": "soft", "ramp": round(t2 - t1, 3),
                                       "score": round(max(s1, s2), 3),
                                       "content_delta": round(delta, 2)})
                    # Skip the closing spike too when it was itself a boundary.
                    i += 2 if (i + 1 < len(peaks)
                               and abs(peaks[i + 1] - t2) < fps_dt) else 1
                    dissolved = True

        if not dissolved:
            boundaries.append({"t": round(t1, 3), "kind": "hard", "ramp": 0.0,
                               "score": round(s1, 3)})
            i += 1

    boundaries.sort(key=lambda b: b["t"])
    # Re-apply the minimum-shot rule after ramp merging moved some boundaries.
    merged: list[dict] = []
    for b in boundaries:
        if merged and b["t"] - merged[-1]["t"] < MIN_SHOT_S:
            continue
        merged.append(b)

    return merged, {
        "mode": "scdet_adaptive",
        "frames_scored": len(frames),
        "score_median": round(centre, 4),
        "score_mad": round(spread, 4),
        "adaptive_threshold": round(adaptive, 4),
        "soft_threshold": soft_level,
        "stage1_cuts": len(prelim),
        "stage2_added": len(merged) - len(prelim),
        "long_shots_rescanned": rescanned,
        "soft_transitions": sum(1 for b in merged if b["kind"] == "soft"),
    }


# ---------------------------------------------------------------- per-shot --

@dataclass
class Shot:
    index: int
    start: float
    end: float
    still: str = ""
    transition_in: str = "cut"         # cut | dissolve — how this shot begins
    transition_ramp: float = 0.0       # dissolve length in seconds, else 0
    luma: float | None = None          # 0-255 average
    saturation: float | None = None    # 0-~180
    motion: float | None = None        # mean abs frame delta proxy

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)


def shots_from_cuts(boundaries: list[dict], duration: float) -> list[Shot]:
    """Turn boundary records into shots, tagging how each one is entered."""
    times = [0.0] + [b["t"] for b in boundaries] + [duration]
    kinds = ["cut"] + ["dissolve" if b["kind"] == "soft" else "cut"
                       for b in boundaries]
    ramps = [0.0] + [b.get("ramp", 0.0) for b in boundaries]
    out: list[Shot] = []
    for i, (a, b) in enumerate(zip(times, times[1:])):
        if b - a >= MIN_SHOT_S:
            out.append(Shot(index=i, start=round(a, 3), end=round(b, 3),
                            transition_in=kinds[i], transition_ramp=ramps[i]))
    for i, s in enumerate(out):                     # renumber after filtering
        s.index = i
    return out


def extract_still(path: Path, t: float, dest: Path, width: int = 720) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cp = run([FFMPEG, "-hide_banner", "-nostats", "-y",
              "-ss", f"{t:.3f}", "-i", str(path),
              "-frames:v", "1", "-vf", f"scale={width}:-2",
              "-fps_mode", "passthrough", "-q:v", "3", str(dest)])
    return cp.returncode == 0 and dest.exists() and dest.stat().st_size > 0


def shot_stats(path: Path, shot: Shot) -> None:
    """Average luma / saturation / motion across the shot."""
    length = max(shot.duration - 0.10, 0.10)
    cp = run([FFMPEG, "-hide_banner", "-nostats",
              "-ss", f"{shot.start + 0.05:.3f}", "-t", f"{length:.3f}",
              "-i", str(path),
              "-vf", "scale=320:-2,signalstats,metadata=print:file=-",
              "-fps_mode", "passthrough", "-an", "-f", "null", "-"])
    blob = cp.stdout + cp.stderr
    ys = [float(m) for m in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", blob)]
    ss = [float(m) for m in re.findall(r"lavfi\.signalstats\.SATAVG=([\d.]+)", blob)]
    if ys:
        shot.luma = round(statistics.fmean(ys), 2)
    if ss:
        shot.saturation = round(statistics.fmean(ss), 2)
    # Motion proxy: how much consecutive frames differ inside the shot.
    cp2 = run([FFMPEG, "-hide_banner", "-nostats",
               "-ss", f"{shot.start + 0.05:.3f}", "-t", f"{length:.3f}",
               "-i", str(path),
               "-vf", "scale=160:-2,tblend=all_mode=difference,signalstats,"
                      "metadata=print:file=-",
               "-fps_mode", "passthrough", "-an", "-f", "null", "-"])
    blob2 = cp2.stdout + cp2.stderr
    ds = [float(m) for m in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", blob2)]
    if ds:
        shot.motion = round(statistics.fmean(ds), 3)


def contact_sheet(stills: list[Path], dest: Path, cols: int = CONTACT_COLS) -> bool:
    if not stills:
        return False
    rows = math.ceil(len(stills) / cols)
    dest.parent.mkdir(parents=True, exist_ok=True)
    listing = dest.with_suffix(".txt")
    # ffmpeg concat demuxer needs escaped, absolute paths, one per line.
    listing.write_text(
        "".join(f"file '{p.resolve().as_posix()}'\nduration 1\n" for p in stills)
        + f"file '{stills[-1].resolve().as_posix()}'\n",
        encoding="utf-8")
    cp = run([FFMPEG, "-hide_banner", "-nostats", "-y",
              "-f", "concat", "-safe", "0", "-i", str(listing),
              "-vf", (f"scale={CONTACT_TILE_W}:-2,"
                      f"tile={cols}x{rows}:margin=8:padding=6:color=0x111318"),
              "-frames:v", "1", "-fps_mode", "passthrough",
              "-q:v", "3", str(dest)])
    listing.unlink(missing_ok=True)
    return cp.returncode == 0 and dest.exists()


# ---------------------------------------------------------------- download --

def download(url: str, workdir: Path, cookies_browser: str | None,
             cookies_file: str | None) -> Path | None:
    workdir.mkdir(parents=True, exist_ok=True)
    ytdlp = which("yt-dlp")
    if not ytdlp:
        print("  ! yt-dlp not found (pip install -U yt-dlp)", file=sys.stderr)
        return None
    tmpl = str(workdir / "%(id)s.%(ext)s")
    cmd = [ytdlp, "--no-playlist", "--no-warnings",
           "-f", "bv*+ba/b", "--merge-output-format", "mp4",
           "-o", tmpl, "--write-info-json", "--restrict-filenames"]
    if cookies_browser:
        cmd += ["--cookies-from-browser", cookies_browser]
    if cookies_file:
        cmd += ["--cookies", cookies_file]
    cmd.append(url)
    cp = run(cmd)
    if cp.returncode != 0:
        print(f"  ! download failed: {cp.stderr.strip().splitlines()[-1:]}",
              file=sys.stderr)
        return None
    vids = sorted(workdir.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    return vids[-1] if vids else None


# ----------------------------------------------------------------- metrics --

def summarise(shots: list[Shot], p: Probe) -> dict:
    durs = [s.duration for s in shots]
    if not durs:
        return {"shot_count": 0}
    lumas = [s.luma for s in shots if s.luma is not None]
    sats = [s.saturation for s in shots if s.saturation is not None]
    mots = [s.motion for s in shots if s.motion is not None]

    buckets = {"<1s": 0, "1-2s": 0, "2-3s": 0, "3-5s": 0, "5-8s": 0, ">8s": 0}
    for d in durs:
        if d < 1:
            buckets["<1s"] += 1
        elif d < 2:
            buckets["1-2s"] += 1
        elif d < 3:
            buckets["2-3s"] += 1
        elif d < 5:
            buckets["3-5s"] += 1
        elif d < 8:
            buckets["5-8s"] += 1
        else:
            buckets[">8s"] += 1

    def r(x, n=3):
        return round(x, n) if x is not None else None

    return {
        "shot_count": len(shots),
        "duration_s": r(p.duration),
        "cuts_per_min": r(len(shots) / p.duration * 60 if p.duration else 0, 2),
        "shot_len_min": r(min(durs)),
        "shot_len_max": r(max(durs)),
        "shot_len_mean": r(statistics.fmean(durs)),
        "shot_len_median": r(statistics.median(durs)),
        "shot_len_stdev": r(statistics.pstdev(durs)) if len(durs) > 1 else 0.0,
        "shot_len_histogram": buckets,
        # A high ratio means the edit alternates long and short shots rather
        # than holding one tempo -- the numeric fingerprint of "rhythm".
        "tempo_variance_ratio": r(statistics.pstdev(durs) / statistics.fmean(durs)
                                  if len(durs) > 1 and statistics.fmean(durs) else 0, 3),
        "luma_mean": r(statistics.fmean(lumas), 2) if lumas else None,
        "luma_range": r(max(lumas) - min(lumas), 2) if len(lumas) > 1 else None,
        "saturation_mean": r(statistics.fmean(sats), 2) if sats else None,
        "motion_mean": r(statistics.fmean(mots), 3) if mots else None,
        "motion_max": r(max(mots), 3) if mots else None,
        "hard_cuts": sum(1 for s in shots if s.transition_in == "cut") - 1,
        "dissolves": sum(1 for s in shots if s.transition_in == "dissolve"),
        "resolution": f"{p.width}x{p.height}" if p.width else "unknown",
        "aspect": p.aspect,
        "fps": r(p.fps, 2),
        "has_audio": p.has_audio,
    }


def analyse_file(video: Path, out_root: Path, label: str,
                 source_url: str = "", stills: bool = True) -> dict:
    print(f"  probing {video.name}")
    p = probe(video)
    if not p.duration:
        print("  ! could not read duration; skipping", file=sys.stderr)
        return {"id": label, "error": "probe_failed", "source_url": source_url}

    print(f"  {p.duration:.2f}s  {p.width}x{p.height} ({p.aspect})  {p.fps:.2f}fps")
    print("  detecting cuts (2 passes)")
    boundaries, diag = detect_cuts(video, p.duration)
    shots = shots_from_cuts(boundaries, p.duration)
    print(f"  {len(shots)} shots  (stage1 {diag['stage1_cuts']}, "
          f"+{diag['stage2_added']} from {diag['long_shots_rescanned']} long shots, "
          f"{diag.get('soft_transitions', 0)} dissolve(s), "
          f"threshold {diag.get('adaptive_threshold')})")

    shot_dir = out_root / label / "shots"
    still_paths: list[Path] = []
    for s in shots:
        shot_stats(video, s)
        if stills:
            mid = s.start + s.duration / 2
            dest = shot_dir / f"shot_{s.index:03d}.jpg"
            if extract_still(video, mid, dest):
                s.still = dest.relative_to(out_root).as_posix()
                still_paths.append(dest)
            head = shot_dir / f"shot_{s.index:03d}_in.jpg"
            extract_still(video, s.start + 0.05, head)

    sheet_rel = ""
    if still_paths:
        sheet = out_root / label / "contact_sheet.jpg"
        if contact_sheet(still_paths, sheet):
            sheet_rel = sheet.relative_to(out_root).as_posix()
            print(f"  contact sheet -> {sheet_rel}")

    record = {
        "id": label,
        "source_url": source_url,
        "file": video.name,
        "detection": diag,
        "metrics": summarise(shots, p),
        "contact_sheet": sheet_rel,
        "shots": [asdict(s) | {"duration": s.duration} for s in shots],
        # Filled in by a human (or a vision pass) after reading the sheet.
        "manual": {
            "genre_pack": None,
            "scene_types": [],
            "transitions": [],
            "camera_moves": [],
            "characters": [],
            "props": [],
            "sound_design": [],
            "notes": "",
        },
    }
    (out_root / label).mkdir(parents=True, exist_ok=True)
    (out_root / label / "metrics.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return record


# -------------------------------------------------------------------- main --

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Shot-level analyser for short-form video.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--urls", help="text file, one URL per line (# = comment)")
    src.add_argument("--url", action="append", help="a single URL (repeatable)")
    src.add_argument("--local", help="directory of already-downloaded videos")
    ap.add_argument("--out", default="./out", help="output directory")
    ap.add_argument("--cookies-from-browser",
                    help="chrome | firefox | edge — required for private "
                         "collections such as your own /saved/ page")
    ap.add_argument("--cookies", help="path to a cookies.txt file")
    ap.add_argument("--no-stills", action="store_true",
                    help="metrics only, no image extraction")
    ap.add_argument("--limit", type=int, default=0, help="stop after N videos")
    args = ap.parse_args()

    out_root = Path(args.out).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    dl_dir = out_root / "_downloads"

    jobs: list[tuple[str, Path | None]] = []
    if args.local:
        for f in sorted(Path(args.local).glob("*")):
            if f.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm", ".m4v"}:
                jobs.append(("", f))
    else:
        urls: list[str] = []
        if args.urls:
            for line in Path(args.urls).read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
        urls += args.url or []
        jobs = [(u, None) for u in urls]

    if args.limit:
        jobs = jobs[:args.limit]
    if not jobs:
        print("nothing to do", file=sys.stderr)
        return 1

    print(f"ffmpeg : {FFMPEG}")
    print(f"ffprobe: {FFPROBE or '(absent — falling back to ffmpeg -i)'}")
    print(f"{len(jobs)} item(s) -> {out_root}\n")

    records, failed = [], []
    for i, (url, local) in enumerate(jobs, 1):
        name = local.name if local else url
        print(f"[{i}/{len(jobs)}] {name}")
        video = local
        if video is None:
            video = download(url, dl_dir, args.cookies_from_browser, args.cookies)
            if video is None:
                failed.append(url)
                print()
                continue
        label = video.stem
        try:
            records.append(analyse_file(video, out_root, label, url,
                                        stills=not args.no_stills))
        except Exception as exc:                      # keep the batch alive
            print(f"  ! {type(exc).__name__}: {exc}", file=sys.stderr)
            failed.append(url or str(local))
        print()

    index = {
        "generated_by": "shotscan.py",
        "ffmpeg": FFMPEG,
        "settings": {
            "pass1_threshold": PASS1_THRESHOLD,
            "pass2_threshold": PASS2_THRESHOLD,
            "long_shot_s": LONG_SHOT_S,
            "min_shot_s": MIN_SHOT_S,
        },
        "count": len(records),
        "failed": failed,
        "videos": records,
    }
    (out_root / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"done: {len(records)} analysed, {len(failed)} failed")
    print(f"index -> {out_root / 'index.json'}")
    if records:
        allshots = [sh["duration"] for r in records for sh in r.get("shots", [])]
        if allshots:
            print(f"corpus: {len(allshots)} shots, "
                  f"median {statistics.median(allshots):.2f}s, "
                  f"mean {statistics.fmean(allshots):.2f}s")
    return 0 if records else 1


if __name__ == "__main__":
    sys.exit(main())
