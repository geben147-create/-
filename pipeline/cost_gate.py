#!/usr/bin/env python3
"""
cost_gate.py — refuse any generation that is not free.

The rule this enforces is in CLAUDE.md: when the user says free, free means
zero. Not "cheapest paid", not "affordable", not "only 8 credits". Zero.

A rule written in prose gets skipped; that is exactly how 72 credits were
spent on 2026-09-06. So any pipeline that submits work calls this first and
lets it raise.

    from cost_gate import assert_free
    quote = pollo_estimate(...)          # whatever your client returns
    assert_free(quote, label="S1 clip")  # raises unless it is genuinely 0
    submit(...)

    $ python cost_gate.py quote.json     # or check a saved quote from a shell
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

POLICY = Path(__file__).resolve().parent.parent / "packs" / "cost_policy.yaml"


class PaidGenerationBlocked(RuntimeError):
    """Raised when a quote is not zero and no explicit override was given."""


def _limit() -> float:
    """Read max_credit_per_shot from the policy; default to 0 (free only)."""
    try:
        import yaml
        d = yaml.safe_load(POLICY.read_text(encoding="utf-8")) or {}
        return float(d.get("max_credit_per_shot", 0))
    except Exception:
        return 0.0


def charge_of(quote: dict) -> float:
    """The number that is actually billed.

    `cost` is the list price and is NOT what gets charged; a promotion can
    zero it out, and reading the wrong field either blocks free work or waves
    paid work through. `discountCost` is the real figure.
    """
    for k in ("discountCost", "discount_cost"):
        if k in quote and quote[k] is not None:
            return float(quote[k])
    for k in ("cost", "originCredit"):
        if k in quote and quote[k] is not None:
            return float(quote[k])
    raise KeyError(f"no cost field in quote: {sorted(quote)}")


def assert_free(quote: dict, label: str = "generation",
                allow_paid: bool = False) -> float:
    """Return the charge, or raise if it exceeds the policy limit.

    `allow_paid` exists for the one legitimate case: the user was shown the
    figure and said to spend it. It is never set from inference, a balance
    check, or an instruction like "go ahead" that assumed free.
    """
    charge = charge_of(quote)
    limit = _limit()
    if allow_paid or charge <= limit:
        return charge
    raise PaidGenerationBlocked(
        f"BLOCKED: {label} costs {charge:g} credits, limit is {limit:g}.\n"
        f"  A cheaper paid model is still paid. Do not substitute one.\n"
        f"  Either find a model quoting 0, or show the user this figure and\n"
        f"  wait for them to approve spending it."
    )


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip())
        return 2
    quote = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    try:
        charge = assert_free(quote, label=sys.argv[1])
    except PaidGenerationBlocked as e:
        print(e, file=sys.stderr)
        return 1
    print(f"OK: free ({charge:g} credits)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
