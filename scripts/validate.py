#!/usr/bin/env python3
"""Schema + hygiene gate for the ledger. Run after any ledger change; CI runs it too.

Checks:
  - every company file validates against schema/fact.schema.json
  - HTTPS sources only, no future dates, no GW units (schema-enforced units)
  - unique fact IDs across the whole ledger
  - resolvable superseded_by pointers (target exists, same company)
  - excerpt <= 200 chars (schema-enforced), power facts carry status + site
  - source domains resolve to a known tier; Tier D is an ERROR, Tier C a warning
  - archive_url absent -> warning (not fatal)
  - scoring/config sanity: category + component weights sum to ~1.0

Exit code 0 = clean (warnings allowed), 1 = errors.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schema" / "fact.schema.json"
SOURCES_PATH = ROOT / "config" / "sources.yaml"
SCORING_PATH = ROOT / "config" / "scoring.v1.yaml"
COMPANIES_DIR = ROOT / "data" / "companies"

POWER_METRICS = {"power_capacity_mw", "ppa_mw"}

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def host_of(url: str) -> str:
    rest = url.split("://", 1)[-1]
    return rest.split("/", 1)[0].split("?", 1)[0].lower().strip()


def build_tier_map(sources_cfg: dict) -> dict:
    m = {}
    for tier, domains in sources_cfg.get("tiers", {}).items():
        for d in domains or []:
            m[d.lower()] = tier
    return m


def tier_for_url(url: str, dom_to_tier: dict) -> str:
    host = host_of(url)
    best_tier, best_len = "D", -1
    for domain, tier in dom_to_tier.items():
        if host == domain or host.endswith("." + domain):
            if len(domain) > best_len:
                best_tier, best_len = tier, len(domain)
    return best_tier


def not_future(label: str, value: str, today: date, fact_id: str) -> None:
    try:
        d = date.fromisoformat(value)
    except (ValueError, TypeError):
        err(f"{fact_id}: {label} is not a valid date: {value!r}")
        return
    if d > today:
        err(f"{fact_id}: {label} is in the future: {value}")


def validate_config() -> None:
    cfg = yaml.safe_load(SCORING_PATH.read_text())
    cat_total = 0.0
    for cat_name, cat in cfg["categories"].items():
        cat_total += cat["weight"]
        comp_total = sum(c["weight"] for c in cat["components"].values())
        if abs(comp_total - 1.0) > 1e-9:
            err(f"scoring: component weights in '{cat_name}' sum to {comp_total}, expected 1.0")
        for comp_name, comp in cat["components"].items():
            has_metric = ("metric" in comp) ^ ("metrics" in comp)
            if not has_metric:
                err(f"scoring: component '{cat_name}.{comp_name}' must set exactly one of metric/metrics")
            bands = comp.get("bands", [])
            if not bands or bands[0][0] != 0:
                err(f"scoring: component '{cat_name}.{comp_name}' bands must start at threshold 0")
            if bands != sorted(bands):
                err(f"scoring: component '{cat_name}.{comp_name}' bands must be ascending by threshold")
    if abs(cat_total - 1.0) > 1e-9:
        err(f"scoring: category weights sum to {cat_total}, expected 1.0")


def main() -> int:
    today = date.today()
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft7Validator(schema)
    sources_cfg = yaml.safe_load(SOURCES_PATH.read_text())
    dom_to_tier = build_tier_map(sources_cfg)

    validate_config()

    all_ids: dict[str, str] = {}          # id -> company file
    all_facts: dict[str, dict] = {}       # id -> fact
    files = sorted(COMPANIES_DIR.glob("*.json"))

    for path in files:
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            err(f"{path.name}: invalid JSON: {e}")
            continue

        for schema_err in sorted(validator.iter_errors(data), key=str):
            loc = "/".join(str(p) for p in schema_err.path)
            err(f"{path.name}: schema: {loc}: {schema_err.message}")

        file_company = data.get("company")
        for fact in data.get("facts", []):
            fid = fact.get("id", "<no id>")
            if fid in all_ids:
                err(f"duplicate fact id {fid} in {path.name} and {all_ids[fid]}")
            all_ids[fid] = path.name
            all_facts[fid] = fact

            if fact.get("company") != file_company:
                err(f"{fid}: company {fact.get('company')!r} != file company {file_company!r}")

            src = fact.get("source", {})
            for label, key in [("date_published", "date_published"), ("date_accessed", "date_accessed")]:
                if key in src:
                    not_future(label, src[key], today, fid)
            if "as_of_date" in fact:
                not_future("as_of_date", fact["as_of_date"], today, fid)
            if "added" in fact:
                not_future("added", fact["added"], today, fid)

            url = src.get("url", "")
            tier = tier_for_url(url, dom_to_tier)
            if tier == "D":
                err(f"{fid}: source domain '{host_of(url)}' is unknown (Tier D), add it to config/sources.yaml or drop the fact")
            elif tier == "C":
                warn(f"{fid}: source '{host_of(url)}' is Tier C, recorded but not scoreable")

            if not src.get("archive_url"):
                warn(f"{fid}: no archive_url, capture a web.archive.org snapshot")

            if fact.get("metric") in POWER_METRICS:
                if fact.get("status") in (None, "n/a"):
                    err(f"{fid}: power fact must carry a real status (announced/contracted/under_construction/operational)")
                if not fact.get("site"):
                    err(f"{fid}: power fact must carry a site")

    # superseded_by pointers must resolve within the same company
    for fid, fact in all_facts.items():
        target = fact.get("superseded_by")
        if target:
            if target not in all_facts:
                err(f"{fid}: superseded_by points to unknown fact {target}")
            elif all_facts[target].get("company") != fact.get("company"):
                err(f"{fid}: superseded_by {target} is a different company")

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")

    n = len(all_facts)
    if errors:
        print(f"\nvalidate: {len(errors)} error(s), {len(warnings)} warning(s) across {len(files)} file(s), {n} fact(s)")
        return 1
    print(f"validate: OK, {len(files)} file(s), {n} fact(s), {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
