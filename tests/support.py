"""Shared test helpers. Every test works on copies and temporary files; the committed
repository is never modified. All test data is synthetic data and an illustrative example."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "tools"))

import capacity_calc as C  # noqa: E402,F401
import validate as V  # noqa: E402,F401


class Sandbox:
    """A full copy of the repository (without .git and tests) in a temporary folder."""

    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "__pycache__", "tests"))

    def path(self, rel: str) -> Path:
        return self.root / rel

    def read(self, rel: str) -> str:
        return self.path(rel).read_text(encoding="utf-8")

    def write(self, rel: str, text: str) -> None:
        self.path(rel).parent.mkdir(parents=True, exist_ok=True)
        self.path(rel).write_text(text, encoding="utf-8")

    def replace(self, rel: str, old: str, new: str, count: int = 1) -> None:
        text = self.read(rel)
        assert old in text, old
        self.write(rel, text.replace(old, new, count))

    def append(self, rel: str, text: str) -> None:
        self.write(rel, self.read(rel) + text)

    def regenerate(self) -> None:
        C.run(self.root)

    def run(self, blocklist=None) -> dict[str, tuple[bool, str]]:
        res = V.validate(self.root, blocklist)
        return {c.split(" ", 1)[0]: (ok, note) for c, ok, note in res.rows}

    def close(self) -> None:
        self.tmp.cleanup()
