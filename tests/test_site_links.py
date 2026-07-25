"""Every internal link in the generated site must resolve.

The site is generated into two directory depths (docs/ and docs/company/), which
is exactly where relative hrefs go wrong: an evidence link written as
"company/openai.html#f-..." works from the home page and 404s from a company
page. That shipped once. These tests walk the real generated HTML and fail if any
relative href points at a file that does not exist, or at a fragment that no
element on the target page carries.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_site  # noqa: E402

HREF = re.compile(r'href="([^"]+)"')
ID = re.compile(r'id="([^"]+)"')


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    (out / "company").mkdir()
    old = build_site.SITE
    build_site.SITE = out
    try:
        build_site.main()
    finally:
        build_site.SITE = old
    return out


def html_files(site):
    return sorted(site.rglob("*.html"))


def test_site_builds(site):
    names = {p.relative_to(site).as_posix() for p in html_files(site)}
    assert "index.html" in names
    assert "methodology.html" in names
    assert "changelog.html" in names
    assert sum(1 for n in names if n.startswith("company/")) >= 8


def test_internal_links_resolve(site):
    ids = {p: set(ID.findall(p.read_text())) for p in html_files(site)}
    broken = []
    for path in html_files(site):
        for href in HREF.findall(path.read_text()):
            if href.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            target, _, frag = href.partition("#")
            page = path if not target else (path.parent / target).resolve()
            rel = path.relative_to(site).as_posix()
            if not page.exists():
                broken.append(f"{rel} -> {href} (no such file)")
                continue
            if frag and frag not in ids.get(page, set()):
                broken.append(f"{rel} -> {href} (no element with that id)")
    assert not broken, "broken internal links:\n" + "\n".join(broken)


def test_evidence_pills_are_same_page_anchors(site):
    """Score-breakdown evidence chips must never carry a path component."""
    bad = []
    for path in sorted((site / "company").glob("*.html")):
        for href in re.findall(r'<a class="ev" href="([^"]+)"', path.read_text()):
            if not href.startswith("#f-"):
                bad.append(f"{path.name}: {href}")
    assert not bad, "evidence pills must be bare '#f-...' fragments: " + ", ".join(bad)


def test_tiles_agree_with_the_score(site):
    """A lab whose silicon component scores zero must not be shown as designing
    its own chips. The tiles and the breakdown read the same eligibility rule."""
    import json

    index = json.loads((build_site.ROOT / "index.json").read_text())
    ledger = build_site.load_ledger()
    for c in index["companies"]:
        facts = ledger.get(c["company"], [])
        tiles = build_site.stat_tiles(c["company"], facts)
        silicon_tile_yes = ">yes<" in tiles.split("Designs its own chips")[0][-160:]
        scored = c["categories"]["compute_ownership"]["components"]["custom_silicon_programs"]
        assert silicon_tile_yes == (scored["band_points"] > 0), (
            f'{c["company"]}: "designs its own chips" tile disagrees with the score'
        )
