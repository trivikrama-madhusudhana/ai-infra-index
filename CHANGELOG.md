# Changelog

One entry per cycle: facts added, superseded, rejected, and the score movements they caused.

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
