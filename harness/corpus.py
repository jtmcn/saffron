"""A corpus of fixtures, and the one number a pass reports.

`lens_scoring` answers a question about one run and one defect. This composes
it across fixtures, because a prompt change cannot be read through one
fixture's noise (`docs/evidence/2026-09-08-lens-scoring-second-pass.md`: the
per-defect scores moved by a third between two passes that changed nothing
relevant, while the blocker count stayed identical).
"""

from __future__ import annotations

from pathlib import Path

from harness.lens_scoring import Fixture, load_fixture


def load_corpus(root: Path) -> list[Fixture]:
    """Every fixture under `root`, ordered by spec id.

    A directory declares itself a fixture by holding a `fixture.toml`; a
    README or a stray export beside them is not one. Ordered so a pass's
    fixtures, its output files and its table all agree without a caller
    sorting three times.
    """
    found = [
        load_fixture(child)
        for child in sorted(root.iterdir())
        if child.is_dir() and (child / "fixture.toml").is_file()
    ]
    return sorted(found, key=lambda fixture: fixture.spec_id)
