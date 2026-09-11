"""The gate suite, through its interface: an in-memory tree stands in for a cell.

The order rules each get a named test, because each exists for a defect: an
order that is only a list is an order the next edit can reshuffle (item 78).
"""

import contextlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from saffron.cell.runtime import Completed
from saffron.gates.suite import GateSuite
from saffron.repos.policy import GateDeclaration, Policy

FAIL = {"file": "a.py", "code": "E501", "message": "too long"}


class _Tree:
    """The in-memory adapter: each gate answers from a table, the worktree is
    two lists, and every read the suite makes is recorded in order."""

    def __init__(self, answers=None, *, changed=(), dirty=(), patch=""):
        self.answers = answers or {}
        self.changed = list(changed)
        self.dirty = list(dirty)
        self._patch = patch
        self.calls: list[str] = []
        self.cwd = Path("/work")

    @property
    def executor(self):
        return self

    def run(self, argv, cwd, timeout_s):
        name = Path(argv[0]).name
        self.calls.append(f"run {name}")
        answer = self.answers.get(name, {"status": "pass", "tool": f"{name} 1.0"})
        if answer is None:  # a gate that broke: no contract on stdout
            return Completed(1, "", "boom")
        payload = {"gate": name, **answer}
        return Completed(1 if payload.get("failures") else 0, json.dumps(payload), "")

    def changed_files(self, base):
        return list(self.changed)

    def patch(self, base):
        return self._patch

    def dirty_paths(self):
        self.calls.append("dirty_paths")
        return list(self.dirty)

    @contextlib.contextmanager
    def reverted(self, base, paths):
        yield

    @contextlib.contextmanager
    def mutated(self, mutant):
        yield "no tree here"


@dataclass(frozen=True)
class _Spec:
    risk: str = "standard"
    touches: list[str] = field(default_factory=lambda: ["src/**", "infra/**"])
    forbidden: list[str] = field(default_factory=list)
    acceptance: list = field(default_factory=list)
    spec_type: str = "feature"


def _suite(gates=("lint", "tests"), *, policy=None, spec=None):
    return GateSuite(
        gates={name: Path(f"/gates/.saffron/gates/{name}") for name in gates},
        spec=spec or _Spec(),
        policy=policy or Policy(gates={name: GateDeclaration() for name in gates}),
        diff_base="base",
    )


def _lint(*failures):
    # The same `tool` `_Tree` reports by default: a different one is drift, and
    # drift would pass every comparison test below for the wrong reason.
    return {
        "lint": {
            "status": "fail" if failures else "pass",
            "tool": "lint 1.0",
            "failures": list(failures),
        }
    }


def test_the_core_gates_run_around_the_declared_ones_in_a_fixed_order():
    run = _suite().baseline(_Tree())
    assert [r.gate for r in run.results] == [
        "scope",
        "integrity",
        "size",
        "lint",
        "tests",
        "witness",
        "revert",
        "committed",
        "census",
        "criteria",
    ]


def test_witness_follows_tests_whatever_order_the_repo_declares_them_in():
    run = _suite(("tests", "lint")).baseline(_Tree())
    assert [r.gate for r in run.results][3:6] == ["tests", "witness", "lint"]


def test_committed_reads_the_tree_only_after_every_declared_gate_has_run():
    """An artifact a gate writes (`.coverage`, a build dir) must be dirty at
    baseline and head alike, or `committed` charges it to the task with nothing
    on the other side to cancel it (items 14, 78)."""
    suite = _suite()
    base_tree, head_tree = _Tree(), _Tree()
    suite.against(head_tree, suite.baseline(base_tree))
    assert base_tree.calls == ["run lint", "run tests", "dirty_paths"]
    assert head_tree.calls == ["run lint", "run tests", "dirty_paths"]


def test_an_elevate_on_path_elevates_the_tier_and_blocks_on_size_and_witness():
    policy = Policy(
        gates={"lint": GateDeclaration(), "tests": GateDeclaration()},
        elevate_on=["infra/**"],
    )
    run = _suite(policy=policy).baseline(_Tree(changed=["infra/deploy.tf"]))
    assert run.effective_risk == "elevated"
    assert run.advisory_gates == frozenset()


def test_at_standard_size_and_witness_are_advisory():
    run = _suite().baseline(_Tree(changed=["src/a.py"]))
    assert run.effective_risk == "standard"
    assert run.advisory_gates == {"size", "witness"}


def test_a_gate_declared_non_blocking_is_advisory_even_when_elevated():
    policy = Policy(
        gates={"lint": GateDeclaration(blocking=False), "tests": GateDeclaration()}
    )
    run = _suite(policy=policy, spec=_Spec(risk="elevated")).baseline(_Tree())
    assert run.advisory_gates == {"lint"}


def test_a_baseline_with_an_errored_gate_says_which():
    run = _suite().baseline(_Tree({"lint": None}))
    assert run.aborted == ["lint"]


def test_an_errored_gate_aborts_before_drift_is_asked():
    """`error` ≠ `fail`: the gate broke, and nothing downstream of it is
    trusted enough to report — not even that another gate stopped running."""
    suite = _suite()
    baseline = suite.baseline(_Tree())
    comparison = suite.against(
        _Tree({"lint": None, "tests": {"status": "skip"}}), baseline
    )
    assert comparison.aborted == ("lint",)
    assert comparison.drift == ()
    assert comparison.new_failures == ()


def test_a_gate_that_stopped_running_is_drift_not_green():
    suite = _suite()
    baseline = suite.baseline(_Tree())
    comparison = suite.against(_Tree({"tests": {"status": "skip"}}), baseline)
    assert comparison.aborted == ()
    assert comparison.drift == ("tests: pass at baseline, skip at head",)
    assert comparison.new_failures == ()


def test_one_baseline_failure_cancels_one_head_failure_not_all_of_them():
    suite = _suite()
    baseline = suite.baseline(_Tree(_lint(FAIL)))
    comparison = suite.against(_Tree(_lint(FAIL, FAIL)), baseline)
    assert [(n.gate, n.failure.file) for n in comparison.new_failures] == [
        ("lint", "a.py")
    ]


def test_an_advisory_gates_failure_is_reported_but_blocks_nothing():
    policy = Policy(
        gates={"lint": GateDeclaration(blocking=False), "tests": GateDeclaration()}
    )
    suite = _suite(policy=policy)
    comparison = suite.against(_Tree(_lint(FAIL)), suite.baseline(_Tree()))
    assert comparison.drift == ()
    assert comparison.new_failures == ()
    assert [r.status for r in comparison.run.results if r.gate == "lint"] == ["fail"]


def test_the_head_runs_tier_decides_what_blocks_not_the_baselines():
    """The baseline's diff is empty, so it never elevates; a head that crosses
    `elevate_on` must block on `size` even though the baseline called it
    advisory (§5.6)."""
    policy = Policy(
        gates={"lint": GateDeclaration(), "tests": GateDeclaration()},
        elevate_on=["infra/**"],
    )
    suite = _suite(policy=policy)
    oversized = "".join(
        [
            "diff --git a/infra/x.tf b/infra/x.tf\n",
            "--- a/infra/x.tf\n+++ b/infra/x.tf\n@@ -0,0 +1,601 @@\n",
            "+x\n" * 601,
        ]
    )
    baseline = suite.baseline(_Tree())
    comparison = suite.against(_Tree(changed=["infra/x.tf"], patch=oversized), baseline)
    assert "size" in baseline.advisory_gates
    assert [n.gate for n in comparison.new_failures] == ["size"]


def test_a_tree_left_dirty_at_head_is_a_blocking_new_failure():
    suite = _suite()
    comparison = suite.against(_Tree(dirty=["a.py"]), suite.baseline(_Tree()))
    assert [(n.gate, n.failure.file) for n in comparison.new_failures] == [
        ("committed", "a.py")
    ]
