#!/usr/bin/env python3
"""Generate the static site from index.json + the ledger. No framework, no build step.

    python scripts/build_site.py

Writes plain HTML/CSS into docs/. Built for two readers at once: someone
non-technical who wants to know who is winning the physical AI buildout and why,
and someone technical who wants the exact math and the underlying evidence. Every
displayed number links to the fact that produced it.

Link rule: pages in docs/company/ are one directory deep, so anything they point
at outside their own page needs the "../" prefix. Evidence pills point at facts
on the same page and must stay bare fragments. tests/test_site_links.py walks the
generated HTML and fails if any of that drifts.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "docs"
COMPANIES_DIR = ROOT / "data" / "companies"
REPO_URL = "https://github.com/trivikrama-madhusudhana/ai-infra-index"
SITE_URL = "https://trivikrama-madhusudhana.github.io/ai-infra-index"

SCORING_PATH = sorted((ROOT / "config").glob("scoring.v*.yaml"),
                     key=lambda p: int(p.stem.split(".v")[1]))[-1]
SCORING = yaml.safe_load(SCORING_PATH.read_text())
SOURCES = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text())
SCOREABLE_TIERS = set(SOURCES.get("scoreable_tiers", ["A", "B"]))

METRIC_LABEL = {
    "power_capacity_mw": "Power capacity", "datacenter_site": "Datacenter site",
    "ppa_mw": "Power-purchase agreement", "gpu_count": "Accelerator fleet",
    "custom_silicon": "Custom silicon", "cloud_partnership": "Cloud partnership",
    "owned_facility": "Owned facility", "capex_announced_usd": "Announced capex",
    "interconnection_filing": "Interconnection filing", "energy_source_mix": "Energy-source mix",
}
ALL_METRICS = list(METRIC_LABEL)
NOT_DISCLOSED_ALWAYS = [
    "Electricity price paid", "Power usage effectiveness (PUE)",
    "Fleet utilization", "Internal inference / training cost",
]

# How each lab writes its own name. The slug stays the URL and the ledger key.
DISPLAY_NAME = {
    "openai": "OpenAI", "anthropic": "Anthropic", "google": "Google",
    "meta": "Meta", "xai": "xAI", "minimax": "MiniMax",
    "moonshot": "Moonshot AI", "zhipu": "Zhipu AI",
}

# Plain-language gloss for each scoring category, one line a non-technical reader gets.
CAT_PLAIN = {
    "power_capacity": "Megawatts the lab's own datacenters draw today or are actively building.",
    "compute_ownership": "How many AI chips it controls, and whether it designs its own.",
    "vertical_integration": "How much of the stack (chips, datacenters, power) it owns rather than rents.",
    "expansion_pipeline": "Announced capacity, capital, and grid filings that are committed but not yet live.",
    "energy_security": "Power it has locked in through long-term contracts and owned generation.",
}

# ---------------------------------------------------------------------------


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def display_name(slug: str) -> str:
    return DISPLAY_NAME.get(slug, slug)


def host_of(url: str) -> str:
    return url.split("://", 1)[-1].split("/", 1)[0].split("?", 1)[0].lower()


def load_tier_map() -> dict:
    m = {}
    for tier, doms in SOURCES["tiers"].items():
        for d in doms or []:
            m[d.lower()] = tier
    return m


TIERS = load_tier_map()


def tier_for(url: str) -> str:
    host = host_of(url)
    best, blen = "D", -1
    for dom, t in TIERS.items():
        if host == dom or host.endswith("." + dom):
            if len(dom) > blen:
                best, blen = t, len(dom)
    return best


def scores(fact: dict) -> bool:
    """Same eligibility test the scoring engine applies. Keeps the summary tiles
    from claiming something the score breakdown below them contradicts."""
    return (
        not fact.get("superseded_by")
        and not fact.get("covered_by")
        and fact["verification"]["verified"]
        and tier_for(fact["source"]["url"]) in SCOREABLE_TIERS
    )


def why_not_scored(fact: dict) -> str:
    if fact.get("superseded_by"):
        return "superseded by a newer fact"
    if fact.get("covered_by"):
        return "its value is already inside a broader fact that scores"
    if not fact["verification"]["verified"]:
        return "not yet confirmed against its source"
    t = tier_for(fact["source"]["url"])
    if t not in SCOREABLE_TIERS:
        return f"Tier {t} source, recorded for context but never scored"
    return ""


def comp_metrics(cat_name, comp_name):
    c = SCORING["categories"][cat_name]["components"][comp_name]
    return c.get("metrics", [c.get("metric")])


def fmt_int(v):
    return f"{int(round(v)):,}"


def compact_usd(v) -> str:
    """$900B rather than $900,000,000,000. The exact figure rides along in a title."""
    v = float(v)
    for cut, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if abs(v) >= cut:
            n = v / cut
            s = f"{n:.1f}".rstrip("0").rstrip(".")
            return f"${s}{suffix}"
    return "$" + fmt_int(v)


def compact_num(v) -> str:
    v = float(v)
    if abs(v) >= 1e6:
        s = f"{v / 1e6:.1f}".rstrip("0").rstrip(".")
        return s + "M"
    return fmt_int(v)


def human_value(cat_name, comp_name, comp):
    """A value string a non-technical reader can read at a glance."""
    if comp["missing"]:
        return "none on record"
    agg = comp["aggregation"]
    val = comp["aggregated_value"]
    metrics = comp_metrics(cat_name, comp_name)
    if agg == "bool_any":
        return "yes" if val >= 1 else "no"
    if agg in ("count", "count_distinct_site"):
        n = int(round(val))
        return f"{n} site" + ("" if n == 1 else "s") if agg == "count_distinct_site" else str(n)
    if any(m in ("power_capacity_mw", "ppa_mw") for m in metrics):
        return f"{fmt_int(val)} MW"
    if "capex_announced_usd" in metrics:
        return compact_usd(val)
    if "gpu_count" in metrics:
        return f"{fmt_int(val)} chips"
    return fmt_int(val)


def value_title(cat_name, comp_name, comp) -> str:
    """Exact figure behind an abbreviated one, for the title attribute."""
    if comp["missing"]:
        return ""
    if "capex_announced_usd" in comp_metrics(cat_name, comp_name):
        return "$" + fmt_int(comp["aggregated_value"])
    return ""


def fmt_num(v) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, float)):
        if v == int(v):
            return f"{int(v):,}"
        return f"{v:,.2f}"
    return esc(v)


def truncate(s: str, n: int = 72) -> str:
    s = str(s)
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def tier_badge(t: str) -> str:
    names = {"A": "primary / official source", "B": "reputable press or research",
             "C": "secondary, not scored", "D": "unlisted domain, not scored"}
    return f'<span class="badge tier tier-{t.lower()}" title="Tier {t}: {names.get(t, "unknown")}">Tier {t}</span>'


def ver_badge(v: dict) -> str:
    if v.get("verified"):
        return '<span class="badge ok" title="A second pass re-opened the source and confirmed this number">verified</span>'
    return '<span class="badge no" title="Not yet confirmed against its source; shown but not scored">unverified</span>'


def scored_badge(f: dict, labels: dict | None = None) -> str:
    if f.get("superseded_by"):
        sid = f["superseded_by"]
        label = (labels or {}).get(sid, sid[-3:])
        return (f'<span class="badge off" title="A later fact replaced this one; it no longer '
                f'scores">superseded by <a href="#f-{esc(sid)}">{esc(label)}</a></span>')
    if f.get("covered_by"):
        cid = f["covered_by"]
        label = (labels or {}).get(cid, cid[-3:])
        return (f'<span class="badge off" title="This value is already inside a broader fact, so '
                f'counting it again would double count">counted in '
                f'<a href="#f-{esc(cid)}">{esc(label)}</a></span>')
    reason = why_not_scored(f)
    if not reason:
        return ""
    return f'<span class="badge off" title="{esc(reason)}">not scored</span>'


def is_judgment_call(f: dict) -> bool:
    return (f.get("notes") or "").lower().startswith("judgment call")


def jc_badge(f: dict) -> str:
    return '<span class="badge warn" title="A deliberate, debatable classification choice">judgment call</span>' if is_judgment_call(f) else ""


LEGEND = (
    '<p class="legend muted">'
    '<span class="badge tier tier-a">Tier A</span> primary source &nbsp;'
    '<span class="badge tier tier-b">Tier B</span> reputable press &nbsp;'
    '<span class="badge ok">verified</span> confirmed against its source &nbsp;'
    '<span class="badge no">unverified</span> recorded, not scored &nbsp;'
    '<span class="badge off">not scored</span> outside the scoring rules</p>'
)

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='7' fill='%232f6fbf'/%3E"
    "%3Cg fill='white'%3E%3Crect x='7' y='17' width='4' height='9' rx='1'/%3E"
    "%3Crect x='14' y='11' width='4' height='15' rx='1'/%3E"
    "%3Crect x='21' y='6' width='4' height='20' rx='1'/%3E%3C/g%3E%3C/svg%3E"
)

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{site_url}/preview.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{favicon}">
<link rel="stylesheet" href="{css}">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site">
  <a class="wordmark" href="{home}">AI Infrastructure Index</a>
  <nav>
    <a href="{home}"{cur_home}>Ranking</a>
    <a href="{methodology}"{cur_meth}>Methodology</a>
    <a href="{changelog}"{cur_chg}>Changelog</a>
    <a href="{repo}">Source</a>
  </nav>
</header>
<main id="main">
{body}
</main>
<footer>
  <p>Every number links to a public source. Unknown means unknown. We never estimate.</p>
  <p><strong>This is an open work in progress and we want your input.</strong> Challenge a number, send a
  better source, or propose a smarter way to score. <a href="{repo}/issues">Open an issue or a pull request</a>.</p>
  <p class="muted">Scores come from a deterministic engine anyone can rerun:
  <code>python scripts/score.py --as-of {asof}</code></p>
</footer>
</body>
</html>
"""

DEFAULT_DESC = ("A deterministic, source-linked scorecard of the physical AI buildout: "
                "megawatts, datacenters, chips and capital the frontier labs actually own.")


def page(title, body, depth=0, asof="", desc=DEFAULT_DESC, current=""):
    up = "../" * depth
    mark = ' class="current" aria-current="page"'
    return PAGE.format(
        title=esc(title), desc=esc(desc), body=body, css=up + "style.css", home=up + "index.html",
        methodology=up + "methodology.html", changelog=up + "changelog.html",
        repo=REPO_URL, asof=esc(asof), favicon=FAVICON, site_url=SITE_URL,
        cur_home=mark if current == "home" else "",
        cur_meth=mark if current == "methodology" else "",
        cur_chg=mark if current == "changelog" else "",
    )


# ---------------------------------------------------------------------------
# Minimal markdown -> HTML (headings, tables, code fences, lists, blockquote,
# links, bold, inline code). Enough for METHODOLOGY.md and CHANGELOG.md.
# ---------------------------------------------------------------------------

def md_inline(s: str) -> str:
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return s


def md_to_html(md: str) -> str:
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("<!--"):
            i += 1
            continue
        if ln.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(esc(lines[i]))
                i += 1
            i += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>")
            continue
        if ln.startswith("#"):
            lvl = len(ln) - len(ln.lstrip("#"))
            out.append(f"<h{lvl}>{md_inline(ln[lvl:].strip())}</h{lvl}>")
            i += 1
            continue
        if ln.strip().startswith("|"):
            tbl = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                tbl.append(lines[i])
                i += 1
            out.append(render_md_table(tbl))
            continue
        if ln.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i][1:].strip())
                i += 1
            out.append("<blockquote>" + md_inline(" ".join(buf)) + "</blockquote>")
            continue
        if ln.strip().startswith("- "):
            items = []
            while i < len(lines) and (lines[i].strip().startswith("- ") or
                                      (items and lines[i].strip() and lines[i].startswith((" ", "\t")))):
                if lines[i].strip().startswith("- "):
                    items.append([lines[i].strip()[2:]])
                else:
                    items[-1].append(lines[i].strip())   # wrapped continuation of the item above
                i += 1
            out.append("<ul>" + "".join("<li>" + md_inline(" ".join(it)) + "</li>" for it in items) + "</ul>")
            continue
        if ln.strip() == "":
            i += 1
            continue
        buf = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", ">", "```")) and not lines[i].strip().startswith("- "):
            buf.append(lines[i])
            i += 1
        out.append("<p>" + md_inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


def render_md_table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    if len(cells) >= 2 and all(set(c) <= set("-: ") for c in cells[1]):
        head, body = cells[0], cells[2:]
    else:
        head, body = cells[0], cells[1:]
    h = "".join(f"<th>{md_inline(c)}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>" for r in body)
    return f'<div class="scroll"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


# ---------------------------------------------------------------------------

def load_ledger():
    out = {}
    for p in sorted(COMPANIES_DIR.glob("*.json")):
        d = json.loads(p.read_text())
        out[d["company"]] = d["facts"]
    return out


def short_labels(fact_ids) -> dict:
    """Compact pill text per fact id. Ids look like xai-2026-07-25-002, so the last
    three digits usually read fine, but two collection dates can both end in -002.
    Where that happens, fall back to day + sequence so no two pills read alike."""
    ids = list(fact_ids)
    tails = [i.rsplit("-", 1)[-1] for i in ids]
    labels = {}
    for fid, tail in zip(ids, tails):
        if tails.count(tail) > 1:
            parts = fid.split("-")
            labels[fid] = f"{parts[-2]}-{parts[-1]}" if len(parts) >= 2 else tail
        else:
            labels[fid] = tail
    return labels


def ev_pill(fid: str, by_id: dict, labels: dict) -> str:
    """Evidence chip. Facts live on the same page, so this must be a bare fragment."""
    f = by_id.get(fid)
    if f:
        tip = (f'{METRIC_LABEL.get(f["metric"], f["metric"])} '
               f'{fmt_num(f["value"])} at {f["site"]}, {f["source"]["publisher"]} '
               f'{f["as_of_date"]} - jump to this fact')
    else:
        tip = "jump to this fact"
    return f'<a class="ev" href="#f-{esc(fid)}" title="{esc(tip)}">{esc(labels.get(fid, fid[-3:]))}</a>'


def build_home(index, ledger):
    comps = index["companies"]
    asof = index["meta"]["generated_as_of"]
    top_score = max((c["score"] for c in comps), default=1) or 1

    rows = []
    for rank, c in enumerate(comps, 1):
        slug = c["company"]
        top = max(c["categories"].items(), key=lambda kv: kv[1]["weighted_contribution"])
        top_label = top[1]["label"] if c["score"] > 0 else "nothing scoreable yet"
        pct = 0 if top_score == 0 else round(c["score"] / top_score * 100)
        zero = " zero" if c["score"] == 0 else ""
        rows.append(
            f'<tr class="rrow{zero}"><td class="rank">{rank}</td>'
            f'<td class="lab"><a href="company/{esc(slug)}.html">{esc(display_name(slug))}</a></td>'
            f'<td class="score"><span class="bar" aria-hidden="true"><span class="fill" style="width:{pct}%"></span></span>'
            f'<span class="scoreval">{c["score"]:.1f}</span></td>'
            f'<td class="num">{c["eligible_fact_count"]}</td>'
            f'<td class="muted strong-area">{esc(top_label)}</td></tr>'
        )

    measure_rows = "".join(
        f'<tr><td>{esc(cat["label"])}</td><td class="muted">{esc(CAT_PLAIN.get(name, ""))}</td>'
        f'<td class="num">{round(cat["weight"] * 100)}%</td></tr>'
        for name, cat in SCORING["categories"].items()
    )

    body = f"""
<h1>The physical AI race, scored on public evidence</h1>
<p class="lede">Model benchmarks are everywhere. The megawatts are not. This index tracks the
infrastructure the frontier labs actually control, and every number on it traces to a source you
can open. Capacity is credited to whoever owns the site, so a lab that rents its compute scores
low here on purpose.</p>

<h2>The ranking</h2>
<p class="muted section-sub">Score out of 100, as of {esc(asof)}. Click a lab for its full
breakdown and the evidence behind every point.</p>
<div class="scroll">
<table class="rank-table">
<thead><tr>
<th class="num">#</th><th>Lab</th>
<th>Score <span class="muted th-note">out of 100</span></th>
<th class="num">Facts <span class="muted th-note">scored</span></th>
<th>Strongest area</th>
</tr></thead>
<tbody>{''.join(rows)}
</tbody>
</table>
</div>
<p class="note">A lab at 0 is not one with no infrastructure, it is one whose infrastructure is not
yet documented in public sources we will score. Unknown means unknown; we never estimate.</p>

<h2>How the score works</h2>
<p>Each lab gets a score from 0 to 100. It rewards infrastructure a lab actually owns and can
point to in public: power its datacenters draw today, sites it holds, chips it designs, deals it
has signed. Renting compute from someone else's cloud counts for little. Five things go into the
score:</p>
<div class="scroll"><table class="measure">
<thead><tr><th>What we measure</th><th>In plain terms</th><th class="num">Weight</th></tr></thead>
<tbody>{measure_rows}</tbody>
</table></div>
<p class="muted">Scoring version {index['meta']['scoring_version']}. The
<a href="methodology.html">methodology</a> has the full rubric and the command to reproduce every
number.</p>

<h2>Help make it better</h2>
<p>This index is early and it gets sharper the more people push on it. We are actively looking for
input from anyone who knows this terrain: challenge a number you think is wrong, point us at a
better or missing source, flag a datacenter or deal we have not captured, or argue for a smarter way
to weigh the score. Nothing here is settled.</p>
<p><a href="{REPO_URL}/issues">Open an issue</a> to raise a correction or an idea, or send a
<a href="{REPO_URL}/pulls">pull request</a> against the evidence ledger. Every fact traces to a public
source precisely so it can be checked and argued with.</p>
"""
    (SITE / "index.html").write_text(page("AI Infrastructure Index", body, 0, asof, current="home"))


def stat_tiles(slug, facts):
    """Headline numbers. Built from scoreable facts only, so these can never
    disagree with the score breakdown further down the page."""
    live = [f for f in facts if scores(f)]

    def s(metric, statuses):
        return sum(f["value"] for f in live if f["metric"] == metric and f["status"] in statuses
                   and isinstance(f["value"], (int, float)) and not isinstance(f["value"], bool))

    owned_op = s("power_capacity_mw", {"operational"})
    owned_uc = s("power_capacity_mw", {"under_construction"})
    owned_sites = len({f["site"] for f in live if f["metric"] == "owned_facility" and f["status"] in ("under_construction", "operational")})
    silicon = any(f["metric"] == "custom_silicon" for f in live)
    # Summed, not max: the scoring engine sums gpu_count, and a tile that used a
    # different aggregation would print a different fleet size to the breakdown
    # a screen below it.
    fleet = sum(f["value"] for f in live if f["metric"] == "gpu_count"
                and isinstance(f["value"], (int, float)) and not isinstance(f["value"], bool))
    capex = s("capex_announced_usd", {"announced", "contracted", "under_construction", "operational", "n/a"})
    partner = sum(f["value"] for f in live if f["metric"] == "cloud_partnership" and f["unit"] == "MW"
                  and isinstance(f["value"], (int, float)) and not isinstance(f["value"], bool))

    def tile(label, value, disclosed, title=""):
        v = value if disclosed else '<span class="nd">not disclosed</span>'
        t = f' title="{esc(title)}"' if title and disclosed else ""
        return (f'<div class="tile"><div class="tval"{t}>{v}</div>'
                f'<div class="tlab">{esc(label)}</div></div>')

    tiles = [
        tile("Owned power, operational", f"{fmt_int(owned_op)} MW", owned_op > 0),
        tile("Owned power, building", f"{fmt_int(owned_uc)} MW", owned_uc > 0),
        tile("Owned datacenter sites", str(owned_sites), owned_sites > 0),
        tile("Designs its own chips", "yes" if silicon else "no", True),
        tile("Accelerators on record", compact_num(fleet), fleet > 0, f"{fmt_int(fleet)} chips"),
        tile("Announced capital", compact_usd(capex), capex > 0, "$" + fmt_int(capex)),
    ]
    note = ""
    if partner > 0:
        note = (f'<p class="muted tilenote">Plus {fmt_int(partner)} MW of rented or partner-operated '
                f'capacity, recorded below but not counted as owned.</p>')
    return '<div class="tiles">' + "".join(tiles) + "</div>" + note


STATUS_ORDER = ["announced", "contracted", "under_construction", "operational", "n/a"]


def status_chip(status: str) -> str:
    cls = status.replace("_", "-")
    return f'<span class="st st-{esc(cls)}">{esc(status.replace("_", " "))}</span>'


def build_company(c, facts, asof, rank, total):
    slug = c["company"]
    name = display_name(slug)
    live = [f for f in facts if not f.get("superseded_by")]
    by_id = {f["id"]: f for f in facts}
    pill_labels = short_labels(by_id)

    # ---- score breakdown, plain-language first, exact math behind a toggle ----
    cat_html = []
    for cat_name in SCORING["categories"]:          # rubric order, not alphabetical
        cat = c["categories"][cat_name]
        comp_rows = []
        for comp_name in SCORING["categories"][cat_name]["components"]:
            comp = cat["components"][comp_name]
            links = " ".join(ev_pill(fid, by_id, pill_labels) for fid in comp["fact_ids"])
            facts_cell = links if links else '<span class="muted">&mdash;</span>'
            vt = value_title(cat_name, comp_name, comp)
            vt_attr = f' title="{esc(vt)}"' if vt else ""
            decay = (f'<div class="decay">discounted for age: '
                     f'{", ".join(pill_labels.get(x, x[-3:]) for x in comp["decayed_fact_ids"])}</div>'
                     if comp["decayed_fact_ids"] else "")
            zero = " nil" if comp["missing"] else ""
            comp_rows.append(
                f'<tr class="crow{zero}"><td class="cname">{esc(comp["label"])}</td>'
                f'<td class="hval"{vt_attr}>{esc(human_value(cat_name, comp_name, comp))}</td>'
                f'<td class="num pts">{comp["band_points"]:g}</td>'
                f'<td class="facts">{facts_cell}</td></tr>'
                f'<tr class="detail"><td colspan="4">'
                f'<code>{esc(comp["input_expression"])}</code> '
                f'&rarr; {comp["band_points"]:g} pts &times; weight {comp["weight"]:g} '
                f'= {comp["weighted_points"]:g} of this category&rsquo;s '
                f'{comp["weight"] * 100:g}{decay}'
                f'</td></tr>'
            )
        pct = 0 if not cat["weight"] else round(cat["weighted_contribution"] / (cat["weight"] * 100) * 100)
        cat_html.append(
            f'<section class="catblock"><div class="cathead"><h3>{esc(cat["label"])}</h3>'
            f'<span class="catpts"><span class="minibar" aria-hidden="true">'
            f'<span class="fill" style="width:{pct}%"></span></span>'
            f'{cat["weighted_contribution"]:g} of {round(cat["weight"] * 100)} pts</span></div>'
            f'<p class="catdesc">{esc(CAT_PLAIN.get(cat_name, ""))}</p>'
            f'<div class="scroll"><table class="breakdown">'
            f'<colgroup><col class="c-comp"><col class="c-found"><col class="c-pts"><col class="c-ev"></colgroup>'
            f'<thead><tr><th>Component</th><th>What we found</th>'
            f'<th class="num">Points <span class="muted th-note">of 100</span></th>'
            f'<th>Evidence</th></tr></thead>'
            f'<tbody>{"".join(comp_rows)}</tbody></table></div></section>'
        )

    # ---- facilities ----
    fac_facts = [f for f in live if f["metric"] in ("power_capacity_mw", "owned_facility", "cloud_partnership", "datacenter_site")]
    sites = {}
    for f in fac_facts:
        sites.setdefault(f["site"], []).append(f)
    fac_rows = []
    for site, fs in sorted(sites.items()):
        fs.sort(key=lambda f: (f["as_of_date"], f["metric"]))
        steps = []
        for f in fs:
            raw = f["value"]
            if isinstance(raw, str):
                val_html = esc(truncate(raw))
                tip = f'{METRIC_LABEL.get(f["metric"], f["metric"])}: {raw}'
            else:
                unit = "" if f["unit"] in ("boolean", "text") else " " + esc(f["unit"])
                val_html = f"{fmt_num(raw)}{unit}"
                tip = f'{METRIC_LABEL.get(f["metric"], f["metric"])} at {f["site"]}'
            steps.append(
                f'<a class="step" href="#f-{esc(f["id"])}" title="{esc(tip)}">'
                f'<span class="scol">{status_chip(f["status"])}</span>'
                f'<span class="smetric">{esc(METRIC_LABEL.get(f["metric"], f["metric"]))}</span>'
                f'<span class="sval">{val_html}</span>'
                f'<span class="sdate">{esc(f["as_of_date"])}</span></a>'
            )
        fac_rows.append(
            f'<tr><td class="sitecell"><span class="mono">{esc(site)}</span></td>'
            f'<td class="steps">{"".join(steps)}</td></tr>'
        )
    fac_html = (
        f'<div class="scroll"><table class="facilities">'
        f'<colgroup><col class="c-site"><col></colgroup>'
        f'<thead><tr><th>Site</th><th>What we know, oldest first</th></tr></thead>'
        f'<tbody>{"".join(fac_rows)}</tbody></table></div>'
        if fac_rows else '<p class="muted">No site-level facilities recorded yet.</p>'
    )

    # ---- evidence, grouped by metric ----
    def fact_card(f):
        src = f["source"]
        t = tier_for(src["url"])
        arch = f' &middot; <a href="{esc(src["archive_url"])}">archived copy</a>' if src.get("archive_url") else ""
        notes = f'<p class="notes muted">{esc(f["notes"])}</p>' if f.get("notes") else ""
        unit = "" if f["unit"] in ("boolean", "text") else " " + esc(f["unit"])
        val = fmt_num(f["value"])
        extra = ""
        if f["metric"] == "capex_announced_usd" and isinstance(f["value"], (int, float)):
            extra = f' <span class="muted">({compact_usd(f["value"])})</span>'
        off = "" if scores(f) else " unscored"
        return (
            f'<article class="fact{off}" id="f-{esc(f["id"])}">'
            f'<div class="fhead"><span class="val">{val}{unit}{extra}</span> '
            f'{status_chip(f["status"])} '
            f'<span class="fmetric">{esc(METRIC_LABEL.get(f["metric"], f["metric"]))}</span> '
            f'<span class="muted">at <span class="mono">{esc(f["site"])}</span>, '
            f'as of {esc(f["as_of_date"])}</span></div>'
            f'<blockquote>{esc(f["excerpt"])}</blockquote>'
            f'<div class="fmeta">{tier_badge(t)}{ver_badge(f["verification"])}{jc_badge(f)}'
            f'{scored_badge(f, pill_labels)}'
            f'<span class="muted">{esc(src["publisher"])}, {esc(src["date_published"])}</span> &middot; '
            f'<a href="{esc(src["url"])}">source</a>{arch} '
            f'<a class="mono small permalink" href="#f-{esc(f["id"])}" '
            f'title="Permalink to this fact">{esc(f["id"])}</a></div>{notes}</article>'
        )

    # Superseded facts are shown too. Nothing is ever deleted from the ledger, so
    # hiding them here would misrepresent it — they are marked and do not score.
    ev = []
    for metric in ALL_METRICS:
        group = sorted([f for f in facts if f["metric"] == metric], key=lambda f: (f["site"], f["as_of_date"]))
        if not group:
            continue
        ev.append(f'<h3 class="evgroup">{esc(METRIC_LABEL[metric])} '
                  f'<span class="muted">{len(group)}</span></h3>')
        ev.extend(fact_card(f) for f in group)

    present = {f["metric"] for f in live}
    missing_metrics = [METRIC_LABEL[m] for m in ALL_METRICS if m not in present]
    nd = NOT_DISCLOSED_ALWAYS + missing_metrics
    scored_n = c["eligible_fact_count"]
    unscored_n = len(facts) - sum(1 for f in facts if scores(f))

    jc_facts = [f for f in live if is_judgment_call(f)]
    jc_callout = ""
    if jc_facts:
        items = "".join(
            f'<li>{esc(METRIC_LABEL.get(f["metric"], f["metric"]))} at '
            f'<span class="mono">{esc(f["site"])}</span>: '
            f'{esc((f.get("notes") or "").split(". ", 1)[0].replace("Judgment call: ", ""))}. '
            f'<a href="#f-{esc(f["id"])}">see the evidence</a>.</li>'
            for f in jc_facts
        )
        jc_callout = (
            '<div class="note jcnote"><strong>A judgment call affects this score.</strong> '
            'One or more facts below rest on a classification we made deliberately and that a '
            f'reasonable person could dispute:<ul>{items}</ul></div>'
        )

    unscored_line = (f' {unscored_n} more '
                     f'{"fact is" if unscored_n == 1 else "facts are"} on record but do not score.'
                     if unscored_n else "")

    body = f"""
<p class="crumb"><a href="../index.html">&larr; All labs</a></p>
<div class="scorehead">
  <div>
    <h1>{esc(name)} <span class="slug mono">{esc(slug)}</span></h1>
    <p class="muted">Rank #{rank} of {total} &middot; as of {esc(asof)}</p>
  </div>
  <div class="scorebox">
    <span class="big">{c['score']:.1f}</span><span class="outof">/ 100</span>
  </div>
</div>
<p class="muted intro">The score is built only from facts confirmed against a public Tier A or B
source. {esc(name)} has {scored_n} such {"fact" if scored_n == 1 else "facts"} on record.{esc(unscored_line)}</p>
{jc_callout}

<h2>At a glance</h2>
{stat_tiles(slug, facts)}

<h2>How the score is built</h2>
<p class="muted section-sub">Five categories, each worth a share of the 100 points. Every row shows
what we found and links to the evidence behind it.</p>
<input type="checkbox" id="showmath" class="vh">
<p class="mathtoggle"><label for="showmath">Show the exact expression the scoring engine ran</label></p>
<div class="cats">{''.join(cat_html)}</div>

<h2>Facilities</h2>
<p class="muted section-sub">Every site we have a fact for, and how its status has moved over time.</p>
{fac_html}

<h2>Evidence</h2>
<p class="muted section-sub">All {len(facts)} facts on record for {esc(name)}, grouped by what they
measure. Nothing is ever removed from the ledger: facts that a later one replaced, or that fall
outside the scoring rules, stay here and are marked.</p>
{LEGEND}
{''.join(ev)}

<h2>Not publicly disclosed</h2>
<p class="muted section-sub">We record only what a public source states. These are unknown for
{esc(name)} and score zero:</p>
<ul class="nd-list">{''.join(f'<li>{esc(x)}</li>' for x in nd)}</ul>
"""
    desc = (f"{name} scores {c['score']:.1f} of 100 on the AI Infrastructure Index: owned power, "
            f"datacenters, chips and capital, each traced to a public source.")
    (SITE / "company" / f"{slug}.html").write_text(
        page(f"{name} – AI Infrastructure Index", body, 1, asof, desc=desc))


def build_doc(md_path, out_name, title, asof, current):
    md = (ROOT / md_path).read_text()
    body = '<div class="prose">' + md_to_html(md) + "</div>"
    (SITE / out_name).write_text(page(title, body, 0, asof, current=current))


def write_css():
    (SITE / "style.css").write_text(CSS)


def main():
    index = json.loads((ROOT / "index.json").read_text())
    ledger = load_ledger()
    asof = index["meta"]["generated_as_of"]
    SITE.mkdir(exist_ok=True)
    (SITE / "company").mkdir(exist_ok=True)
    write_css()
    build_home(index, ledger)
    total = len(index["companies"])
    for rank, c in enumerate(index["companies"], 1):
        build_company(c, ledger.get(c["company"], []), asof, rank, total)
    build_doc("METHODOLOGY.md", "methodology.html", "Methodology – AI Infrastructure Index", asof, "methodology")
    build_doc("CHANGELOG.md", "changelog.html", "Changelog – AI Infrastructure Index", asof, "changelog")
    (SITE / ".nojekyll").write_text("")
    print(f"built docs/ : home + {total} company pages + methodology + changelog")


CSS = """
:root{
 --bg:#fbfbf9; --panel:#fff; --panel-2:#f5f5f2;
 --fg:#15171c; --fg-soft:#3b4048; --muted:#6b7078;
 --line:#e4e4de; --line-soft:#eeeee9;
 --accent:#1a4f9c; --accent-bg:#eaf0fa;
 --fill:#2f6fbf; --fill-track:#e6e6e1;
 --radius:10px;
}
@media (prefers-color-scheme:dark){:root{
 --bg:#0f1114; --panel:#171a1f; --panel-2:#1c2027;
 --fg:#e9eaec; --fg-soft:#c3c7ce; --muted:#8d939d;
 --line:#272b33; --line-soft:#1f232a;
 --accent:#8ab4f8; --accent-bg:#182233;
 --fill:#5b8fd6; --fill-track:#262a31;
}}
*{box-sizing:border-box}
/* No smooth scrolling: evidence permalinks can sit 4,000px down the page and an
   animated jump there reads as the link not working. */
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);
 font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
 -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}
.skip{position:absolute;left:-9999px}
.skip:focus{left:1rem;top:.6rem;background:var(--panel);border:1px solid var(--line);
 padding:.4rem .7rem;border-radius:6px;z-index:5}
.vh{position:absolute;opacity:0;width:1px;height:1px;overflow:hidden}

header.site{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:.6rem;
 max-width:1000px;margin:0 auto;padding:1.3rem 1.3rem;border-bottom:1px solid var(--line)}
.wordmark{font-weight:650;letter-spacing:-.015em;color:var(--fg)}
header.site nav{display:flex;flex-wrap:wrap;gap:1.15rem}
header.site nav a{color:var(--muted);font-size:.92rem}
header.site nav a.current{color:var(--fg);font-weight:550}
main{max-width:1000px;margin:0 auto;padding:1.8rem 1.3rem 3.5rem}
footer{max-width:1000px;margin:0 auto;padding:1.6rem 1.3rem 3rem;border-top:1px solid var(--line);
 color:var(--muted);font-size:.9rem}
footer p{margin:.5rem 0}

h1{font-size:2rem;letter-spacing:-.025em;line-height:1.2;margin:.3rem 0 .9rem}
h2{font-size:1.2rem;letter-spacing:-.01em;margin:2.8rem 0 .5rem;padding-bottom:.35rem;
 border-bottom:1px solid var(--line)}
h3{font-size:1.02rem;letter-spacing:-.005em;margin:0}
p{margin:.6rem 0}
.lede{font-size:1.14rem;line-height:1.6;color:var(--fg-soft);max-width:68ch}
.section-sub{margin:.35rem 0 .9rem;max-width:74ch;font-size:.94rem}
.intro{max-width:74ch}
.muted{color:var(--muted)}
.small{font-size:.82em}
.mono,.mono *{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.9em}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.88em;
 overflow-wrap:anywhere}
.prose{max-width:76ch}
.prose h2{margin-top:2.4rem}

/* ---- tables ---- */
.scroll{overflow-x:auto;margin:.5rem 0 1.1rem;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:.94rem}
th,td{text-align:left;padding:.55rem .65rem;border-bottom:1px solid var(--line-soft);vertical-align:top}
thead th{border-bottom:1px solid var(--line);font-weight:600;color:var(--muted);font-size:.74rem;
 text-transform:uppercase;letter-spacing:.06em;white-space:nowrap}
.th-note{text-transform:none;letter-spacing:0;font-weight:400;font-size:.9em}
td.num,th.num,.num{text-align:right;font-variant-numeric:tabular-nums}
tbody tr:last-child td{border-bottom:none}
table.measure td:first-child{font-weight:550;white-space:nowrap}
table.measure td:nth-child(2){max-width:52ch}

.rank-table{min-width:600px}
.rank-table tbody tr:hover{background:var(--panel-2)}
.rank-table td{padding-top:.6rem;padding-bottom:.6rem}
.rank-table td.rank{color:var(--muted);width:2.6rem;font-variant-numeric:tabular-nums}
.rank-table td.lab a{font-weight:600;font-size:1.02rem;color:var(--fg)}
.rank-table td.lab a:hover{color:var(--accent)}
.rank-table td.score{min-width:190px;white-space:nowrap}
.rank-table tr.zero td.score .scoreval{color:var(--muted)}
.strong-area{font-size:.9rem}
.bar{display:inline-block;vertical-align:middle;width:120px;height:7px;background:var(--fill-track);
 border-radius:99px;overflow:hidden;margin-right:.6rem}
.bar .fill{display:block;height:100%;background:var(--fill);border-radius:99px}
.scoreval{font-weight:600;font-variant-numeric:tabular-nums}

.note{margin:1.2rem 0;padding:.75rem .95rem;background:var(--panel);border:1px solid var(--line);
 border-left:3px solid var(--accent);border-radius:var(--radius);font-size:.93rem;max-width:80ch}
.note p{margin:.3rem 0}

/* ---- company header ---- */
.crumb{margin:0 0 .5rem;font-size:.92rem}
.scorehead{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap}
.scorehead h1{margin-bottom:.2rem}
.slug{font-weight:400;color:var(--muted);font-size:.5em;vertical-align:.45em;letter-spacing:0}
.scorebox{display:flex;align-items:baseline;gap:.25rem;padding:.1rem 0}
.scorebox .big{font-size:2.8rem;line-height:1;font-weight:650;letter-spacing:-.03em;
 font-variant-numeric:tabular-nums}
.scorebox .outof{color:var(--muted);font-size:1rem}

/* ---- tiles ---- */
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;margin:.7rem 0}
@media(max-width:760px){.tiles{grid-template-columns:repeat(2,1fr)}}
@media(max-width:430px){.tiles{grid-template-columns:1fr}}
.tile{border:1px solid var(--line);border-radius:var(--radius);padding:.85rem .95rem;background:var(--panel)}
.tile .tval{font-size:1.45rem;font-weight:620;letter-spacing:-.02em;font-variant-numeric:tabular-nums;
 line-height:1.25}
.tile .tlab{font-size:.82rem;color:var(--muted);margin-top:.2rem}
.tile .nd{font-size:1rem;font-weight:500;color:var(--muted)}
.tilenote{font-size:.88rem;margin:.5rem 0 0;max-width:74ch}

/* ---- score breakdown ---- */
.mathtoggle{margin:.2rem 0 1.2rem;font-size:.9rem}
.mathtoggle label{display:inline-flex;align-items:center;gap:.5rem;cursor:pointer;color:var(--muted);
 border:1px solid var(--line);border-radius:99px;padding:.25rem .8rem;background:var(--panel)}
.mathtoggle label:hover{color:var(--fg);border-color:var(--muted)}
.mathtoggle label::before{content:"";width:.55rem;height:.55rem;border-radius:99px;
 background:var(--fill-track);border:1px solid var(--line)}
#showmath:checked ~ .mathtoggle label{color:var(--fg)}
#showmath:checked ~ .mathtoggle label::before{background:var(--fill);border-color:var(--fill)}
#showmath:not(:checked) ~ .cats tr.detail{display:none}
#showmath:focus-visible ~ .mathtoggle label{outline:2px solid var(--accent);outline-offset:2px}

.catblock{margin:1.6rem 0}
.cathead{display:flex;justify-content:space-between;align-items:baseline;gap:.75rem;flex-wrap:wrap;
 border-bottom:1px solid var(--line);padding-bottom:.3rem}
.catpts{font-size:.85rem;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap;
 display:inline-flex;align-items:center;gap:.55rem}
.minibar{display:inline-block;width:74px;height:6px;background:var(--fill-track);border-radius:99px;
 overflow:hidden}
.minibar .fill{display:block;height:100%;background:var(--fill);border-radius:99px}
.catdesc{margin:.45rem 0 .55rem;color:var(--muted);font-size:.93rem;max-width:74ch}
table.breakdown{table-layout:fixed;min-width:620px}
.c-comp{width:36%}.c-found{width:22%}.c-pts{width:14%}.c-ev{width:28%}
table.breakdown td.cname{font-weight:500}
table.breakdown td.hval{font-variant-numeric:tabular-nums;font-weight:550}
table.breakdown td.pts{font-weight:550}
table.breakdown tr.nil td.cname,table.breakdown tr.nil td.hval,table.breakdown tr.nil td.pts{
 color:var(--muted);font-weight:450}
table.breakdown tr:not(.detail) td{border-bottom:none;padding-bottom:.2rem}
table.breakdown tr.detail td{border-bottom:1px solid var(--line-soft);padding-top:.1rem;
 padding-bottom:.6rem;font-size:.82rem;color:var(--muted)}
table.breakdown tr.detail code{font-size:.95em;color:var(--fg-soft)}
table.breakdown tbody tr.detail:last-child td{border-bottom:none}
.decay{margin-top:.15rem}
a.ev{display:inline-block;margin:0 .3rem .2rem 0;padding:.02rem .38rem;border:1px solid var(--line);
 border-radius:5px;background:var(--panel);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
 font-size:.78rem;color:var(--accent);text-decoration:none}
a.ev:hover{background:var(--accent-bg);border-color:var(--accent);text-decoration:none}

/* ---- status chips ---- */
.st{display:inline-block;font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;
 padding:.06rem .38rem;border-radius:4px;border:1px solid var(--line);color:var(--muted);
 background:var(--panel-2);white-space:nowrap}
.st-operational{color:#245c24;background:#e7f0e7;border-color:#cfe3cf}
.st-under-construction{color:#7a5c1e;background:#fbf2e0;border-color:#ecdcbb}
.st-contracted{color:#2a4d86;background:#eef2fa;border-color:#d6e0f2}
@media (prefers-color-scheme:dark){
 .st-operational{color:#8fce8f;background:#1a2e1a;border-color:#274027}
 .st-under-construction{color:#e0b878;background:#33290f;border-color:#4d3d1a}
 .st-contracted{color:#9cc0f0;background:#1a2436;border-color:#26364f}}

/* ---- facilities ---- */
table.facilities{min-width:640px}
.c-site{width:24%}
td.sitecell{padding-top:.7rem}
td.steps{padding:.45rem .65rem}
a.step{display:grid;grid-template-columns:10.7rem 9.5rem minmax(0,1fr) 6rem;align-items:baseline;
 gap:.6rem;padding:.3rem .45rem;border-radius:6px;color:var(--fg);text-decoration:none;
 font-size:.92rem}
a.step:hover{background:var(--panel-2);text-decoration:none}
a.step .smetric{color:var(--muted);font-size:.84rem}
a.step .sval{font-variant-numeric:tabular-nums}
a.step .sdate{color:var(--muted);font-size:.8rem;text-align:right;font-variant-numeric:tabular-nums}

/* ---- evidence ---- */
.evgroup{margin:1.9rem 0 .5rem;font-size:.78rem;text-transform:uppercase;letter-spacing:.07em;
 color:var(--muted);font-weight:600}
.evgroup .muted{font-weight:400}
.fact{border:1px solid var(--line);border-radius:var(--radius);padding:.85rem .95rem;margin:.6rem 0;
 background:var(--panel);scroll-margin-top:1rem}
.fact.unscored{background:transparent;border-style:dashed}
.fact:target{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.fact .fhead{display:flex;flex-wrap:wrap;gap:.45rem;align-items:baseline}
.fact .val{font-weight:620;font-variant-numeric:tabular-nums}
.fact .fmetric{font-size:.86rem;color:var(--fg-soft)}
.fact blockquote{margin:.55rem 0;padding-left:.85rem;border-left:2px solid var(--line);
 color:var(--fg-soft);font-style:italic;max-width:84ch}
.fact .fmeta{font-size:.85rem;display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;
 color:var(--muted)}
.fact .permalink{color:var(--muted)}
.fact .notes{font-size:.86rem;margin:.45rem 0 0;max-width:84ch}
.legend{font-size:.85rem;margin:.4rem 0 1rem;line-height:2.1}
.badge{font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;padding:.08rem .4rem;
 border-radius:4px;border:1px solid var(--line);white-space:nowrap}
.badge.tier-a,.badge.ok{background:#e7f0e7;color:#245c24;border-color:#cfe3cf}
.badge.tier-b{background:#eef2fa;color:#2a4d86;border-color:#d6e0f2}
.badge.tier-c,.badge.tier-d{background:#f5f0e6;color:#7a5c1e;border-color:#e8ddc4}
.badge.no{background:#f6eaea;color:#8a3232;border-color:#eccccc}
.badge.warn{background:#fbf2e0;color:#8a5a1e;border-color:#ecdcbb}
.badge.off{background:var(--panel-2);color:var(--muted)}
@media (prefers-color-scheme:dark){
 .badge.tier-a,.badge.ok{background:#1a2e1a;color:#8fce8f;border-color:#274027}
 .badge.tier-b{background:#1a2436;color:#9cc0f0;border-color:#26364f}
 .badge.tier-c,.badge.tier-d{background:#332b18;color:#d9c088;border-color:#4a3e22}
 .badge.no{background:#331a1a;color:#e29a9a;border-color:#4d2626}
 .badge.warn{background:#33290f;color:#e0b878;border-color:#4d3d1a}}
.jcnote{border-left-color:#c98a2e}
.jcnote ul{margin:.45rem 0 0;padding-left:1.1rem}
.jcnote li{margin:.25rem 0}

ul.nd-list{columns:2;max-width:44rem;color:var(--muted);font-size:.94rem}
@media(max-width:560px){ul.nd-list{columns:1}}
blockquote{margin:.9rem 0;padding:.5rem .95rem;border-left:3px solid var(--line);color:var(--muted)}
pre{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:.85rem;
 overflow-x:auto}
pre code{font-size:.85rem}
ul li{margin:.2rem 0}

@media(max-width:560px){
 h1{font-size:1.65rem}
 .scorebox .big{font-size:2.2rem}
 main{padding:1.3rem 1rem 3rem}
 header.site,footer{padding-left:1rem;padding-right:1rem}
}
"""


if __name__ == "__main__":
    main()
