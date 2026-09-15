"""The one live check: the records hold."""

from pathlib import Path

from records.check import check_all
from tests.test_citations import addresses

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO


def test_the_backlog_records_hold():
    sections, _ = addresses(ROOT / "DESIGN.md")
    violations = check_all(ROOT, sections)
    assert violations == [], "\n".join(str(v) for v in violations)
