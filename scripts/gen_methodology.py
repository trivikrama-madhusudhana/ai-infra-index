#!/usr/bin/env python3
"""Render config/scoring.v1.yaml -> METHODOLOGY.md. Never hand-edit METHODOLOGY.md.

    python scripts/gen_methodology.py           # write METHODOLOGY.md
    python scripts/gen_methodology.py --check    # CI: fail if stale
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCORING_PATH = ROOT / "config" / "scoring.v1.yaml"
OUT_PATH = ROOT / "METHODOLOGY.md"


def pct(w: float) -> str:
    return f"{w * 100:g}%"


def fmt_bands(bands: list) -> str:
    rows = ["| At least | Points |", "| --- | --- |"]
    for threshold, points in bands:
        t = f"{int(threshold):,}" if threshold == int(threshold) else f"{threshold:,}"
        rows.append(f"| {t} | {points} |")
    return "\n".join(rows)


def render(cfg: dict) -> str:
    L = []
    A = L.append

    A(f"# {cfg['title']}: Methodology")
    A("")
    A("<!-- GENERATED FROM config/scoring.v1.yaml BY scripts/gen_methodology.py. DO NOT EDIT BY HAND. -->")
    A("")
    A(f"**Scoring version:** {cfg['version']}")
    A("")
    A(" ".join(cfg["description"].split()))
    A("")

    A("## Reproducing the score")
    A("")
    A("The score is a pure function of the fact ledger, this rubric, and a scoring date.")
    A("On a clean clone:")
    A("")
    A("```")
    A("python scripts/score.py --as-of <YYYY-MM-DD>")
    A("```")
    A("")
    A("reproduces the committed `index.json` byte for byte. No network, no model, no randomness.")
    A("")

    A("## Eligibility")
    A("")
    A("A fact contributes to the score only if all of the following hold; otherwise it")
    A("contributes zero and is listed as ineligible in the per-company breakdown.")
    A("")
    elig = cfg["eligibility"]
    A(f"- **Verified:** `verification.verified` is `true`. Required: `{str(elig['require_verified']).lower()}`.")
    A(f"- **Tier:** the source domain resolves to Tier {' or '.join(elig['require_tiers'])} (see `config/sources.yaml`).")
    A(f"- **Not superseded:** the fact has no `superseded_by` pointer. Excluded when superseded: `{str(elig['exclude_superseded']).lower()}`.")
    A("")
    A("> " + " ".join(elig["note"].split()))
    A("")

    A("## Staleness decay")
    A("")
    d = cfg["decay"]
    A("> " + " ".join(d["note"].split()))
    A("")
    A(f"- Applies to status: {', '.join('`'+s+'`' for s in d['applies_to_status'])}")
    A(f"- Age threshold: **{d['age_months']} months**, measured from `{d['age_measured_from']}` to the scoring date")
    A(f"- Multiplier when stale and un-followed-up: **{d['multiplier']}×**")
    A(f"- Follow-up statuses that cancel decay: {', '.join('`'+s+'`' for s in d['follow_up_status'])}")
    A("")

    A("## Aggregations")
    A("")
    for name, desc in cfg["aggregations"].items():
        A(f"- **`{name}`** {desc}")
    A("")
    A("Each component maps its aggregated value through bands: the value scores the")
    A("points of the highest threshold it meets or exceeds.")
    A("")

    A("## Categories and components")
    A("")
    A("| Category | Weight |")
    A("| --- | --- |")
    for cat in cfg["categories"].values():
        A(f"| {cat['label']} | {pct(cat['weight'])} |")
    A("")

    for cat_name, cat in cfg["categories"].items():
        A(f"### {cat['label']} ({pct(cat['weight'])})")
        A("")
        A(" ".join(cat["description"].split()))
        A("")
        for comp_name, comp in cat["components"].items():
            metrics = comp.get("metrics", [comp.get("metric")])
            A(f"#### {comp['label']}")
            A("")
            A(f"- **Component weight (within category):** {pct(comp['weight'])}")
            A(f"- **Metric(s):** {', '.join('`'+m+'`' for m in metrics)}")
            A(f"- **Counts statuses:** {', '.join('`'+s+'`' for s in comp['status_filter'])}")
            A(f"- **Aggregation:** `{comp['aggregation']}`")
            A("")
            A(" ".join(comp["description"].split()))
            A("")
            A(fmt_bands(comp["bands"]))
            A("")

    A("## Category math")
    A("")
    A("```")
    A("category.points        = sum(component.weight * component.band_points)")
    A("category.contribution  = category.weight * category.points")
    A("score                  = sum(category.contribution)          # 0-100")
    A("```")
    A("")
    A("Methodology changes bump the version (`scoring.v2.yaml`, old file retained),")
    A("rescore history under both versions, and get a CHANGELOG entry explaining the diff.")
    A("")

    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if METHODOLOGY.md is stale")
    args = ap.parse_args(argv)

    cfg = yaml.safe_load(SCORING_PATH.read_text())
    text = render(cfg)

    if args.check:
        if not OUT_PATH.exists() or OUT_PATH.read_text() != text:
            print("METHODOLOGY.md is stale, rerun: python scripts/gen_methodology.py", file=sys.stderr)
            return 1
        print("METHODOLOGY.md is current")
        return 0

    OUT_PATH.write_text(text)
    print(f"wrote {OUT_PATH.relative_to(ROOT)} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
