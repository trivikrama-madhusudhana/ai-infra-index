# Owner decisions

Recorded 2026-07-20. These bind all research and scoring.

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
