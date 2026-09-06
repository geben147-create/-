#!/usr/bin/env python3
"""Fetch YouTube metadata + subtitles (manual first, then auto captions) with yt-dlp.

Usage:
  yt_subs.py URL [--langs ko,en] [--all-langs] [--comments N] [--audio] [--video]
             [--cookies-from-browser chrome] [--out DIR]
Writes ./yt-analysis/<id>/{meta.json,transcript.<lang>.txt,transcript.<lang>.timed.txt,
comments.json,report.md}. Prints the report path.
"""
import argparse, json, os, re, subprocess, sys, shutil, glob, html

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

def ensure_ytdlp():
    if shutil.which("yt-dlp"):
        return "yt-dlp"
    print("yt-dlp not found -> installing with pip", file=sys.stderr)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U", "yt-dlp"], check=False)
    if shutil.which("yt-dlp"):
        return "yt-dlp"
    return f"{sys.executable} -m yt_dlp"

def vtt_to_lines(path):
    """Parse WebVTT -> list of (start_seconds, text) with duplicates from rolling captions removed."""
    lines, last = [], None
    ts_re = re.compile(r"(\d+):(\d\d):(\d\d)\.(\d+)\s+-->")
    ts_re2 = re.compile(r"(\d\d):(\d\d)\.(\d+)\s+-->")
    cur = None
    with open(path, encoding="utf-8", errors="ignore") as f:
        for raw in f:
            raw = raw.rstrip("\n")
            m = ts_re.match(raw)
            if m:
                cur = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]); continue
            m = ts_re2.match(raw)
            if m:
                cur = int(m[1]) * 60 + int(m[2]); continue
            if cur is None or not raw.strip() or raw.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
                continue
            txt = re.sub(r"<[^>]+>", "", raw)
            txt = html.unescape(txt).strip()
            if not txt or txt == last:
                continue
            last = txt
            lines.append((cur, txt))
    # merge lines that repeat as rolling windows (auto captions)
    merged = []
    for t, txt in lines:
        if merged and txt in merged[-1][1]:
            continue
        if merged and merged[-1][1] in txt:
            merged[-1] = (merged[-1][0], txt); continue
        merged.append((t, txt))
    return merged

def fmt(t):
    h, r = divmod(int(t), 3600); m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--langs", default="ko,en")
    ap.add_argument("--all-langs", action="store_true")
    ap.add_argument("--comments", type=int, default=0)
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--cookies-from-browser", default=None)
    ap.add_argument("--out", default="yt-analysis")
    a = ap.parse_args()

    ytdlp = ensure_ytdlp().split()
    base = ytdlp + ["--no-warnings", "--ignore-config"]
    if a.cookies_from_browser:
        base += ["--cookies-from-browser", a.cookies_from_browser]

    # 1) metadata
    rc, out, err = run(base + ["--dump-single-json", "--skip-download",
                               *( ["--write-comments", "--extractor-args", f"youtube:max_comments={a.comments},all,{a.comments},0"] if a.comments else []),
                               a.url])
    if rc != 0:
        print(err.strip(), file=sys.stderr)
        print("HINT: retry with --cookies-from-browser chrome  (or check proxy/VPN)", file=sys.stderr)
        sys.exit(rc)
    info = json.loads(out)
    vid = info.get("id", "video")
    outdir = os.path.join(a.out, vid); os.makedirs(outdir, exist_ok=True)

    meta = {k: info.get(k) for k in ("id", "title", "channel", "uploader", "upload_date", "duration",
                                     "view_count", "like_count", "comment_count", "description",
                                     "tags", "categories", "webpage_url", "chapters", "language")}
    meta["subtitle_langs"] = sorted((info.get("subtitles") or {}).keys())
    meta["auto_caption_langs"] = sorted((info.get("automatic_captions") or {}).keys())
    json.dump(meta, open(os.path.join(outdir, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    comments = []
    if a.comments and info.get("comments"):
        comments = sorted(info["comments"], key=lambda c: -(c.get("like_count") or 0))[: a.comments]
        json.dump([{k: c.get(k) for k in ("author", "text", "like_count", "timestamp")} for c in comments],
                  open(os.path.join(outdir, "comments.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 2) subtitles: manual + auto, requested langs (or all)
    langs = "all" if a.all_langs else a.langs
    sub_cmd = base + ["--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", langs,
                      "--sub-format", "vtt/srt/best", "-o", os.path.join(outdir, "%(id)s.%(ext)s"), a.url]
    run(sub_cmd)
    tracks = {}
    for p in sorted(glob.glob(os.path.join(outdir, f"{vid}.*.vtt")) + glob.glob(os.path.join(outdir, f"{vid}.*.srt"))):
        lang = os.path.basename(p).split(".")[1]
        if lang in tracks:
            continue  # manual track already parsed (yt-dlp writes it with the same name)
        lines = vtt_to_lines(p) if p.endswith(".vtt") else []
        if not lines:
            continue
        tracks[lang] = lines
        with open(os.path.join(outdir, f"transcript.{lang}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(t for _, t in lines))
        with open(os.path.join(outdir, f"transcript.{lang}.timed.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(f"[{fmt(s)}] {t}" for s, t in lines))

    # 2b) fallback: youtube-transcript-api
    if not tracks:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            for tr in YouTubeTranscriptApi().list(vid):
                data = tr.fetch()
                lines = [(x.start, x.text) for x in data]
                tracks[tr.language_code] = lines
                with open(os.path.join(outdir, f"transcript.{tr.language_code}.timed.txt"), "w", encoding="utf-8") as f:
                    f.write("\n".join(f"[{fmt(s)}] {t}" for s, t in lines))
                with open(os.path.join(outdir, f"transcript.{tr.language_code}.txt"), "w", encoding="utf-8") as f:
                    f.write("\n".join(t for _, t in lines))
                break
        except Exception as e:  # noqa
            print(f"youtube-transcript-api fallback failed: {e}", file=sys.stderr)

    # 3) optional media
    if a.audio:
        run(base + ["-f", "bestaudio[ext=m4a]/bestaudio", "-o", os.path.join(outdir, "audio.%(ext)s"), a.url])
    if a.video:
        run(base + ["-f", "bv*[height<=720]+ba/b[height<=720]", "--merge-output-format", "mp4",
                    "-o", os.path.join(outdir, "video.%(ext)s"), a.url])

    # 4) report
    rep = [f"# {meta['title']}", "",
           f"- URL: {meta['webpage_url']}", f"- Channel: {meta['channel'] or meta['uploader']}",
           f"- Uploaded: {meta['upload_date']}  Duration: {fmt(meta['duration'] or 0)}",
           f"- Views: {meta['view_count']}  Likes: {meta['like_count']}  Comments: {meta['comment_count']}",
           f"- Subtitle tracks: {meta['subtitle_langs']}  Auto captions: {meta['auto_caption_langs']}", ""]
    if meta.get("chapters"):
        rep.append("## Chapters")
        rep += [f"- [{fmt(c['start_time'])}] {c['title']}" for c in meta["chapters"]]
        rep.append("")
    rep += ["## Description", meta.get("description") or "", ""]
    if not tracks:
        rep += ["## Transcript", "_No captions available. Re-run with --audio and transcribe with "
                "`.claude/skills/video-analysis/scripts/transcribe.py`._", ""]
    for lang, lines in tracks.items():
        rep += [f"## Transcript ({lang}) — {len(lines)} lines", ""]
        rep += [f"[{fmt(s)}] {t}" for s, t in lines]
        rep.append("")
    if comments:
        rep += ["## Top comments", ""]
        rep += [f"- ({c.get('like_count') or 0}👍) {c.get('author')}: {(c.get('text') or '').strip()}" for c in comments]
    path = os.path.join(outdir, "report.md")
    open(path, "w", encoding="utf-8").write("\n".join(rep))
    print(path)

if __name__ == "__main__":
    main()
