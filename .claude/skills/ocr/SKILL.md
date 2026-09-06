---
name: ocr
description: Extract text from images, screenshots, scanned PDFs and video frames with Tesseract OCR (Korean + English + 100 languages). Use when the user says "OCR", "글자 추출", "이미지에서 텍스트", "스크린샷 텍스트", "자막 이미지", "표 읽어줘", or hands over png/jpg/pdf whose text must be read. For handwriting or very noisy images, also Read the image directly (Claude vision) and merge.
---

# OCR

```bash
python3 "${CLAUDE_SKILL_DIR:-.claude/skills/ocr}/scripts/ocr.py" <img or pdf or glob...> --lang kor+eng [--psm 6] [--json]
```
- Prints text per file with `=== file ===` headers; `--json` gives boxes + confidence.
- PDFs are rasterised at 200 dpi (needs `pdftoppm` from poppler, or falls back to PyMuPDF).
- `--preprocess` applies grayscale + upscale + threshold (helps small subtitles / low-contrast video frames).
- Language codes: `kor`, `eng`, `jpn`, `chi_sim`; combine with `+`.

Install if missing: `brew install tesseract tesseract-lang` / `sudo apt install tesseract-ocr tesseract-ocr-kor` /
`winget install UB-Mannheim.TesseractOCR` then `pip install pytesseract pillow`.

After OCR, always sanity-check numbers and names against the image with the Read tool (vision).
For better Korean accuracy on documents, alternatives: `pip install easyocr` (`easyocr -l ko en -f img.png`)
or `pip install paddleocr` (PP-OCRv4 is stronger for CJK).
