#!/usr/bin/env python3
"""Deterministic scoring engine for the AI Infrastructure Index.

Pure function of (ledger, config/scoring.v1.yaml, config/sources.yaml, --as-of).
No LLM, no network, no randomness, no wall-clock reads. Given the same inputs it
must reproduce index.json byte for byte.

    python scripts/score.py --as-of 2026-07-20            # write index.json
    python scripts/score.py --as-of 2026-07-20 --check    # diff against committed
    python scripts/score.py --as-of 2026-07-20 --stdout   # print, write nothing

The output records `--as-of` so staleness decay is reproducible.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCORING_PATH = ROOT / "config" / "scoring.v1.yaml"
SOURCES_PATH = ROOT / "config" / "sources.yaml"
COMPANIES_DIR = ROOT / "data" / "companies"
INDEX_PATH = ROOT / "index.json"

# Round money-ish aggregates and points to fixed decimals so output is stable.
POINT_DP = 4
SCORE_DP = 2


def r(x: float, dp: int) -> float:
    """Round to `dp` places and normalise -0.0 to 0.0 for stable JSON."""
    v = round(float(x), dp)
    return 0.0 if v == 0 else v


# ---------------------------------------------------------------------------
# Source tiering (mirrors validate.py; kept local so score.py has no imports
# from sibling scripts and stays a self-contained pure function).
# ---------------------------------------------------------------------------

def host_of(url: str) -> str:
    rest = url.split("://", 1)[-1]
    return rest.split("/", 1)[0].split("?", 1)[0].lower().strip()


def build_tier_map(sources_cfg: dict) -> dict:
    """domain -> tier letter, longest-suffix wins at lookup time."""
    dom_to_tier = {}
    for tier, domains in sources_cfg.get("tiers", {}).items():
        for d in domains or []:
            dom_to_tier[d.lower()] = tier
    return dom_to_tier


def tier_for_url(url: str, dom_to_tier: dict) -> str:
    host = host_of(url)
    best_tier, best_len = "D", -1
    for domain, tier in dom_to_tier.items():
        if host == domain or host.endswith("." + domain):
            if len(domain) > best_len:
                best_tier, best_len = tier, len(domain)
    return best_tier


# ---------------------------------------------------------------------------
# Eligibility + decay
# ---------------------------------------------------------------------------

def months_between(older: date, newer: date) -> int:
    return (newer.year - older.year) * 12 + (newer.month - older.month)


def is_eligible(fact: dict, elig: dict, tier: str) -> bool:
    if elig.get("exclude_superseded", True) and fact.get("superseded_by"):
        return False
    if elig.get("require_verified", True) and not fact.get("verification", {}).get("verified"):
        return False
    if tier not in set(elig.get("require_tiers", ["A", "B"])):
        return False
    return True


def decay_multiplier(fact: dict, eligible_facts: list, decay_cfg: dict, as_of: date) -> float:
    """0.5 for a stale, un-followed-up announcement; else 1.0."""
    if fact.get("status") not in set(decay_cfg.get("applies_to_status", [])):
        return 1.0
    as_of_date = date.fromisoformat(fact["as_of_date"])
    if months_between(as_of_date, as_of) < decay_cfg.get("age_months", 24):
        return 1.0
    follow = set(decay_cfg.get("follow_up_status", []))
    site = fact.get("site")
    company = fact.get("company")
    for other in eligible_facts:
        if (
            other is not fact
            and other.get("company") == company
            and other.get("site") == site
            and other.get("status") in follow
        ):
            return 1.0
    return float(decay_cfg.get("multiplier", 0.5))


# ---------------------------------------------------------------------------
# Aggregation + banding
# ---------------------------------------------------------------------------

def numeric_value(fact: dict) -> float:
    v = fact.get("value")
    if isinstance(v, bool):
        return 1.0
    if isinstance(v, (int, float)):
        return float(v)
    return 0.0


def aggregate(kind: str, facts: list, multipliers: dict) -> float:
    if kind == "sum":
        return sum(numeric_value(f) * multipliers[id(f)] for f in facts)
    if kind == "max":
        return max((numeric_value(f) * multipliers[id(f)] for f in facts), default=0.0)
    if kind == "count":
        return float(len(facts))
    if kind == "count_distinct_site":
        return float(len({f.get("site") for f in facts}))
    if kind == "bool_any":
        return 1.0 if facts else 0.0
    raise ValueError(f"unknown aggregation: {kind}")


def band_points(value: float, bands: list) -> float:
    pts = 0.0
    for threshold, points in bands:
        if value >= threshold:
            pts = float(points)
        else:
            break
    return pts


def metrics_of(component: dict) -> set:
    if "metrics" in component:
        return set(component["metrics"])
    return {component["metric"]}


def input_expression(component: dict, value: float, unit_hint: str) -> str:
    agg = component["aggregation"]
    metrics = "|".join(sorted(metrics_of(component)))
    statuses = ",".join(component["status_filter"])
    val = int(value) if value == int(value) else round(value, 2)
    return f"{agg}({metrics} where status in [{statuses}]) = {val}{unit_hint}"


UNIT_HINT = {
    "power_capacity_mw": " MW",
    "ppa_mw": " MW",
    "capex_announced_usd": " USD",
    "gpu_count": " chips",
}


def score_component(name: str, comp: dict, eligible: list, decay_cfg: dict, as_of: date) -> dict:
    metrics = metrics_of(comp)
    statuses = set(comp["status_filter"])
    qualifying = [
        f for f in eligible
        if f.get("metric") in metrics and f.get("status") in statuses
    ]
    multipliers = {id(f): decay_multiplier(f, eligible, decay_cfg, as_of) for f in qualifying}
    decayed_ids = sorted(f["id"] for f in qualifying if multipliers[id(f)] != 1.0)

    value = aggregate(comp["aggregation"], qualifying, multipliers)
    pts = band_points(value, comp["bands"])
    weighted = comp["weight"] * pts

    unit_hint = ""
    for m in comp.get("metrics", [comp.get("metric")]):
        if m in UNIT_HINT:
            unit_hint = UNIT_HINT[m]
            break

    return {
        "label": comp["label"],
        "weight": comp["weight"],
        "aggregation": comp["aggregation"],
        "input_expression": input_expression(comp, value, unit_hint),
        "aggregated_value": r(value, POINT_DP),
        "band_points": pts,
        "weighted_points": r(weighted, POINT_DP),
        "fact_ids": sorted(f["id"] for f in qualifying),
        "decayed_fact_ids": decayed_ids,
        "missing": len(qualifying) == 0,
    }


def score_company(company: str, facts: list, cfg: dict, dom_to_tier: dict, as_of: date) -> dict:
    elig_cfg = cfg["eligibility"]
    decay_cfg = cfg["decay"]

    annotated = []
    ineligible = []
    for f in facts:
        tier = tier_for_url(f["source"]["url"], dom_to_tier)
        if is_eligible(f, elig_cfg, tier):
            annotated.append(f)
        else:
            ineligible.append({"id": f["id"], "tier": tier, "verified": f["verification"]["verified"],
                               "superseded": bool(f.get("superseded_by"))})

    categories = {}
    total = 0.0
    for cat_name, cat in cfg["categories"].items():
        comps = {}
        cat_points = 0.0
        for comp_name, comp in cat["components"].items():
            scored = score_component(comp_name, comp, annotated, decay_cfg, as_of)
            comps[comp_name] = scored
            cat_points += scored["weighted_points"]
        contribution = cat["weight"] * cat_points
        total += contribution
        categories[cat_name] = {
            "label": cat["label"],
            "weight": cat["weight"],
            "points": r(cat_points, POINT_DP),
            "weighted_contribution": r(contribution, POINT_DP),
            "components": comps,
        }

    return {
        "company": company,
        "score": r(total, SCORE_DP),
        "eligible_fact_count": len(annotated),
        "ineligible_facts": sorted(ineligible, key=lambda x: x["id"]),
        "categories": categories,
    }


def load_ledger() -> list:
    companies = []
    for path in sorted(COMPANIES_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        companies.append((data["company"], data.get("facts", [])))
    return companies


def build_index(as_of: date) -> dict:
    cfg = yaml.safe_load(SCORING_PATH.read_text())
    sources_cfg = yaml.safe_load(SOURCES_PATH.read_text())
    dom_to_tier = build_tier_map(sources_cfg)

    ledger = load_ledger()
    scored = [score_company(name, facts, cfg, dom_to_tier, as_of) for name, facts in ledger]
    scored.sort(key=lambda c: (-c["score"], c["company"]))

    return {
        "meta": {
            "scoring_version": cfg["version"],
            "generated_as_of": as_of.isoformat(),
            "companies_scored": len(scored),
        },
        "companies": scored,
    }


def dumps(index: dict) -> str:
    return json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic AI Infrastructure Index scorer")
    ap.add_argument("--as-of", required=True, help="scoring date YYYY-MM-DD (governs decay)")
    ap.add_argument("--check", action="store_true", help="fail if committed index.json differs")
    ap.add_argument("--stdout", action="store_true", help="print to stdout, write nothing")
    args = ap.parse_args(argv)

    as_of = date.fromisoformat(args.as_of)
    text = dumps(build_index(as_of))

    if args.stdout:
        sys.stdout.write(text)
        return 0
    if args.check:
        if not INDEX_PATH.exists():
            print("index.json missing", file=sys.stderr)
            return 1
        if INDEX_PATH.read_text() != text:
            print("index.json is stale, rerun: python scripts/score.py --as-of <date>", file=sys.stderr)
            return 1
        print("index.json is current")
        return 0

    INDEX_PATH.write_text(text)
    print(f"wrote {INDEX_PATH.relative_to(ROOT)} ({len(text)} bytes, as-of {as_of})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
