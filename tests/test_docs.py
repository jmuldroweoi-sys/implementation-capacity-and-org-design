"""Documentation regression tests (P6 readiness review, 2026-10-07).
Checks status and claim wording only; no calculation is involved."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from support import ROOT

PINNED_BY_R4 = {"docs/source-precedence.md", "data/synthetic/README.md"}


def markdown_files() -> list[Path]:
    out = []
    for path in sorted(ROOT.rglob("*.md")):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(("upstream/", ".git/")) or rel in PINNED_BY_R4:
            continue
        out.append(path)
    return out


class DocumentationTest(unittest.TestCase):
    def test_readme_opening_does_not_claim_cost_to_serve(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        opening = text.split("\n\n")[1]
        self.assertNotRegex(opening, r"and cost-to-serve modeling")
        self.assertIn("cost-to-serve is planned", opening)

    def test_no_stale_r4_status_in_documentation(self) -> None:
        stale = re.compile(r"R4 is not built|until R4 exists|Not built; fixtures only", re.IGNORECASE)
        hits = [p.relative_to(ROOT).as_posix() for p in markdown_files() if stale.search(p.read_text(encoding="utf-8"))]
        self.assertEqual(hits, [])

    def test_readme_names_all_four_repositories(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        fit = next(par for par in text.split("\n\n") if par.startswith("**How the"))
        for name in ("R1", "R2", "R3", "R4"):
            self.assertIn(name, fit)


if __name__ == "__main__":
    unittest.main()
