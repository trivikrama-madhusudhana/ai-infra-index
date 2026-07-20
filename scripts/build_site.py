#!/usr/bin/env python3
"""Generate the static site from index.json + the ledger. No framework, no build step.

    python scripts/build_site.py

Writes plain HTML/CSS into site/. Built for two readers at once: someone
non-technical who wants to know who is winning the physical AI buildout and why,
and someone technical who wants the exact math and the underlying evidence. Every
displayed number links to the fact that produced it.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
COMPANIES_DIR = ROOT / "data" / "companies"
REPO_URL = "https://github.com/trivikrama-madhusudhana/ai-infra-index"

SCORING = yaml.safe_load((ROOT / "config" / "scoring.v1.yaml").read_text())

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


def host_of(url: str) -> str:
    return url.split("://", 1)[-1].split("/", 1)[0].split("?", 1)[0].lower()


def load_tier_map() -> dict:
    cfg = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text())
    m = {}
    for tier, doms in cfg["tiers"].items():
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


def comp_metrics(cat_name, comp_name):
    c = SCORING["categories"][cat_name]["components"][comp_name]
    return c.get("metrics", [c.get("metric")])


def fmt_int(v):
    return f"{int(round(v)):,}"


def human_value(cat_name, comp_name, comp):
    """A value string a non-technical reader can read at a glance."""
    if comp["missing"]:
        return "none recorded"
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
        return "$" + fmt_int(val)
    if "gpu_count" in metrics:
        return f"{fmt_int(val)} chips"
    return fmt_int(val)


def fmt_num(v) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, float)):
        if v == int(v):
            return f"{int(v):,}"
        return f"{v:,.2f}"
    return esc(v)


def tier_badge(t: str) -> str:
    names = {"A": "primary / official source", "B": "reputable press or research", "C": "secondary, not scored"}
    return f'<span class="badge tier tier-{t.lower()}" title="Tier {t}: {names.get(t, "unknown")}">Tier {t}</span>'


def ver_badge(v: dict) -> str:
    if v.get("verified"):
        return '<span class="badge ok" title="A second pass re-opened the source and confirmed this number">verified</span>'
    return '<span class="badge no" title="Not yet confirmed against its source; shown but not scored">unverified</span>'


LEGEND = (
    '<p class="legend muted">'
    'Badges: <span class="badge tier tier-a">Tier A</span> primary source, '
    '<span class="badge tier tier-b">Tier B</span> reputable press, '
    '<span class="badge ok">verified</span> confirmed against its source, '
    '<span class="badge no">unverified</span> recorded but not scored.</p>'
)

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="{css}">
</head>
<body>
<header class="site">
  <a class="wordmark" href="{home}">AI Infrastructure Index</a>
  <nav>
    <a href="{methodology}">Methodology</a>
    <a href="{changelog}">Changelog</a>
    <a href="{repo}">Source</a>
  </nav>
</header>
<main>
{body}
</main>
<footer>
  <p>Every number links to a public source. Unknown means unknown. We never estimate.</p>
  <p class="muted">Scores come from a deterministic engine anyone can rerun: <code>python scripts/score.py --as-of {asof}</code>.</p>
</footer>
</body>
</html>
"""


def page(title, body, depth=0, asof=""):
    up = "../" * depth
    return PAGE.format(
        title=esc(title), body=body, css=up + "style.css", home=up + "index.html",
        methodology=up + "methodology.html", changelog=up + "changelog.html",
        repo=REPO_URL, asof=esc(asof),
    )


# ---------------------------------------------------------------------------
# Minimal markdown -> HTML (headings, tables, code fences, lists, blockquote,
# bold, inline code). Enough for METHODOLOGY.md and CHANGELOG.md.
# ---------------------------------------------------------------------------

def md_inline(s: str) -> str:
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
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
            buf = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                buf.append("<li>" + md_inline(lines[i].strip()[2:]) + "</li>")
                i += 1
            out.append("<ul>" + "".join(buf) + "</ul>")
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


def fact_link(company, fid):
    return f'<a href="company/{company}.html#f-{esc(fid)}">{esc(fid[-3:])}</a>'


def fact_link_local(fid):
    return f'<a href="#f-{esc(fid)}">evidence</a>'


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
        rows.append(
            f'<tr><td class="rank">{rank}</td>'
            f'<td class="lab"><a href="company/{esc(slug)}.html">{esc(slug)}</a></td>'
            f'<td class="score"><span class="bar"><span class="fill" style="width:{pct}%"></span></span>'
            f'<span class="scoreval">{c["score"]:.1f}</span></td>'
            f'<td>{c["eligible_fact_count"]}</td>'
            f'<td class="muted">{esc(top_label)}</td></tr>'
        )

    measure_rows = "".join(
        f'<tr><td>{esc(cat["label"])}</td><td>{esc(CAT_PLAIN.get(name, ""))}</td>'
        f'<td class="num">{round(cat["weight"] * 100)}%</td></tr>'
        for name, cat in SCORING["categories"].items()
    )

    body = f"""
<h1>The physical AI race, scored on public evidence</h1>
<p class="lede">Model benchmarks are everywhere. The megawatts are not. This index tracks the
infrastructure the frontier labs actually control, and every number on it traces to a source you
can open. Capacity is credited to whoever owns the site, so a lab that rents its compute scores
low here on purpose.</p>

<h2>How to read this</h2>
<p>Each lab gets a score from 0 to 100. It rewards infrastructure a lab actually owns and can
point to in public: power its datacenters draw today, sites it holds, chips it designs, deals it
has signed. Renting compute from someone else's cloud counts for little. Five things go into the
score:</p>
<div class="scroll"><table class="measure">
<thead><tr><th>What we measure</th><th>In plain terms</th><th>Weight</th></tr></thead>
<tbody>{measure_rows}</tbody>
</table></div>

<h2>The ranking</h2>
<div class="scroll">
<table class="rank-table">
<thead><tr><th>#</th><th>Lab</th><th>Score</th><th>Facts</th><th>Strongest area</th></tr></thead>
<tbody>{''.join(rows)}
</tbody>
</table>
</div>
<p class="note">Every number on this site links to a public source. Unknown means unknown. We never estimate.
A lab at 0 is not one with no infrastructure, it is one whose infrastructure is not yet documented
in public sources we will score.</p>
<p class="muted">Baseline as of {esc(asof)}, scoring version {index['meta']['scoring_version']}. The
<a href="methodology.html">methodology</a> has the full rubric and the command to reproduce every number.</p>
"""
    (SITE / "index.html").write_text(page("AI Infrastructure Index", body, 0, asof))


def stat_tiles(slug, facts):
    live = [f for f in facts if not f.get("superseded_by") and f["verification"]["verified"]]

    def s(metric, statuses):
        return sum(f["value"] for f in live if f["metric"] == metric and f["status"] in statuses
                   and isinstance(f["value"], (int, float)) and not isinstance(f["value"], bool))

    owned_op = s("power_capacity_mw", {"operational"})
    owned_uc = s("power_capacity_mw", {"under_construction"})
    owned_sites = len({f["site"] for f in live if f["metric"] == "owned_facility" and f["status"] in ("under_construction", "operational")})
    silicon = any(f["metric"] == "custom_silicon" for f in live)
    fleet = max([f["value"] for f in live if f["metric"] == "gpu_count" and isinstance(f["value"], (int, float))], default=0)
    capex = s("capex_announced_usd", {"announced", "contracted", "under_construction", "operational", "n/a"})
    partner = sum(f["value"] for f in live if f["metric"] == "cloud_partnership" and f["unit"] == "MW"
                  and isinstance(f["value"], (int, float)) and not isinstance(f["value"], bool))

    def tile(label, value, disclosed):
        v = value if disclosed else '<span class="nd">not disclosed</span>'
        return f'<div class="tile"><div class="tval">{v}</div><div class="tlab">{esc(label)}</div></div>'

    tiles = [
        tile("Owned power, operational", f"{fmt_int(owned_op)} MW", owned_op > 0),
        tile("Owned power, building", f"{fmt_int(owned_uc)} MW", owned_uc > 0),
        tile("Owned datacenter sites", str(owned_sites), owned_sites > 0),
        tile("Designs its own chips", "yes", silicon) if silicon else tile("Designs its own chips", "no", True),
        tile("Est. accelerators", f"{fmt_int(fleet)}", fleet > 0),
        tile("Announced capital", "$" + fmt_int(capex), capex > 0),
    ]
    note = ""
    if partner > 0:
        note = f'<p class="muted tilenote">Plus {fmt_int(partner)} MW of rented or partner-operated capacity, which is recorded but does not count as owned. See the cloud-partnership facts below.</p>'
    return '<div class="tiles">' + "".join(tiles) + "</div>" + note


def build_company(c, facts, asof):
    slug = c["company"]
    live = [f for f in facts if not f.get("superseded_by")]

    # ---- score breakdown, plain-language first, exact math underneath ----
    cat_html = []
    for cat_name in SCORING["categories"]:          # rubric order, not alphabetical
        cat = c["categories"][cat_name]
        comp_rows = []
        for comp_name in SCORING["categories"][cat_name]["components"]:
            comp = cat["components"][comp_name]
            links = " ".join(fact_link(slug, fid) for fid in comp["fact_ids"])
            facts_cell = links if links else '<span class="muted">none</span>'
            decay = f'<div class="muted small">discounted for age: {", ".join(x[-3:] for x in comp["decayed_fact_ids"])}</div>' if comp["decayed_fact_ids"] else ""
            comp_rows.append(
                f'<tr><td>{esc(comp["label"])}</td>'
                f'<td class="hval">{esc(human_value(cat_name, comp_name, comp))}</td>'
                f'<td class="num">{comp["band_points"]:g}</td>'
                f'<td class="facts">{facts_cell}</td></tr>'
                f'<tr class="detail"><td colspan="4"><code>{esc(comp["input_expression"])}</code> '
                f'&rarr; {comp["band_points"]:g} pts &times; weight {comp["weight"]:g} = {comp["weighted_points"]:g}{decay}</td></tr>'
            )
        cat_html.append(
            f'<div class="catblock"><div class="cathead"><h3>{esc(cat["label"])}</h3>'
            f'<span class="catpts">{cat["weighted_contribution"]:g} of {round(cat["weight"]*100)} points</span></div>'
            f'<p class="catdesc">{esc(CAT_PLAIN.get(cat_name, ""))}</p>'
            f'<div class="scroll"><table class="breakdown">'
            f'<thead><tr><th>Component</th><th>What we found</th><th>Points</th><th>Evidence</th></tr></thead>'
            f'<tbody>{"".join(comp_rows)}</tbody></table></div></div>'
        )

    # ---- facilities ----
    fac_facts = [f for f in live if f["metric"] in ("power_capacity_mw", "owned_facility", "cloud_partnership", "datacenter_site")]
    sites = {}
    for f in fac_facts:
        sites.setdefault(f["site"], []).append(f)
    fac_rows = []
    for site, fs in sorted(sites.items()):
        fs.sort(key=lambda f: f["as_of_date"])
        timeline = " &rarr; ".join(
            f'<a href="#f-{esc(f["id"])}">{esc(f["status"].replace("_", " "))} '
            f'{fmt_num(f["value"])}{"" if f["unit"] in ("boolean","text") else " "+esc(f["unit"])}</a>'
            for f in fs
        )
        fac_rows.append(f'<tr><td class="mono">{esc(site)}</td><td>{timeline}</td></tr>')
    fac_html = (
        f'<div class="scroll"><table><thead><tr><th>Site</th><th>Status over time</th></tr></thead>'
        f'<tbody>{"".join(fac_rows)}</tbody></table></div>'
        if fac_rows else '<p class="muted">No site-level facilities recorded yet.</p>'
    )

    # ---- evidence ----
    ev = []
    for f in sorted(live, key=lambda f: (f["metric"], f["site"])):
        src = f["source"]
        t = tier_for(src["url"])
        arch = f' &middot; <a href="{esc(src["archive_url"])}">archived copy</a>' if src.get("archive_url") else ""
        notes = f'<p class="notes muted">{esc(f["notes"])}</p>' if f.get("notes") else ""
        unit = "" if f["unit"] in ("boolean", "text") else " " + esc(f["unit"])
        ev.append(
            f'<article class="fact" id="f-{esc(f["id"])}">'
            f'<div class="fhead"><span class="metric">{esc(METRIC_LABEL.get(f["metric"], f["metric"]))}</span> '
            f'<span class="val">{fmt_num(f["value"])}{unit}</span> '
            f'<span class="status">{esc(f["status"].replace("_", " "))}</span> '
            f'<span class="muted">at {esc(f["site"])}, as of {esc(f["as_of_date"])}</span></div>'
            f'<blockquote>{esc(f["excerpt"])}</blockquote>'
            f'<div class="fmeta">{tier_badge(t)} {ver_badge(f["verification"])} '
            f'<span class="muted">{esc(src["publisher"])}, {esc(src["date_published"])}</span> &middot; '
            f'<a href="{esc(src["url"])}">source</a>{arch} '
            f'<span class="muted mono small">{esc(f["id"])}</span></div>{notes}</article>'
        )

    present = {f["metric"] for f in live}
    missing_metrics = [METRIC_LABEL[m] for m in ALL_METRICS if m not in present]
    nd = NOT_DISCLOSED_ALWAYS + missing_metrics
    verified_n = sum(1 for f in live if f["verification"]["verified"])

    body = f"""
<p class="crumb"><a href="index.html">&larr; all labs</a></p>
<h1>{esc(slug)}</h1>
<p class="scoreline"><span class="big">{c['score']:.1f}</span> <span class="muted">out of 100 &middot; as of {esc(asof)}</span></p>
<p class="muted">The score below is built only from facts confirmed against a public source. This lab has
{verified_n} such facts on record.</p>

<h2>At a glance</h2>
{stat_tiles(slug, facts)}

<h2>How the score is built</h2>
<p class="muted">Five categories, each worth a share of the 100 points. Every row shows what we
found and links to the evidence. The grey line under each row is the exact expression the scoring
engine evaluated, for anyone who wants to check the math.</p>
{''.join(cat_html)}

<h2>Facilities</h2>
<p class="muted">Every site we have a fact for, and how its status has moved over time.</p>
{fac_html}

<h2>Evidence</h2>
<p class="muted">All {len(live)} facts on record for {esc(slug)}. Unverified facts are shown for transparency but do not score.</p>
{LEGEND}
{''.join(ev)}

<h2>Not publicly disclosed</h2>
<p class="muted">We record only what a public source states. These are unknown for {esc(slug)} and score zero:</p>
<ul class="nd-list">{''.join(f'<li>{esc(x)}</li>' for x in nd)}</ul>
"""
    (SITE / "company" / f"{slug}.html").write_text(page(f"{slug} - AI Infrastructure Index", body, 1, asof))


def build_doc(md_path, out_name, title, asof):
    md = (ROOT / md_path).read_text()
    body = md_to_html(md)
    (SITE / out_name).write_text(page(title, body, 0, asof))


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
    for c in index["companies"]:
        build_company(c, ledger.get(c["company"], []), asof)
    build_doc("METHODOLOGY.md", "methodology.html", "Methodology - AI Infrastructure Index", asof)
    build_doc("CHANGELOG.md", "changelog.html", "Changelog - AI Infrastructure Index", asof)
    (SITE / ".nojekyll").write_text("")
    n = len(index["companies"])
    print(f"built site/ : home + {n} company pages + methodology + changelog")


CSS = """
:root{--bg:#fbfbfa;--fg:#1a1a1a;--muted:#6b6b6b;--line:#e3e3e0;--accent:#1f5199;--card:#fff;--fill:#2f6fbf;}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#e8e8e6;--muted:#9a9a97;--line:#2c2c2c;--accent:#7aa6e0;--card:#1c1c1c;--fill:#3b6ea5;}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);
 font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
header.site{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:.5rem;
 max-width:960px;margin:0 auto;padding:1.4rem 1.2rem;border-bottom:1px solid var(--line)}
.wordmark{font-weight:600;letter-spacing:-.01em;color:var(--fg)}
header.site nav a{margin-left:1.1rem;color:var(--muted);font-size:.92rem}
main{max-width:960px;margin:0 auto;padding:1.6rem 1.2rem 3rem}
footer{max-width:960px;margin:0 auto;padding:1.6rem 1.2rem 3rem;border-top:1px solid var(--line);color:var(--muted);font-size:.9rem}
h1{font-size:1.9rem;letter-spacing:-.02em;line-height:1.2;margin:.4rem 0 1rem}
h2{font-size:1.25rem;letter-spacing:-.01em;margin:2.4rem 0 .6rem;padding-bottom:.3rem;border-bottom:1px solid var(--line)}
h3{font-size:1.05rem;margin:0}
.lede{font-size:1.12rem;color:#333;max-width:70ch}
@media (prefers-color-scheme:dark){.lede{color:#cfcfcd}}
.muted{color:var(--muted)}
.small{font-size:.82em}
.mono,.mono *{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.86em}
.scroll{overflow-x:auto;margin:.4rem 0 1rem}
table{border-collapse:collapse;width:100%;font-size:.93rem}
th,td{text-align:left;padding:.5rem .6rem;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;color:var(--muted);font-size:.82rem;text-transform:uppercase;letter-spacing:.04em}
td.num,th.num,.num{text-align:right;font-variant-numeric:tabular-nums}
table.measure td:first-child{font-weight:500;white-space:nowrap}
.rank-table td.rank{color:var(--muted);width:2rem}
.rank-table td.lab a{font-weight:600;font-size:1.02rem}
.rank-table td.score{min-width:180px}
.bar{display:inline-block;vertical-align:middle;width:120px;height:8px;background:var(--line);border-radius:4px;overflow:hidden;margin-right:.5rem}
.bar .fill{display:block;height:100%;background:var(--fill)}
.scoreval{font-weight:600;font-variant-numeric:tabular-nums}
.note{margin:1.2rem 0;padding:.7rem .9rem;background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:2px;font-size:.94rem}
.scoreline{margin:.2rem 0 .4rem}
.scoreline .big{font-size:2.6rem;font-weight:600;letter-spacing:-.02em}
.crumb{margin:0 0 .4rem}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.7rem;margin:.6rem 0}
.tile{border:1px solid var(--line);border-radius:6px;padding:.8rem .9rem;background:var(--card)}
.tile .tval{font-size:1.5rem;font-weight:600;letter-spacing:-.01em;font-variant-numeric:tabular-nums}
.tile .tlab{font-size:.82rem;color:var(--muted);margin-top:.2rem}
.tile .nd{font-size:1rem;font-weight:500;color:var(--muted)}
.tilenote{font-size:.88rem;margin:.2rem 0 0}
.catblock{margin:1.2rem 0}
.cathead{display:flex;justify-content:space-between;align-items:baseline;gap:.5rem;border-bottom:1px solid var(--line);padding-bottom:.25rem}
.catpts{font-size:.85rem;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
.catdesc{margin:.4rem 0 .5rem;color:var(--muted)}
table.breakdown td.hval{font-variant-numeric:tabular-nums;font-weight:500}
table.breakdown tr.detail td{border-bottom:1px solid var(--line);padding-top:.15rem;font-size:.82rem;color:var(--muted)}
table.breakdown tr.detail code{font-size:.95em}
table.breakdown tr:not(.detail) td{border-bottom:none}
td.facts a{margin-right:.35rem;font-family:ui-monospace,monospace;font-size:.82em}
.fact{border:1px solid var(--line);border-radius:6px;padding:.8rem .9rem;margin:.7rem 0;background:var(--card)}
.fact .fhead{display:flex;flex-wrap:wrap;gap:.4rem;align-items:baseline}
.fact .metric{font-weight:600}
.fact .val{font-variant-numeric:tabular-nums}
.fact .status{font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);border:1px solid var(--line);border-radius:2px;padding:.02rem .3rem}
.fact blockquote{margin:.5rem 0;padding-left:.8rem;border-left:2px solid var(--line);color:#333;font-style:italic}
@media (prefers-color-scheme:dark){.fact blockquote{color:#cfcfcd}}
.fact .fmeta{font-size:.85rem;display:flex;flex-wrap:wrap;gap:.35rem;align-items:center}
.fact .notes{font-size:.85rem;margin:.4rem 0 0}
.legend{font-size:.85rem;margin:.3rem 0 .8rem}
.badge{font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;padding:.05rem .35rem;border-radius:2px;border:1px solid var(--line);white-space:nowrap}
.badge.tier-a{background:#e7f0e7;color:#245c24;border-color:#cfe3cf}
.badge.tier-b{background:#eef2fa;color:#2a4d86;border-color:#d6e0f2}
.badge.tier-c{background:#f5f0e6;color:#7a5c1e;border-color:#e8ddc4}
.badge.ok{background:#e7f0e7;color:#245c24;border-color:#cfe3cf}
.badge.no{background:#f6eaea;color:#8a3232;border-color:#eccccc}
@media (prefers-color-scheme:dark){
 .badge.tier-a,.badge.ok{background:#1a2e1a;color:#8fce8f;border-color:#274027}
 .badge.tier-b{background:#1a2436;color:#9cc0f0;border-color:#26364f}
 .badge.tier-c{background:#332b18;color:#d9c088;border-color:#4a3e22}
 .badge.no{background:#331a1a;color:#e29a9a;border-color:#4d2626}}
ul.nd-list{columns:2;max-width:40rem}
@media(max-width:560px){ul.nd-list{columns:1}}
blockquote{margin:.8rem 0;padding:.5rem .9rem;border-left:3px solid var(--line);color:var(--muted)}
pre{background:var(--card);border:1px solid var(--line);border-radius:4px;padding:.8rem;overflow-x:auto}
pre code{font-family:ui-monospace,monospace;font-size:.85rem}
code{font-family:ui-monospace,monospace;font-size:.9em}
"""


if __name__ == "__main__":
    main()
