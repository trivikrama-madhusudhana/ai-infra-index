"""Golden determinism test for the scoring engine.

Points the engine at the frozen fixture ledger and asserts:
  1. two runs on the same input produce byte-identical output, and
  2. that output equals the committed golden file.

Regenerate the golden intentionally (after a rubric change) with:
    python tests/test_score_golden.py --update
"""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import score  # noqa: E402

FIXTURE_COMPANIES = ROOT / "tests" / "fixtures" / "companies"
GOLDEN = ROOT / "tests" / "fixtures" / "index.golden.json"
AS_OF = date(2026, 7, 20)


def _render():
    # Redirect the engine at the fixture ledger; config/* stay the real files.
    score.COMPANIES_DIR = FIXTURE_COMPANIES
    return score.dumps(score.build_index(AS_OF))


def test_deterministic_and_matches_golden():
    first = _render()
    second = _render()
    assert first == second, "engine is not deterministic: two runs differ"
    assert GOLDEN.exists(), "golden file missing; run: python tests/test_score_golden.py --update"
    assert first == GOLDEN.read_text(), (
        "output drifted from golden. If intentional (rubric change), "
        "regenerate: python tests/test_score_golden.py --update"
    )


if __name__ == "__main__":
    if "--update" in sys.argv:
        GOLDEN.write_text(_render())
        print(f"wrote {GOLDEN.relative_to(ROOT)}")
    else:
        test_deterministic_and_matches_golden()
        print("golden test passed")
