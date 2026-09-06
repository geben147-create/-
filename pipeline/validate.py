#!/usr/bin/env python3
"""
validate.py — enforce the pack contract.

Two jobs:
  * check every genre pack is internally consistent (ids resolve, ranges sane)
  * check a shot manifest obeys the pack it declares

This exists because a rule written in prose is a rule that gets skipped. The
numbers in pack.yaml are only real if something refuses the run when they are
broken.

    python validate.py --packs
    python validate.py --manifest my_manifest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml required:  pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
PACKS = ROOT / "packs" / "genre"


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def done(self, what: str) -> int:
        for w in self.warnings:
            print(f"  WARN  {w}")
        for e in self.errors:
            print(f"  FAIL  {e}")
        if not self.errors:
            print(f"  OK    {what}"
                  f"{f' ({len(self.warnings)} warning(s))' if self.warnings else ''}")
        return 1 if self.errors else 0


def load_pack(name: str) -> tuple[dict, dict]:
    d = PACKS / name
    if not d.is_dir():
        available = ", ".join(sorted(p.name for p in PACKS.iterdir() if p.is_dir()))
        sys.exit(f"unknown genre pack '{name}'. available: {available}")
    pack = yaml.safe_load((d / "pack.yaml").read_text(encoding="utf-8"))
    shots = yaml.safe_load((d / "shots.yaml").read_text(encoding="utf-8"))
    return pack, shots


def check_pack(name: str, rep: Report) -> None:
    pack, shots = load_pack(name)
    ids = {s["id"] for s in shots.get("shots", [])}

    for key in ("id", "speech_modes", "lens_contact", "shot_len_s", "forbid"):
        if key not in pack:
            rep.err(f"{name}: pack.yaml is missing '{key}'")

    rng = pack.get("shot_len_s", {})
    lo, hi, tgt = rng.get("min"), rng.get("max"), rng.get("target")
    if None not in (lo, hi) and lo >= hi:
        rep.err(f"{name}: shot_len_s.min ({lo}) must be below max ({hi})")
    if tgt is not None and None not in (lo, hi) and not (lo <= tgt <= hi):
        rep.err(f"{name}: shot_len_s.target ({tgt}) sits outside min-max")

    for r in pack.get("required_shots") or []:
        if r["id"] not in ids:
            rep.err(f"{name}: required_shots references unknown id '{r['id']}'")
    for sid in (pack.get("max_repeat") or {}):
        if sid not in ids:
            rep.err(f"{name}: max_repeat references unknown id '{sid}'")

    if not (d := (PACKS / name / "directing.md")).exists() or not d.read_text().strip():
        rep.err(f"{name}: directing.md missing or empty")
    if not pack.get("forbid"):
        rep.warn(f"{name}: no forbid list -- every genre has a characteristic failure")


def check_manifest(path: Path, rep: Report) -> None:
    man = json.loads(path.read_text(encoding="utf-8"))
    pack_name = man.get("genre_pack")
    if not pack_name:
        rep.err("manifest declares no genre_pack; no genre rule can be applied")
        return
    pack, shots_vocab = load_pack(pack_name)
    vocab = {s["id"] for s in shots_vocab.get("shots", [])}
    shots = man.get("shots", [])
    if not shots:
        rep.err("manifest has no shots")
        return

    rng = pack.get("shot_len_s", {})
    lo, hi = rng.get("min"), rng.get("max")
    seen_vocab: dict[str, int] = {}

    for s in shots:
        sid = s.get("shot_id", "<no shot_id>")
        d = s.get("duration_s")
        if d is None:
            rep.err(f"{sid}: no duration_s")
        elif lo is not None and hi is not None and not (lo <= d <= hi):
            rep.err(f"{sid}: duration {d}s is outside the {pack['id']} "
                    f"range {lo}-{hi}s")
        v = s.get("shot_vocab_id")
        if v:
            if v not in vocab:
                rep.err(f"{sid}: shot_vocab_id '{v}' is not in {pack_name}/shots.yaml")
            seen_vocab[v] = seen_vocab.get(v, 0) + 1
        if not s.get("action"):
            rep.err(f"{sid}: no action -- one shot must state one action")
        if s.get("precision_tier") == "tier_a_code_only" and not s.get("code_overlay"):
            rep.err(f"{sid}: tier_a requires code_overlay=true; figures are never generated")

    for r in pack.get("required_shots") or []:
        got = seen_vocab.get(r["id"], 0)
        if got < r.get("min", 1):
            rep.err(f"{pack['id']} requires at least {r.get('min',1)} x {r['id']}, found {got}")
    for sid, cap in (pack.get("max_repeat") or {}).items():
        if seen_vocab.get(sid, 0) > cap:
            rep.err(f"{sid} used {seen_vocab[sid]} times, cap is {cap}")

    # end_state of shot N must match start_state of shot N+1
    for a, b in zip(shots, shots[1:]):
        ea, sb = a.get("end_state"), b.get("start_state")
        if ea is None or sb is None:
            rep.warn(f"{a.get('shot_id')} -> {b.get('shot_id')}: missing state, "
                     f"continuity cannot be checked")
            continue
        for k in set(ea) & set(sb):
            if ea[k] != sb[k]:
                rep.err(f"{a.get('shot_id')} -> {b.get('shot_id')}: "
                        f"{k} changes across the cut ({ea[k]!r} -> {sb[k]!r})")


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate genre packs and shot manifests.")
    ap.add_argument("--packs", action="store_true", help="check every genre pack")
    ap.add_argument("--manifest", help="check a shot manifest against its pack")
    args = ap.parse_args()
    if not args.packs and not args.manifest:
        ap.error("give --packs or --manifest")

    status = 0
    if args.packs:
        print("genre packs:")
        for d in sorted(p for p in PACKS.iterdir() if p.is_dir()):
            rep = Report()
            check_pack(d.name, rep)
            status |= rep.done(d.name)
    if args.manifest:
        print(f"manifest: {args.manifest}")
        rep = Report()
        check_manifest(Path(args.manifest), rep)
        status |= rep.done(Path(args.manifest).name)
    return status


if __name__ == "__main__":
    sys.exit(main())
