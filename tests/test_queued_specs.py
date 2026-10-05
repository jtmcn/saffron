"""This repo's own queue, checked the way `saffron queue` refuses a spec, before
a cell spends anything. Only the refusals that need neither the ledger nor
GitHub: those move with state, and these are facts about the text, so CI can
hold them on every pull request that adds or edits a spec."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from saffron.intake import DiscoveredSpec, discover_specs
from saffron.repos.mirror import retirement_markers
from saffron.repos.policy import load_policy
from saffron.scheduler import (
    _dangling_marker_refusals,
    _retired_ids,
    _unmatched_criterion_path,
    protected_touch_refusal,
    retirement_refusal,
)
from tests.test_scheduler import _write

REPO = Path(__file__).resolve().parents[1]
SPECS = REPO / ".saffron" / "specs"
QUEUED, UNPARSED = discover_specs(SPECS)
RETIRED, STOPPED = _retired_ids(SPECS)


@dataclass(frozen=True)
class _RetiredCase:
    """A `done/` file's case, carried unparsed: the three per-spec tests
    below read nothing from it but its name."""

    path: Path


def _cases(directory: Path) -> list[DiscoveredSpec | _RetiredCase]:
    """Every queued spec in `directory`, plus every file in its `done/`
    except `README.md`, named by filename either way.

    A retired file is never parsed here: a spec `done/` holds is no longer
    checked, so a file that stopped parsing still gets a case rather than
    vanishing from the parametrization.
    """
    queued, _ = discover_specs(directory)
    done = directory / "done"
    retired = sorted(done.glob("*.md")) if done.is_dir() else []
    return [*queued, *(_RetiredCase(p) for p in retired if p.name != "README.md")]


CASES = _cases(SPECS)


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


@pytest.mark.parametrize("queued", CASES, ids=lambda d: d.path.name)
def test_no_queued_spec_is_refused_on_its_own_text(queued):
    if not isinstance(queued, DiscoveredSpec):
        return  # retired to done/: no longer queued, so nothing here applies
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


def test_a_retired_case_checks_nothing_and_a_queued_one_is_still_checked(
    tmp_path, monkeypatch
):
    directory = tmp_path / "specs"
    (directory / "done").mkdir(parents=True)
    (directory / "SA-8888.md").write_text(
        "---\n"
        "id: SA-8888\n"
        "title: t\n"
        "type: chore\n"
        "depends_on:\n"
        "  - SA-9999\n"
        "acceptance:\n"
        "  - claim: a\n"
        "    witness: tests/nowhere.py::test_absent\n"
        "    preserves: true\n"
        "  - claim: b\n"
        "    witness: tests/test_queued_specs.py::test_every_queued_spec_parses\n"
        "---\n"
        "body\n"
    )
    monkeypatch.setattr("tests.test_queued_specs._authored_at", lambda path: None)

    queued_case = _cases(directory)[0]
    with pytest.raises(AssertionError):
        test_no_queued_spec_is_refused_on_its_own_text(queued_case)
    with pytest.raises(AssertionError):
        test_every_preserves_witness_names_a_test_the_suite_collects(
            queued_case, frozenset()
        )
    with pytest.raises(AssertionError):
        test_no_witness_that_claims_a_change_exists_where_the_spec_was_written(
            queued_case
        )

    shutil.move(str(directory / "SA-8888.md"), directory / "done" / "SA-8888.md")
    retired_case = _cases(directory)[0]
    assert test_no_queued_spec_is_refused_on_its_own_text(retired_case) is None
    assert (
        test_every_preserves_witness_names_a_test_the_suite_collects(
            retired_case, frozenset()
        )
        is None
    )
    assert (
        test_no_witness_that_claims_a_change_exists_where_the_spec_was_written(
            retired_case
        )
        is None
    )


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


def test_retiring_a_spec_keeps_every_case_id(tmp_path, collected):
    directory = tmp_path / "specs"
    done = directory / "done"
    done.mkdir(parents=True)
    _write(directory, "SA-7001.md", id="SA-7001")
    _write(directory, "SA-7002.md", id="SA-7002")
    (done / "broken.md").write_text("no frontmatter here")
    (done / "README.md").write_text("docs")

    before = {c.path.name for c in _cases(directory)}
    shutil.move(str(directory / "SA-7001.md"), done / "SA-7001.md")
    after = {c.path.name for c in _cases(directory)}

    expected = {"SA-7001.md", "SA-7002.md", "broken.md"}
    assert before == expected
    assert after == expected
    assert "README.md" not in before
    assert "README.md" not in after

    tests = (
        "test_no_queued_spec_is_refused_on_its_own_text",
        "test_every_preserves_witness_names_a_test_the_suite_collects",
        "test_no_witness_that_claims_a_change_exists_where_the_spec_was_written",
    )
    for test in tests:
        for path in sorted((SPECS / "done").glob("SA-*.md")):
            node = f"tests/test_queued_specs.py::{test}[{path.name}]"
            assert node in collected


@pytest.mark.parametrize("queued", CASES, ids=lambda d: d.path.name)
def test_every_preserves_witness_names_a_test_the_suite_collects(queued, collected):
    if not isinstance(queued, DiscoveredSpec):
        return
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


@pytest.mark.parametrize("queued", CASES, ids=lambda d: d.path.name)
def test_no_witness_that_claims_a_change_exists_where_the_spec_was_written(queued):
    if not isinstance(queued, DiscoveredSpec):
        return
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
