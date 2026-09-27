"""`saffron.qualify` (backlog item b-792ab2, step 4): each layer's end-review
findings, anchored against its own diff, probed and decided into follow-up
groups and a leftover pool. `saffron.qualify` is imported inside each test
body, never at module scope. It does not exist at this spec's own tree base,
and a module-scope import would fail collection under `revert`.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from saffron import probe as probe_check
from saffron.agents.findings import Finding, Severity
from saffron.cell import session
from saffron.end_review import LayerReview
from saffron.gates.contract import GateResult
from saffron.intake import Mutant
from saffron.ledger import Ledger
from saffron.phases import review
from saffron.probe import Verdict
from saffron.record.memory import MemoryRecord

_EMAIL = "-c", "user.email=t@example.com", "-c", "user.name=Test"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *_EMAIL, "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _numbered(prefix: str, overrides: dict[int, str] | None = None) -> list[str]:
    lines = [f"{prefix}_l{i}" for i in range(1, 13)]
    for i, text in (overrides or {}).items():
        lines[i - 1] = text
    return lines


def _write(mirror: Path, path: str, lines: list[str]) -> None:
    full = mirror / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text("\n".join(lines) + "\n")


def _stack_mirror(tmp_path: Path, monkeypatch) -> tuple[Path, dict[str, str]]:
    """The git history the four commits in the spec's notes describe.

    `A` seeds `alpha`, `beta` and `gamma`. `M` adds `m.py`. `H1` moves
    `alpha`'s line 2. `H2` moves `beta`'s line 2 and inserts a line into
    `gamma` after its own line 5.
    """
    config = tmp_path / "gitconfig"
    config.write_text("[diff]\n    context = 0\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    mirror = tmp_path / "mirror"
    mirror.mkdir()
    _git(mirror, "init", "-q")

    def commit(message: str) -> str:
        _git(mirror, "add", "-A")
        _git(mirror, "commit", "-q", "-m", message)
        return _git(mirror, "rev-parse", "HEAD").strip()

    gamma = _numbered("gamma", {10: "gamma_calls beta_rate alpha_l2_new"})
    _write(mirror, "src/a.py", _numbered("alpha"))
    _write(mirror, "src/b.py", _numbered("beta"))
    _write(mirror, "src/c.py", gamma)
    shas = {"A": commit("A")}

    _write(mirror, "src/m.py", ["moved_main_only"])
    shas["M"] = commit("M")

    _write(mirror, "src/a.py", _numbered("alpha", {2: "alpha_l2_new"}))
    shas["H1"] = commit("H1")

    gamma_h2 = _numbered(
        "gamma", {2: "gamma_l2_new", 10: "gamma_calls beta_rate alpha_l2_new"}
    )
    gamma_h2 = gamma_h2[:5] + ["gamma_inserted"] + gamma_h2[5:]
    _write(mirror, "src/b.py", _numbered("beta", {2: "beta_rate"}))
    _write(mirror, "src/c.py", gamma_h2)
    shas["H2"] = commit("H2")
    return mirror, shas


def _finding(
    lens: str, severity: Severity, file: str, line: int, claim: str, probe=None
):
    return Finding(
        lens=lens, severity=severity, file=file, line=line, claim=claim, probe=probe
    )


def _spec_findings_te2() -> list[Finding]:
    return [
        _finding("spec", "concern", "src/c.py", 11, "f6"),
        _finding(
            "spec",
            "concern",
            "src/b.py",
            2,
            "f1",
            Mutant(file="src/b.py", find="beta_rate", replace="beta_gone"),
        ),
        _finding(
            "spec",
            "blocker",
            "src/b.py",
            3,
            "f2",
            Mutant(file="src/b.py", find="beta_l3", replace="beta_k"),
        ),
        _finding(
            "spec",
            "concern",
            "src/c.py",
            2,
            "f3",
            Mutant(file="src/c.py", find="nothing_here", replace="x"),
        ),
        _finding(
            "spec",
            "note",
            "src/c.py",
            3,
            "f4",
            Mutant(file="src/c.py", find="gamma_l2_new", replace="gamma_s"),
        ),
        _finding(
            "spec",
            "blocker",
            "src/c.py",
            13,
            "f5",
            Mutant(file="src/c.py", find="gamma_l12", replace="gamma_x"),
        ),
        _finding(
            "spec",
            "concern",
            "src/c.py",
            4,
            "f7",
            Mutant(file="src/c.py", find="nothing_here", replace="x"),
        ),
        _finding(
            "spec",
            "concern",
            "src/c.py",
            5,
            "f8",
            Mutant(file="tests/test_c.py", find="test_gone", replace="test_kept"),
        ),
        _finding(
            "spec",
            "concern",
            "src/c.py",
            6,
            "f10",
            Mutant(file="src/c.py", find="nothing_here", replace="y"),
        ),
    ]


def _standards_findings_te2() -> list[Finding]:
    return [
        _finding("standards", "note", "src/b.py", 4, "s1"),
        _finding("standards", "blocker", "src/b.py", 5, "s2"),
        _finding("standards", "note", "src/c.py", 12, "s3"),
    ]


def _join_findings() -> list[Finding]:
    return [
        _finding("join", "concern", "src/c.py", 11, "j1"),
        _finding("join", "concern", "src/m.py", 1, "j2"),
        _finding(
            "join",
            "blocker",
            "src/b.py",
            2,
            "j3",
            Mutant(file="src/b.py", find="beta_rate", replace="beta_j"),
        ),
    ]


def _spec_findings_te1() -> list[Finding]:
    return [
        _finding("spec", "concern", "src/a.py", 2, "c-a"),
        _finding("spec", "concern", "src/m.py", 1, "c-m"),
        _finding("spec", "concern", "src/c.py", 10, "c-c"),
    ]


_VERDICT_BY_EDIT: dict[tuple[str, str], Verdict] = {
    ("beta_rate", "beta_gone"): "survived",
    ("beta_l3", "beta_k"): "killed",
    ("nothing_here", "x"): "unproven",
    ("gamma_l2_new", "gamma_s"): "survived",
    ("nothing_here", "y"): "unproven",
}


def _install_probe_double(monkeypatch, h1_sha: str) -> list[dict]:
    """`session.probe_findings`'s own dedup and ordering, over a fixed
    verdict table rather than a real cell. Raises `KeyError` for any
    `spec.base_sha` but `H1`, the way a lookup keyed on it would."""
    calls: list[dict] = []

    def fake(targets, **kw):
        if kw["spec"].base_sha != h1_sha:
            raise KeyError(kw["spec"].base_sha)
        calls.append({"targets": targets, **kw})
        by_key: dict[tuple, list[Finding]] = {}
        for f in targets:
            by_key.setdefault(review.probe_key(f.probe), []).append(f)
        probes = review.distinct_probes(targets)
        refused = {
            review.probe_key(p): reason
            for p in probes
            if (reason := probe_check.probe_refusal(p.file, kw["test_paths"]))
            is not None
        }
        ordered = [p for p in probes if review.probe_key(p) in refused] + [
            p for p in probes if review.probe_key(p) not in refused
        ]
        entries = []
        for p in ordered:
            key = review.probe_key(p)
            if key in refused:
                verdict, reason = "unproven", refused[key]
            else:
                verdict = _VERDICT_BY_EDIT[(p.find, p.replace)]
                reason = (
                    ""
                    if verdict != "unproven"
                    else f"{p.file}: find text not found for {p.replace}"
                )
            for f in by_key[key]:
                review.apply_probe_verdict(f, verdict)
            entries.append({"probe": p.model_dump(), "reason": reason})
        return entries

    monkeypatch.setattr(session, "probe_findings", fake)
    return calls


@dataclass
class _Built:
    """One built fixture. `run` calls `qualify` with the same eight
    keywords every test needs to check were forwarded, by identity."""

    ledger: Ledger
    layers: list[LayerReview]
    mirror: Path
    shas: dict[str, str]
    calls: list[dict]
    repo: Path
    gates_dir: Path
    thread_env: dict[str, str]
    test_paths: list[str]
    gates: dict[str, Path]
    created: set[str]
    note: object

    def run(self, qualify_fn):
        return qualify_fn(
            self.ledger,
            self.layers,
            None,
            mirror=self.mirror,
            repo=self.repo,
            gates_dir=self.gates_dir,
            thread_env=self.thread_env,
            test_paths=self.test_paths,
            gates=self.gates,
            created=self.created,
            note=self.note,
        )


def _key(ledger: Ledger, task_id: int) -> str:
    """`Ledger.record_key`, narrowed. Every task this test creates has one."""
    key = ledger.record_key(task_id)
    assert key is not None
    return key


def _build(tmp_path: Path, monkeypatch) -> _Built:
    mirror, shas = _stack_mirror(tmp_path, monkeypatch)
    ledger = Ledger(tmp_path / "ledger.db", record=MemoryRecord())
    repo_id = ledger.upsert_repo(
        "acme", "https://example/o", "/m.git", policy_sha="p" * 64
    )

    ledger.create_run(repo_id, base_sha=shas["A"])  # a spare run naming no task

    run1 = ledger.create_run(repo_id, base_sha=shas["A"])
    task1 = ledger.create_task(
        run1, spec_id="TE-1", spec_sha="s" * 64, branch="saffron/TE-1"
    )
    run2 = ledger.create_run(repo_id, base_sha=shas["A"])
    task2 = ledger.create_task(
        run2, spec_id="TE-2", spec_sha="s" * 64, branch="saffron/TE-2"
    )

    ledger.record_gate_result(
        GateResult(gate="tests", status="pass", tool="pytest 8.0", collected=[]),
        run_id=run1,
    )
    ledger.record_gate_result(
        GateResult(gate="lint", status="pass", tool="ruff 1.0", collected=None),
        run_id=run1,
    )
    ledger.record_gate_result(
        GateResult(
            gate="tests",
            status="pass",
            tool="pytest 8.0",
            collected=["tests/t.py::test_old"],
        ),
        run_id=run2,
    )
    ledger.record_gate_result(
        GateResult(gate="lint", status="pass", tool="ruff 1.0", collected=None),
        run_id=run2,
    )

    ledger.set_task_package(
        task1, "READY_FOR_REVIEW", "saffron/TE-1", shas["H1"], "https://pr/1"
    )
    ledger.set_task_package(
        task2, "READY_FOR_REVIEW", "saffron/TE-2", shas["H2"], "https://pr/2"
    )
    ledger.record_stack_layer(task1, position=1, predecessor_task_id=None, generation=1)
    ledger.record_stack_layer(
        task2, position=2, predecessor_task_id=task1, generation=1
    )

    ledger.record_findings(task2, _join_findings())
    ledger.record_findings(task2, _spec_findings_te2() + _standards_findings_te2())
    ledger.record_findings(task1, _spec_findings_te1())

    calls = _install_probe_double(monkeypatch, shas["H1"])

    layers = [
        LayerReview(
            _key(ledger, task2),
            [
                review.LensReview("spec", _spec_findings_te2()),
                review.LensReview("standards", _standards_findings_te2()),
            ],
        ),
        LayerReview(
            _key(ledger, task1),
            [review.LensReview("spec", _spec_findings_te1())],
        ),
    ]
    return _Built(
        ledger,
        layers,
        mirror,
        shas,
        calls,
        repo=Path("/repo-sentinel"),
        gates_dir=Path("/gates-sentinel"),
        thread_env={"SENTINEL": "1"},
        test_paths=["tests/**"],
        gates={"tests": Path("/gates-sentinel/tests")},
        created=set(),
        note=lambda step, ok, detail: None,
    )


def test_each_layers_findings_are_anchored_probed_and_grouped_by_layer_and_file(
    tmp_path, monkeypatch
):
    from saffron.qualify import qualify

    built = _build(tmp_path, monkeypatch)
    result = built.run(qualify)

    groups = [
        (
            g.task_key,
            g.file,
            [(f.finding.claim, f.finding.severity) for f in g.findings],
        )
        for g in result.groups
    ]
    te1_key = built.ledger.record_key(
        built.ledger._db.execute(
            "SELECT task_id FROM tasks WHERE spec_id = 'TE-1'"
        ).fetchone()["task_id"]
    )
    te2_key = built.ledger.record_key(
        built.ledger._db.execute(
            "SELECT task_id FROM tasks WHERE spec_id = 'TE-2'"
        ).fetchone()["task_id"]
    )
    assert groups == [
        (te2_key, "src/c.py", [("f6", "concern"), ("f4", "blocker")]),
        (te2_key, "src/b.py", [("f1", "blocker"), ("s2", "blocker")]),
        (te1_key, "src/a.py", [("c-a", "concern")]),
        (te1_key, "src/c.py", [("c-c", "concern")]),
    ]

    pool = [(q.finding.claim, q.outcome, q.reason) for q in result.pool]
    assert pool == [
        ("f3", "unverified", "src/c.py: find text not found for x"),
        ("f5", "unanchored", ""),
        ("f7", "unverified", "src/c.py: find text not found for x"),
        ("f8", "unverified", "tests/test_c.py is a test; a probe must target source"),
        ("f10", "unverified", "src/c.py: find text not found for y"),
        ("s1", "note", ""),
        ("s3", "unanchored", ""),
        ("c-m", "unanchored", ""),
    ]


def test_a_layers_probes_run_in_a_gate_only_cell_on_its_own_tree(tmp_path, monkeypatch):
    from saffron.qualify import qualify

    built = _build(tmp_path, monkeypatch)
    built.run(qualify)

    assert len(built.calls) == 1
    call = built.calls[0]
    assert [f.claim for f in call["targets"]] == [
        "f1",
        "f2",
        "f3",
        "f4",
        "f7",
        "f8",
        "f10",
    ]
    assert call["spec"].base_sha == built.shas["H1"]
    assert call["spec"].stacked_on is None
    assert call["spec"].spec_id == "TE-2"
    assert call["spec"].branch == "saffron/TE-2"
    assert "+beta_rate" in call["patch"]
    assert "alpha_l2_new" not in call["patch"]
    assert [r.collected for r in call["base_results"]] == [
        ["tests/t.py::test_old"],
        None,
    ]
    for name in ("repo", "gates_dir", "thread_env", "gates", "created", "note"):
        assert call[name] is getattr(built, name)
    assert call["test_paths"] is built.test_paths
    assert call["mirror"] is built.mirror


def test_each_layers_qualifications_are_facts_numbered_within_its_task(
    tmp_path, monkeypatch
):
    from saffron.qualify import qualify

    built = _build(tmp_path, monkeypatch)
    built.run(qualify)

    def rows(spec_id: str) -> list:
        task_key = built.ledger.record_key(
            built.ledger._db.execute(
                "SELECT task_id FROM tasks WHERE spec_id = ?", (spec_id,)
            ).fetchone()["task_id"]
        )
        return list(
            built.ledger._db.execute(
                "SELECT * FROM qualifications WHERE task_key = ? ORDER BY position",
                (task_key,),
            )
        )

    te2 = rows("TE-2")
    assert [r["claim"] for r in te2] == [
        "f6",
        "f1",
        "f2",
        "f3",
        "f4",
        "f5",
        "f7",
        "f8",
        "f10",
        "s1",
        "s2",
        "s3",
    ]
    te1 = rows("TE-1")
    assert [r["claim"] for r in te1] == ["c-a", "c-m", "c-c"]

    f1 = te2[1]
    assert (f1["lens"], f1["severity"], f1["file"], f1["line"], f1["claim"]) == (
        "spec",
        "concern",
        "src/b.py",
        2,
        "f1",
    )
    assert (f1["probe_verdict"], f1["outcome"], f1["reason"]) == (
        "survived",
        "qualified",
        "",
    )

    f2 = te2[2]
    assert (f2["probe_verdict"], f2["outcome"]) == ("killed", "killed")

    f3 = te2[3]
    assert (f3["probe_verdict"], f3["outcome"], f3["reason"]) == (
        "unproven",
        "unverified",
        "src/c.py: find text not found for x",
    )

    s1 = te2[9]
    assert (s1["probe_verdict"], s1["outcome"]) == (None, "note")

    f4 = te2[4]
    assert (f4["severity"], f4["probe_verdict"], f4["outcome"]) == (
        "note",
        "survived",
        "qualified",
    )

    f5 = te2[5]
    assert (f5["probe_verdict"], f5["outcome"]) == (None, "unanchored")
