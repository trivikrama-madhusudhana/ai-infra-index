# Owner decisions

Recorded 2026-07-20, extended 2026-07-25. These bind all research and scoring.

## 1. Attribution of partner-owned capacity: attribute to the owner

Datacenter capacity is counted under whoever **physically owns** the site, not the
lab that rents it. Concretely, for the 8 tracked labs:

- `power_capacity_mw` and `owned_facility` facts are recorded **only for sites the
  lab itself owns/operates.** Capacity a lab merely rents from Microsoft, AWS,
  Oracle, CoreWeave, or Google Cloud is **not** the lab's physical capacity and is
  **not** logged as `power_capacity_mw`/`owned_facility`.
- Such cloud/partner arrangements are still recorded, as a `cloud_partnership`
  fact, for transparency and display, with the owner and the nature of the deal in
  `excerpt`/`notes`. `cloud_partnership` does not feed the physical-capacity score
  (by design: renting is not owning).
- Consequence, stated plainly: labs that run entirely on rented cloud capacity
  score near zero on Power capacity and Vertical integration. That is the intended
  meaning of an *infrastructure* index.

## 2. Chinese-lab Tier B publishers: expanded

SCMP, TechNode, Pandaily, Caixin Global, and Yicai Global are promoted to Tier B
(scoreable) for the Chinese labs. Every fact sourced from translated/secondary
coverage must flag the translation uncertainty in `notes`.

## 3. Working title: "AI Infrastructure Index" (unchanged).

---

Recorded 2026-07-25, after an audit found the engine summing the same asset more
than once in six places. The index's promise is that every number traces to a
source; a number that counts one thing twice breaks that promise even when every
underlying fact is true.

## 4. Count each asset and each committed dollar exactly once

No metric may include the same physical asset or the same commitment twice. Three
relationships cause it, and each has one mechanism:

- **Progress at a site** — the same asset, later. The old fact gets
  `superseded_by`. This was already the rule; it is now enforced by review.
- **One asset under two site slugs** — the earlier or narrower reading gets
  `superseded_by` pointing at the fact that describes the site most completely.
  The equivalence is recorded in the superseding fact's `notes` when it is
  written, or here in this file when the correction comes later; facts are never
  edited after they merge, and a `site` slug is never rewritten.
- **A figure contained inside a broader figure** — a site's fleet inside a
  company-wide fleet, a tranche inside a programme total. The narrower fact gets
  **`covered_by`** (new in scoring v2), stays on the record, stays on the page,
  and does not score.

Aggregating is the engine's job, so the fix belongs in the ledger and the rubric,
never in what a page chooses to display. A summary tile may not print a different
number from the breakdown below it.

## 5. When a total and its parts are both on record, the total scores

If a whole-company or whole-programme figure and its constituent parts cover the
same metric and the same period, the broader figure scores and the parts carry
`covered_by`. The total is the source's own complete statement; the parts are a
breakdown of it, and the ledger will rarely hold every part. Preferring the total
also fails conservatively: it never invents capacity the parts do not evidence.

Applied: Anthropic's New Carlisle fleet (500,000 H100e) is inside its 1,000,000
H100e company total, both from the same Epoch report. OpenAI's September 2025
"over $400 billion" is cumulative Stargate investment, not new money on top of
the January 2025 $500 billion programme.

## 6. Capital is additive across distinct periods and projects, never within one

Two capex facts sum only if they cover different periods **and** different
programmes. Two statements of the same fiscal year, or two statements of the same
programme's total, describe one commitment: the later one supersedes, or the
narrower one is `covered_by` the broader.

Consecutive years therefore do sum. Google's FY2025 ($91bn) and FY2026 ($195bn)
guidance and its Intersect Power acquisition ($4.75bn) stand as three separate
commitments, as do Meta's 2025 actual ($72.2bn) and 2026 guidance ($125bn). The
component measures capital committed to the buildout across the window the ledger
covers, not a single year's run rate, and dropping a real prior-year commitment
would understate labs that front-loaded their spending. This is a deliberate
choice with a cost: the figure is cumulative and is not comparable to any single
year's guidance, and it mixes company-wide capex with AI-specific capex wherever
a lab only discloses the former.

## 7. Colossus 2 and Southaven are one xAI facility; MACROHARDRR is not

`colossus-2` and `colossus-2-southaven-ms` name the same campus in Southaven,
DeSoto County, Mississippi. Epoch AI geolocates it to Memphis, TN and SemiAnalysis
to Southaven, MS, and the ledger's own notes on `xai-2026-07-20-027` already
record that split. Its earlier partial readings — 110,000 GB200 and 245 MW of
on-site turbines — are progress at that site, not capacity on top of Epoch's
440,000 chips and 946 MW, and are now superseded. `colossus-2` is the canonical
slug because the current facts carry it.

`macrohardrr-southaven-ms` stays a separate site: the sources describe MACROHARDRR
as a third building xAI bought adjacent to Colossus 2, not the same structure. It
is the same campus, so its own capacity figures must be checked against Colossus 2
before they are ever summed with them.
