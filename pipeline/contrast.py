#!/usr/bin/env python3
"""
Scrim alpha calculator (WCAG 2.x relative luminance, sRGB compositing).

The guide's table is computed for a DARK scrim (#080A0E) under WHITE text,
where the worst frame of the video is pure white.

This build uses the reference art direction: a LIGHT page. So the polarity
inverts -- a near-white scrim under near-black text, and the worst frame the
video can produce is pure BLACK. Same method, mirrored inputs.
"""

def lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def lum(rgb):
    r, g, b = (lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

def composite(scrim, backdrop, alpha):
    """sRGB-space alpha compositing -- what the browser actually does."""
    return tuple(alpha * s + (1 - alpha) * b for s, b in zip(scrim, backdrop))

SCRIM_LIGHT = (247, 247, 250)   # --scrim-light  #F7F7FA
INK         = (14, 17, 22)      # --ink          #0E1116
INK_2       = (74, 80, 90)      # --ink-2 flattened, for the body-copy check
WORST_DARK  = (0, 0, 0)         # worst frame a video can show under a light scrim

SCRIM_DARK  = (8, 10, 14)       # the guide's own scrim, for cross-checking
ON_VIDEO    = (242, 245, 249)   # the guide's #F2F5F9
WORST_LIGHT = (255, 255, 255)

def table(title, scrim, backdrop, texts):
    print(f"\n{title}")
    print(f"{'alpha':>6} | " + " | ".join(f"{n:>16}" for n, _ in texts))
    print("-" * (8 + 19 * len(texts)))
    for a in (0.30, 0.45, 0.50, 0.58, 0.62, 0.70, 0.78, 0.85, 0.90):
        bg = composite(scrim, backdrop, a)
        cells = []
        for _, t in texts:
            r = contrast(t, bg)
            verdict = "body" if r >= 4.5 else ("large" if r >= 3.0 else "FAIL")
            cells.append(f"{r:8.2f}:1 {verdict:<5}")
        print(f"{a:>6.2f} | " + " | ".join(f"{c:>16}" for c in cells))

table("LIGHT build (this site): near-white scrim #F7F7FA over a pure-BLACK worst frame",
      SCRIM_LIGHT, WORST_DARK, [("ink #0E1116", INK), ("ink-2 #4A505A", INK_2)])

table("Cross-check of the guide's own table: #080A0E scrim over a pure-WHITE worst frame",
      SCRIM_DARK, WORST_LIGHT, [("#F2F5F9", ON_VIDEO)])
