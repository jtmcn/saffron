"""This repo's own queue, checked the way `saffron queue` refuses a spec, before
a cell spends anything. Only the refusals that need neither the ledger nor
GitHub: those move with state, and these are facts about the text, so CI can
hold them on every pull request that adds or edits a spec."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from saffron.intake import discover_specs
from saffron.repos.mirror import retirement_markers
from saffron.repos.policy import load_policy
from saffron.scheduler import (
    _dangling_marker_refusals,
    _retired_ids,
    _unmatched_criterion_path,
    protected_touch_refusal,
    retirement_refusal,
)

REPO = Path(__file__).resolve().parents[1]
SPECS = REPO / ".saffron" / "specs"
QUEUED, UNPARSED = discover_specs(SPECS)


def _markers() -> list[tuple[str, str]]:
    # At HEAD, as production reads them at `base_sha`: a marker only in the
    # working tree has not reached anything a cell would be cut from.
    head = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return retirement_markers(REPO, head)


def _known_ids() -> frozenset[str]:
    retired, _failures = _retired_ids(SPECS)
    return frozenset(d.spec.id for d in QUEUED) | retired


def test_every_queued_spec_parses():
    assert [f"{f.path.name}: {f.reason}" for f in UNPARSED] == []


def test_no_two_specs_share_an_id():
    # The branch is `saffron/<id>`, so two specs with one id package onto one
    # branch and one pull request.
    retired, _failures = _retired_ids(SPECS)
    ids = [d.spec.id for d in QUEUED]
    assert sorted({i for i in ids if ids.count(i) > 1}) == []
    assert sorted(set(ids) & retired) == []


@pytest.mark.parametrize("queued", QUEUED, ids=lambda d: d.path.name)
def test_no_queued_spec_is_refused_on_its_own_text(queued):
    spec = queued.spec
    policy, _sha = load_policy(REPO)
    reasons = [
        protected_touch_refusal(spec.touches, policy.protected, spec.forbidden),
        retirement_refusal(spec, _markers()),
    ]
    if (path := _unmatched_criterion_path(spec)) is not None:
        reasons.append(
            f"acceptance criteria name {path!r}, which no touches pattern matches"
        )
    known = _known_ids()
    reasons += [
        f"depends_on {dep}, which no spec here or in done/ declares"
        for dep in spec.depends_on
        if dep not in known
    ]
    assert [r for r in reasons if r is not None] == []


def test_every_retired_by_marker_names_a_spec():
    assert [r.reason for r in _dangling_marker_refusals(_markers(), _known_ids())] == []
