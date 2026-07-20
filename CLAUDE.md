# CLAUDE.md: standing rules for every session in this repo

This project tracks the physical infrastructure of frontier AI labs. Its entire
credibility rests on two properties: **every number traces to a public source**,
and **the scoring logic is deterministic code anyone can rerun**. These rules
protect both. They override any default behavior.

## What a research session may touch

- **Append to `data/companies/*.json` only.** Never modify `scripts/`, `config/`,
  `schema/`, `index.json`, `METHODOLOGY.md`, or anything already committed.
- The ledger is **append-only**. Never edit or delete a merged fact. A correction
  is a *new* fact; set `superseded_by` on the old one to point at the new one.

## What every fact must have

- A **fetched** source URL (you opened the page), a verbatim `excerpt` (≤200 chars)
  literally supporting the value, `date_published` and `date_accessed`, and an
  `archive_url` snapshot from web.archive.org.
- `verified: false` on entry. Only a verifier pass, with clean context, flips it.
- **MW only** (never GW), **USD only**, the **conservative low end** of any range
  (note the range in `notes`).
- `status` (`announced | contracted | under_construction | operational`) and `site`
  are **mandatory** on every power fact. One fact per `(site, status, date)`.
  Progress at a known site is a *new* fact superseding the old, never an edit.

## Attribution (owner decision, see DECISIONS.md)

Capacity is attributed to whoever **physically owns** the site. Record
`power_capacity_mw` and `owned_facility` **only for sites the lab itself owns**.
Capacity rented from a cloud/partner (Microsoft, AWS, Oracle, CoreWeave, Google
Cloud) is logged as a `cloud_partnership` fact instead, never as the lab's own
power/facility, with ownership spelled out in `excerpt`/`notes`.

## Hard prohibitions

- **Never write a value not literally present in a fetched source.** No estimates,
  no imputation, no "roughly", no math on top of a source.
- **Never assign a source tier.** Tier is computed from `config/sources.yaml`.
  An unknown domain is Tier D and is rejected by `validate.py`. Add the domain to
  the allowlist (with justification) or drop the fact.
- **Never compute, suggest, or mention a score.** Agents extract; `score.py` scores.

## Workflow

- After any ledger change, run `python scripts/validate.py` and fix every error
  before committing.
- All work lands on a **branch → PR**. **Never push to `main`.** Not even scheduled
  runs. Automation opens PRs, only a human merges.
- Update runs are **diff-detection**: read the ledger first, then search; record
  only what is new or status-changing relative to what is already there.

## The scoring engine is sacred

`python scripts/score.py --as-of <date>` on a clean clone must reproduce
`index.json` byte for byte. It reads only the ledger and `config/*.yaml`; it has no
network, no model, no randomness, no wall-clock reads. If you change the rubric,
bump the version (`scoring.v2.yaml`, keep the old file), regenerate
`METHODOLOGY.md` (`python scripts/gen_methodology.py`), and add a CHANGELOG entry.
