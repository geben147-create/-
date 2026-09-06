---
name: youtube-analysis
description: Analyze any YouTube video from its URL. Pulls metadata, creator subtitles AND auto-generated captions (Korean/English/any language) with yt-dlp, optionally top comments, then summarizes / answers questions. Use when the user gives a youtube.com or youtu.be link, says "이 영상 분석해줘", "자막 뽑아줘", "유튜브 요약", "transcript", "subtitles", or wants to research what a video says. Falls back to youtube-transcript-api and to Whisper audio transcription when no captions exist.
---

# YouTube analysis (yt-dlp based)

## Fast path (use this first)

```bash
python3 "${CLAUDE_SKILL_DIR:-.claude/skills/youtube-analysis}/scripts/yt_subs.py" "<URL>" --langs ko,en --comments 30
```

Output: a Markdown file in `./yt-analysis/<video_id>/` containing
`meta.json`, `transcript.<lang>.txt` (plain text), `transcript.<lang>.timed.txt`
(with `[mm:ss]` stamps), `comments.json` (if requested) and `report.md`
that concatenates everything. Read `report.md`, then answer the user.

Flags:
- `--langs ko,en,ja` language priority (creator subs first, then auto captions).
- `--all-langs` grab every available track.
- `--comments N` also fetch top N comments (no API key needed).
- `--audio` download audio (m4a) so it can be transcribed with Whisper when there are no captions:
  `python3 .claude/skills/video-analysis/scripts/transcribe.py yt-analysis/<id>/audio.m4a --lang ko`
- `--video` download the video (720p) for frame/vision analysis with the `video-analysis` skill.
- `--cookies-from-browser chrome` when YouTube blocks the request (age-restricted, "Sign in to confirm you're not a bot").

## Analysis procedure

1. Run the script. If it errors with a proxy/403 message, retry with `--cookies-from-browser chrome` (or `firefox`, `edge`).
2. Read `report.md`. For long videos (> 1h) read `transcript.<lang>.txt` in chunks.
3. Produce: TL;DR (3 lines) → 구조/챕터별 요약 (with timestamps) → 핵심 주장·수치·인용 → 반론/주의점 → 댓글 반응 요약 (if fetched).
4. Quote timestamps like `[12:34]` so the user can jump to them.
5. If the user asks something visual ("what's on the slide at 3:00", thumbnails, charts), download with `--video` and hand off to the `video-analysis` skill.

## Alternatives available on this machine

- MCP `youtube-transcript` (`@fabriqa.ai/youtube-transcript-mcp`): tools `get-transcript`, `get-transcript-languages`. Zero-config, good for quick transcripts under ~25k tokens.
- `claude-video-vision` plugin: `/watch-video <url> "question"` sends frames + audio to Claude (needs ffmpeg; yt-dlp for URLs).
- `last30days` plugin: `/last30days <topic>` when the user wants what YouTube/Reddit/X say about a topic in the last 30 days rather than one video.
