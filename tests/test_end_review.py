"""The end review's lenses, `review_stack`, the join lens, `run_end_review`,
`layer_cell` and `Ledger.record_end_review`. `saffron.end_review` is
imported inside every test body here, never at module scope. It does not
exist at this spec's own tree base, and a module-scope import would fail collection
under `revert`.
"""

from __future__ import annotations

import dataclasses
import json
import re
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

import pytest

from saffron.agents import context
from saffron.agents.findings import Finding
from saffron.intake import Criterion, Mutant, Spec
from saffron.ledger import Ledger
from saffron.phases import implement, review
from saffron.record.fold import fold
from saffron.record.memory import MemoryRecord

PROMPTS = Path(review.__file__).resolve().parents[1] / "agents" / "prompts"
CONTEXT_MD = (Path(__file__).resolve().parents[1] / "CONTEXT.md").read_text()

_FOURTEEN = (
    ".claude",
    "claude.md",
    "context.md",
    "design.md",
    "driver.py",
    "pytest",
    "uv run",
    "make check",
    "ruff",
    "prek",
    "saffron/",
    "docs/",
    "/opt/",
    "://",
)


def _sha(ch: str) -> str:
    return ch * 40


def _flatten(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _block(findings: list[dict]) -> str:
    return f"Here it is.\n<output>\n{json.dumps({'findings': findings})}\n</output>"


def _turn(text: str, cost: float = 0.1) -> implement.AttemptResult:
    return implement.AttemptResult(
        session_id="s1",
        subtype="success",
        terminal_reason="completed",
        num_turns=1,
        cost_usd_est=cost,
        text=text,
    )


def _scripted(calls: list[dict], script: list):
    remaining = list(script)

    def run(container, *, prompt, options, **kwargs):
        calls.append(
            {
                "container": container,
                "prompt": prompt,
                "options": options,
                "kwargs": kwargs,
            }
        )
        if not remaining:
            raise AssertionError("agent double exhausted, no reply left")
        outcome = remaining.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    return run


def test_a_layers_fields_come_from_its_own_row_and_its_own_task(tmp_path):
    """`layer_fields` reads one layer's `stack_layers` row, its own task and
    its own run, never a fresh read of a predecessor's current head."""
    import saffron.end_review as end_review

    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("r", "/o", "/m.git", policy_sha="p" * 64)

    def _run(letter: str) -> int:
        return ledger.create_run(repo_id, base_sha=_sha(letter))

    def _task(run_id: int, spec_id: str, branch: str) -> int:
        return ledger.create_task(
            run_id, spec_id=spec_id, spec_sha="s" * 64, branch=branch
        )

    run_9a = _run("b")
    task_9a = _task(run_9a, "TE-9", "saffron/TE-9-a")
    ledger.record_push(task_9a, _sha("a"))
    ledger.set_task_state(task_9a, "EXHAUSTED")
    ledger.record_findings(
        task_9a,
        [
            Finding(
                lens="correctness", severity="concern", file="q.py", line=1, claim="c6"
            )
        ],
    )

    run_7 = _run("d")
    task_7 = _task(run_7, "TE-7", "saffron/TE-7")
    ledger.set_task_package(
        task_7, "READY_FOR_REVIEW", "saffron/TE-7", _sha("7"), "https://h/pull/7"
    )
    ledger.record_findings(
        task_7,
        [
            Finding(
                lens="correctness", severity="concern", file="q.py", line=1, claim="c5"
            )
        ],
    )

    run_9 = _run("b")
    task_9 = _task(run_9, "TE-9", "saffron/TE-9")
    ledger.set_task_package(
        task_9, "READY_FOR_REVIEW", "saffron/TE-9", _sha("9"), "https://h/pull/9"
    )

    findings = [
        Finding(
            lens="correctness",
            severity="blocker",
            file="z.py",
            line=8,
            claim="q first half\nsecond half",
            anchored=True,
        ),
        Finding(
            lens="adequacy", severity="note", file="y.py", line=5, claim="k middle"
        ),
        Finding(
            lens="contract",
            severity="concern",
            file="x.py",
            line=3,
            claim="b last {braces}",
            anchored=True,
        ),
        Finding(lens="spec", severity="concern", file="x.py", line=4, claim="c4"),
        Finding(lens="standards", severity="concern", file="x.py", line=4, claim="c7"),
        Finding(lens="join", severity="concern", file="x.py", line=4, claim="c8"),
    ]
    ids = ledger.record_findings(task_9, findings)
    ledger.record_rebuttal(ids[2], verdict="withdrawn", rebuttal="r1\n  argued")

    run_9c = _run("b")
    task_9c = _task(run_9c, "TE-9", "saffron/TE-9-c")
    ledger.record_push(task_9c, _sha("f"))
    ledger.set_task_state(task_9c, "EXHAUSTED")

    run_11 = _run("b")
    task_11 = _task(run_11, "TE-11", "saffron/TE-11")

    run_12 = _run("b")
    task_12 = _task(run_12, "TE-12", "saffron/TE-12")
    ledger.record_push(task_12, _sha("c"))

    ledger.record_stack_layer(
        task_7, position=1, predecessor_task_id=None, generation=1
    )
    ledger.record_stack_layer(
        task_9, position=2, predecessor_task_id=task_7, generation=1
    )
    ledger.record_push(task_7, _sha("e"))
    ledger.record_stack_layer(
        task_11, position=3, predecessor_task_id=task_9, generation=1
    )
    ledger.record_stack_layer(
        task_12, position=4, predecessor_task_id=task_11, generation=1
    )

    key_7 = ledger.record_key(task_7)
    key_9 = ledger.record_key(task_9)
    key_9c = ledger.record_key(task_9c)
    key_11 = ledger.record_key(task_11)
    key_12 = ledger.record_key(task_12)
    assert key_7 is not None
    assert key_9 is not None
    assert key_9c is not None
    assert key_11 is not None
    assert key_12 is not None

    fields_9 = end_review.layer_fields(ledger, key_9)
    assert fields_9.spec_id == "TE-9"
    assert fields_9.branch == "saffron/TE-9"
    assert fields_9.pr_url == "https://h/pull/9"
    # The head T7 had when T9's layer was recorded, not T7's later repush.
    assert fields_9.base == _sha("7")
    assert fields_9.head == _sha("9")

    fields_7 = end_review.layer_fields(ledger, key_7)
    assert fields_7.base == _sha("d")
    assert fields_7.head == _sha("e")

    lines = fields_9.known.splitlines()
    assert len(lines) == 3
    assert "q first half second half" in lines[0]
    assert "blocker" in lines[0]
    assert "correctness" in lines[0]
    assert "z.py:8" in lines[0]
    assert "k middle" in lines[1]
    assert "note" in lines[1]
    assert "adequacy" in lines[1]
    assert "y.py:5" in lines[1]
    assert "b last {braces}" in lines[2]
    assert "concern" in lines[2]
    assert "contract" in lines[2]
    assert "x.py:3" in lines[2]
    assert "withdrawn" in lines[2]
    assert "r1 argued" in lines[2]

    for excluded in ("c4", "c7", "c8", "c5", "c6"):
        assert excluded not in fields_9.known

    with pytest.raises(ValueError):
        end_review.layer_fields(ledger, key_9c)
    with pytest.raises(ValueError):
        end_review.layer_fields(ledger, key_11)
    with pytest.raises(ValueError):
        end_review.layer_fields(ledger, key_12)

    ledger.close()


def test_each_end_review_prompt_is_its_own_file_filled_with_the_layers_fields():
    """Each lens's file, filled through `context.build_system_prompt`,
    carries every one of `LayerFields`'s values verbatim. Each raw file
    carries its own required prose, with no fact this repository owns."""
    import saffron.end_review as end_review

    fields = end_review.LayerFields(
        spec_id="TE-9",
        branch="saffron/layer-b",
        pr_url="https://h/pull/41",
        base="7",
        head="9",
        known="- concern (contract) x.py:3: b last {braces}",
    )
    spec_body = "Fix the {gap}, and keep {{this}} as written."
    diff = (
        "diff --git a/x.py b/x.py\n"
        "--- a/x.py\n"
        "+++ b/x.py\n"
        "@@ -1 +1 @@\n"
        "-old {}\n"
        "+new {}\n"
    )
    acceptance = [
        Criterion(claim="Does the plain thing", witness="tests/test_a.py::test_plain"),
        Criterion(
            claim="Still holds the old thing",
            witness="tests/test_b.py::test_old",
            preserves=True,
        ),
        Criterion(
            claim="Does another plain thing", witness="tests/test_c.py::test_more"
        ),
    ]
    touches = ["saffron/foo.py"]
    forbidden = ["saffron/bar.py"]
    claude_md = "Line one of the standards.\nLine two of the standards."

    # `END_LENSES` is read in this order: the Spec lens's prompt is built
    # and run before the Standards lens's, both here and in `review_layer`.
    assert list(end_review.END_LENSES) == ["spec", "standards"]

    for lens in end_review.END_LENSES:
        prompt = end_review.end_review_prompt(
            lens,
            fields,
            spec_body=spec_body,
            diff=diff,
            acceptance=acceptance,
            touches=touches,
            forbidden=forbidden,
            context_md=CONTEXT_MD,
            claude_md=claude_md,
            prompts_dir=PROMPTS,
        )
        flat = _flatten(prompt)
        for value in (
            fields.spec_id,
            fields.branch,
            fields.pr_url,
            fields.base,
            fields.head,
            fields.known,
        ):
            assert _flatten(value) in flat
        assert f"{fields.base}..{fields.head}" in flat
        assert _flatten(diff) in flat
        assert _flatten(spec_body) in flat
        assert _flatten(context.standing_instructions(claude_md)) in flat
        assert _flatten(context.sections_for("REVIEW", CONTEXT_MD)) in flat

        raw = (PROMPTS / end_review.END_LENSES[lens]).read_text()
        raw_flat = _flatten(raw)
        assert _flatten(raw.split("{")[0]) in flat, "each lens fills its own file"
        assert "do not manufacture one" in raw_flat.lower()
        for token in (
            "`blocker`",
            "`concern`",
            "`note`",
            "`file`",
            "`line`",
            "`severity`",
            "`claim`",
        ):
            assert token in raw_flat
        raw_lower = raw_flat.lower()
        for forbidden_string in _FOURTEEN:
            assert forbidden_string not in raw_lower

    spec_prompt = end_review.end_review_prompt(
        "spec",
        fields,
        spec_body=spec_body,
        diff=diff,
        acceptance=acceptance,
        touches=touches,
        forbidden=forbidden,
        context_md=CONTEXT_MD,
        claude_md=claude_md,
        prompts_dir=PROMPTS,
    )
    spec_flat = _flatten(spec_prompt)
    for criterion in acceptance:
        assert _flatten(criterion.claim) in spec_flat
        assert criterion.witness in spec_flat
    # The preserving criterion sits in the middle, so the tag tracks its flag.
    assert f"{acceptance[1].witness}` (preserves)" in spec_flat
    assert spec_flat.count("(preserves)") == 1
    assert _flatten(context.constraints_block(touches, forbidden, [])) in spec_flat

    spec_raw = _flatten((PROMPTS / "end-review-spec.md").read_text())
    for token in ("`probe`", "`find`", "`replace`"):
        assert token in spec_raw

    standards_raw = _flatten((PROMPTS / "end-review-standards.md").read_text())
    assert "`probe`" not in standards_raw
    standards_lower = standards_raw.lower()
    assert "never against a file in the worktree" in standards_lower
    assert "is saffron's process glossary, not this repository's" in standards_lower
    from saffron.cell.worktree import WORKTREE_MOUNT

    assert WORKTREE_MOUNT not in standards_raw


def test_a_layer_is_read_by_the_spec_lens_then_the_standards_lens():
    """`review_layer` runs the Spec lens and then the Standards lens
    through `review.run_lens`, each a fresh session. The second runs
    whether or not the first came back with an error."""
    import saffron.end_review as end_review

    fields = end_review.LayerFields(
        spec_id="TE-3",
        branch="saffron/layer-c",
        pr_url="https://h/pull/3",
        base="base1",
        head="head1",
        known="",
    )
    diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,2 +1,2 @@\n-old\n+new\n"
    acceptance = [Criterion(claim="c", witness="tests/x.py::t")]
    touches = ["saffron/x.py"]
    forbidden = ["saffron/y.py"]

    def _expected_prompt(lens: str) -> str:
        return end_review.end_review_prompt(
            lens,
            fields,
            spec_body="fix it",
            diff=diff,
            acceptance=acceptance,
            touches=touches,
            forbidden=forbidden,
            context_md=CONTEXT_MD,
            claude_md=None,
            prompts_dir=PROMPTS,
        )

    def _read(agent) -> list[review.LensReview]:
        return end_review.review_layer(
            "cell-1",
            fields,
            spec_body="fix it",
            diff=diff,
            acceptance=acceptance,
            touches=touches,
            forbidden=forbidden,
            context_md=CONTEXT_MD,
            claude_md=None,
            prompts_dir=PROMPTS,
            max_turns=17,
            budget_usd=1.25,
            agent=agent,
            emit=lambda event: None,
        )

    spec_finding_with_probe = {
        "file": "a.py",
        "line": 2,
        "severity": "blocker",
        "claim": "m1",
        "probe": {"file": "a.py", "find": "x", "replace": "y"},
    }
    spec_finding_no_probe = {
        "file": "a.py",
        "line": 2,
        "severity": "note",
        "claim": "m2",
    }
    spec_reply_text = _block([spec_finding_with_probe, spec_finding_no_probe])
    assert '"probe": null' not in spec_reply_text

    standards_finding = {
        "file": "a.py",
        "line": 2,
        "severity": "concern",
        "claim": "m3",
    }
    standards_reply_text = _block([standards_finding])

    calls = []
    agent = _scripted(
        calls, [_turn(spec_reply_text, cost=0.2), _turn(standards_reply_text, cost=0.3)]
    )

    reviews = _read(agent)

    assert len(calls) == 2
    for call in calls:
        assert call["container"] == "cell-1"
        assert call["options"]["tools"] == review.REVIEW_TOOLS
        assert call["options"]["max_turns"] == 17
        assert call["options"]["max_budget_usd"] == 1.25
        assert "resume" not in call["kwargs"]

    for lens, call in zip(end_review.END_LENSES, calls, strict=True):
        assert call["options"]["system_prompt"] == _expected_prompt(lens)

    assert [r.lens for r in reviews] == ["spec", "standards"]
    spec_review, standards_review = reviews
    assert spec_review.error is None
    assert standards_review.error is None
    assert not any(f.anchored for f in spec_review.findings + standards_review.findings)
    assert spec_review.findings[0].probe == Mutant(file="a.py", find="x", replace="y")
    assert spec_review.findings[1].probe is None
    assert review.reported_model("standards") is review.reported_model("correctness")

    calls2 = []
    failed = implement.AgentFailed(
        "boom",
        attempt=implement.AttemptResult(
            session_id=None,
            subtype="error",
            terminal_reason=None,
            num_turns=1,
            cost_usd_est=0.4,
        ),
    )
    agent2 = _scripted(calls2, [failed, _turn(standards_reply_text, cost=0.3)])

    reviews2 = _read(agent2)

    assert len(calls2) == 2
    spec_review2, standards_review2 = reviews2
    assert spec_review2.error is not None
    assert spec_review2.cost_usd == 0.4
    assert standards_review2.error is None
    assert len(standards_review2.findings) == 1


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def _stack_mirror(tmp_path: Path, monkeypatch) -> tuple[Path, str, dict[str, str]]:
    """The git mirror criteria 1, 2, 3 and 5 share.

    A global config pins `diff.noprefix`, `user.name` and `user.email`.
    Main carries five layers from one root, and a branch carries three
    from the same root.
    """
    config = tmp_path / "gitconfig"
    config.write_text(
        "[diff]\n    noprefix = true\n"
        "[user]\n    name = Test\n    email = test@example.com\n"
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    mirror = tmp_path / "mirror"
    mirror.mkdir()
    _git(mirror, "init", "-q")

    def commit(filename: str, content: str) -> str:
        (mirror / filename).write_text(content)
        _git(mirror, "add", filename)
        _git(mirror, "commit", "-q", "-m", f"msg {filename}")
        return _git(mirror, "rev-parse", "HEAD").strip()

    sha_a = commit("a.txt", "a\n")
    commit("m.txt", "moved main\n")
    shas: dict[str, str] = {}
    for spec_id in ("TE-4", "TE-7", "TE-3", "TE-9", "TE-5"):
        shas[spec_id] = commit(f"{spec_id}.txt", f"{spec_id} layer\n")

    _git(mirror, "checkout", "-q", "-b", "branch2", sha_a)
    commit("m2.txt", "moved main\n")
    for spec_id in ("TE-1", "TE-8", "TE-6"):
        shas[spec_id] = commit(f"{spec_id}.txt", f"{spec_id} layer\n")

    return mirror, sha_a, shas


_STACK_SPECS = ("TE-4", "TE-7", "TE-3", "TE-9", "TE-5", "TE-1", "TE-8", "TE-6")
_STACK_ORDER = ("TE-9", "TE-4", "TE-7", "TE-5", "TE-3", "TE-6", "TE-1", "TE-8")
_STACK_LAYERS = (
    ("TE-4", 1, None),
    ("TE-7", 2, "TE-4"),
    ("TE-3", 3, "TE-7"),
    ("TE-9", 4, "TE-3"),
    ("TE-5", 5, "TE-9"),
    ("TE-1", 1, None),
    ("TE-8", 2, "TE-1"),
    ("TE-6", 3, "TE-8"),
)


def _stack_specs() -> dict[str, Spec]:
    return {
        spec_id: Spec(
            id=spec_id,
            title="t",
            type="chore",
            body=f"body {spec_id}",
            touches=[f"{spec_id}.py"],
            forbidden=[f"no-{spec_id}.py"],
            acceptance=[
                Criterion(
                    claim=f"claim {spec_id}", witness=f"tests/test_{spec_id}.py::t"
                )
            ],
        )
        for spec_id in _STACK_SPECS
    }


def _stack_ledger(tmp_path: Path, sha_a: str, shas: dict[str, str]):
    """The `Ledger`, its two batches and eight `READY_FOR_REVIEW` tasks,
    each packaged at its own commit and laid out as the two `stack_layers`
    chains.

    Returns the ledger, its record, both batch ids and `spec id -> task_id`.
    """
    record = MemoryRecord()
    ledger = Ledger(tmp_path / "ledger.db", record=record)
    repo_id = ledger.upsert_repo("thermal-edge", "/o", "/m.git", policy_sha="p" * 64)
    batch1 = ledger.create_batch(100.0)
    batch2 = ledger.create_batch(100.0)
    batch_of = dict.fromkeys(("TE-4", "TE-7", "TE-3", "TE-9", "TE-5"), batch1)
    batch_of.update(dict.fromkeys(("TE-1", "TE-8", "TE-6"), batch2))

    task_ids: dict[str, int] = {}
    for spec_id in _STACK_ORDER:
        run_id = ledger.create_run(repo_id, base_sha=sha_a, batch_id=batch_of[spec_id])
        task_id = ledger.create_task(
            run_id, spec_id=spec_id, spec_sha="s" * 64, branch=f"saffron/{spec_id}"
        )
        ledger.set_task_package(
            task_id,
            "READY_FOR_REVIEW",
            f"saffron/{spec_id}",
            shas[spec_id],
            f"https://h/pull/{spec_id}",
        )
        task_ids[spec_id] = task_id

    ledger.record_findings(
        task_ids["TE-5"],
        [
            Finding(
                lens="correctness",
                severity="concern",
                file="q.py",
                line=1,
                claim="in-cell c5",
            )
        ],
    )
    attempt_id = ledger.open_attempt(task_ids["TE-5"], phase="IMPLEMENT")
    ledger.close_attempt(
        attempt_id,
        session_id="s",
        subtype="success",
        terminal_reason=None,
        num_turns=1,
        cost_usd_est=1.0,
    )

    for spec_id, position, predecessor in _STACK_LAYERS:
        ledger.record_stack_layer(
            task_ids[spec_id],
            position=position,
            predecessor_task_id=task_ids[predecessor] if predecessor else None,
            generation=0,
        )

    return ledger, record, batch1, batch2, task_ids


def _stack_script() -> list:
    """The nine scripted replies, in call order across both `review_stack`
    calls.

    TE-9's Spec call fails clean and TE-6's raises raw. The difference
    between a caught `AgentFailed` and an uncaught raise reaches both
    lenses of one layer, and only one of the other.
    """
    f5_spec = {
        "file": "TE-5.txt",
        "line": 1,
        "severity": "blocker",
        "claim": "f5 spec",
        "probe": {"file": "TE-5.txt", "find": "TE-5 layer", "replace": "fixed"},
    }
    f5_standards = {
        "file": "TE-5.txt",
        "line": 1,
        "severity": "concern",
        "claim": "f5 standards",
    }
    f9_standards = {
        "file": "TE-9.txt",
        "line": 1,
        "severity": "note",
        "claim": "f9 standards",
    }
    return [
        _turn(_block([f5_spec]), cost=0.5),
        _turn(_block([f5_standards]), cost=0.5),
        implement.AgentFailed(
            "boom",
            attempt=implement.AttemptResult(
                session_id=None,
                subtype="error",
                terminal_reason=None,
                num_turns=1,
                cost_usd_est=0.75,
            ),
        ),
        _turn(_block([f9_standards]), cost=0.25),
        _turn(_block([]), cost=0.25),
        _turn(_block([]), cost=0.25),
        RuntimeError("runner crashed"),
        _turn(_block([]), cost=0.25),
        _turn(_block([]), cost=0.25),
    ]


def _open_cell_double(calls: list[str]):
    """Records every spec id it is given, in order. Raises for `TE-8`,
    and yields `critic-<spec>` for the rest."""

    @contextmanager
    def open_cell(fields):
        calls.append(fields.spec_id)
        if fields.spec_id == "TE-8":
            raise OSError("no cell for TE-8")
        yield f"critic-{fields.spec_id}"

    return open_cell


def _end_review_kwargs(mirror: Path, open_cell, agent) -> dict:
    return {
        "mirror": mirror,
        "open_cell": open_cell,
        "context_md": CONTEXT_MD,
        "claude_md": "Read the standards once.",
        "prompts_dir": PROMPTS,
        "max_turns": 17,
        "budget_usd": 1.0,
        "agent": agent,
        "emit": lambda event: None,
    }


def test_the_end_review_reads_each_layer_top_down_until_its_reserve_runs_short(
    tmp_path, monkeypatch
):
    """`review_stack` reads a batch's layers highest position first, inside
    one reserve, and records every lens through `record_end_review`."""
    import saffron.end_review as end_review

    mirror, sha_a, shas = _stack_mirror(tmp_path, monkeypatch)
    ledger, record, batch1, batch2, task_ids = _stack_ledger(tmp_path, sha_a, shas)
    specs = _stack_specs()
    keys = {
        spec_id: ledger.record_key(task_id) for spec_id, task_id in task_ids.items()
    }

    cell_calls: list[str] = []
    open_cell = _open_cell_double(cell_calls)
    agent_calls: list = []
    agent = _scripted(agent_calls, _stack_script())
    kwargs = _end_review_kwargs(mirror, open_cell, agent)

    batch1_reviews = end_review.review_stack(ledger, str(batch1), 4.0, specs, **kwargs)
    batch2_reviews = end_review.review_stack(ledger, str(batch2), 4.0, specs, **kwargs)

    assert len(agent_calls) == 9
    assert cell_calls == ["TE-5", "TE-9", "TE-3", "TE-6", "TE-8", "TE-1"]

    assert [r.task_key for r in batch1_reviews] == [
        keys["TE-5"],
        keys["TE-9"],
        keys["TE-3"],
        keys["TE-7"],
        keys["TE-4"],
    ]
    te5_review, te9_review, te3_review, te7_review, te4_review = batch1_reviews
    assert [r.lens for r in te5_review.reviews] == ["spec", "standards"]
    assert te5_review.reviews[0].findings[0].probe == Mutant(
        file="TE-5.txt", find="TE-5 layer", replace="fixed"
    )
    assert te9_review.reviews[0].error is not None
    assert te9_review.reviews[0].cost_usd == 0.75
    assert te3_review.reviews[0].error is None
    assert te7_review.reviews == []
    assert te4_review.reviews == []

    assert [r.task_key for r in batch2_reviews] == [
        keys["TE-6"],
        keys["TE-8"],
        keys["TE-1"],
    ]
    te6_review, te8_review, te1_review = batch2_reviews
    assert [r.lens for r in te6_review.reviews] == ["spec", "standards"]
    assert [r.lens for r in te8_review.reviews] == ["spec", "standards"]
    for r in te6_review.reviews:
        assert r.cost_usd == 0.0
        assert "runner crashed" in (r.error or "")
    for r in te8_review.reviews:
        assert r.cost_usd == 0.0
        assert "no cell for TE-8" in (r.error or "")
    assert te1_review.reviews[0].error is None

    rows = {
        (row["task_key"], row["lens"]): row
        for row in ledger._db.execute("SELECT * FROM end_reviews").fetchall()
    }
    assert len(rows) == 16

    def row_for(spec_id: str, lens: str):
        return rows[(keys[spec_id], lens)]

    for spec_id, cost in (("TE-5", 0.5), ("TE-3", 0.25), ("TE-1", 0.25)):
        for lens in ("spec", "standards"):
            row = row_for(spec_id, lens)
            assert row["status"] == "reviewed"
            assert row["error"] is None
            assert row["cost_usd"] == cost
    assert row_for("TE-9", "standards")["status"] == "reviewed"
    assert row_for("TE-9", "standards")["error"] is None
    assert row_for("TE-9", "spec")["status"] == "error"
    assert row_for("TE-9", "spec")["cost_usd"] == 0.75
    assert row_for("TE-9", "spec")["error"] is not None
    for spec_id in ("TE-7", "TE-4"):
        for lens in ("spec", "standards"):
            row = row_for(spec_id, lens)
            assert row["status"] == "not_reached"
            assert row["cost_usd"] == 0.0
            assert row["error"] is None
    for lens in ("spec", "standards"):
        row = row_for("TE-6", lens)
        assert row["status"] == "error"
        assert row["cost_usd"] == 0.0
        assert "runner crashed" in row["error"]
        row8 = row_for("TE-8", lens)
        assert row8["status"] == "error"
        assert row8["cost_usd"] == 0.0
        assert "no cell for TE-8" in row8["error"]

    te5_findings = ledger.findings(task_ids["TE-5"])
    assert [f["claim"] for f in te5_findings] == [
        "in-cell c5",
        "f5 spec",
        "f5 standards",
    ]
    assert [f["lens"] for f in te5_findings] == ["correctness", "spec", "standards"]
    assert all(not f["anchored"] for f in te5_findings)

    te9_findings = ledger.findings(task_ids["TE-9"])
    assert [f["claim"] for f in te9_findings] == ["f9 standards"]

    for spec_id in ("TE-7", "TE-4", "TE-3", "TE-6", "TE-8", "TE-1"):
        assert ledger.findings(task_ids[spec_id]) == []

    ledger.close()


def test_each_layer_is_read_from_its_own_commit_in_its_own_cell(tmp_path, monkeypatch):
    """The diff handed to each lens is `head^..head` in the mirror, never
    `fields.base..head`, and every other field is that layer's own `Spec`."""
    import saffron.end_review as end_review

    mirror, sha_a, shas = _stack_mirror(tmp_path, monkeypatch)
    ledger, record, batch1, batch2, task_ids = _stack_ledger(tmp_path, sha_a, shas)
    specs = _stack_specs()

    agent_calls: list = []
    agent = _scripted(agent_calls, _stack_script())
    kwargs = _end_review_kwargs(mirror, _open_cell_double([]), agent)

    end_review.review_stack(ledger, str(batch1), 4.0, specs, **kwargs)
    end_review.review_stack(ledger, str(batch2), 4.0, specs, **kwargs)

    assert len(agent_calls) == 9
    assert [call["container"] for call in agent_calls] == [
        "critic-TE-5",
        "critic-TE-5",
        "critic-TE-9",
        "critic-TE-9",
        "critic-TE-3",
        "critic-TE-3",
        "critic-TE-6",
        "critic-TE-1",
        "critic-TE-1",
    ]
    for call in agent_calls:
        assert call["options"]["max_turns"] == 17
        assert call["options"]["max_budget_usd"] == 1.0
        assert "resume" not in call["kwargs"]

    for index, spec_id in ((0, "TE-5"), (2, "TE-9"), (4, "TE-3")):
        prompt = _flatten(agent_calls[index]["options"]["system_prompt"])
        assert f"+{spec_id} layer" in prompt
        assert f"body {spec_id}" in prompt
        assert "Read the standards once." in prompt
        assert f"tests/test_{spec_id}.py::t" in prompt
        assert (
            _flatten(
                context.constraints_block([f"{spec_id}.py"], [f"no-{spec_id}.py"], [])
            )
            in prompt
        )

    for index, spec_id in ((1, "TE-5"), (3, "TE-9"), (5, "TE-3")):
        prompt = _flatten(agent_calls[index]["options"]["system_prompt"])
        assert f"body {spec_id}" in prompt
        assert f"claim {spec_id}" not in prompt

    assert "+TE-9 layer" not in _flatten(agent_calls[0]["options"]["system_prompt"])

    bottom_prompt = _flatten(agent_calls[7]["options"]["system_prompt"])
    assert "+TE-1 layer" in bottom_prompt
    assert "diff --git a/TE-1.txt b/TE-1.txt" in bottom_prompt
    assert "moved main" not in bottom_prompt
    assert "msg TE-1" not in bottom_prompt

    ledger.close()


def test_each_layers_end_review_folds_back_from_the_record(tmp_path, monkeypatch):
    """A fold into a fresh ledger rebuilds every `end_reviews` row and
    finding as recorded. `fold_task` with no facts drops one layer's
    rows, and no other."""
    import saffron.end_review as end_review

    mirror, sha_a, shas = _stack_mirror(tmp_path, monkeypatch)
    ledger, record, batch1, batch2, task_ids = _stack_ledger(tmp_path, sha_a, shas)
    specs = _stack_specs()

    kwargs = _end_review_kwargs(
        mirror, _open_cell_double([]), _scripted([], _stack_script())
    )
    end_review.review_stack(ledger, str(batch1), 4.0, specs, **kwargs)
    end_review.review_stack(ledger, str(batch2), 4.0, specs, **kwargs)

    source_rows = {
        (row["task_key"], row["lens"]): dict(row)
        for row in ledger._db.execute("SELECT * FROM end_reviews").fetchall()
    }
    te5_key = ledger.record_key(task_ids["TE-5"])
    te9_key = ledger.record_key(task_ids["TE-9"])

    def _without_ids(row) -> dict:
        return {
            k: v for k, v in dict(row).items() if k not in ("finding_id", "task_id")
        }

    source_findings = [_without_ids(row) for row in ledger.findings(task_ids["TE-5"])]

    fresh = Ledger(tmp_path / "fresh.db")
    fresh_repo_id = fresh.upsert_repo(
        "unrelated", "/other", "/m2.git", policy_sha="q" * 64
    )
    fresh_run_id = fresh.create_run(fresh_repo_id, base_sha="z" * 40)
    fresh.create_task(
        fresh_run_id, spec_id="ZZ-1", spec_sha="t" * 64, branch="saffron/ZZ-1"
    )

    fold(record, fresh)

    fresh_rows = {
        (row["task_key"], row["lens"]): dict(row)
        for row in fresh._db.execute("SELECT * FROM end_reviews").fetchall()
    }
    assert fresh_rows == source_rows

    fresh_te5_task_id = fresh._db.execute(
        "SELECT task_id FROM tasks WHERE record_key = ?", (te5_key,)
    ).fetchone()["task_id"]
    fresh_findings = [_without_ids(row) for row in fresh.findings(fresh_te5_task_id)]
    assert fresh_findings == source_findings

    assert fresh.batch_spend(batch1) == 2.5

    fold(record, ledger)
    reloaded_rows = {
        (row["task_key"], row["lens"]): dict(row)
        for row in ledger._db.execute("SELECT * FROM end_reviews").fetchall()
    }
    assert reloaded_rows == source_rows
    assert len(reloaded_rows) == 16

    fresh.fold_task(te9_key, [])
    remaining_rows = fresh._db.execute("SELECT * FROM end_reviews").fetchall()
    assert len(remaining_rows) == 14
    assert all(row["task_key"] != te9_key for row in remaining_rows)

    ledger.close()
    fresh.close()


def test_a_batchs_spend_counts_its_own_end_review(tmp_path, monkeypatch):
    """`batch_spend` sums an attempt and an end review together on one
    batch, and reads a second batch's end review alone on the same
    ledger."""
    import saffron.end_review as end_review

    mirror, sha_a, shas = _stack_mirror(tmp_path, monkeypatch)
    ledger, record, batch1, batch2, task_ids = _stack_ledger(tmp_path, sha_a, shas)
    specs = _stack_specs()

    kwargs = _end_review_kwargs(
        mirror, _open_cell_double([]), _scripted([], _stack_script())
    )
    end_review.review_stack(ledger, str(batch1), 4.0, specs, **kwargs)
    end_review.review_stack(ledger, str(batch2), 4.0, specs, **kwargs)

    assert ledger.batch_spend(batch1) == 3.5
    assert ledger.batch_spend(batch2) == 0.5

    ledger.close()


# The join lens's own fixture: one linear mirror, five stacks, each
# stack's commits next to each other. `TE-7` also rewrites `TE-9`'s file.
_JOIN_COMMIT_ORDER = (
    "TE-9",
    "TE-3",
    "TE-7",
    "TE-4",
    "TE-2",
    "TE-6",
    "TE-8",
    "TE-5",
    "TE-1",
    "TE-10",
)
# spec_id -> (position, predecessor spec_id or None), one batch per stack.
_JOIN_STACKS = {
    1: {"TE-9": (1, None), "TE-3": (2, "TE-9"), "TE-7": (3, "TE-3")},
    2: {"TE-4": (1, None), "TE-2": (2, "TE-4")},
    3: {"TE-6": (1, None), "TE-8": (2, "TE-6")},
    4: {"TE-5": (1, None), "TE-1": (2, "TE-5")},
    5: {"TE-10": (1, None)},
}
# Recorded in this order, per the spec's own table, never position order.
_JOIN_RECORDING_ORDER = {
    1: ("TE-3", "TE-7", "TE-9"),
    2: ("TE-4", "TE-2"),
    3: ("TE-6", "TE-8"),
    4: ("TE-5", "TE-1"),
    5: ("TE-10",),
}
_JOIN_RESERVES = {1: 1.0, 2: 0.75, 3: 4.0, 4: 4.0, 5: 0.5}


def _join_mirror(tmp_path: Path, monkeypatch) -> tuple[Path, str, dict[str, str]]:
    config = tmp_path / "join-gitconfig"
    config.write_text(
        "[diff]\n    noprefix = true\n"
        "[user]\n    name = Test\n    email = test@example.com\n"
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    mirror = tmp_path / "join-mirror"
    mirror.mkdir()
    _git(mirror, "init", "-q")

    def commit(
        filename: str, content: str, rewrite: dict[str, str] | None = None
    ) -> str:
        (mirror / filename).write_text(content)
        _git(mirror, "add", filename)
        for other, other_content in (rewrite or {}).items():
            (mirror / other).write_text(other_content)
            _git(mirror, "add", other)
        _git(mirror, "commit", "-q", "-m", f"msg {filename}")
        return _git(mirror, "rev-parse", "HEAD").strip()

    sha_a = commit("a.txt", "a\n")
    commit("m.txt", "moved main\n")
    shas: dict[str, str] = {}
    for spec_id in _JOIN_COMMIT_ORDER:
        if spec_id == "TE-7":
            shas[spec_id] = commit(
                f"{spec_id}.txt",
                f"{spec_id} layer\n",
                rewrite={"TE-9.txt": "TE-9 layer v2\n"},
            )
        else:
            shas[spec_id] = commit(f"{spec_id}.txt", f"{spec_id} layer\n")
    return mirror, sha_a, shas


def _join_ledger(tmp_path: Path, sha_a: str, shas: dict[str, str]):
    """The `Ledger`, its five batches and ten `READY_FOR_REVIEW` tasks,
    laid out as `_JOIN_STACKS`, each layer recorded in `_JOIN_RECORDING_ORDER`.

    Returns the ledger, its record, `batch number -> batch id` and
    `spec id -> task_id`.
    """
    record = MemoryRecord()
    ledger = Ledger(tmp_path / "join-ledger.db", record=record)
    repo_id = ledger.upsert_repo("join-edge", "/o", "/m.git", policy_sha="p" * 64)

    batch_ids = {
        n: ledger.create_batch(reserve) for n, reserve in _JOIN_RESERVES.items()
    }
    spec_batch = {
        spec_id: n for n, layers in _JOIN_STACKS.items() for spec_id in layers
    }

    task_ids: dict[str, int] = {}
    for spec_id in _JOIN_COMMIT_ORDER:
        run_id = ledger.create_run(
            repo_id, base_sha=sha_a, batch_id=batch_ids[spec_batch[spec_id]]
        )
        task_id = ledger.create_task(
            run_id, spec_id=spec_id, spec_sha="s" * 64, branch=f"saffron/{spec_id}"
        )
        ledger.set_task_package(
            task_id,
            "READY_FOR_REVIEW",
            f"saffron/{spec_id}",
            shas[spec_id],
            f"https://h/pull/{spec_id}",
        )
        task_ids[spec_id] = task_id

    ledger.record_findings(
        task_ids["TE-7"],
        [
            Finding(
                lens="correctness",
                severity="concern",
                file="q.py",
                line=1,
                claim="in-cell c7",
            )
        ],
    )

    for batch_num, order in _JOIN_RECORDING_ORDER.items():
        layers = _JOIN_STACKS[batch_num]
        for spec_id in order:
            position, predecessor = layers[spec_id]
            ledger.record_stack_layer(
                task_ids[spec_id],
                position=position,
                predecessor_task_id=task_ids[predecessor] if predecessor else None,
                generation=0,
            )

    return ledger, record, batch_ids, task_ids


def _join_specs() -> dict:
    """One `Spec` per layer, built in sorted id order. Not the bottom-up
    order the join lens must read the stack in."""

    specs = {}
    for spec_id in sorted(_JOIN_COMMIT_ORDER):
        body = "body TE-3 {gap}" if spec_id == "TE-3" else f"body {spec_id}"
        specs[spec_id] = Spec(
            id=spec_id,
            title="t",
            type="chore",
            body=body,
            touches=[f"{spec_id}.py"],
            forbidden=[f"no-{spec_id}.py"],
            acceptance=[
                Criterion(
                    claim=f"claim {spec_id}", witness=f"tests/test_{spec_id}.py::t"
                )
            ],
        )
    return specs


def _join_open_cell(calls: list):
    """Records every `LayerFields` it is given, in order. Raises for
    `TE-8`, and yields `critic-<spec>` for the rest."""

    @contextmanager
    def open_cell(fields):
        calls.append(fields)
        if fields.spec_id == "TE-8":
            raise RuntimeError("no cell for TE-8")
        yield f"critic-{fields.spec_id}"

    return open_cell


def _join_script() -> list:
    j7 = {"file": "TE-7.txt", "line": 1, "severity": "concern", "claim": "j7 join"}
    return [
        _turn(_block([j7]), cost=0.25),
        implement.AgentFailed(
            "boom",
            attempt=implement.AttemptResult(
                session_id=None,
                subtype="error",
                terminal_reason=None,
                num_turns=1,
                cost_usd_est=0.4,
            ),
        ),
    ]


def test_the_join_lens_reads_the_whole_stack_once_from_the_top_layers_cell(
    tmp_path, monkeypatch
):
    """`review_joins` reads one batch's whole stack, bottom to top. It
    runs the join lens once, in the top layer's own cell, never per
    layer and never on the bottom layer's cell."""
    import saffron.end_review as end_review

    mirror, sha_a, shas = _join_mirror(tmp_path, monkeypatch)
    ledger, record, batch_ids, task_ids = _join_ledger(tmp_path, sha_a, shas)
    specs = _join_specs()

    cell_calls: list = []
    open_cell = _join_open_cell(cell_calls)
    agent_calls: list = []
    agent = _scripted(agent_calls, _join_script())
    kwargs = _end_review_kwargs(mirror, open_cell, agent)

    result1 = end_review.review_joins(ledger, str(batch_ids[1]), 1.0, specs, **kwargs)
    result2 = end_review.review_joins(ledger, str(batch_ids[2]), 0.75, specs, **kwargs)
    result3 = end_review.review_joins(ledger, str(batch_ids[3]), 4.0, specs, **kwargs)
    result4 = end_review.review_joins(ledger, str(batch_ids[4]), 4.0, specs, **kwargs)
    result5 = end_review.review_joins(ledger, str(batch_ids[5]), 0.5, specs, **kwargs)
    result6 = end_review.review_joins(ledger, "6", 4.0, specs, **kwargs)

    assert len(agent_calls) == 2
    assert [c["container"] for c in agent_calls] == ["critic-TE-7", "critic-TE-1"]
    for call in agent_calls:
        assert call["options"]["tools"] == review.REVIEW_TOOLS
        assert call["options"]["max_turns"] == 17
        assert call["options"]["max_budget_usd"] == 1.0
        assert "resume" not in call["kwargs"]

    assert [f.spec_id for f in cell_calls] == ["TE-7", "TE-8", "TE-1"]
    assert cell_calls[0].head == shas["TE-7"]
    assert cell_calls[1].head == shas["TE-8"]
    assert cell_calls[2].head == shas["TE-1"]

    prompt1 = _flatten(agent_calls[0]["options"]["system_prompt"])
    assert "+TE-9 layer" in prompt1
    assert "+TE-3 layer" in prompt1
    assert "+TE-7 layer" in prompt1
    assert "diff --git a/TE-9.txt b/TE-9.txt" in prompt1
    assert "+TE-9 layer v2" in prompt1
    assert "-TE-9 layer" not in prompt1
    assert f"{shas['TE-9']}^..{shas['TE-7']}" in prompt1
    assert "body TE-9" in prompt1
    assert "body TE-3 {gap}" in prompt1
    assert "body TE-7" in prompt1
    assert "Read the standards once." in prompt1
    assert "moved main" not in prompt1
    assert "msg TE-" not in prompt1
    assert "+TE-4 layer" not in prompt1
    order9 = prompt1.index("body TE-9")
    order3 = prompt1.index("body TE-3 {gap}")
    order7 = prompt1.index("body TE-7")
    assert order9 < order3 < order7

    for spec_id in ("TE-9", "TE-3", "TE-7"):
        heading = f"{spec_id}, branch `saffron/{spec_id}`, head `{shas[spec_id]}`"
        assert heading in prompt1

    assert result1 is not None
    assert result1.lens == "join"
    assert result1.cost_usd == 0.25
    assert result1.error is None
    assert [f.claim for f in result1.findings] == ["j7 join"]
    assert result2 is None
    assert result3 is not None
    assert result3.cost_usd == 0.0
    assert result3.error is not None
    assert "no cell for TE-8" in result3.error
    assert result4 is not None
    assert result4.cost_usd == 0.4
    assert result4.error is not None
    assert result5 is None
    assert result6 is None

    rows = {
        row["task_key"]: row
        for row in ledger._db.execute(
            "SELECT * FROM end_reviews WHERE lens = 'join'"
        ).fetchall()
    }
    assert len(rows) == 4
    key_of = {
        spec_id: ledger.record_key(task_id) for spec_id, task_id in task_ids.items()
    }
    row7 = rows[key_of["TE-7"]]
    assert row7["status"] == "reviewed"
    assert row7["cost_usd"] == 0.25
    assert row7["error"] is None
    row2 = rows[key_of["TE-2"]]
    assert row2["status"] == "not_reached"
    assert row2["cost_usd"] == 0.0
    row8 = rows[key_of["TE-8"]]
    assert row8["status"] == "error"
    assert row8["cost_usd"] == 0.0
    assert "no cell for TE-8" in row8["error"]
    row1 = rows[key_of["TE-1"]]
    assert row1["status"] == "error"
    assert row1["cost_usd"] == 0.4
    assert row1["error"] is not None

    te7_findings = ledger.findings(task_ids["TE-7"])
    assert [f["claim"] for f in te7_findings] == ["in-cell c7", "j7 join"]
    assert [f["lens"] for f in te7_findings] == ["correctness", "join"]
    assert all(not f["anchored"] for f in te7_findings)
    for spec_id in ("TE-9", "TE-3", "TE-8", "TE-1", "TE-10"):
        assert ledger.findings(task_ids[spec_id]) == []

    ledger.close()


def test_the_join_prompt_asks_for_adr_6s_three_joins_and_nothing_else():
    """`end-review-join.md` names ADR 6's three joins, in the design's own
    words, and asks for nothing beyond them."""
    raw = (PROMPTS / "end-review-join.md").read_text()
    flat = _flatten(raw).lower()

    for phrase in (
        "a name one layer uses and another layer produces",
        "a name a layer produces and no later layer uses",
        "work a layer redoes that an earlier layer already provides",
    ):
        assert phrase in flat

    assert "do not manufacture one" in flat

    for field in ("`file`", "`line`", "`severity`", "`claim`"):
        assert field in raw
    for severity in ("`blocker`", "`concern`", "`note`"):
        assert severity in raw
    assert "`probe`" not in raw

    from saffron.cell import worktree

    assert worktree.WORKTREE_MOUNT in raw

    lowered = raw.lower()
    for forbidden in _FOURTEEN:
        assert forbidden not in lowered


def test_the_end_review_runs_the_join_lens_first_and_the_layers_on_what_it_left(
    monkeypatch,
):
    """`run_end_review` calls `review_joins` then `review_stack`, on the
    same ledger, batch key and specs. The reserve is reduced by the
    join's own cost, an errored join's cost included. A join of `None`
    leaves the reserve whole."""
    import saffron.end_review as end_review

    ledger = object()
    specs = object()
    keywords = {
        "mirror": object(),
        "open_cell": object(),
        "context_md": object(),
        "claude_md": object(),
        "prompts_dir": object(),
        "max_turns": object(),
        "budget_usd": object(),
        "agent": object(),
        "emit": object(),
    }

    order: list[str] = []
    join_calls: list = []
    stack_calls: list = []
    join_replies = [
        review.LensReview("join", cost_usd=0.75),
        None,
        review.LensReview("join", cost_usd=0.5, error="boom"),
    ]
    fixed_layers = [end_review.LayerReview("k", [])]

    def fake_review_joins(ledger_arg, batch_key, reserve_usd, specs_arg, **kw):
        order.append("join")
        join_calls.append((ledger_arg, batch_key, reserve_usd, specs_arg, kw))
        return join_replies[len(join_calls) - 1]

    def fake_review_stack(ledger_arg, batch_key, reserve_usd, specs_arg, **kw):
        order.append("stack")
        stack_calls.append((ledger_arg, batch_key, reserve_usd, specs_arg, kw))
        return fixed_layers

    monkeypatch.setattr(end_review, "review_joins", fake_review_joins)
    monkeypatch.setattr(end_review, "review_stack", fake_review_stack)

    # Sentinel `object()`s stand in for nine keywords `run_end_review` only
    # passes through, never reads, so the untyped call is cast once here.
    run_end_review = cast(Any, end_review.run_end_review)
    r1 = run_end_review(ledger, "1", 5.0, specs, **keywords)
    r2 = run_end_review(ledger, "2", 5.0, specs, **keywords)
    r3 = run_end_review(ledger, "3", 5.0, specs, **keywords)

    assert order == ["join", "stack", "join", "stack", "join", "stack"]
    assert [c[1] for c in join_calls] == ["1", "2", "3"]
    assert [c[1] for c in stack_calls] == ["1", "2", "3"]
    assert [c[2] for c in join_calls] == [5.0, 5.0, 5.0]
    assert [c[2] for c in stack_calls] == [4.25, 5.0, 4.5]
    for ledger_arg, _key, _reserve, specs_arg, kw in join_calls + stack_calls:
        assert ledger_arg is ledger
        assert specs_arg is specs
        assert kw == keywords

    assert r1.join == join_replies[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        r1.__setattr__("join", None)
    assert r1.layers == fixed_layers
    assert r2.join is None
    assert r2.layers == fixed_layers
    assert r3.join == join_replies[2]
    assert r3.layers == fixed_layers


def test_a_layers_critic_cell_is_seeded_at_its_head_and_always_torn_down(
    tmp_path, monkeypatch
):
    """`layer_cell` removes a leftover container, brings a fresh one up
    at the layer's own head through `session.cell_up`, and yields it. It
    always tears the cell down through `session.cell_down`, whether
    `cell_up` raises, the body raises, or neither does."""
    import saffron.end_review as end_review
    from saffron.cell import runtime, session

    fields = end_review.LayerFields(
        spec_id="TE-1",
        branch="saffron/TE-1",
        pr_url="https://h/pull/1",
        base="b" * 40,
        head="h" * 40,
        known="",
    )
    repo = tmp_path / "repo"
    mirror = tmp_path / "mirror"
    gates_dir = tmp_path / "gates"
    thread_env = {"X": "1"}

    log: list = []

    def fake_remove_container(container):
        log.append(("remove", container))
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")

    def fake_cell_up(**kw):
        log.append(("up", kw))
        kw["note"]("cell_up", "up detail")

    def fake_cell_down(**kw):
        log.append(("down", kw))
        kw["note"]("cell_down", True, "down detail")

    monkeypatch.setattr(runtime, "remove_container", fake_remove_container)
    monkeypatch.setattr(session, "cell_up", fake_cell_up)
    monkeypatch.setattr(session, "cell_down", fake_cell_down)

    with end_review.layer_cell(
        fields, repo=repo, mirror=mirror, gates_dir=gates_dir, thread_env=thread_env
    ) as container:
        log.append(("body", container))

    assert [step for step, *_ in log] == ["remove", "up", "body", "down"]
    up_kwargs = log[1][1]
    assert up_kwargs["repo"] == repo
    assert up_kwargs["mirror"] == mirror
    assert up_kwargs["tree_base"] == fields.head
    assert up_kwargs["branch"] == fields.branch
    assert up_kwargs["network"] == "saffron-cells"
    assert up_kwargs["gates_dir"] == gates_dir
    assert up_kwargs["thread_env"] == thread_env
    assert log[0] == ("remove", up_kwargs["container"])
    assert "TE-1" in up_kwargs["volume"]
    assert "TE-1" in up_kwargs["state"]
    assert log[2] == ("body", up_kwargs["container"])
    down_kwargs = log[3][1]
    assert down_kwargs["network"] == up_kwargs["network"]
    assert down_kwargs["volume"] == up_kwargs["volume"]
    assert down_kwargs["state"] == up_kwargs["state"]
    assert down_kwargs["container"] == up_kwargs["container"]
    assert down_kwargs["created"] is up_kwargs["created"]

    log.clear()

    def fake_cell_up_raises(**kw):
        log.append(("up", kw))
        kw["created"].add(kw["container"])
        kw["note"]("cell_up", "boom")
        raise RuntimeError("boom")

    monkeypatch.setattr(session, "cell_up", fake_cell_up_raises)
    with (
        pytest.raises(RuntimeError),
        end_review.layer_cell(
            fields, repo=repo, mirror=mirror, gates_dir=gates_dir, thread_env=thread_env
        ),
    ):
        log.append(("body", "unreached"))

    assert [step for step, *_ in log] == ["remove", "up", "down"]
    assert log[1][1]["container"] in log[1][1]["created"]

    log.clear()
    monkeypatch.setattr(session, "cell_up", fake_cell_up)
    with (
        pytest.raises(ValueError),
        end_review.layer_cell(
            fields, repo=repo, mirror=mirror, gates_dir=gates_dir, thread_env=thread_env
        ),
    ):
        raise ValueError("body boom")

    assert log[-1][0] == "down"
