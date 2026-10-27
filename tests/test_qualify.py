"""`saffron.qualify` (backlog item b-792ab2, step 4): each layer's end-review
findings, anchored against its own diff, probed and decided into follow-up
groups and a leftover pool. `saffron.qualify` is imported inside each test
body, never at module scope. It does not exist at this spec's own tree base,
and a module-scope import would fail collection under `revert`.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from saffron import finish
from saffron import probe as probe_check
from saffron.agents.findings import Finding, Severity
from saffron.cell import session
from saffron.end_review import LayerFields, LayerReview, layer_fields
from saffron.gates.contract import GateResult
from saffron.intake import Mutant
from saffron.ledger import Ledger
from saffron.phases import review
from saffron.probe import Verdict
from saffron.record.memory import MemoryRecord
from saffron.repos.mirror import GitError, UnreadablePath, file_at

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


def _write_bytes(mirror: Path, path: str, data: bytes) -> None:
    full = mirror / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(data)


def _symlink(mirror: Path, path: str, target: str) -> None:
    full = mirror / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.symlink_to(target)


def _seed_unreadable(mirror: Path) -> None:
    """Six paths `file_at` cannot read as text, plus `src/c_link.py`, an
    in-tree symlink it can read. All are planted before commit `A`'s own
    `add -A` so none is in any range's diff. `src` itself needs no seeding:
    it is already a directory.
    """
    sub = mirror / "vendor" / "sub"
    sub.mkdir(parents=True)
    _git(sub, "init", "-q")
    _git(sub, "commit", "-q", "--allow-empty", "-m", "sub")
    _symlink(mirror, "src/out.py", "../../outside.py")
    _symlink(mirror, "src/hop.py", "out.py")
    _symlink(mirror, "src/c_link.py", "c.py")
    _write(mirror, "src/gone.py", ["gone_only_line"])
    _symlink(mirror, "src/gone_link.py", "gone.py")
    _write_bytes(mirror, "src/latin.py", b"\xff\xfe")


def _delete_loose_object(mirror: Path, sha: str, path: str) -> None:
    """`sha:path`'s blob, removed from `.git/objects` so `ls-tree` still
    lists `path` but `git show` can no longer read it."""
    blob = _git(mirror, "rev-parse", f"{sha}:{path}").strip()
    (mirror / ".git" / "objects" / blob[:2] / blob[2:]).unlink()


def _stack_mirror(
    tmp_path: Path, monkeypatch, *, unreadable: bool = False
) -> tuple[Path, dict[str, str]]:
    """The git history the four commits in the spec's notes describe.

    `A` seeds `alpha`, `beta` and `gamma`. `M` adds `m.py`. `H1` moves
    `alpha`'s line 2. `H2` moves `beta`'s line 2 and inserts a line into
    `gamma` after its own line 5. `unreadable` additionally seeds the
    paths `_seed_unreadable` names, untouched by every later commit, and
    deletes `src/gone.py`'s blob after `H2`.
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
    if unreadable:
        _seed_unreadable(mirror)
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
    if unreadable:
        _delete_loose_object(mirror, shas["H2"], "src/gone.py")
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
            "note",
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


def _in_cell_findings_te2() -> list[Finding]:
    """`TE-2`'s own REVIEW concerns, plus two decoys: `i3` and `i4` are not
    `concern` severity, so `qualify` never takes them as inputs. `i7` sits
    on a file no diff touches, so it is `unanchored`."""
    return [
        _finding("correctness", "concern", "src/b.py", 1, "i1"),
        _finding("adequacy", "note", "src/b.py", 2, "i3"),
        _finding("correctness", "blocker", "src/b.py", 2, "i4"),
        _finding("adequacy", "concern", "src/b.py", 1, "i6"),
        _finding("adequacy", "concern", "src/z.py", 1, "i7"),
    ]


def _in_cell_findings_te0() -> list[Finding]:
    return [_finding("correctness", "concern", "src/m.py", 1, "u1")]


_VERDICT_BY_EDIT: dict[tuple[str, str], Verdict] = {
    ("beta_rate", "beta_gone"): "survived",
    ("beta_l3", "beta_k"): "killed",
    ("nothing_here", "x"): "unproven",
    ("gamma_l2_new", "gamma_s"): "survived",
    ("nothing_here", "y"): "unproven",
}


def _install_probe_double(
    monkeypatch, shas: dict[str, str], raise_on: frozenset[str] = frozenset()
) -> list[dict]:
    """`session.probe_findings`'s own dedup and ordering, over a fixed
    verdict table rather than a real cell. Raises `RuntimeError` for a
    `spec.base_sha` named in `raise_on`, and `KeyError` for any sha this
    fixture never committed."""
    calls: list[dict] = []
    by_sha = {sha: name for name, sha in shas.items()}

    def fake(targets, **kw):
        base_sha = kw["spec"].base_sha
        name = by_sha.get(base_sha)
        if name is None:
            raise KeyError(base_sha)
        calls.append({"targets": targets, **kw})
        if name in raise_on:
            raise RuntimeError(f"no cell at {name}")
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
    """One built fixture. `run` calls `qualify` with the same nine
    keywords every test needs to check were forwarded, by identity.
    `fields` is built fresh each call, from `layer_fields` over whatever
    `self.layers` holds right now. A test that narrows `self.layers`
    between calls then gets a matching `fields` mapping too."""

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
    join_review: review.LensReview | None = None
    batch_id: int | None = None

    def run(self, qualify_fn, fields: dict[str, LayerFields] | None = None):
        if fields is None:
            fields = {
                layer.task_key: layer_fields(self.ledger, layer.task_key)
                for layer in self.layers
            }
        return qualify_fn(
            self.ledger,
            self.layers,
            self.join_review,
            fields=fields,
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


def _spec_key(ledger: Ledger, spec_id: str) -> str:
    """The record key of the one task this fixture ever creates for
    `spec_id`."""
    return _key(
        ledger,
        ledger._db.execute(
            "SELECT task_id FROM tasks WHERE spec_id = ?", (spec_id,)
        ).fetchone()["task_id"],
    )


def _build(
    tmp_path: Path,
    monkeypatch,
    *,
    in_cell: bool = False,
    join: bool = False,
    te0: bool = False,
    raise_on: frozenset[str] = frozenset(),
    unreadable: bool = False,
) -> _Built:
    mirror, shas = _stack_mirror(tmp_path, monkeypatch, unreadable=unreadable)
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

    if in_cell:
        ledger.record_findings(task2, _in_cell_findings_te2())
    ledger.record_findings(task2, _join_findings())
    ledger.record_findings(task2, _spec_findings_te2() + _standards_findings_te2())
    ledger.record_findings(task1, _spec_findings_te1())

    calls = _install_probe_double(monkeypatch, shas, raise_on)

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

    if te0:
        run0 = ledger.create_run(repo_id, base_sha=shas["A"])
        task0 = ledger.create_task(
            run0, spec_id="TE-0", spec_sha="s" * 64, branch="saffron/TE-0"
        )
        ledger.record_gate_result(
            GateResult(gate="tests", status="pass", tool="pytest 8.0", collected=[]),
            run_id=run0,
        )
        ledger.set_task_package(
            task0, "READY_FOR_REVIEW", "saffron/TE-0", shas["M"], "https://pr/0"
        )
        ledger.record_stack_layer(
            task0, position=0, predecessor_task_id=None, generation=1
        )
        ledger.record_findings(task0, _in_cell_findings_te0())
        layers.append(LayerReview(_key(ledger, task0), []))

    join_review = review.LensReview("join", _join_findings()) if join else None

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
        join_review=join_review,
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

    pool = [(q.task_key, q.finding.claim, q.outcome, q.reason) for q in result.pool]
    assert pool == [
        (te2_key, "f3", "unverified", "src/c.py: find text not found for x"),
        (te2_key, "f5", "unanchored", ""),
        (te2_key, "f7", "unverified", "src/c.py: find text not found for x"),
        (
            te2_key,
            "f8",
            "unverified",
            "tests/test_c.py is a test; a probe must target source",
        ),
        (te2_key, "f10", "unverified", "src/c.py: find text not found for y"),
        (te2_key, "s1", "note", ""),
        (te2_key, "s3", "unanchored", ""),
        (te1_key, "c-m", "unanchored", ""),
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


def test_a_layers_own_review_concerns_follow_its_end_review_findings(
    tmp_path, monkeypatch
):
    from saffron.qualify import qualify

    built = _build(tmp_path, monkeypatch, in_cell=True, te0=True)
    result = built.run(qualify)

    te1_key = _spec_key(built.ledger, "TE-1")
    te2_key = _spec_key(built.ledger, "TE-2")
    te0_key = _spec_key(built.ledger, "TE-0")

    groups = [
        (
            g.task_key,
            g.file,
            [(f.finding.claim, f.finding.severity) for f in g.findings],
        )
        for g in result.groups
    ]
    assert groups == [
        (te2_key, "src/c.py", [("f6", "concern"), ("f4", "blocker")]),
        (
            te2_key,
            "src/b.py",
            [("f1", "blocker"), ("s2", "blocker"), ("i1", "concern")],
        ),
        (te1_key, "src/a.py", [("c-a", "concern")]),
        (te1_key, "src/c.py", [("c-c", "concern")]),
        (te0_key, "src/m.py", [("u1", "concern")]),
    ]

    pool = [(q.task_key, q.finding.claim, q.outcome, q.reason) for q in result.pool]
    assert pool == [
        (te2_key, "f3", "unverified", "src/c.py: find text not found for x"),
        (te2_key, "f5", "unanchored", ""),
        (te2_key, "f7", "unverified", "src/c.py: find text not found for x"),
        (
            te2_key,
            "f8",
            "unverified",
            "tests/test_c.py is a test; a probe must target source",
        ),
        (te2_key, "f10", "unverified", "src/c.py: find text not found for y"),
        (te2_key, "s1", "note", ""),
        (te2_key, "s3", "unanchored", ""),
        (te2_key, "i6", "unverified", "its REVIEW probe did not survive"),
        (te2_key, "i7", "unanchored", ""),
        (te1_key, "c-m", "unanchored", ""),
    ]

    def rows(spec_id: str) -> list:
        task_key = _spec_key(built.ledger, spec_id)
        return list(
            built.ledger._db.execute(
                "SELECT * FROM qualifications WHERE task_key = ? ORDER BY position",
                (task_key,),
            )
        )

    assert [r["claim"] for r in rows("TE-2")] == [
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
        "i1",
        "i6",
        "i7",
    ]
    assert [r["claim"] for r in rows("TE-1")] == ["c-a", "c-m", "c-c"]
    assert [r["claim"] for r in rows("TE-0")] == ["u1"]


def test_the_join_is_walked_first_over_the_stack_and_belongs_to_the_top_layer(
    tmp_path, monkeypatch
):
    from saffron.qualify import qualify

    built = _build(
        tmp_path, monkeypatch, in_cell=True, join=True, raise_on=frozenset({"M"})
    )
    result = built.run(qualify)

    te1_key = _spec_key(built.ledger, "TE-1")
    te2_key = _spec_key(built.ledger, "TE-2")

    groups = [
        (
            g.task_key,
            g.file,
            [(f.finding.claim, f.finding.severity) for f in g.findings],
        )
        for g in result.groups
    ]
    assert groups == [
        (
            te2_key,
            "src/c.py",
            [("j1", "concern"), ("f6", "concern"), ("f4", "blocker")],
        ),
        (
            te2_key,
            "src/b.py",
            [("f1", "blocker"), ("s2", "blocker"), ("i1", "concern")],
        ),
        (te1_key, "src/a.py", [("c-a", "concern")]),
        (te1_key, "src/c.py", [("c-c", "concern")]),
    ]

    pool = [(q.task_key, q.finding.claim, q.outcome, q.reason) for q in result.pool]
    assert pool == [
        (te2_key, "j2", "unanchored", ""),
        (te2_key, "j3", "unverified", "no cell at M"),
        (te2_key, "f3", "unverified", "src/c.py: find text not found for x"),
        (te2_key, "f5", "unanchored", ""),
        (te2_key, "f7", "unverified", "src/c.py: find text not found for x"),
        (
            te2_key,
            "f8",
            "unverified",
            "tests/test_c.py is a test; a probe must target source",
        ),
        (te2_key, "f10", "unverified", "src/c.py: find text not found for y"),
        (te2_key, "s1", "note", ""),
        (te2_key, "s3", "unanchored", ""),
        (te2_key, "i6", "unverified", "its REVIEW probe did not survive"),
        (te2_key, "i7", "unanchored", ""),
        (te1_key, "c-m", "unanchored", ""),
    ]

    fresh = tmp_path / "second"
    fresh.mkdir()
    built2 = _build(
        fresh,
        monkeypatch,
        in_cell=True,
        join=True,
        raise_on=frozenset({"M", "H1"}),
    )
    result2 = built2.run(qualify)

    te1_key2 = _spec_key(built2.ledger, "TE-1")
    te2_key2 = _spec_key(built2.ledger, "TE-2")

    groups2 = [
        (
            g.task_key,
            g.file,
            [(f.finding.claim, f.finding.severity) for f in g.findings],
        )
        for g in result2.groups
    ]
    assert groups2 == [
        (te2_key2, "src/c.py", [("j1", "concern"), ("f6", "concern")]),
        (te2_key2, "src/b.py", [("s2", "blocker"), ("i1", "concern")]),
        (te1_key2, "src/a.py", [("c-a", "concern")]),
        (te1_key2, "src/c.py", [("c-c", "concern")]),
    ]

    pool2 = [(q.task_key, q.finding.claim, q.outcome, q.reason) for q in result2.pool]
    assert pool2 == [
        (te2_key2, "j2", "unanchored", ""),
        (te2_key2, "j3", "unverified", "no cell at M"),
        (te2_key2, "f1", "unverified", "no cell at H1"),
        (te2_key2, "f2", "unverified", "no cell at H1"),
        (te2_key2, "f3", "unverified", "no cell at H1"),
        (te2_key2, "f4", "unverified", "no cell at H1"),
        (te2_key2, "f5", "unanchored", ""),
        (te2_key2, "f7", "unverified", "no cell at H1"),
        (te2_key2, "f8", "unverified", "no cell at H1"),
        (te2_key2, "f10", "unverified", "no cell at H1"),
        (te2_key2, "s1", "note", ""),
        (te2_key2, "s3", "unanchored", ""),
        (te2_key2, "i6", "unverified", "its REVIEW probe did not survive"),
        (te2_key2, "i7", "unanchored", ""),
        (te1_key2, "c-m", "unanchored", ""),
    ]


def test_the_joins_probes_run_on_the_stack_counted_from_the_bottom_run(
    tmp_path, monkeypatch
):
    from saffron.qualify import qualify

    built = _build(tmp_path, monkeypatch, join=True, raise_on=frozenset({"M"}))
    built.run(qualify)

    assert len(built.calls) == 2
    join_call = built.calls[0]
    assert [f.claim for f in join_call["targets"]] == ["j3"]
    assert join_call["spec"].base_sha == built.shas["M"]
    assert join_call["spec"].stacked_on is None
    assert join_call["spec"].spec_id == "TE-2"
    assert join_call["spec"].branch == "saffron/TE-2"
    assert "+alpha_l2_new" in join_call["patch"]
    assert "moved_main_only" not in join_call["patch"]
    assert [r.collected for r in join_call["base_results"]] == [[], None]
    for name in ("repo", "gates_dir", "thread_env", "gates", "created", "note"):
        assert join_call[name] is getattr(built, name)
    assert join_call["test_paths"] is built.test_paths
    assert join_call["mirror"] is built.mirror

    layer_call = built.calls[1]
    assert layer_call["spec"].base_sha == built.shas["H1"]


def test_the_joins_qualifications_come_first_under_the_top_layer(tmp_path, monkeypatch):
    from saffron.qualify import qualify

    built = _build(
        tmp_path, monkeypatch, in_cell=True, join=True, raise_on=frozenset({"M"})
    )
    built.run(qualify)

    def rows(spec_id: str) -> list:
        task_key = _spec_key(built.ledger, spec_id)
        return list(
            built.ledger._db.execute(
                "SELECT * FROM qualifications WHERE task_key = ? ORDER BY position",
                (task_key,),
            )
        )

    te2 = rows("TE-2")
    assert len(te2) == 18
    assert [(r["claim"], r["outcome"]) for r in te2[:3]] == [
        ("j1", "qualified"),
        ("j2", "unanchored"),
        ("j3", "unverified"),
    ]
    assert [r["claim"] for r in te2[3:]] == [
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
        "i1",
        "i6",
        "i7",
    ]

    te1 = rows("TE-1")
    assert [r["claim"] for r in te1] == ["c-a", "c-m", "c-c"]


def test_a_path_the_mirror_cannot_read_raises_out_of_qualify(tmp_path, monkeypatch):
    """`qualify` passes `file_at` itself as `anchor`'s `read_head` (backlog
    item b-00534f). A read that raises is never caught: it comes out of
    `qualify` unchanged, and the finding whose read raised gets no
    `qualifications` row at all. An absent path reads as no file, and a
    readable file or in-tree symlink anchors."""
    from saffron.qualify import qualify

    built = _build(tmp_path, monkeypatch, unreadable=True)
    te2_task_id = built.ledger._db.execute(
        "SELECT task_id FROM tasks WHERE spec_id = 'TE-2'"
    ).fetchone()["task_id"]
    te2_key = _key(built.ledger, te2_task_id)

    def _one_finding_layer(file: str, line: int, claim: str) -> None:
        built.layers = [
            LayerReview(
                te2_key,
                [
                    review.LensReview(
                        "spec", [_finding("spec", "concern", file, line, claim)]
                    )
                ],
            )
        ]

    # `UnreadablePath`: a tree or submodule mode, a symlink out of the tree or to a
    # non-regular file. `GitError`: a missing blob. `UnicodeDecodeError`: bad bytes.
    raising: list[tuple[str, int, str, type[Exception]]] = [
        ("src", 3, "r-tree", UnreadablePath),
        ("vendor/sub", 3, "r-sub", UnreadablePath),
        ("src/out.py", 3, "r-out", UnreadablePath),
        ("src/hop.py", 3, "r-hop", UnreadablePath),
        ("src/gone.py", 3, "r-gone", GitError),
        ("src/gone_link.py", 3, "r-gone-link", GitError),
        ("src/latin.py", 1, "r-latin", UnicodeDecodeError),
    ]
    for path, line, claim, exc_type in raising:
        with pytest.raises(exc_type) as expected:
            file_at(built.mirror, built.shas["H2"], path)

        _one_finding_layer(path, line, claim)
        with pytest.raises(exc_type) as caught:
            built.run(qualify)

        assert type(caught.value) is exc_type
        assert str(caught.value) == str(expected.value)

    _one_finding_layer("src/z.py", 1, "r-absent")
    result = built.run(qualify)
    assert result.groups == []
    assert [(q.finding.claim, q.outcome) for q in result.pool] == [
        ("r-absent", "unanchored")
    ]

    for path, claim in (("src/c.py", "r-c"), ("src/c_link.py", "r-c-link")):
        _one_finding_layer(path, 11, claim)
        result = built.run(qualify)
        assert result.pool == []
        assert len(result.groups) == 1
        group = result.groups[0]
        assert group.task_key == te2_key
        assert group.file == path
        assert [q.finding.claim for q in group.findings] == [claim]

    rows = built.ledger.qualifications(te2_task_id)
    assert [r["claim"] for r in rows] == ["r-absent", "r-c", "r-c-link"]


def _graded_fixture(tmp_path: Path, monkeypatch) -> _Built:
    """`A` seeds `alpha`/`beta`/`gamma`. `M` adds `m.py`, a file neither
    layer ever touches. `H1` and `H2` are the packaged heads TE-1 and TE-2
    pushed. A graded branch forks off `H1`: `R1` adds TE-1's own review
    line, `H2b` restacks `H2`'s own change on it, `R2` adds TE-2's. The end
    review graded TE-1 at `R1` and TE-2 at `R2`, each ahead of its own
    packaged head.
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

    alpha = [f"a{i}" for i in range(1, 8)]
    beta = [f"b{i}" for i in range(1, 8)]
    gamma = [f"g{i}" for i in range(1, 8)]
    _write(mirror, "src/a.py", alpha)
    _write(mirror, "src/b.py", beta)
    _write(mirror, "src/c.py", gamma)
    shas = {"A": commit("A")}

    _write(mirror, "src/m.py", ["m1"])
    shas["M"] = commit("M")

    alpha_h1 = [*alpha[:1], "a2_new", *alpha[2:]]
    _write(mirror, "src/a.py", alpha_h1)
    shas["H1"] = commit("H1")

    beta_h2 = [*beta[:1], "b2_new", *beta[2:]]
    gamma_h2 = [*gamma[:1], "g2_new", *gamma[2:]]
    _write(mirror, "src/b.py", beta_h2)
    _write(mirror, "src/c.py", gamma_h2)
    shas["H2"] = commit("H2")

    _git(mirror, "checkout", "-q", shas["H1"])
    _write(mirror, "src/a.py", [*alpha_h1, "a8_review"])
    shas["R1"] = commit("R1")

    _write(mirror, "src/b.py", beta_h2)
    _write(mirror, "src/c.py", gamma_h2)
    shas["H2b"] = commit("H2b")

    _write(mirror, "src/c.py", [*gamma_h2, "g8_review"])
    shas["R2"] = commit("R2")

    _git(mirror, "checkout", "-q", shas["H2"])

    ledger = Ledger(tmp_path / "ledger.db", record=MemoryRecord())
    repo_id = ledger.upsert_repo(
        "acme", "https://example/o", "/m.git", policy_sha="p" * 64
    )
    run1 = ledger.create_run(repo_id, base_sha=shas["A"])
    task1 = ledger.create_task(
        run1, spec_id="TE-1", spec_sha="s" * 64, branch="saffron/TE-1"
    )
    run2 = ledger.create_run(repo_id, base_sha=shas["A"])
    task2 = ledger.create_task(
        run2, spec_id="TE-2", spec_sha="s" * 64, branch="saffron/TE-2"
    )
    for run_id in (run1, run2):
        ledger.record_gate_result(
            GateResult(gate="tests", status="pass", tool="pytest 8.0", collected=[]),
            run_id=run_id,
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

    te1_key = _key(ledger, task1)
    te2_key = _key(ledger, task2)

    te1_findings = [
        _finding("spec", "concern", "src/a.py", 2, "te1-a2"),
        _finding("spec", "concern", "src/m.py", 1, "te1-m"),
        _finding(
            "spec",
            "blocker",
            "src/a.py",
            8,
            "te1-review",
            Mutant(file="src/a.py", find="a8_review", replace="a8_x"),
        ),
    ]
    te2_findings = [
        _finding("spec", "concern", "src/b.py", 2, "te2-b2"),
        _finding("spec", "concern", "src/m.py", 1, "te2-m"),
        _finding(
            "spec",
            "blocker",
            "src/c.py",
            8,
            "te2-review",
            Mutant(file="src/c.py", find="g8_review", replace="g8_x"),
        ),
    ]
    join_findings = [
        _finding("join", "concern", "src/c.py", 8, "join-review"),
        _finding("join", "concern", "src/m.py", 1, "join-m"),
        _finding(
            "join",
            "blocker",
            "src/b.py",
            2,
            "join-b2",
            Mutant(file="src/b.py", find="b2_new", replace="b2_x"),
        ),
    ]
    # Both under a lens in `review.LENSES`. `ic-packaged` cites `H2`'s own
    # change. `ic-review` cites `R2`'s line, which no packaged diff carries.
    in_cell_concerns = [
        _finding("correctness", "concern", "src/b.py", 2, "ic-packaged"),
        _finding("correctness", "concern", "src/c.py", 8, "ic-review"),
    ]

    ledger.record_findings(task2, in_cell_concerns)
    ledger.record_findings(task2, te2_findings)
    ledger.record_findings(task1, te1_findings)

    layers = [
        LayerReview(te2_key, [review.LensReview("spec", te2_findings)]),
        LayerReview(te1_key, [review.LensReview("spec", te1_findings)]),
    ]
    join_review = review.LensReview("join", join_findings)

    return _Built(
        ledger,
        layers,
        mirror,
        shas,
        [],
        repo=Path("/repo-sentinel"),
        gates_dir=Path("/gates-sentinel"),
        thread_env={"SENTINEL": "1"},
        test_paths=["tests/**"],
        gates={"tests": Path("/gates-sentinel/tests")},
        created=set(),
        note=lambda step, ok, detail: None,
        join_review=join_review,
    )


def _install_recording_probe(monkeypatch, calls: list[dict]) -> None:
    """Every probed finding survives. Records each call's `spec.base_sha`
    and `patch`, which range a call was read over."""

    def fake(targets, **kw):
        calls.append({"base_sha": kw["spec"].base_sha, "patch": kw["patch"]})
        entries = []
        for p in review.distinct_probes(targets):
            entries.append({"probe": p.model_dump(), "reason": ""})
        for f in targets:
            if f.probe is not None:
                review.apply_probe_verdict(f, "survived")
        return entries

    monkeypatch.setattr(session, "probe_findings", fake)


def test_findings_are_anchored_and_probed_over_the_range_the_end_review_graded(
    tmp_path, monkeypatch
):
    """`qualify.qualify` takes `fields`, the end review's own grading, as a
    required keyword, and reads every range from it through
    `qualify.graded_fields`: the join's from the bottom layer's `diff_base`
    to the top layer's graded `head`, and each layer's own end-review
    findings the same way. A layer's in-cell REVIEW concerns keep the
    packaged range instead, since their line numbers were recorded there.
    A layer missing from `fields` falls back to the packaged range too,
    in both the per-layer walk and the join.
    """
    from saffron.qualify import graded_fields, qualify

    built = _graded_fixture(tmp_path, monkeypatch)
    te2_key, te1_key = built.layers[0].task_key, built.layers[1].task_key
    calls: list[dict] = []
    _install_recording_probe(monkeypatch, calls)

    fields = {
        te1_key: replace(
            layer_fields(built.ledger, te1_key),
            base=built.shas["H1"],
            diff_base=built.shas["M"],
            head=built.shas["R1"],
        ),
        te2_key: replace(
            layer_fields(built.ledger, te2_key),
            base=built.shas["H1"],
            diff_base=built.shas["R1"],
            head=built.shas["R2"],
        ),
    }

    result = built.run(qualify, fields=fields)

    groups = {
        (g.task_key, g.file): [f.finding.claim for f in g.findings]
        for g in result.groups
    }
    assert groups == {
        (te2_key, "src/b.py"): ["join-b2", "te2-b2", "ic-packaged"],
        (te2_key, "src/c.py"): ["join-review", "te2-review"],
        (te1_key, "src/a.py"): ["te1-a2", "te1-review"],
    }
    pool = {(q.task_key, q.finding.claim): q.outcome for q in result.pool}
    assert pool == {
        (te2_key, "join-m"): "unanchored",
        (te2_key, "te2-m"): "unanchored",
        (te2_key, "ic-review"): "unanchored",
        (te1_key, "te1-m"): "unanchored",
    }

    assert len(calls) == 3
    assert calls[0]["base_sha"] == built.shas["M"]
    assert "+g8_review" in calls[0]["patch"]
    assert "+a8_review" in calls[0]["patch"]
    assert calls[1]["base_sha"] == built.shas["R1"]
    assert "+g8_review" in calls[1]["patch"]
    assert "+a8_review" not in calls[1]["patch"]
    assert calls[2]["base_sha"] == built.shas["M"]
    assert "+a8_review" in calls[2]["patch"]

    assert graded_fields(built.ledger, fields, te1_key) == fields[te1_key]
    assert graded_fields(built.ledger, fields, te2_key) == fields[te2_key]
    assert graded_fields(built.ledger, {}, te1_key) == layer_fields(
        built.ledger, te1_key
    )

    # A top layer missing from `fields` moves both the join and TE-2's own
    # walk to the packaged range, so neither anchors its review line.
    fresh_top = tmp_path / "missing-top"
    fresh_top.mkdir()
    built_top = _graded_fixture(fresh_top, monkeypatch)
    te2_key_t, te1_key_t = built_top.layers[0].task_key, built_top.layers[1].task_key
    calls_top: list[dict] = []
    _install_recording_probe(monkeypatch, calls_top)
    fields_top = {
        te1_key_t: replace(
            layer_fields(built_top.ledger, te1_key_t),
            base=built_top.shas["H1"],
            diff_base=built_top.shas["M"],
            head=built_top.shas["R1"],
        )
    }
    result_top = built_top.run(qualify, fields=fields_top)
    pool_top = {(q.task_key, q.finding.claim): q.outcome for q in result_top.pool}
    assert pool_top[(te2_key_t, "join-review")] == "unanchored"
    assert pool_top[(te2_key_t, "te2-review")] == "unanchored"
    assert pool_top[(te2_key_t, "join-m")] == "unanchored"
    assert pool_top[(te2_key_t, "te2-m")] == "unanchored"
    assert pool_top[(te2_key_t, "ic-review")] == "unanchored"
    groups_top = {
        (g.task_key, g.file): [f.finding.claim for f in g.findings]
        for g in result_top.groups
    }
    assert groups_top == {
        (te1_key_t, "src/a.py"): ["te1-a2", "te1-review"],
        (te2_key_t, "src/b.py"): ["join-b2", "te2-b2", "ic-packaged"],
    }

    # A bottom layer missing from `fields`: TE-1's own walk falls back to
    # the packaged range, so its review-line finding is no longer anchored.
    fresh_bottom = tmp_path / "missing-bottom"
    fresh_bottom.mkdir()
    built_bottom = _graded_fixture(fresh_bottom, monkeypatch)
    te2_key_b, te1_key_b = (
        built_bottom.layers[0].task_key,
        built_bottom.layers[1].task_key,
    )
    calls_bottom: list[dict] = []
    _install_recording_probe(monkeypatch, calls_bottom)
    fields_bottom = {
        te2_key_b: replace(
            layer_fields(built_bottom.ledger, te2_key_b),
            base=built_bottom.shas["H1"],
            diff_base=built_bottom.shas["R1"],
            head=built_bottom.shas["R2"],
        )
    }
    result_bottom = built_bottom.run(qualify, fields=fields_bottom)
    pool_bottom = {(q.task_key, q.finding.claim): q.outcome for q in result_bottom.pool}
    assert pool_bottom[(te1_key_b, "te1-review")] == "unanchored"
    groups_bottom = {
        (g.task_key, g.file): [f.finding.claim for f in g.findings]
        for g in result_bottom.groups
    }
    assert groups_bottom[(te2_key_b, "src/c.py")] == ["join-review", "te2-review"]
    # The join's bottom falls back to TE-1's packaged range, not the top's.
    assert calls_bottom[0]["base_sha"] == built_bottom.shas["M"]
    assert "+a2_new" in calls_bottom[0]["patch"]


def _later_diff_fixture(tmp_path: Path, monkeypatch) -> _Built:
    """`A` seeds `src/a.py` (60 lines), `src/b.py`, `src/gone.py` and
    `src/u.py`. `H1` (TE-1's packaged head) rewrites `a.py:10`. `H2`
    (TE-2's packaged head, on `H1`) rewrites `a.py:10,20,38,44`, `b.py:6`
    and `gone.py:2`. A review branch off `H1`: `R1` edits `a.py:10` in
    place and `u.py:3`, and deletes `a.py:20`. `H2b` restacks `H2`'s own
    content onto `R1`'s shifted tree. `R2` inserts two lines after `H2`'s
    own `a.py:40` and deletes `gone.py`. TE-2's graded head is `R2`. TE-1's
    is its own packaged head, `H1`."""
    mirror = tmp_path / "mirror"
    mirror.mkdir()
    _git(mirror, "init", "-q")

    def commit(message: str) -> str:
        _git(mirror, "add", "-A")
        _git(mirror, "commit", "-q", "-m", message)
        return _git(mirror, "rev-parse", "HEAD").strip()

    _write(mirror, "src/a.py", [f"a{i}" for i in range(1, 61)])
    _write(mirror, "src/b.py", [f"b{i}" for i in range(1, 9)])
    _write(mirror, "src/gone.py", [f"g{i}" for i in range(1, 4)])
    _write(mirror, "src/u.py", [f"u{i}" for i in range(1, 6)])
    shas = {"A": commit("A")}

    a = [f"a{i}" for i in range(1, 61)]
    a[9] = "a10_h1"
    _write(mirror, "src/a.py", a)
    shas["H1"] = commit("H1")

    a2 = list(a)
    a2[9], a2[19], a2[37], a2[43] = "a10_h2", "a20_h2", "a38_h2", "a44_h2"
    b2 = [f"b{i}" for i in range(1, 9)]
    b2[5] = "b6_h2 retry_budget"
    gone2 = [f"g{i}" for i in range(1, 4)]
    gone2[1] = "g2_h2"
    _write(mirror, "src/a.py", a2)
    _write(mirror, "src/b.py", b2)
    _write(mirror, "src/gone.py", gone2)
    shas["H2"] = commit("H2")

    _git(mirror, "checkout", "-q", shas["H1"])
    r1 = list(a)
    r1[9] = "a10_h1 retry_budget"
    del r1[19]
    u1 = [f"u{i}" for i in range(1, 6)]
    u1[2] = "u3_r1"
    _write(mirror, "src/a.py", r1)
    _write(mirror, "src/u.py", u1)
    shas["R1"] = commit("R1")

    h2b = list(r1)
    h2b[36], h2b[42] = "a38_h2", "a44_h2"
    _write(mirror, "src/a.py", h2b)
    _write(mirror, "src/b.py", b2)
    _write(mirror, "src/gone.py", gone2)
    shas["H2b"] = commit("H2b")

    r2 = list(h2b)
    r2[39:39] = ["ins1", "ins2"]
    _write(mirror, "src/a.py", r2)
    (mirror / "src" / "gone.py").unlink()
    shas["R2"] = commit("R2")

    _git(mirror, "checkout", "-q", shas["H2"])

    ledger = Ledger(tmp_path / "ledger.db", record=MemoryRecord())
    repo_id = ledger.upsert_repo(
        "acme", "https://example/o", "/m.git", policy_sha="p" * 64
    )
    batch_id = ledger.create_batch(100.0)
    run1 = ledger.create_run(repo_id, base_sha=shas["A"], batch_id=batch_id)
    task1 = ledger.create_task(
        run1, spec_id="TE-1", spec_sha="s" * 64, branch="saffron/TE-1"
    )
    run2 = ledger.create_run(repo_id, base_sha=shas["A"], batch_id=batch_id)
    task2 = ledger.create_task(
        run2, spec_id="TE-2", spec_sha="s" * 64, branch="saffron/TE-2"
    )

    ledger.set_task_package(
        task1, "READY_FOR_REVIEW", "saffron/TE-1", shas["H1"], "https://pr/1"
    )
    ledger.set_task_package(
        task2, "READY_FOR_REVIEW", "saffron/TE-2", shas["H2"], "https://pr/2"
    )
    ledger.record_stack_layer(task1, position=1, predecessor_task_id=None, generation=0)
    ledger.record_stack_layer(
        task2, position=2, predecessor_task_id=task1, generation=0
    )

    te1_key = _key(ledger, task1)
    te2_key = _key(ledger, task2)

    te1_concern = [_finding("correctness", "concern", "src/a.py", 10, "c1-a10")]
    te2_concerns = [
        _finding("correctness", "concern", "src/a.py", 10, "c-a10"),
        _finding("correctness", "concern", "src/a.py", 20, "c-a20"),
        _finding("correctness", "concern", "src/a.py", 38, "c-a38"),
        _finding("correctness", "concern", "src/a.py", 44, "c-a44"),
        _finding("correctness", "concern", "src/gone.py", 2, "c-gone2"),
        _finding("correctness", "concern", "src/b.py", 6, "c-b6"),
        _finding("correctness", "concern", "src/u.py", 3, "c-u3"),
    ]
    te2_end_review = [_finding("spec", "concern", "src/a.py", 10, "er-a10")]

    ledger.record_findings(task1, te1_concern)
    ledger.record_findings(task2, te2_concerns)

    layers = [
        LayerReview(te2_key, [review.LensReview("spec", te2_end_review)]),
        LayerReview(te1_key, []),
    ]

    return _Built(
        ledger,
        layers,
        mirror,
        shas,
        [],
        repo=Path("/repo-sentinel"),
        gates_dir=Path("/gates-sentinel"),
        thread_env={"SENTINEL": "1"},
        test_paths=["tests/**"],
        gates={"tests": Path("/gates-sentinel/tests")},
        created=set(),
        note=lambda step, ok, detail: None,
        join_review=None,
        batch_id=batch_id,
    )


def test_an_in_cell_concern_whose_cited_line_a_review_commit_changed_is_not_drafted(
    tmp_path, monkeypatch
):
    """An in-cell concern still anchors over its packaged range. But it is
    `unverified` when its cited line sits in a hunk of the diff from that
    packaged head to a later graded one. So the writer never drafts a fix
    for code a review commit already changed.
    """
    from saffron.qualify import qualify

    built = _later_diff_fixture(tmp_path, monkeypatch)
    te2_key, te1_key = built.layers[0].task_key, built.layers[1].task_key

    def _raise(*args, **kwargs):
        raise AssertionError("no finding here carries a probe")

    monkeypatch.setattr(session, "probe_findings", _raise)

    fields = {
        te1_key: layer_fields(built.ledger, te1_key),
        te2_key: replace(
            layer_fields(built.ledger, te2_key),
            base=built.shas["H1"],
            diff_base=built.shas["H1"],
            head=built.shas["R2"],
        ),
    }

    result = built.run(qualify, fields=fields)

    pool = {(q.task_key, q.finding.claim): (q.outcome, q.reason) for q in result.pool}
    dropped = ("c-a10", "c-a20", "c-a38", "c-gone2")
    for claim in dropped:
        outcome, reason = pool[(te2_key, claim)]
        assert outcome == "unverified"
        assert f"packaged head {built.shas['H2']}" in reason
        assert f"graded head {built.shas['R2']}" in reason
    assert pool[(te2_key, "c-u3")] == ("unanchored", "")

    groups = {
        (g.task_key, g.file): [f.finding.claim for f in g.findings]
        for g in result.groups
    }
    assert groups == {
        (te2_key, "src/a.py"): ["er-a10", "c-a44"],
        (te2_key, "src/b.py"): ["c-b6"],
        (te1_key, "src/a.py"): ["c1-a10"],
    }

    assert built.batch_id is not None
    written = finish.write_findings(
        built.ledger, built.batch_id, [], tmp_path / "findings.json"
    )
    data = json.loads(written.read_text())
    by_claim = {row["claim"]: row for row in data["findings"]}
    for claim in dropped:
        row = by_claim[claim]
        assert row["outcome"] == "unverified"
        assert f"packaged head {built.shas['H2']}" in row["reason"]
        assert f"graded head {built.shas['R2']}" in row["reason"]
    assert by_claim["c-u3"]["outcome"] == "unanchored"
    for claim in ("er-a10", "c-a44", "c-b6", "c1-a10"):
        assert by_claim[claim]["outcome"] == "follow_up"
