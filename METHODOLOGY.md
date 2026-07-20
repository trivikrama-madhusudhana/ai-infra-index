# AI Infrastructure Index: Methodology

<!-- GENERATED FROM config/scoring.v1.yaml BY scripts/gen_methodology.py. DO NOT EDIT BY HAND. -->

**Scoring version:** 1

A deterministic scorecard of the physical AI race: power capacity, compute ownership, vertical integration, expansion pipeline, and energy security. Every input is a verified fact from a Tier A/B public source; nothing is estimated or imputed. Missing data scores zero and displays as unknown.

## Reproducing the score

The score is a pure function of the fact ledger, this rubric, and a scoring date.
On a clean clone:

```
python scripts/score.py --as-of <YYYY-MM-DD>
```

reproduces the committed `index.json` byte for byte. No network, no model, no randomness.

## Eligibility

A fact contributes to the score only if all of the following hold; otherwise it
contributes zero and is listed as ineligible in the per-company breakdown.

- **Verified:** `verification.verified` is `true`. Required: `true`.
- **Tier:** the source domain resolves to Tier A or B (see `config/sources.yaml`).
- **Not superseded:** the fact has no `superseded_by` pointer. Excluded when superseded: `true`.

> A fact that fails any eligibility rule contributes nothing and is listed as ineligible in the per-company breakdown, never silently dropped.

## Staleness decay

> An `announced` fact at least 24 months older than the scoring date, with no later eligible fact at the same (company, site) in a follow_up_status, has its numeric value multiplied by 0.5 before sum/max aggregation. Decay never removes a fact from count or presence (bool_any) aggregations.

- Applies to status: `announced`
- Age threshold: **24 months**, measured from `as_of_date` to the scoring date
- Multiplier when stale and un-followed-up: **0.5×**
- Follow-up statuses that cancel decay: `contracted`, `under_construction`, `operational`

## Aggregations

- **`sum`** Sum of the (decay-adjusted) numeric values.
- **`max`** Largest single (decay-adjusted) numeric value.
- **`count`** Number of qualifying facts.
- **`count_distinct_site`** Number of distinct `site` values among qualifying facts.
- **`bool_any`** 1 if any qualifying fact exists, else 0.

Each component maps its aggregated value through bands: the value scores the
points of the highest threshold it meets or exceeds.

## Categories and components

| Category | Weight |
| --- | --- |
| Power capacity | 30% |
| Compute ownership | 20% |
| Vertical integration | 20% |
| Expansion pipeline | 15% |
| Energy security | 15% |

### Power capacity (30%)

Electrical capacity physically being delivered today or actively under construction. This is the hardest constraint in the AI build-out and the heaviest category. Operational capacity is weighted above construction.

#### Operational capacity (MW)

- **Component weight (within category):** 65%
- **Metric(s):** `power_capacity_mw`
- **Counts statuses:** `operational`
- **Aggregation:** `sum`

Total MW of power capacity reported as operational, summed across sites.

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 15 |
| 100 | 35 |
| 300 | 50 |
| 600 | 65 |
| 1,000 | 80 |
| 2,000 | 90 |
| 4,000 | 100 |

#### Under-construction capacity (MW)

- **Component weight (within category):** 35%
- **Metric(s):** `power_capacity_mw`
- **Counts statuses:** `under_construction`
- **Aggregation:** `sum`

Total MW of power capacity reported as under construction, summed across sites.

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 15 |
| 100 | 35 |
| 300 | 50 |
| 600 | 65 |
| 1,000 | 80 |
| 2,000 | 90 |
| 4,000 | 100 |

### Compute ownership (20%)

The scale of accelerator compute the lab controls, plus whether it designs its own silicon and owns datacenter sites rather than renting all of them.

#### Accelerator fleet (chips)

- **Component weight (within category):** 55%
- **Metric(s):** `gpu_count`
- **Counts statuses:** `announced`, `contracted`, `under_construction`, `operational`, `n/a`
- **Aggregation:** `sum`

Total accelerators attributed to the lab. These are third-party estimates (Epoch AI, SemiAnalysis) recorded as facts and attributed to their source; we never estimate fleet sizes ourselves.

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 20 |
| 10,000 | 40 |
| 50,000 | 60 |
| 100,000 | 75 |
| 300,000 | 90 |
| 1,000,000 | 100 |

#### Custom silicon programs

- **Component weight (within category):** 25%
- **Metric(s):** `custom_silicon`
- **Counts statuses:** `announced`, `contracted`, `under_construction`, `operational`, `n/a`
- **Aggregation:** `count`

Count of distinct in-house accelerator/silicon programs.

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 60 |
| 2 | 100 |

#### Owned datacenter sites

- **Component weight (within category):** 20%
- **Metric(s):** `owned_facility`
- **Counts statuses:** `under_construction`, `operational`
- **Aggregation:** `count_distinct_site`

Distinct datacenter sites the lab owns (not solely rented from a cloud).

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 40 |
| 3 | 70 |
| 6 | 100 |

### Vertical integration (20%)

How many layers of the stack (silicon, datacenter, power) the lab demonstrably owns or controls rather than renting from a partner.

#### Silicon layer

- **Component weight (within category):** 34%
- **Metric(s):** `custom_silicon`
- **Counts statuses:** `announced`, `contracted`, `under_construction`, `operational`, `n/a`
- **Aggregation:** `bool_any`

Whether the lab designs its own accelerators.

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 100 |

#### Datacenter layer

- **Component weight (within category):** 33%
- **Metric(s):** `owned_facility`
- **Counts statuses:** `under_construction`, `operational`
- **Aggregation:** `count_distinct_site`

Whether the lab owns datacenter facilities, and at how many sites.

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 60 |
| 3 | 100 |

#### Power layer

- **Component weight (within category):** 33%
- **Metric(s):** `ppa_mw`, `energy_source_mix`
- **Counts statuses:** `contracted`, `under_construction`, `operational`
- **Aggregation:** `bool_any`

Whether the lab directly contracts or owns power supply.

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 100 |

### Expansion pipeline (15%)

Committed-but-not-yet-live growth: announced and contracted power, capital commitments, and grid interconnection filings. Subject to staleness decay.

#### Announced / contracted capacity (MW)

- **Component weight (within category):** 50%
- **Metric(s):** `power_capacity_mw`
- **Counts statuses:** `announced`, `contracted`
- **Aggregation:** `sum`

MW of power announced or contracted but not yet under construction.

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 15 |
| 100 | 35 |
| 300 | 50 |
| 600 | 65 |
| 1,000 | 80 |
| 2,000 | 90 |
| 4,000 | 100 |

#### Announced capital (USD)

- **Component weight (within category):** 30%
- **Metric(s):** `capex_announced_usd`
- **Counts statuses:** `announced`, `contracted`, `under_construction`, `operational`, `n/a`
- **Aggregation:** `sum`

Publicly announced infrastructure capital commitments, in USD.

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 20 |
| 1,000,000,000 | 40 |
| 10,000,000,000 | 60 |
| 50,000,000,000 | 80 |
| 100,000,000,000 | 100 |

#### Grid interconnection filings

- **Component weight (within category):** 20%
- **Metric(s):** `interconnection_filing`
- **Counts statuses:** `announced`, `contracted`, `under_construction`, `operational`, `n/a`
- **Aggregation:** `count`

Count of grid interconnection queue filings (ERCOT/FERC/utility).

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 50 |
| 3 | 80 |
| 6 | 100 |

### Energy security (15%)

Secured, ideally firm and clean, power supply: long-term PPAs, energy-mix disclosures, and any owned generation feeding operational sites.

#### Contracted power (PPA MW)

- **Component weight (within category):** 55%
- **Metric(s):** `ppa_mw`
- **Counts statuses:** `contracted`, `operational`
- **Aggregation:** `sum`

MW of power secured through contracted or operational power-purchase agreements.

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 15 |
| 100 | 35 |
| 300 | 50 |
| 600 | 65 |
| 1,000 | 80 |
| 2,000 | 100 |

#### Energy-source diversity

- **Component weight (within category):** 25%
- **Metric(s):** `energy_source_mix`
- **Counts statuses:** `announced`, `contracted`, `under_construction`, `operational`, `n/a`
- **Aggregation:** `count_distinct_site`

Distinct sites with a disclosed energy-source mix.

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 50 |
| 2 | 80 |
| 3 | 100 |

#### Owned / operational generation

- **Component weight (within category):** 20%
- **Metric(s):** `ppa_mw`
- **Counts statuses:** `operational`
- **Aggregation:** `bool_any`

Whether any PPA/generation is actually operational and feeding load.

| At least | Points |
| --- | --- |
| 0 | 0 |
| 1 | 100 |

## Category math

```
category.points        = sum(component.weight * component.band_points)
category.contribution  = category.weight * category.points
score                  = sum(category.contribution)          # 0-100
```

Methodology changes bump the version (`scoring.v2.yaml`, old file retained),
rescore history under both versions, and get a CHANGELOG entry explaining the diff.
