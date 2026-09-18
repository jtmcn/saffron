from __future__ import annotations

import json
from pathlib import Path

from harness.register_scoring import Claim, claims_in

REPO = Path(__file__).resolve().parent.parent
SPREAD = REPO / "docs/evidence/passes/2026-09-11-lens-corpus-spread"


def _pass(root: Path, runs: dict[str, dict[int, list[dict]]]) -> Path:
    for fixture, by_run in runs.items():
        (root / fixture).mkdir(parents=True)
        for run, lenses in by_run.items():
            (root / fixture / f"run-{run}.json").write_text(json.dumps(lenses))
    return root


def test_a_claim_carries_its_fixture_run_and_lens(tmp_path):
    directory = _pass(
        tmp_path,
        {"SA-0001": {1: [{"lens": "correctness", "findings": [{"claim": "a claim"}]}]}},
    )
    assert claims_in(directory) == [Claim("SA-0001", 1, "correctness", "a claim")]


def test_a_lens_that_errored_contributes_no_claim(tmp_path):
    directory = _pass(
        tmp_path,
        {"SA-0001": {1: [{"lens": "contract", "error": "boom", "findings": None}]}},
    )
    assert claims_in(directory) == []


def test_a_finding_with_no_claim_is_skipped(tmp_path):
    directory = _pass(
        tmp_path, {"SA-0001": {1: [{"lens": "adequacy", "findings": [{"claim": ""}]}]}}
    )
    assert claims_in(directory) == []


def test_the_real_spread_pass_yields_every_claim_it_holds():
    """Pins the published corpus: 8 fixtures, 3 runs each."""
    claims = claims_in(SPREAD)
    assert len(claims) == 64
    assert {c.run for c in claims} == {1, 2, 3}
    assert len({c.fixture for c in claims}) == 8
