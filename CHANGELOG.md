# Changelog

One entry per cycle: facts added, superseded, rejected, and the score movements they caused.

## 2026-07-25: Update cycle

First incremental cycle after the baseline. Eight researchers swept their own lab for
announcements in the trailing 21 days and for status progression at every site already in the
ledger; five verifiers then re-fetched each new fact and checked it against its own cited source
with no access to the researcher's reasoning.

**42 facts proposed, 38 confirmed, 2 rejected, 2 amended.** The ledger goes from 150 to 194
facts. Nothing was deleted: rejected facts stay in the ledger with `verified: false` and a note
explaining what the page actually said, and each amendment is a new fact with the old one
pointed at it via `superseded_by`.

Scores (scoring v1, as-of 2026-07-25):

| Lab | 2026-07-20 | 2026-07-25 | Change |
|---|---|---|---|
| xAI | 60.06 | 67.01 | +6.95 |
| Google | 47.25 | 56.00 | +8.75 |
| Meta | 53.55 | 54.30 | +0.75 |
| OpenAI | 22.73 | 29.48 | +6.75 |
| Anthropic | 14.60 | 14.60 | — |
| Zhipu | 0.00 | 9.96 | +9.96 |
| MiniMax | 0.00 | 0.00 | — |
| Moonshot | 0.00 | 0.00 | — |

What moved, and why:

- **xAI +6.95.** Colossus 2 flipped from under construction to operational on Epoch AI's site
  entry, taking operational capacity from 597 to 1,543 MW and the accelerator fleet from 640,000
  to 1,080,000 chips. Both figures are Epoch's own estimates, built from satellite and drone
  imagery, a cooling-power model and the SpaceX S-1; the final 946 MW milestone is modelled
  rather than observed, and that is worth remembering before treating it as measured. Southaven's
  41 gas turbines also moved from a scheduled hearing to a permit granted by Mississippi DEQ.
- **Google +8.75.** The eighth-generation TPU (8t training / 8i inference) is a second custom
  silicon program, taking that component from 60 to 100 points. Project Tembo near Cheyenne,
  Wyoming adds 2,700 MW to a pipeline that was previously empty. Texas contracted power rose from
  6,200 to 7,800 MW, Alphabet's 2026 capex guidance from $180-190bn to $195-205bn (recorded at
  the floor), and a new 1,600 MW Arkansas solar PPA broke ground.
- **OpenAI +6.75, and its first owned site.** Project Camellia in Effingham County, Georgia is the
  first site OpenAI states it is itself designing and developing, paying full infrastructure and
  electric-service costs, entirely privately funded. Every previous OpenAI site is partner-owned
  and therefore scores as `cloud_partnership`; this one does not. The 3,200 MW contracted with
  Georgia Power is phased 2028-2032, so none of it is energised. Abilene rose from 200 to 421 MW
  operational, still credited to Oracle as owner.
- **Zhipu 0.00 to 9.96, on a narrower basis than first reported.** Z.ai has built its own AI
  computing centre stocked exclusively with domestic chips. The `owned_facility` fact survived
  verification; the accompanying claim of **1,000 MW operational did not** and was rejected, because
  the sources say "1GW-class" with only part of the facility running and give no megawatt figure
  for the live portion. A 100,000-chip Ascend count was also rejected: it is Z.ai's own claim
  about what GLM-5 was *trained on*, with no statement that Z.ai owns the accelerators. What
  remains is one owned site and a 10,000-chip per-cluster floor. Every source traces back to a
  single leak; the company has confirmed nothing.
- **Meta +0.75.** Sturgeon County, Alberta — its first Canadian datacenter — broke ground at
  1,000 MW with US$9.17bn capex, and Temple, Texas went live on 22 July.
- **Anthropic unchanged at 14.60.** It added five facts this cycle and every one of them is a
  `cloud_partnership`: AMD MI450 capacity, the quantified 3,500 MW Google/Broadcom TPU program,
  the $35bn Broadcom/Apollo financing vehicle, over 1 GW of Fluidstack-based capacity, and over
  1 GW of non-binding direct-lease LOIs. Under owner-attribution none of that is owned
  infrastructure, so the score does not move. That is the rule working as intended, not a gap.

Rejected and amended:

- `zhipu-2026-07-25-001` — 1,000 MW operational, rejected. Design/class capacity, partly energised.
- `zhipu-2026-07-25-005` — 100,000 Ascend chips, rejected. A training-run count and a company claim.
- `anthropic-2026-07-25-001` — amended from `contracted` to `announced`. AMD's release announces a
  partnership to deploy "up to 2 gigawatts" with forward-looking-statement hedging; only the
  inbound equity is committed.
- `zhipu-2026-07-25-003` — amended. The source says the facility "will train" the GLM family; the
  original said "deploy", and partial energisation is now explicit.

Excluded before merge, with reasons:

- Moonshot's $500m Series C was proposed as `capex_announced_usd`. A funding round is not
  announced infrastructure capex, and mapping one to the other is imputation, so it was dropped.
- Bloomberg-only details of the Anthropic TPU financing vehicle (tranche structure, Google lease
  backstop) were refused: the pages 403 with no readable snapshot, and every other outlet
  carrying them is off the source allowlist.
- Google's Steel River notes described a "virtual" PPA with Google as "anchor investor". The cited
  page says neither; both descriptors were removed at verification.

Maintenance and corrections:

- **History snapshot corrected.** `data/history/index-2026-07-20.json` held a stale mid-run capture
  (Google at 29.22) while the committed `index.json` for the same date said 47.25. The snapshot
  has been replaced with the authoritative baseline index.
- **Archive coverage.** 28 of the 29 facts that lacked a `web.archive.org` snapshot now have one:
  20 recovered from existing captures and 8 saved on demand. 193 of 194 facts now carry an
  archive URL. The one holdout is a GlobeNewswire release that Wayback refuses to capture.
- **Source spot-check.** Five randomly chosen existing sources were re-fetched; all five resolve.
  Two have drifted to new URLs and should be updated on a future pass:
  `epoch.ai/blog/...` now redirects to `epoch.ai/latest/...`, and
  `datacenters.google/locations/berkeley-county-south-carolina/` redirects to
  `/locations/south-carolina/`.

Flagged for a human, deliberately not acted on:

- `minimax-2026-07-20-001` looks mis-sited. It attributes $142m to `alibaba-cloud`, but the source
  figure is MiniMax's total R&D compute across all suppliers; its Alibaba spend was roughly $58m.
  A superseding correction is warranted once someone confirms the right split.
- Ledger gaps found outside the 21-day window and not recorded: an xAI "Colossus 3" site in
  Mississippi; OpenAI's Stargate Argentina, Stargate UK and the SB Energy investment; Google's
  $4bn West Memphis datacenter.
- One verification batch (Moonshot and MiniMax) ran against a scratch directory that a second
  agent was writing to concurrently, so its page cache may have been mixed. Those eight facts were
  all confirmed, and none of them affect any score — every one is either a `cloud_partnership` or
  carries a prose value that aggregates to zero. The 16 score-bearing confirmations from the other
  batches were independently re-verified in isolated fetches and all 16 held.

## 2026-07-20: Baseline

First pass at all eight labs. Eight research agents pulled the documented record from public
sources, a second agent re-fetched every source to confirm the number matched the page, and a
third searched for anything the first pass missed. 152 candidate facts came back; 136 survived
into the ledger. The 16 that did not were all sourced from domains I will not score a facts
ledger on (Wikipedia, an aggregator, a fan blog, an arxiv preprint), and each dropped fact is
logged with its reason.

Capacity is credited to whoever owns the site. That single rule drives most of the ranking. xAI
and Meta lead because they own their datacenters (Colossus, Prineville and the Hyperion build).
OpenAI scores low despite the 500 billion dollar Stargate program, because Stargate is operated
by Crusoe, Oracle, Vantage and SB Energy, so every megawatt of it lands as a `cloud_partnership`
fact rather than owned capacity. Anthropic is lower still: it rents everything, owns no power,
and its accelerators are AWS and Google silicon, not its own.

Numbers as of 2026-07-20 (scoring v1): xai 60.06, meta 53.55, google 47.25, openai 22.73,
anthropic 14.60, and moonshot / minimax / zhipu at 0.00.

Corrections made during assembly:

- Anthropic's two `custom_silicon` facts (Broadcom TPU, AWS Trainium) were reclassified to
  `cloud_partnership`. Both describe a partner's chip that Anthropic uses, not silicon Anthropic
  designs, so under owner-attribution they should not credit its silicon layer. This moved
  Anthropic from 26.40 to 14.60.

Same-day refinements:

- **Google power gap closed.** A focused research pass across four angles (US datacenters,
  international, PPAs, capex) added 14 verified facts: owned datacenters at The Dalles, Council
  Bluffs, and Berkeley County from Google's own site, a 225 MW South Carolina PPA, and a 250 MW
  operational figure for New Albany. Google moved from 29.22 to 47.25. Per-site megawatts are
  still hard to source precisely, so power capacity is likely still under-counted, not over.
- **xAI Terafab kept, now labeled.** The Terafab chip-fab fact still counts as custom silicon,
  since xAI co-owns the JV. It is now flagged on the dashboard as an explicit judgment call so
  readers can weigh it themselves.
- **Archive snapshots backfilled.** 121 of 136 facts gained a web.archive.org snapshot from the
  Wayback availability API; 15 with no existing snapshot are pending a save pass.

Still thin: the Chinese labs (Moonshot, MiniMax, Zhipu) remain sparsely documented and mostly
unverified. Zero there means "not publicly documented", not "no infrastructure".
