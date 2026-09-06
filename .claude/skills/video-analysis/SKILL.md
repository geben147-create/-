---
name: video-analysis
description: Analyze local video files (mp4/mov/mkv/webm) or downloaded YouTube videos with vision + audio. Extracts key frames with ffmpeg (scene detection), transcribes speech with faster-whisper (Korean/English/any), runs OCR on frames, then Claude reads the frames as images. Use when the user says "영상 분석", "비디오 분석", "프레임 뽑아", "이 영상에서 무슨 말 해", "자막 없는 영상", "transcribe", "what happens in this video", or gives a video file path.
---

# Video analysis (frames + speech + OCR)

## 1. Probe
```bash
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate -of json "<video>"
```

## 2. Key frames (vision)
```bash
bash "${CLAUDE_SKILL_DIR:-.claude/skills/video-analysis}/scripts/extract_frames.sh" "<video>" [max_frames=24] [mode=scene|interval]
```
Writes `./video-analysis/<name>/frames/frame_<HH-MM-SS>.jpg` (timestamp in file name, burned-in
overlay at bottom) and prints a JSON list. Then **Read the jpg files** (the Read tool shows images)
in batches of 6-10 and describe what changes between them. Keep `max_frames` ≤ 30 per pass;
for long videos do a coarse pass, then a second pass on the interesting range with
`START=00:12:00 END=00:15:00`.

## 3. Speech → text
```bash
python3 "${CLAUDE_SKILL_DIR:-.claude/skills/video-analysis}/scripts/transcribe.py" "<video or audio>" --lang ko --model small
```
Uses faster-whisper (CPU works; `--model medium|large-v3` for accuracy, `--device cuda` for GPU).
Writes `transcript.txt`, `transcript.srt`, `transcript.timed.txt` next to the frames dir.
Auto-installs `faster-whisper` if missing. `--lang auto` detects language.

## 4. Text on screen (OCR)
```bash
python3 .claude/skills/ocr/scripts/ocr.py video-analysis/<name>/frames/*.jpg --lang kor+eng
```

## 5. Report
Combine: timeline table (`시간 | 화면 | 음성 | 화면 텍스트`), then summary, then answer the
user's question. Cite timestamps. Save as `video-analysis/<name>/report.md`.

## Alternatives on this machine
- `claude-video-vision` plugin: `/watch-video file.mp4 "question"` does frames + audio in one shot.
- `video-frames` skill (mugnimaestra) — `extract_frames.py --preset ocr|detailed --scene-threshold 0.3`.
- Gemini-backed `yt-analysis` MCP if the user prefers cloud video understanding (needs GEMINI_API_KEY).
