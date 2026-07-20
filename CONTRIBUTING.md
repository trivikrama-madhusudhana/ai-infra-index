# Contributing

**We want your input, and this project is better for scrutiny.** Challenge a number you think is
wrong, point us at a better or missing source, flag a datacenter or deal we have not captured, or
argue for a smarter way to weigh the score. Open an issue for a correction or an idea, or send a
pull request against the ledger. Nothing here is settled.

This project tracks the physical infrastructure of frontier AI labs. Its whole
credibility rests on two things: every number traces to a public source, and the
scoring logic is deterministic code anyone can rerun. These rules protect both.

## What a change may touch

Facts live in `data/companies/*.json`, one file per lab, and they are append-only.
A fact is never edited or deleted after it merges. A correction is a new fact, and
the old one gets a `superseded_by` pointer to it. Progress at a site (announced to
under construction to operational) is a new fact that supersedes the old one, not
an edit to it.

## What every fact needs

- A source URL you actually opened, a verbatim `excerpt` (200 chars or fewer) that
  literally supports the value, `date_published` and `date_accessed`, and ideally a
  web.archive.org snapshot in `archive_url`.
- `verified: false` on entry. Only a separate verification pass, working from the
  fact and its source alone, flips it to true.
- Power in MW (never GW), money in USD, and the conservative low end of any range,
  with the range noted in `notes`.
- A real `status` (`announced`, `contracted`, `under_construction`, `operational`)
  and a `site` slug on every power fact.

## Hard rules

- Never record a value that is not literally present in a fetched source. No
  estimates, no imputation, no arithmetic on top of a source.
- Never assign a source tier by hand. Tier is computed from `config/sources.yaml`.
  An unknown domain is Tier D and the validator rejects it: add the domain to the
  allowlist with justification, or drop the fact.
- Capacity is attributed to whoever owns the site. Record `power_capacity_mw` and
  `owned_facility` only for sites the lab itself owns. Capacity rented from a cloud
  or partner is a `cloud_partnership` fact instead, with ownership spelled out in
  `notes`. See `DECISIONS.md`.
- Scores are never computed or asserted by a contributor. The engine scores; people
  gather evidence.

## Workflow

Run `python scripts/validate.py` after any ledger change and fix every error before
committing. Work lands on a branch and goes through a pull request; `main` is never
pushed to directly. Automation may open a PR, but a human always merges.

If you change the rubric, bump the version (`scoring.v2.yaml`, keep the old file),
regenerate `METHODOLOGY.md` with `python scripts/gen_methodology.py`, and add a
`CHANGELOG.md` entry explaining the diff. `python scripts/score.py --as-of <date>`
on a clean clone must reproduce `index.json` byte for byte; CI enforces it.
