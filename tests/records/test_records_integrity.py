"""The one live check: the records hold."""

import os
from pathlib import Path

from ontology import design_record
from tests.records.check import building_pr, check_all, merged_prs
from tests.test_citations import addresses

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO
PRINCIPLES = {
    n
    for n, _, _ in design_record.principles(
        design_record.parse(design_record.appendices(ROOT))
    )
}


def test_the_backlog_records_hold():
    sections = addresses(ROOT / "DESIGN.md")
    violations = check_all(
        ROOT,
        sections,
        principles=PRINCIPLES,
        merged=merged_prs(ROOT),
        building=building_pr(os.environ.get("GITHUB_REF")),
    )
    assert violations == [], "\n".join(str(v) for v in violations)


def test_the_merge_history_reads_a_pull_request_this_repo_merged():
    # An empty set passes every `awaiting` silently, so pin one known merge.
    assert 287 in merged_prs(ROOT)
