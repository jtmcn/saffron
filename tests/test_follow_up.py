"""`saffron.follow_up` (backlog item b-792ab2, step 7): turning a stack
batch's qualified end-review findings into follow-up spec candidates.

Imported inside each test body, never at module scope. The module does
not exist at this spec's own tree base, and a module-scope import would
fail collection under `revert`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from saffron.agents.artifacts import hash_artifact
from saffron.agents.findings import Finding
from saffron.end_review import LayerReview, StackReview
from saffron.intake import Mutant
from saffron.ledger import Ledger
from saffron.phases import review
from saffron.qualify import FollowUpGroup, Qualification, Qualified
from saffron.record.memory import MemoryRecord

_GIT = ("-c", "user.email=t@example.com", "-c", "user.name=Test")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *_GIT, "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _write(repo: Path, path: str, text: str) -> None:
    full = repo / path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(text)


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _mirror(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """`base`, `H1` and `H2`, as the spec's notes table describes them."""
    mirror = tmp_path / "mirror"
    mirror.mkdir()
    _git(mirror, "init", "-q")
    _write(mirror, "src/a.py", "alpha\n")
    _write(mirror, "src/b.py", "beta\nbeta_l2\n")
    _write(mirror, "src/c.py", "gamma\n")
    _write(mirror, "tests/test_a.py", "def test_a(): pass\n")
    _write(mirror, "tests/test_c.py", "def test_c(): pass\n")
    shas = {"base": _commit(mirror, "base")}
    _write(mirror, "src/a.py", "alpha_new\n")
    _write(mirror, "tests/test_a.py", "def test_a(): assert True\n")
    shas["H1"] = _commit(mirror, "H1")
    _write(mirror, "src/b.py", "beta\nbeta_rate\n")
    _write(mirror, "src/c.py", "gamma gamma\n")
    _write(mirror, "tests/test_b.py", "def test_b(): pass\n")
    shas["H2"] = _commit(mirror, "H2")
    return mirror, shas


def _spec_text(fields: dict, body: str = "Follow-up body.") -> str:
    front = yaml.safe_dump(fields, sort_keys=False)
    return f"---\n{front}---\n{body}\n"


_ONE_MD_FIELDS = {
    "id": "SA-0101",
    "title": "One",
    "type": "feature",
    "budget_usd": 12.0,
    "touches": ["src/a.py"],
}
ONE_MD_TEXT = _spec_text(_ONE_MD_FIELDS)


def _specs_dir(tmp_path: Path) -> Path:
    specs = tmp_path / "specs"
    specs.mkdir()
    _write(specs, "one.md", ONE_MD_TEXT)
    _write(
        specs,
        "SA-0102-two.md",
        _spec_text(
            {
                "id": "SA-0102",
                "title": "Two",
                "type": "feature",
                "budget_usd": 12.0,
                "touches": ["src/b.py"],
            }
        ),
    )
    _write(
        specs,
        "SB-0400-other.md",
        _spec_text({"id": "SB-0400", "title": "Other", "type": "feature"}),
    )
    (specs / "done").mkdir()
    _write(
        specs / "done",
        "SA-0105-old.md",
        _spec_text({"id": "SA-0105", "title": "Old", "type": "feature"}),
    )
    return specs


def _revision(spec_id: str, *, budget: float, body: str) -> str:
    return _spec_text(
        {
            "id": spec_id,
            "title": "Two",
            "type": "feature",
            "budget_usd": budget,
            "touches": ["src/b.py"],
        },
        body=body,
    )


def _build(tmp_path: Path) -> SimpleNamespace:
    """The arrangement every test in this module shares: the mirror's three
    commits, the four spec files, and the five tasks the spec's notes
    describe, in the order given."""
    mirror, shas = _mirror(tmp_path)
    specs_dir = _specs_dir(tmp_path)
    record = MemoryRecord()
    ledger = Ledger(tmp_path / "ledger.db", record=record)
    repo_id = ledger.upsert_repo(
        "acme", "https://example/o", str(mirror), policy_sha=None
    )
    batch_id = ledger.create_batch(100.0)

    run_before = ledger.create_run(repo_id, shas["base"])
    task_before = ledger.create_task(run_before, "SA-0102", "b" * 64, "saffron/before")
    ledger.record_spec_text(
        task_before,
        origin="revision",
        spec_id="SA-0102",
        path=".saffron/specs/SA-0102-two.md",
        text=_revision("SA-0102", budget=9.0, body="before"),
    )

    run_101 = ledger.create_run(repo_id, shas["base"], batch_id)
    task_101 = ledger.create_task(run_101, "SA-0101", "1" * 64, "saffron/SA-0101")
    attempt_101 = ledger.open_attempt(task_101, phase="IMPLEMENTING")
    ledger.close_attempt(
        attempt_101,
        session_id=None,
        subtype="success",
        terminal_reason=None,
        num_turns=5,
        cost_usd_est=0.5,
    )
    ledger.set_task_package(
        task_101, "READY_FOR_REVIEW", "saffron/SA-0101", shas["H1"], "https://pr/101"
    )
    ledger.record_stack_layer(
        task_101, position=1, predecessor_task_id=None, generation=1
    )

    run_102 = ledger.create_run(repo_id, shas["base"], batch_id)
    task_102 = ledger.create_task(run_102, "SA-0102", "2" * 64, "saffron/SA-0102")
    ledger.record_spec_text(
        task_102,
        origin="revision",
        spec_id="SA-0102",
        path=".saffron/specs/SA-0102-two.md",
        text=_revision("SA-0102", budget=9.0, body="draft body"),
    )
    ledger.record_spec_text(
        task_102,
        origin="revision",
        spec_id="SA-0102",
        path=".saffron/specs/SA-0102-two.md",
        text=_revision("SA-0102", budget=10.0, body="revised body"),
    )
    ledger.set_task_package(
        task_102, "READY_FOR_REVIEW", "saffron/SA-0102", shas["H2"], "https://pr/102"
    )
    ledger.record_stack_layer(
        task_102, position=2, predecessor_task_id=task_101, generation=1
    )

    run_after = ledger.create_run(repo_id, shas["base"])
    task_after = ledger.create_task(run_after, "SA-0102", "3" * 64, "saffron/after")
    ledger.record_spec_text(
        task_after,
        origin="revision",
        spec_id="SA-0102",
        path=".saffron/specs/SA-0102-two.md",
        text=_revision("SA-0102", budget=8.0, body="after"),
    )

    run_107 = ledger.create_run(repo_id, shas["base"])
    ledger.create_task(run_107, "SA-0107", "7" * 64, "saffron/SA-0107")

    return SimpleNamespace(
        record=record,
        ledger=ledger,
        repo_id=repo_id,
        batch_id=batch_id,
        mirror=mirror,
        shas=shas,
        specs_dir=specs_dir,
        task_101=task_101,
        task_102=task_102,
        task_before=task_before,
        task_after=task_after,
    )


def _stack(built: SimpleNamespace) -> StackReview:
    key_101 = built.ledger.record_key(built.task_101)
    key_102 = built.ledger.record_key(built.task_102)
    return StackReview(
        join=review.LensReview("join", []),
        layers=[LayerReview(key_102, []), LayerReview(key_101, [])],
    )


def _finding(lens, severity, file, line, claim, probe=None, verdict=None) -> Finding:
    finding = Finding(
        lens=lens, severity=severity, file=file, line=line, claim=claim, probe=probe
    )
    if verdict is not None:
        finding.probe_verdict = verdict
    return finding


def _q(task_key: str, finding: Finding) -> Qualified:
    return Qualified(task_key=task_key, finding=finding, outcome="qualified", reason="")


def _candidate(
    id_: str,
    *,
    type_: str = "feature",
    budget: float = 10.0,
    touches: tuple[str, ...] = ("src/b.py", "tests/test_b.py"),
    depends_on: tuple[str, ...] = (),
    title: str = "A layer's rate, re-read",
    claims: tuple[str, ...] = ("claim-rate", "claim-concern-b"),
    mutant: tuple[str, str, str] | None = None,
) -> str:
    acceptance = []
    for i, claim in enumerate(claims):
        entry: dict = {"claim": claim, "witness": f"tests/test_b.py::test_w{i}"}
        if mutant is not None and i == 0:
            entry["mutant"] = {
                "file": mutant[0],
                "find": mutant[1],
                "replace": mutant[2],
            }
        acceptance.append(entry)
    fields: dict = {
        "id": id_,
        "title": title,
        "type": type_,
        "budget_usd": budget,
        "touches": list(touches),
        "acceptance": acceptance,
    }
    if depends_on:
        fields["depends_on"] = list(depends_on)
    return _spec_text(fields)


def _mint_stub(ledger: Ledger, repo_id: int, base_sha: str, calls: list):
    def mint(candidate):
        calls.append(candidate)
        run_id = ledger.create_run(repo_id, base_sha)
        return ledger.create_task(
            run_id,
            candidate.spec.id,
            candidate.spec_sha,
            f"saffron/{candidate.spec.id}",
            risk=candidate.spec.risk,
            budget_usd=candidate.spec.budget_usd,
        )

    return mint


def _write_stub(calls: list, turns: list):
    def write(group, prompt):
        calls.append((group, prompt))
        turn = turns[len(calls) - 1]
        if isinstance(turn, BaseException):
            raise turn
        from saffron import spec_review

        if isinstance(turn, spec_review.SpecWriterSession):
            return turn
        return spec_review.SpecWriterSession(
            text=turn,
            cost_usd=0.25,
            error=None,
            resets_at=None,
            session_id=f"s{len(calls)}",
            num_turns=3,
            spec_sha=hash_artifact(turn),
        )

    return write


def _qualify_stub(calls: list, groups: list[FollowUpGroup], pool: list[Qualified]):
    def qualify(layers, join):
        calls.append((layers, join))
        return Qualification(groups=list(groups), pool=list(pool))

    return qualify


def _eighteen_groups(
    key_101: str, key_102: str, *, findings: dict
) -> list[FollowUpGroup]:
    def g(file, *keyed):
        return FollowUpGroup(task_key=key_102, file=file, findings=tuple(keyed))

    return [
        g(
            "src/b.py",
            _q(key_102, findings["rate"]),
            _q(key_102, findings["concern_b"]),
            _q(key_102, findings["gone"]),
        ),  # 1
        FollowUpGroup(
            task_key=key_101,
            file="src/a.py",
            findings=(_q(key_101, findings["concern_a"]),),
        ),  # 2
        g("src/b.py", _q(key_102, findings["concern_b"])),  # 3
        g("src/b.py", _q(key_102, findings["concern_b"])),  # 4
        g("src/b.py", _q(key_102, findings["concern_b"])),  # 5
        g("src/b.py", _q(key_102, findings["concern_b"])),  # 6
        g("src/b.py", _q(key_102, findings["concern_b"])),  # 7
        g("src/b.py", _q(key_102, findings["concern_b"])),  # 8
        g(
            "src/b.py", _q(key_102, findings["rate"]), _q(key_102, findings["gone"])
        ),  # 9
        g("src/b.py", _q(key_102, findings["concern_b"])),  # 10
        g("src/b.py", _q(key_102, findings["concern_b"])),  # 11
        g("src/b.py", _q(key_102, findings["concern_b"])),  # 12
        g("src/b.py", _q(key_102, findings["concern_b"])),  # 13
        g("src/b.py", _q(key_102, findings["concern_b"])),  # 14
        FollowUpGroup(
            task_key=key_101,
            file="src/b.py",
            findings=(_q(key_101, findings["gone"]), _q(key_101, findings["lost"])),
        ),  # 15
        g("src/c.py", _q(key_102, findings["gamma"])),  # 16
        g("src/b.py", _q(key_102, findings["rate"])),  # 17
        g("src/b.py", _q(key_102, findings["concern_b"])),  # 18
    ]


def _shared_findings() -> dict:
    return {
        "rate": _finding(
            "spec",
            "blocker",
            "src/b.py",
            2,
            "claim-rate",
            Mutant(file="src/b.py", find="beta_rate", replace="beta_slow"),
            "survived",
        ),
        "gone": _finding(
            "spec",
            "blocker",
            "src/b.py",
            2,
            "claim-gone",
            Mutant(file="src/b.py", find="beta_l2", replace="beta_dead"),
            "survived",
        ),
        "lost": _finding(
            "spec",
            "blocker",
            "src/b.py",
            3,
            "claim-lost",
            Mutant(file="src/gone.py", find="alpha", replace="alpha_dead"),
            "survived",
        ),
        "concern_b": _finding("spec", "concern", "src/b.py", 1, "claim-concern-b"),
        "concern_a": _finding("spec", "concern", "src/a.py", 1, "claim-concern-a"),
        "gamma": _finding(
            "adequacy",
            "blocker",
            "src/c.py",
            1,
            "claim-gamma",
            Mutant(file="src/c.py", find="gamma", replace="delta"),
            "survived",
        ),
    }


def _eighteen_turns() -> list:
    from saffron import spec_review

    return [
        _candidate("SA-0108", mutant=("src/b.py", "not_here", "y")),  # 1 accepted
        _candidate(
            "SA-0109",
            budget=11.0,
            touches=("src/a.py", "tests/test_b.py"),
            title="Alpha note",
            claims=("claim-concern-a",),
        ),  # 2 accepted
        _candidate("SA-0999", claims=("claim-concern-b",)),  # 3 id
        _candidate("SA-0110", type_="refactor", claims=("claim-concern-b",)),  # 4 type
        _candidate(
            "SA-0110", depends_on=("SA-0001",), claims=("claim-concern-b",)
        ),  # 5 depends_on
        _candidate("SA-0110", budget=11.0, claims=("claim-concern-b",)),  # 6 budget
        _candidate(
            "SA-0110", touches=("src/**",), claims=("claim-concern-b",)
        ),  # 7 touches (glob)
        _candidate(
            "SA-0110", touches=(), claims=("claim-concern-b",)
        ),  # 8 touches (empty)
        _candidate(
            "SA-0110",
            claims=("claim-rate",),
            mutant=("src/b.py", "beta_rate", "beta_x"),
        ),  # 9 mutant
        _candidate(
            "SA-0110",
            touches=("src/b.py", "src/c.py"),
            claims=("claim-concern-b",),
        ),  # 10 touches (unchanged file)
        _candidate(
            "SA-0110",
            touches=("src/b.py", "tests/test_c.py"),
            claims=("claim-concern-b",),
        ),  # 11 touches (untouched test)
        "not a spec at all\n",  # 12 parse
        spec_review.SpecWriterSession(
            text="",
            cost_usd=0.25,
            error="idle bound",
            resets_at=None,
            session_id="s13",
            num_turns=3,
            spec_sha=None,
        ),  # 13 error
        RuntimeError("cell gone"),  # 14 raise
        _candidate(
            "SA-0110",
            title="(-)",
            claims=("claim-rate",),
            mutant=("src/c.py", "beta_rate", "beta_z"),
        ),  # 17 accepted
    ]


def test_a_group_the_host_refuses_or_the_sub_cap_cannot_cover_goes_to_the_pool(
    tmp_path, monkeypatch
):
    from saffron import follow_up, spec_review

    monkeypatch.setattr(spec_review, "SPEC_WRITER_SESSION_USD", 1.0)

    built = _build(tmp_path)
    stack = _stack(built)
    key_101 = built.ledger.record_key(built.task_101)
    key_102 = built.ledger.record_key(built.task_102)
    findings = _shared_findings()
    groups = _eighteen_groups(key_101, key_102, findings=findings)
    pool = [
        Qualified(
            key_102,
            _finding("spec", "note", "src/z.py", 1, "stray-1"),
            "unanchored",
            "",
        ),
        Qualified(
            key_102, _finding("spec", "note", "src/z.py", 2, "stray-2"), "note", ""
        ),
    ]

    qualify_calls: list = []
    write_calls: list = []
    mint_calls: list = []
    pooled: list = []
    emitted: list = []

    candidates = follow_up.write_follow_ups(
        built.ledger,
        stack,
        batch_key=str(built.batch_id),
        qualify=_qualify_stub(qualify_calls, groups, pool),
        write=_write_stub(write_calls, _eighteen_turns()),
        mint=_mint_stub(built.ledger, built.repo_id, built.shas["base"], mint_calls),
        mirror=built.mirror,
        specs_dir=built.specs_dir,
        repo_id=built.repo_id,
        test_paths=["tests/**"],
        cap_usd=4.25,
        emit=emitted.append,
        pooled=pooled,
    )

    assert qualify_calls == [(stack.layers, stack.join)]
    assert len(emitted) == 18
    assert "2" in emitted[0]
    assert len(write_calls) == 15
    assert len(candidates) == 3
    assert len(pooled) == 17

    got_claims = [tuple(q.finding.claim for q in p.group.findings) for p in pooled]
    assert got_claims == [
        ("claim-gone",),
        ("claim-concern-b",),
        ("claim-concern-b",),
        ("claim-concern-b",),
        ("claim-concern-b",),
        ("claim-concern-b",),
        ("claim-concern-b",),
        ("claim-gone",),
        ("claim-rate",),
        ("claim-concern-b",),
        ("claim-concern-b",),
        ("claim-concern-b",),
        ("claim-concern-b",),
        ("claim-concern-b",),
        ("claim-gone", "claim-lost"),
        ("claim-gamma",),
        ("claim-concern-b",),
    ]
    assert pooled[14].group.task_key == key_101
    for reason, needle in [
        (pooled[0].reason, "probe"),
        (pooled[1].reason, "id"),
        (pooled[2].reason, "type"),
        (pooled[3].reason, "depends_on"),
        (pooled[4].reason, "budget"),
        (pooled[5].reason, "touches"),
        (pooled[6].reason, "touches"),
        (pooled[7].reason, "probe"),
        (pooled[8].reason, "mutant"),
        (pooled[9].reason, "touches"),
        (pooled[10].reason, "touches"),
        (pooled[11].reason, "parse"),
        (pooled[12].reason, "error"),
        (pooled[13].reason, "raise"),
        (pooled[14].reason, "probe"),
        (pooled[15].reason, "probe"),
        (pooled[16].reason, "sub-cap"),
    ]:
        assert needle in reason, reason

    assert len(built.ledger.attempts(built.task_101)) == 1
    assert built.ledger.attempts(built.task_101)[0]["phase"] == "IMPLEMENTING"
    assert built.ledger.attempts(built.task_before) == []
    assert built.ledger.attempts(built.task_after) == []
    writing = [
        a
        for a in built.ledger.attempts(built.task_102)
        if a["phase"] == spec_review.WRITING_PHASE
    ]
    assert len(writing) == 11
    assert [a["subtype"] for a in writing].count("error") == 1
    assert built.ledger.batch_spend(built.batch_id) == pytest.approx(4.0)

    # SA-0110 is the highest id now, so the calls below start at SA-0111.

    # A reset time met earlier pools every later group with it too.
    reset_pool: list = []
    reset_calls: list = []
    reset_groups = [
        FollowUpGroup(key_102, "src/b.py", (_q(key_102, findings["concern_b"]),))
        for _ in range(3)
    ]
    reset_session = spec_review.SpecWriterSession(
        text="",
        cost_usd=0.1,
        error=None,
        resets_at=99999999,
        session_id="r1",
        num_turns=1,
        spec_sha=None,
    )
    reset_candidates = follow_up.write_follow_ups(
        built.ledger,
        stack,
        batch_key=str(built.batch_id),
        qualify=_qualify_stub([], reset_groups, []),
        write=_write_stub(reset_calls, [reset_session]),
        mint=_mint_stub(built.ledger, built.repo_id, built.shas["base"], []),
        mirror=built.mirror,
        specs_dir=built.specs_dir,
        repo_id=built.repo_id,
        test_paths=["tests/**"],
        cap_usd=50.0,
        emit=lambda line: None,
        pooled=reset_pool,
    )
    assert reset_candidates == []
    assert len(reset_calls) == 1
    assert len(reset_pool) == 3
    assert all("rate limit" in p.reason for p in reset_pool)
    reset_writing = [
        a
        for a in built.ledger.attempts(built.task_102)
        if a["phase"] == spec_review.WRITING_PHASE
    ]
    assert len(reset_writing) == 12

    # `test_paths` that match nothing changed in the stack's range pools
    # every group with no write call at all.
    notest_pool: list = []
    notest_calls: list = []
    one_group = [
        FollowUpGroup(key_102, "src/b.py", (_q(key_102, findings["concern_b"]),))
    ]
    notest_candidates = follow_up.write_follow_ups(
        built.ledger,
        stack,
        batch_key=str(built.batch_id),
        qualify=_qualify_stub([], one_group, []),
        write=_write_stub(notest_calls, []),
        mint=_mint_stub(built.ledger, built.repo_id, built.shas["base"], []),
        mirror=built.mirror,
        specs_dir=built.specs_dir,
        repo_id=built.repo_id,
        test_paths=["spec/**"],
        cap_usd=50.0,
        emit=lambda line: None,
        pooled=notest_pool,
    )
    assert notest_candidates == []
    assert notest_calls == []
    assert len(notest_pool) == 1
    assert "test path" in notest_pool[0].reason

    # `mint` raising propagates, leaving `pooled` holding whatever was
    # already decided.
    raise_pool: list = []
    two_groups = [
        FollowUpGroup(key_102, "src/b.py", (_q(key_102, findings["concern_b"]),)),
        FollowUpGroup(key_102, "src/b.py", (_q(key_102, findings["concern_b"]),)),
    ]
    turns = [
        _candidate("SA-0999", claims=("claim-concern-b",)),
        _candidate("SA-0111", claims=("claim-concern-b",)),
    ]

    def _raising_mint(candidate):
        raise RuntimeError("mint down")

    with pytest.raises(RuntimeError, match="mint down"):
        follow_up.write_follow_ups(
            built.ledger,
            stack,
            batch_key=str(built.batch_id),
            qualify=_qualify_stub([], two_groups, []),
            write=_write_stub([], turns),
            mint=_raising_mint,
            mirror=built.mirror,
            specs_dir=built.specs_dir,
            repo_id=built.repo_id,
            test_paths=["tests/**"],
            cap_usd=50.0,
            emit=lambda line: None,
            pooled=raise_pool,
        )
    assert len(raise_pool) == 1
    assert "id" in raise_pool[0].reason


def test_an_accepted_follow_up_is_a_minted_task_with_its_text_and_its_writers_cost(
    tmp_path, monkeypatch
):
    from saffron import follow_up, spec_review

    monkeypatch.setattr(spec_review, "SPEC_WRITER_SESSION_USD", 1.0)

    built = _build(tmp_path)
    stack = _stack(built)
    key_101 = built.ledger.record_key(built.task_101)
    key_102 = built.ledger.record_key(built.task_102)
    findings = _shared_findings()
    groups = _eighteen_groups(key_101, key_102, findings=findings)
    turns = _eighteen_turns()

    write_calls: list = []
    mint_calls: list = []
    pooled: list = []

    candidates = follow_up.write_follow_ups(
        built.ledger,
        stack,
        batch_key=str(built.batch_id),
        qualify=_qualify_stub([], groups, []),
        write=_write_stub(write_calls, turns),
        mint=_mint_stub(built.ledger, built.repo_id, built.shas["base"], mint_calls),
        mirror=built.mirror,
        specs_dir=built.specs_dir,
        repo_id=built.repo_id,
        test_paths=["tests/**"],
        cap_usd=4.25,
        emit=lambda line: None,
        pooled=pooled,
    )

    assert [c.spec.id for c in candidates] == ["SA-0108", "SA-0109", "SA-0110"]
    assert candidates[0].path == Path(
        ".saffron/specs/SA-0108-a-layer-s-rate-re-read.md"
    )
    assert candidates[2].path == Path(".saffron/specs/SA-0110-follow-up.md")
    assert candidates[1].path.name.startswith("SA-0109-")

    assert all(c.task_id is None for c in mint_calls)
    other_ids = {built.task_101, built.task_102, built.task_before, built.task_after}
    for c in candidates:
        assert c.task_id is not None
        assert c.task_id not in other_ids

    for c in candidates:
        attempts = built.ledger.attempts(c.task_id)
        assert len(attempts) == 1
        attempt = attempts[0]
        assert attempt["phase"] == spec_review.WRITING_PHASE
        assert attempt["cost_usd_est"] == pytest.approx(0.25)
        assert attempt["num_turns"] == 3
        assert attempt["session_id"].startswith("s")

        row = built.ledger.spec_text(c.task_id)
        assert row["origin"] == "follow_up"
        assert row["spec_id"] == c.spec.id
        assert row["path"] == str(c.path)
        assert row["spec_sha"] == hash_artifact(row["text"])

        facts = built.record.read(built.ledger.record_key(c.task_id))
        assert [f.kind for f in facts] == [
            "task_created",
            "attempt_opened",
            "attempt_closed",
            "spec_text",
        ]
        assert facts[1].batch_key is None
        assert facts[2].batch_key is None
        assert facts[3].batch_key == str(built.batch_id)

    assert candidates[0].spec_sha == hash_artifact(turns[0])

    prompt1 = write_calls[0][1]
    assert "SA-0108" in prompt1
    assert "budget_usd must not exceed 10.0" in prompt1
    assert "tests/test_a.py" in prompt1
    assert "tests/test_b.py" in prompt1
    assert "claim-rate" in prompt1
    assert "claim-concern-b" in prompt1
    assert "src/b.py:2" in prompt1
    assert "beta_rate" in prompt1
    assert "beta_slow" in prompt1
    assert "survived" in prompt1
    assert "revised body" in prompt1
    assert "+beta_rate" in prompt1
    assert built.shas["H2"] in prompt1
    assert "claim-gone" not in prompt1
    assert "draft body" not in prompt1
    assert "before" not in prompt1
    assert "after" not in prompt1
    assert "alpha_new" not in prompt1

    prompt2 = write_calls[1][1]
    assert "SA-0109" in prompt2
    assert "src/a.py" in prompt2
    assert "tests/test_b.py" in prompt2
    assert "+alpha_new" in prompt2
    assert built.shas["H1"] in prompt2
    assert built.shas["H2"] in prompt2
    assert ONE_MD_TEXT in prompt2
    assert "+beta_rate" not in prompt2


def test_a_hundred_dollar_night_writes_one_follow_up_at_the_writer_ceiling(tmp_path):
    from saffron import follow_up, spec_review

    assert follow_up.WRITER_SHARE == 0.25

    built = _build(tmp_path)
    stack = _stack(built)
    key_102 = built.ledger.record_key(built.task_102)
    concern = _finding("spec", "concern", "src/b.py", 1, "claim-concern-b")
    groups = [
        FollowUpGroup(key_102, "src/b.py", (_q(key_102, concern),)) for _ in range(3)
    ]
    ids = ["SA-0108", "SA-0109", "SA-0110"]

    def write(group, prompt):
        text = _candidate(ids[len(calls)], claims=("claim-concern-b",))
        calls.append(text)
        return spec_review.SpecWriterSession(
            text=text,
            cost_usd=spec_review.SPEC_WRITER_SESSION_USD,
            error=None,
            resets_at=None,
            session_id=f"w{len(calls)}",
            num_turns=2,
            spec_sha=hash_artifact(text),
        )

    calls: list = []
    pooled: list = []
    candidates = follow_up.write_follow_ups(
        built.ledger,
        stack,
        batch_key=str(built.batch_id),
        qualify=_qualify_stub([], groups, []),
        write=write,
        mint=_mint_stub(built.ledger, built.repo_id, built.shas["base"], []),
        mirror=built.mirror,
        specs_dir=built.specs_dir,
        repo_id=built.repo_id,
        test_paths=["tests/**"],
        cap_usd=25.0,  # a $100 night's share, pinned apart from WRITER_SHARE itself
        emit=lambda line: None,
        pooled=pooled,
    )
    assert [c.spec.id for c in candidates] == ["SA-0108"]
    assert len(pooled) == 2


@pytest.mark.parametrize(
    "share, expected", [(0.18, []), (0.37, ["SA-0108", "SA-0109"])]
)
def test_a_sub_cap_of_18_dollars_writes_none_and_37_writes_two(
    tmp_path, share, expected
):
    from saffron import follow_up, spec_review

    built = _build(tmp_path)
    stack = _stack(built)
    key_102 = built.ledger.record_key(built.task_102)
    concern = _finding("spec", "concern", "src/b.py", 1, "claim-concern-b")
    groups = [
        FollowUpGroup(key_102, "src/b.py", (_q(key_102, concern),)) for _ in range(3)
    ]
    ids = ["SA-0108", "SA-0109", "SA-0110"]

    def write(group, prompt):
        text = _candidate(ids[len(calls)], claims=("claim-concern-b",))
        calls.append(text)
        return spec_review.SpecWriterSession(
            text=text,
            cost_usd=spec_review.SPEC_WRITER_SESSION_USD,
            error=None,
            resets_at=None,
            session_id=f"w{len(calls)}",
            num_turns=2,
            spec_sha=hash_artifact(text),
        )

    calls: list = []
    pooled: list = []
    candidates = follow_up.write_follow_ups(
        built.ledger,
        stack,
        batch_key=str(built.batch_id),
        qualify=_qualify_stub([], groups, []),
        write=write,
        mint=_mint_stub(built.ledger, built.repo_id, built.shas["base"], []),
        mirror=built.mirror,
        specs_dir=built.specs_dir,
        repo_id=built.repo_id,
        test_paths=["tests/**"],
        cap_usd=100.0 * share,
        emit=lambda line: None,
        pooled=pooled,
    )
    assert [c.spec.id for c in candidates] == expected


def test_the_next_spec_id_reads_both_spec_directories_and_the_repos_tasks(tmp_path):
    from saffron.follow_up import next_spec_id

    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "SA-0003-x.md").write_text("not a real spec\n")
    (specs / "SB-0900-x.md").write_text("not a real spec\n")
    # A name that carries "SA-0950" past its own start, so a pattern not
    # anchored on the prefix would read 950 as an SA number here.
    (specs / "ZSA-0950-decoy.md").write_text("not a real spec\n")
    (specs / "SA9999-nohyphen.md").write_text("not a real spec\n")
    ledger = Ledger(tmp_path / "ledger.db", record=MemoryRecord())
    repo_id = ledger.upsert_repo("acme", "https://example/o", "/m.git", policy_sha=None)
    other_repo_id = ledger.upsert_repo(
        "other", "https://example/o2", "/m2.git", policy_sha=None
    )

    assert next_spec_id("SA-0001", specs, ledger, repo_id) == "SA-0004"

    (specs / "done").mkdir()
    (specs / "done" / "SA-0012-y.md").write_text("not a real spec\n")
    assert next_spec_id("SA-0001", specs, ledger, repo_id) == "SA-0013"

    run = ledger.create_run(other_repo_id, base_sha="a" * 40)
    ledger.create_task(run, "SA-0090", "s" * 64, "saffron/SA-0090")
    assert next_spec_id("SA-0001", specs, ledger, repo_id) == "SA-0013"

    run = ledger.create_run(repo_id, base_sha="a" * 40)
    ledger.create_task(run, "SA-0020", "s" * 64, "saffron/SA-0020")
    assert next_spec_id("SA-0001", specs, ledger, repo_id) == "SA-0021"

    assert next_spec_id("SB-01", specs, ledger, repo_id) == "SB-901"


def test_a_stack_with_no_layers_writes_nothing_and_raises_nothing(tmp_path):
    from saffron import follow_up

    built = _build(tmp_path)
    lines: list[str] = []
    candidates = follow_up.write_follow_ups(
        built.ledger,
        StackReview(join=None, layers=[]),
        batch_key=str(built.batch_id),
        qualify=_qualify_stub([], [], []),
        write=lambda group, prompt: pytest.fail("no layer, no session"),
        mint=_mint_stub(built.ledger, built.repo_id, built.shas["base"], []),
        mirror=built.mirror,
        specs_dir=built.specs_dir,
        repo_id=built.repo_id,
        test_paths=["tests/**"],
        cap_usd=50.0,
        emit=lines.append,
        pooled=[],
    )
    assert candidates == []
    assert lines == ["0 qualified findings joined no group"]
