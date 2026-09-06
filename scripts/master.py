"""Mix-bus processing, mastering, exports and the level-matched A/B file.
Chain: 20 Hz high-pass -> mid/side width -> loudness normalise to target LUFS ->
4x-oversampled brick-wall limiter at the true-peak ceiling -> (re-check LUFS, one correction pass).
Exports: archive 24-bit 44.1 kHz WAV, distributor candidate 16-bit 44.1 kHz FLAC (TPDF dither),
listening MP3 (320 kbps), A/B MP3 (original 24 s -> 1 s silence -> arranged 24 s, level matched)."""
from __future__ import annotations
import os, subprocess
import numpy as np
from audiolib import (load_audio, save_wav, highpass, mid_side, loudness_normalize, limiter, integrated_lufs,
                      measure, write_json, resample, FFMPEG, stereo_stats)


def master(track_dir: str, manifest: dict, target_lufs: float = -14.0, ceiling_dbtp: float = -1.0,
           side_gain: float | None = None) -> dict:
    pm_path = os.path.join(track_dir, "05_mix", "premaster.wav")
    x, sr = load_audio(pm_path)
    if sr != 44100:  # deliver at 44.1 kHz: resample BEFORE limiting so the ceiling holds at the delivery rate
        x = resample(x, sr, 44100); sr = 44100
    st = stereo_stats(x, sr)
    if side_gain is None:
        side_gain = 0.75 if st["correlation"] < 0.3 else (0.85 if st["correlation"] < 0.5 else 0.92)
    y = highpass(x, sr, 20.0)
    y = mid_side(y, side_gain)
    y, g1 = loudness_normalize(y, sr, target_lufs)
    y = limiter(y, sr, ceiling_dbtp)
    l1 = integrated_lufs(y, sr)
    g2 = 0.0
    if abs(l1 - target_lufs) > 0.3:  # limiter changed the loudness noticeably: one correction pass
        g2 = target_lufs - l1
        y = limiter(y * 10 ** (g2 / 20), sr, ceiling_dbtp)
    y44 = y
    mdir = os.path.join(track_dir, "06_master")
    os.makedirs(mdir, exist_ok=True)
    wav24 = os.path.join(mdir, "arranged_master_44k1_24bit.wav")
    flac16 = os.path.join(mdir, "distributor_candidate_44k1_16bit.flac")
    mp3 = os.path.join(mdir, "LISTEN_arranged.mp3")
    save_wav(wav24, y44, 44100, subtype="PCM_24")
    save_wav(flac16, y44, 44100, subtype="PCM_16", dither=True)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", wav24, "-codec:a", "libmp3lame", "-b:a", "320k", mp3], check=True)

    # ---- A/B file: same musical spot, original vs arranged, level matched before encoding
    orig, osr = load_audio(os.path.join(track_dir, "00_original", "original.wav"), 44100)
    off = manifest["original_offset_in_output_s"]
    cs = manifest["changed_sections"]
    t_orig = (cs[0]["orig_range"][0] - 4.0) if cs else 30.0
    t_orig = max(0.0, min(t_orig, len(orig) / 44100 - 25))
    seg_len = int(24 * 44100)
    a = orig[int(t_orig * 44100): int(t_orig * 44100) + seg_len]
    b = y44[int((t_orig + off) * 44100): int((t_orig + off) * 44100) + seg_len]
    la = integrated_lufs(a, 44100); lb = integrated_lufs(b, 44100)
    ref = min(la, lb, -14.0)
    a = a * 10 ** ((ref - la) / 20); b = b * 10 ** ((ref - lb) / 20)
    ab = np.concatenate([a, np.zeros((44100, 2)), b])
    ab = limiter(ab, 44100, -1.0)
    ab_wav = os.path.join(mdir, "AB_original24s_silence1s_arranged24s.wav")
    save_wav(ab_wav, ab, 44100, subtype="PCM_16", dither=True)
    ab_mp3 = ab_wav.replace(".wav", ".mp3")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", ab_wav, "-codec:a", "libmp3lame", "-b:a", "256k", ab_mp3], check=True)
    os.remove(ab_wav)

    settings = {"target_lufs": target_lufs, "ceiling_dbtp": ceiling_dbtp, "highpass_hz": 20.0, "side_gain": side_gain,
                "limiter_oversampling": 4, "gain_pass1_db": round(g1, 2), "gain_pass2_db": round(g2, 2),
                "ab_compare": {"orig_start_s": round(t_orig, 2), "arranged_start_s": round(t_orig + off, 2), "matched_lufs": round(ref, 2),
                               "order": "original 24 s -> 1 s silence -> arranged 24 s"},
                "premaster_correlation": round(st["correlation"], 3),
                "note": "Target loudness is this session's setting, not a distributor pass mark. Distributors normalise anyway."}
    write_json(os.path.join(mdir, "master_settings.json"), settings)
    return settings


def qc(track_dir: str) -> dict:
    before = measure(os.path.join(track_dir, "00_original", "original.wav"))
    after = measure(os.path.join(track_dir, "06_master", "arranged_master_44k1_24bit.wav"))
    flac = measure(os.path.join(track_dir, "06_master", "distributor_candidate_44k1_16bit.flac"))
    checks = {
        "no_clipping": bool(flac["clipped_samples_ge_0dbfs"] == 0),
        "true_peak_below_-1dBTP": bool(flac["true_peak_dbtp_4x"] <= -0.95),
        "dc_offset_below_1e-4": bool(flac["dc_offset_max_abs"] < 1e-4),
        "head_silence_below_8s": bool(flac["head_silence_s"] < 8),
        "tail_silence_below_8s": bool(flac["tail_silence_s"] < 8),
        "stereo_16bit_44k1": bool(flac["channels"] == 2 and flac["sample_rate"] == 44100 and flac["subtype"] == "PCM_16"),
        "no_negative_correlation_windows": bool(flac["neg_corr_ratio_1s"] < 0.05),
    }
    out = {"original": before, "master_24bit": after, "distributor_flac": flac, "checks": checks,
           "all_technical_checks_pass": all(checks.values()),
           "note": "Passing these numbers does not replace a full human listen (timing, dissonance, separation artefacts)."}
    write_json(os.path.join(track_dir, "06_master", "qc.json"), out)
    return out
