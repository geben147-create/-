#!/usr/bin/env python3
"""Transcribe video/audio with faster-whisper. transcribe.py <file> [--lang ko|en|auto] [--model small] [--device cpu|cuda] [--out DIR]"""
import argparse, os, sys, subprocess, shutil, importlib

def ensure(pkg, mod=None):
    try:
        return importlib.import_module(mod or pkg)
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], check=True)
        return importlib.import_module(mod or pkg)

def fmt(t, srt=False):
    ms = int(round((t - int(t)) * 1000)); h, r = divmod(int(t), 3600); m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}" if srt else (f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}")

ap = argparse.ArgumentParser()
ap.add_argument("file"); ap.add_argument("--lang", default="auto"); ap.add_argument("--model", default="small")
ap.add_argument("--device", default="auto"); ap.add_argument("--out", default=None)
a = ap.parse_args()
fw = ensure("faster-whisper", "faster_whisper")
src = a.file
if shutil.which("ffmpeg") and not src.lower().endswith((".wav", ".mp3", ".m4a", ".flac", ".ogg")):
    wav = os.path.splitext(src)[0] + ".16k.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True); src = wav
name = os.path.basename(a.file).rsplit(".", 1)[0]
out = a.out or os.path.join("video-analysis", name); os.makedirs(out, exist_ok=True)
compute = "int8" if a.device in ("cpu", "auto") else "float16"
model = fw.WhisperModel(a.model, device=a.device, compute_type=compute)
segs, info = model.transcribe(src, language=None if a.lang == "auto" else a.lang, vad_filter=True, beam_size=5)
plain, timed, srt = [], [], []
for i, s in enumerate(segs, 1):
    txt = s.text.strip(); plain.append(txt); timed.append(f"[{fmt(s.start)}] {txt}")
    srt += [str(i), f"{fmt(s.start, True)} --> {fmt(s.end, True)}", txt, ""]
    print(timed[-1], flush=True)
open(os.path.join(out, "transcript.txt"), "w", encoding="utf-8").write("\n".join(plain))
open(os.path.join(out, "transcript.timed.txt"), "w", encoding="utf-8").write("\n".join(timed))
open(os.path.join(out, "transcript.srt"), "w", encoding="utf-8").write("\n".join(srt))
print(f"\nlanguage={info.language} p={info.language_probability:.2f} -> {out}/transcript.*", file=sys.stderr)
