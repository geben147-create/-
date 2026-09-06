#!/usr/bin/env python3
"""
build_video.py — turn 9 stills + scenes.json into a finished 9:16 Instagram video.

Text is NEVER generated into the image. It is composited here, where it is
correct, legible and editable. That split is the whole point: the model draws
the picture, code draws the words.

    python build_video.py                      # images/S1.png .. S9.png
    python build_video.py --images ./images --out out/final.mp4

Needs: ffmpeg with libass, and a Korean font installed (Noto Sans KR).
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys
from pathlib import Path

W, H, FPS = 1080, 1920, 30
XFADE = 0.20                      # short dissolve; the guide keeps cuts dominant
FONT = "Noto Sans KR"

# ASS colours are &HAABBGGRR — blue and red are swapped versus hex.
# outline must CONTRAST with the fill or the text haloes and turns mushy:
# dark rim under white text, white rim under dark text.
THEME = {
    "light":  {"title": "&H00201A16", "outline": "&H00FFFFFF", "check": "&H006F8712",
               "kicker_bg": "&H003DC5FF", "kicker_tx": "&H00201A16"},
    "dark":   {"title": "&H00FFFFFF", "outline": "&H00201A16", "check": "&H003DC5FF",
               "kicker_bg": "&H003DC5FF", "kicker_tx": "&H00201A16"},
    "accent": {"title": "&H00FFFFFF", "outline": "&H00201A16", "check": "&H003DC5FF",
               "kicker_bg": "&H003DC5FF", "kicker_tx": "&H00201A16"},
}


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if p.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{' '.join(cmd[:12])}...\n{p.stderr[-1600:]}")
    return p


def ffmpeg_bin():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ffmpeg not found. Install ffmpeg or `pip install imageio-ffmpeg`.")


FF = ffmpeg_bin()


def t(sec: float) -> str:
    cs = int(round(sec * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ass_for(scene: dict) -> str:
    """One ASS file per scene. Times are local to that scene's clip."""
    th = THEME[scene.get("theme", "light")]
    dur = scene["dur"]
    is_list = bool(scene.get("items"))

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Kicker,{FONT},46,{th['kicker_tx']},{th['kicker_bg']},{th['kicker_bg']},-1,3,16,0,8,90,90,150,1
Style: Title,{FONT},{86 if is_list else 80},{th['title']},{th['outline']},&H60000000,-1,1,4,2,8,90,90,{240 if is_list else 300},1
Style: Item,{FONT},50,{th['title']},{th['outline']},&H00000000,-1,1,3,0,7,120,110,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    if scene.get("kicker"):
        ev.append(f"Dialogue: 0,{t(0.10)},{t(dur)},Kicker,,0,0,0,,"
                  f"{{\\fad(220,120)}}\\h{scene['kicker']}\\h")
    title = scene["title"].replace("\n", "\\N")
    ev.append(f"Dialogue: 0,{t(0.22)},{t(dur)},Title,,0,0,0,,"
              f"{{\\fad(300,160)}}{title}")
    for i, item in enumerate(scene.get("items", [])):
        start = 0.75 + i * 0.62          # staggered reveal keeps eyes moving
        y = 640 + i * 158                # last item ends well above the artwork
        ev.append(f"Dialogue: 0,{t(start)},{t(dur)},Item,,0,0,0,,"
                  f"{{\\pos(120,{y})\\fad(260,140)}}"
                  f"{{\\c{th['check']}}}✓{{\\c{th['title']}}}\\h\\h{item}")
    return head + "\n".join(ev) + "\n"


def build_scene(img: Path, scene: dict, ass: Path, dest: Path, idx: int):
    frames = int(round(scene["dur"] * FPS))
    # Alternate a slow push in and pull out so consecutive cards do not feel
    # mechanical. Movement stays under 8% so the first and last beats settle.
    if idx % 2 == 0:
        z = f"min(1.0+0.00090*on,1.075)"
    else:
        z = f"max(1.075-0.00090*on,1.0)"
    vf = (
        f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
        f"crop={W*2}:{H*2},"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={W}x{H}:fps={FPS},"
        f"subtitles='{ass.as_posix()}':fontsdir='/usr/local/share/fonts',"
        f"format=yuv420p"
    )
    run([FF, "-hide_banner", "-loglevel", "error", "-y",
         "-loop", "1", "-t", f"{scene['dur']:.3f}", "-i", str(img),
         "-vf", vf, "-r", str(FPS), "-frames:v", str(frames),
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", str(dest)])


def stitch(clips: list[Path], durs: list[float], dest: Path):
    """Chain xfade so each card melts into the next instead of snapping."""
    if len(clips) == 1:
        shutil.copy(clips[0], dest); return
    cmd = [FF, "-hide_banner", "-loglevel", "error", "-y"]
    for c in clips:
        cmd += ["-i", str(c)]
    parts, prev, offset = [], "0:v", 0.0
    for i in range(1, len(clips)):
        offset += durs[i - 1] - XFADE
        out = f"x{i}"
        parts.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XFADE}"
                     f":offset={offset:.3f}[{out}]")
        prev = out
    cmd += ["-filter_complex", ";".join(parts), "-map", f"[{prev}]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart",
            str(dest)]
    run(cmd)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenes", default="scenes.json")
    ap.add_argument("--images", default="images")
    ap.add_argument("--work", default="work")
    ap.add_argument("--out", default="out/final.mp4")
    a = ap.parse_args()

    cfg = json.loads(Path(a.scenes).read_text(encoding="utf-8"))
    scenes = cfg["scenes"]
    imgdir, work = Path(a.images), Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)

    missing = [s["id"] for s in scenes
               if not any((imgdir / f"{s['id']}{e}").exists()
                          for e in (".png", ".jpg", ".jpeg", ".webp"))]
    if missing:
        sys.exit(f"missing images for: {', '.join(missing)}\n"
                 f"put them in {imgdir}/ as S1.png .. S9.png")

    clips, durs = [], []
    for i, s in enumerate(scenes):
        img = next(imgdir / f"{s['id']}{e}" for e in (".png", ".jpg", ".jpeg", ".webp")
                   if (imgdir / f"{s['id']}{e}").exists())
        ass = work / f"{s['id']}.ass"
        ass.write_text(ass_for(s), encoding="utf-8")
        clip = work / f"{s['id']}.mp4"
        print(f"  [{i+1}/{len(scenes)}] {s['id']} {s['role']:<11} {s['dur']}s")
        build_scene(img, s, ass, clip, i)
        clips.append(clip); durs.append(s["dur"])

    print("  stitching...")
    stitch(clips, durs, Path(a.out))
    total = sum(durs) - XFADE * (len(durs) - 1)
    print(f"\ndone -> {a.out}  ({total:.2f}s, {W}x{H}, {FPS}fps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
