"""The one live check: the records hold. PR 1 points it at the good fixture;
the migration (PR 2) points it at the repository root and never back."""

from pathlib import Path

from records.check import check_all
from tests.test_citations import addresses

REPO = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "good"
ROOT = FIXTURE  # PR 2 flips this to REPO


def test_the_backlog_records_hold():
    sections, _ = addresses(ROOT / "DESIGN.md")
    violations = check_all(ROOT, sections)
    assert violations == [], "\n".join(str(v) for v in violations)
