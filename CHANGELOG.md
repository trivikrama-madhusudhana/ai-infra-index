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

Numbers as of 2026-07-20 (scoring v1): xai 60.06, meta 53.55, google 29.22, openai 22.73,
anthropic 14.60, and moonshot / minimax / zhipu at 0.00.

Corrections made during assembly:

- Anthropic's two `custom_silicon` facts (Broadcom TPU, AWS Trainium) were reclassified to
  `cloud_partnership`. Both describe a partner's chip that Anthropic uses, not silicon Anthropic
  designs, so under owner-attribution they should not credit its silicon layer. This moved
  Anthropic from 26.40 to 14.60.

Open flags for review (not yet resolved):

- xAI's Terafab fact still counts as `custom_silicon`. xAI co-owns the fab JV, so this is a
  genuine judgment call rather than a clear error, and it props up xAI's vertical-integration
  score. Left as-is pending a decision.
- Google scores 0 on power capacity. Google plainly runs enormous owned datacenters; the gap is
  that per-site megawatt figures are hard to source precisely, not that the capacity is absent.
  This is a coverage gap to close, not a finding that Google has no power.
- The Chinese labs are thin (Moonshot 2 facts, MiniMax 5, Zhipu 5) and mostly unverified. Their
  infrastructure disclosure is sparse and often Chinese-language; MiniMax has no scoreable fact
  yet. Zero here means "not publicly documented", not "no infrastructure".
- Most facts still lack a web.archive.org snapshot. Backfilling archive URLs is the next
  maintenance pass.
