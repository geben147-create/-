#!/usr/bin/env python3
"""
Single source of truth for what each section plays.

Every remote URL below came out of a Pollo generation run made in this repo's
session; the prompts and model choices are recorded in pipeline/PROMPTS.md.
Regenerate site/media/sources.js with:  python3 pipeline/make_manifest.py
"""
import json, pathlib

# tint = the render's own base colour, painted behind the <video>. If the
# network never delivers a frame the section still reads as designed instead
# of flashing a black rectangle.
CLIPS = {
    "s1-hero": {
        "tint": "linear-gradient(160deg,#FAFAFC 0%,#F1F1F6 46%,#E6E6EF 100%)",
        "tintFlat": "#F1F1F6",
        "poster":  {"local": "media/poster/s1-hero.webp",  "remote": None},
        "desktop": {"local": "media/s1-hero-1920.mp4",     "remote": None},
        "webm":    {"local": "media/s1-hero-1920.webm",    "remote": None},
        "mobile":  {"local": "media/s1-hero-mobile-1080v.mp4", "remote": None},
    },
    "s2-broken": {
        "tint": "linear-gradient(160deg,#F0F0F4 0%,#E6E6EC 52%,#DEDEE6 100%)",
        "tintFlat": "#E6E6EC",
        "poster":  {"local": "media/poster/s2-broken.webp", "remote": None},
        "desktop": {"local": "media/s2-broken-1920.mp4",    "remote": None},
        "webm":    {"local": "media/s2-broken-1920.webm",   "remote": None},
    },
    "s3-corridor": {
        "tint": "linear-gradient(180deg,#FAFAFC 0%,#F2F2F7 60%,#EAEAF1 100%)",
        "tintFlat": "#F2F2F7",
        "poster":  {"local": "media/poster/s3-corridor.webp",  "remote": None},
        "desktop": {"local": "media/s3-corridor-scrub.mp4",    "remote": None},
    },
    "s4-a": {
        "tint": "linear-gradient(160deg,#FAFAFC 0%,#EFEFF4 100%)",
        "tintFlat": "#EFEFF4",
        "poster":  {"local": "media/poster/s4-a.webp", "remote": None},
        "desktop": {"local": "media/s4-a-960.mp4",     "remote": None},
    },
    "s4-b": {
        "tint": "linear-gradient(160deg,#FAFAFC 0%,#EFEFF4 100%)",
        "tintFlat": "#EFEFF4",
        "poster":  {"local": "media/poster/s4-b.webp", "remote": None},
        "desktop": {"local": "media/s4-b-960.mp4",     "remote": None},
    },
    "s4-c": {
        "tint": "linear-gradient(160deg,#FAFAFC 0%,#EFEFF4 100%)",
        "tintFlat": "#EFEFF4",
        "poster":  {"local": "media/poster/s4-c.webp", "remote": None},
        "desktop": {"local": "media/s4-c-960.mp4",     "remote": None},
    },
    "s6-cta": {
        "tint": "linear-gradient(160deg,#FBFAF8 0%,#F3F0EA 54%,#EDE9E2 100%)",
        "tintFlat": "#F3F0EA",
        "poster":  {"local": "media/poster/s6-cta.webp", "remote": None},
        "desktop": {"local": "media/s6-cta-1920.mp4",    "remote": None},
        "webm":    {"local": "media/s6-cta-1920.webm",   "remote": None},
    },
}

# Pollo CDN URLs, filled in as each generation finishes.
CDN = "https://videocdn.pollo.ai/web-cdn/pollo/production/cmf20asu60gslb2k5fhlac2gn/ori/"

REMOTE = {
    # --- first-frame stills (gpt-image-2, 2K, quality=medium, 0 credits each).
    #     These double as the <video poster>, so the section is already
    #     composed before a single frame of video arrives.
    "s1-hero.poster": CDN + "1788665412143-578ded88-e134-4ebc-ae7a-1d2cdce6d4d1.png",
    "s2-broken.poster": CDN + "1788665612214-dcc80bcd-e976-490c-8fd4-5c12fd7cf12b.png",
    "s3-corridor.poster": CDN + "1788665699025-ba01e410-c649-4073-84a6-3e7499d9c521.png",
    "s4-a.poster": CDN + "1788666091513-5519e23d-133e-47c9-b393-0287dbf35831.png",
    "s4-b.poster": CDN + "1788666099605-6743c929-5780-4b78-b987-ea21a38eb2a8.png",
    "s4-c.poster": CDN + "1788666104281-67334ca8-4c48-482f-be0d-bd3b25ea1793.png",
    "s6-cta.poster": CDN + "1788665704187-e4b2171b-a26d-4e9b-91b0-e9bb7ec2148c.png",

    # --- clips (image2video). Filled in as each render lands.
    "s1-hero.desktop": CDN + "1788666175207-857f0604-ad2c-4ab1-9eef-137a625d194f.mp4",
    "s1-hero.mobile":  CDN + "1788666180052-79ee0bd7-0f71-4755-8175-6ef263467a76.mp4",
    "s2-broken.desktop": CDN + "1788666123895-81da0b46-f698-4fcd-9d89-a4cb5d5d7261.mp4",
    "s3-corridor.desktop": CDN + "1788666127086-827dd92d-1f0f-49a5-84f6-9f412999de20.mp4",
    "s4-a.desktop": CDN + "1788666307897-f342aee5-018d-438c-a3cf-60efbd1d6e32.mp4",
    "s4-b.desktop": CDN + "1788666322521-76ba6c0e-a582-4dc0-91af-6973c890e101.mp4",
    "s4-c.desktop": CDN + "1788666362575-fa2ab740-5b4e-4646-ab25-65af294ff00d.mp4",
    "s6-cta.desktop": CDN + "1788666370406-cdcd3160-37be-46a3-bd18-6136a8e6d401.mp4",
}

def build():
    for key, url in REMOTE.items():
        clip, slot = key.split(".", 1)
        CLIPS[clip].setdefault(slot, {"local": None})["remote"] = url
    # drop slots that ended up with nothing on either side
    out = {}
    for name, c in CLIPS.items():
        keep = {}
        for k, v in c.items():
            if isinstance(v, dict):
                if v.get("local") or v.get("remote"):
                    keep[k] = v
            else:
                keep[k] = v
        out[name] = keep
    return out

def main():
    data = build()
    js = (
        "/* GENERATED by pipeline/make_manifest.py — do not hand-edit.\n"
        " * `use` decides which column the page reads. pipeline/fetch-media.sh\n"
        " * downloads + encodes the remote column and flips this to \"local\". */\n"
        "window.CLIP_SOURCES = {\n"
        '  use: "remote",\n'
        "  clips: " + json.dumps(data, indent=2, ensure_ascii=False).replace("\n", "\n  ") + "\n"
        "};\n"
    )
    p = pathlib.Path(__file__).resolve().parent.parent / "site" / "media" / "sources.js"
    p.write_text(js, encoding="utf-8")
    have = sum(1 for c in data.values() for v in c.values()
               if isinstance(v, dict) and v.get("remote"))
    print(f"wrote {p}  ({len(data)} clips, {have} remote urls wired)")

if __name__ == "__main__":
    main()
