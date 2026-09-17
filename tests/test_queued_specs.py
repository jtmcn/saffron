"""This repo's own queue, checked the way `saffron queue` refuses a spec, before
a cell spends anything. Only the refusals that need neither the ledger nor
GitHub: those move with state, and these are facts about the text, so CI can
hold them on every pull request that adds or edits a spec."""

from __future__ import annotations

import re
import subprocess
import sys
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
RETIRED, STOPPED = _retired_ids(SPECS)


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
    return frozenset(d.spec.id for d in QUEUED) | RETIRED


def test_every_queued_spec_parses():
    assert [f"{f.path.name}: {f.reason}" for f in UNPARSED] == []


def test_every_retired_spec_still_parses():
    # A `done/` spec that stops parsing credits no dependency, so `saffron
    # queue` refuses every child that names it (`_retired_ids`).
    assert [f"{f.path.name}: {f.reason}" for f in STOPPED] == []


def test_no_two_specs_share_an_id():
    # The branch is `saffron/<id>`, so two specs with one id package onto one
    # branch and one pull request.
    ids = [d.spec.id for d in QUEUED]
    assert sorted({i for i in ids if ids.count(i) > 1}) == []
    assert sorted(set(ids) & RETIRED) == []


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


@pytest.fixture(scope="module")
def collected() -> frozenset[str]:
    # The flags `.saffron/gates/tests` collects with, so a witness resolves here
    # as `criteria` would see it.
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--collect-only"]
        + ["-p", "no:cacheprovider"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    return frozenset(line for line in proc.stdout.splitlines() if "::" in line)


@pytest.mark.parametrize("queued", QUEUED, ids=lambda d: d.path.name)
def test_every_preserves_witness_names_a_test_the_suite_collects(queued, collected):
    # By collection, not by name: a real test in the wrong file or class is a
    # witness `criteria` reports as `witness-not-collected`.
    missing = [
        c.witness
        for c in queued.spec.acceptance
        if c.preserves and c.witness not in collected
    ]
    assert missing == []


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True
    ).stdout


_WITNESS_LINE = r"^[[:space:]-]*(witness|preserves):"


def _authored_at(spec_path: Path) -> str | None:
    """The commit that last changed this spec's witnesses, or `None` while such
    a change is uncommitted — then the working tree is the authoring state.

    Witness lines only: the spec loop edits a spec after its cell merged, and
    a prose fix then must not re-read a witness that cell wrote."""
    rel = spec_path.relative_to(REPO).as_posix()
    pickaxe = f"-G{_WITNESS_LINE}"
    untracked = not _git("ls-files", "--", rel).strip()
    if untracked or _git("diff", "HEAD", "--name-only", pickaxe, "--", rel).strip():
        return None
    return _git("log", "-1", "--format=%H", pickaxe, "--", rel).strip() or None


def _defined_at(witness: str, sha: str | None) -> bool:
    # A grep, not a collection: a checkout per spec costs too much, and for
    # absence it is the stricter reading — any `def name` in the file counts.
    path, _, rest = witness.partition("::")
    name = re.escape(rest.split("[")[0].rsplit("::", 1)[-1])
    if sha is None:
        file = REPO / path
        pattern = rf"^\s*(async\s+)?def\s+{name}\s*\("
        return file.is_file() and re.search(pattern, file.read_text(), re.M) is not None
    # POSIX ERE: `git grep -E` reads `\s` as a literal `s`, so every lookup missed.
    ere = rf"^[[:space:]]*(async[[:space:]]+)?def[[:space:]]+{name}[[:space:]]*\("
    grep = subprocess.run(
        ["git", "-C", str(REPO), "grep", "-q", "-E", ere, sha, "--", path],
        capture_output=True,
        text=True,
    )
    assert grep.returncode in (0, 1), grep.stderr
    return grep.returncode == 0


def test_a_committed_tree_lookup_finds_a_test_that_is_there():
    # Absence is what the check wants, so a lookup that never matches passes it
    # silently; the first draft's `\s` in `git grep -E` did exactly that.
    here = "tests/test_queued_specs.py::test_every_queued_spec_parses"
    assert _defined_at(here, "HEAD")
    assert not _defined_at(here + "_not", "HEAD")


def test_a_committed_spec_is_read_at_a_commit_not_the_working_tree():
    # A `None` here sends every spec to the working tree, which a cell's
    # witnesses have not reached yet, so the check would pass unread.
    done = sorted((SPECS / "done").glob("SA-*.md"))[-1]
    assert _authored_at(done)


def test_the_checkout_has_the_history_the_witness_check_reads():
    # A shallow clone makes every spec's last edit the one commit it has, so a
    # cell's merged witness would read as present at authoring time.
    assert _git("rev-parse", "--is-shallow-repository").strip() == "false"


@pytest.mark.parametrize("queued", QUEUED, ids=lambda d: d.path.name)
def test_no_witness_that_claims_a_change_exists_where_the_spec_was_written(queued):
    # At the spec's own commit, not HEAD: the cell that implements it writes the
    # witness, and HEAD holds it from then until the spec retires to `done/`.
    sha = _authored_at(queued.path)
    present = [
        c.witness
        for c in queued.spec.acceptance
        if not c.preserves and _defined_at(c.witness, sha)
    ]
    assert present == []


def test_every_retired_by_marker_names_a_spec():
    refusals = _dangling_marker_refusals(
        _markers(), _known_ids(), unreadable=len(UNPARSED) + len(STOPPED)
    )
    assert [r.reason for r in refusals] == []
