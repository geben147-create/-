#!/usr/bin/env python3
"""ocr.py <files/globs...> [--lang kor+eng] [--psm 6] [--preprocess] [--json]"""
import argparse, glob, json, os, shutil, subprocess, sys, tempfile, importlib

def ensure(pkg, mod=None):
    try: return importlib.import_module(mod or pkg)
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", pkg], check=True)
        return importlib.import_module(mod or pkg)

ap = argparse.ArgumentParser()
ap.add_argument("files", nargs="+"); ap.add_argument("--lang", default="kor+eng"); ap.add_argument("--psm", default="6")
ap.add_argument("--preprocess", action="store_true"); ap.add_argument("--json", action="store_true")
a = ap.parse_args()
pyt = ensure("pytesseract"); PIL = ensure("pillow", "PIL.Image"); ImageOps = importlib.import_module("PIL.ImageOps")
if not shutil.which("tesseract"):
    sys.exit("tesseract binary not found. brew install tesseract tesseract-lang | apt install tesseract-ocr tesseract-ocr-kor | winget install UB-Mannheim.TesseractOCR")

def pages(path):
    if path.lower().endswith(".pdf"):
        tmp = tempfile.mkdtemp()
        if shutil.which("pdftoppm"):
            subprocess.run(["pdftoppm", "-r", "200", "-png", path, os.path.join(tmp, "p")], check=True)
            return sorted(glob.glob(os.path.join(tmp, "p*.png")))
        fitz = ensure("pymupdf", "fitz"); out = []
        for i, pg in enumerate(fitz.open(path)):
            f = os.path.join(tmp, f"p{i:03d}.png"); pg.get_pixmap(dpi=200).save(f); out.append(f)
        return out
    return [path]

files = [f for pat in a.files for f in (glob.glob(pat) or [pat])]
result = {}
for f in files:
    for p in pages(f):
        img = PIL.open(p)
        if a.preprocess:
            img = ImageOps.grayscale(img); w, h = img.size
            if w < 1600: img = img.resize((w * 2, h * 2))
            img = ImageOps.autocontrast(img).point(lambda x: 255 if x > 150 else 0)
        cfg = f"--psm {a.psm}"
        if a.json:
            d = pyt.image_to_data(img, lang=a.lang, config=cfg, output_type=pyt.Output.DICT)
            words = [{"text": t, "conf": c, "box": [l, tp, w_, h_]} for t, c, l, tp, w_, h_ in
                     zip(d["text"], d["conf"], d["left"], d["top"], d["width"], d["height"]) if t.strip()]
            result[p] = words
        else:
            print(f"=== {p} ==="); print(pyt.image_to_string(img, lang=a.lang, config=cfg).strip()); print()
if a.json: print(json.dumps(result, ensure_ascii=False, indent=1))
