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
        diff_base="7",
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
        diff_base="base1",
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
    import saffron.end_review as end_review

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
        "resolve": end_review.layer_fields,
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
    leaves the reserve whole. `resolve` is wrapped once per call, so the
    keyword each fake receives is not the one passed in. Every other
    keyword still compares equal, and the wrapped one is checked by
    calling it and reading what it delegated to and recorded."""
    import saffron.end_review as end_review

    ledger = object()
    specs = object()

    resolve_calls: list = []

    def fake_resolve(ledger_arg, task_key):
        resolve_calls.append((ledger_arg, task_key))
        return f"fields-for-{task_key}"

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
        "resolve": fake_resolve,
    }
    other_keywords = {k: v for k, v in keywords.items() if k != "resolve"}

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
        kw["resolve"](ledger_arg, f"join-{batch_key}")
        return join_replies[len(join_calls) - 1]

    def fake_review_stack(ledger_arg, batch_key, reserve_usd, specs_arg, **kw):
        order.append("stack")
        stack_calls.append((ledger_arg, batch_key, reserve_usd, specs_arg, kw))
        kw["resolve"](ledger_arg, f"stack-{batch_key}")
        return fixed_layers

    monkeypatch.setattr(end_review, "review_joins", fake_review_joins)
    monkeypatch.setattr(end_review, "review_stack", fake_review_stack)

    # Sentinel `object()`s stand in for eight keywords `run_end_review` only
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
        assert {k: v for k, v in kw.items() if k != "resolve"} == other_keywords
        assert kw["resolve"] is not fake_resolve
        assert callable(kw["resolve"])
    for (_l, batch_key, _r, _s, join_kw), (_l2, _b2, _r2, _s2, stack_kw) in zip(
        join_calls, stack_calls, strict=True
    ):
        assert batch_key == _b2
        assert join_kw["resolve"] is stack_kw["resolve"]

    # The wrapped `resolve` delegates to the one given, and what it
    # returned lands in `fields`, keyed by the task key it was called with.
    assert resolve_calls == [
        (ledger, "join-1"),
        (ledger, "stack-1"),
        (ledger, "join-2"),
        (ledger, "stack-2"),
        (ledger, "join-3"),
        (ledger, "stack-3"),
    ]
    assert r1.fields == {
        "join-1": "fields-for-join-1",
        "stack-1": "fields-for-stack-1",
    }
    assert r2.fields == {
        "join-2": "fields-for-join-2",
        "stack-2": "fields-for-stack-2",
    }
    assert r3.fields == {
        "join-3": "fields-for-join-3",
        "stack-3": "fields-for-stack-3",
    }

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
        diff_base="b" * 40,
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
    assert up_kwargs["network"] == "saffron-cells-endreview-te-1"
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


def test_only_a_spec_sessions_layer_cell_is_granted_capabilities_and_checked(
    tmp_path, monkeypatch
):
    """`layer_cell`'s `spec_session` keyword defaults to `False`, which grants
    no capability and runs no check. Given `True`, `cell_up` gets
    `implement.UNPRIVILEGED_BASH_CAPS` and the check runs on its container
    before the body, still inside the `try` so a raise still tears down."""
    import saffron.end_review as end_review
    from saffron.cell import runtime, session
    from saffron.phases import implement

    fields = end_review.LayerFields(
        spec_id="TE-2",
        branch="saffron/TE-2",
        pr_url="https://h/pull/2",
        base="b" * 40,
        head="h" * 40,
        known="",
        diff_base="b" * 40,
    )
    repo = tmp_path / "repo"
    mirror = tmp_path / "mirror"
    gates_dir = tmp_path / "gates"
    thread_env = {"X": "1"}

    log: list = []

    def fake_remove_container(container):
        log.append(("remove", container))

    def fake_cell_up(**kw):
        log.append(("up", kw))

    def fake_cell_down(**kw):
        log.append(("down", kw))

    def fake_check(container):
        log.append(("check", container))

    monkeypatch.setattr(runtime, "remove_container", fake_remove_container)
    monkeypatch.setattr(session, "cell_up", fake_cell_up)
    monkeypatch.setattr(session, "cell_down", fake_cell_down)
    monkeypatch.setattr(session, "assert_bash_is_unprivileged", fake_check)

    def open_layer_cell(**kw):
        return end_review.layer_cell(
            fields,
            repo=repo,
            mirror=mirror,
            gates_dir=gates_dir,
            thread_env=thread_env,
            **kw,
        )

    with open_layer_cell() as container:
        log.append(("body", container))
    assert [step for step, *_ in log] == ["remove", "up", "body", "down"]
    assert log[1][1].get("cap_add", ()) == ()

    log.clear()
    with open_layer_cell(spec_session=False) as container:
        log.append(("body", container))
    assert [step for step, *_ in log] == ["remove", "up", "body", "down"]
    assert log[1][1].get("cap_add", ()) == ()

    log.clear()
    with open_layer_cell(spec_session=True) as container:
        log.append(("body", container))
    assert [step for step, *_ in log] == ["remove", "up", "check", "body", "down"]
    up_kwargs = log[1][1]
    assert up_kwargs["cap_add"] == ("CAP_SETUID", "CAP_SETGID")
    assert up_kwargs["cap_add"] == implement.UNPRIVILEGED_BASH_CAPS
    check_container = log[2][1]
    assert check_container == up_kwargs["container"]
    assert check_container == log[3][1]

    log.clear()

    def fake_check_raises(container):
        log.append(("check", container))
        raise runtime.CellRuntimeError("did not leave root")

    monkeypatch.setattr(session, "assert_bash_is_unprivileged", fake_check_raises)
    with (
        pytest.raises(runtime.CellRuntimeError),
        open_layer_cell(spec_session=True),
    ):
        log.append(("body", "unreached"))

    assert [step for step, *_ in log] == ["remove", "up", "check", "down"]


def test_two_layer_cells_name_their_own_network_and_proxy_apart_from_any_task(
    tmp_path, monkeypatch
):
    """`layer_cell`'s network is `saffron-cells-endreview-` plus its own spec
    id, and its proxy is `proxy.proxy_name` given `endreview-` plus that id.
    Two layer cells, one per spec id, share neither name with each other nor
    with `_drive_cell`'s own names for the same ids."""
    import saffron.end_review as end_review
    from saffron.cell import proxy, runtime, session

    repo = tmp_path / "repo"
    mirror = tmp_path / "mirror"
    gates_dir = tmp_path / "gates"
    thread_env = {"X": "1"}

    removed_networks: list[str] = []
    removed_containers: list[str] = []
    up_calls: list[dict] = []
    down_calls: list[dict] = []

    monkeypatch.setattr(
        runtime, "remove_network", lambda name: removed_networks.append(name)
    )
    monkeypatch.setattr(
        runtime, "remove_container", lambda name: removed_containers.append(name)
    )
    monkeypatch.setattr(session, "cell_up", lambda **kw: up_calls.append(kw))
    monkeypatch.setattr(session, "cell_down", lambda **kw: down_calls.append(kw))
    monkeypatch.setattr(session, "assert_bash_is_unprivileged", lambda container: None)

    fields1 = end_review.LayerFields(
        spec_id="SA-1",
        branch="saffron/SA-1",
        pr_url="https://h/pull/1",
        base="b" * 40,
        head="h" * 40,
        known="",
        diff_base="b" * 40,
    )
    fields2 = end_review.LayerFields(
        spec_id="SA-2",
        branch="saffron/SA-2",
        pr_url="https://h/pull/2",
        base="b" * 40,
        head="h" * 40,
        known="",
        diff_base="b" * 40,
    )

    with end_review.layer_cell(
        fields1,
        repo=repo,
        mirror=mirror,
        gates_dir=gates_dir,
        thread_env=thread_env,
        spec_session=False,
    ):
        pass
    with end_review.layer_cell(
        fields2,
        repo=repo,
        mirror=mirror,
        gates_dir=gates_dir,
        thread_env=thread_env,
        spec_session=True,
    ):
        pass

    up1, up2 = up_calls
    down1, down2 = down_calls
    assert up1["network"] == "saffron-cells-endreview-sa-1"
    assert up2["network"] == "saffron-cells-endreview-sa-2"
    assert up1["proxy_name"] == proxy.proxy_name("endreview-SA-1")
    assert up2["proxy_name"] == proxy.proxy_name("endreview-SA-2")
    assert down1["network"] == up1["network"]
    assert down1["proxy_name"] == up1["proxy_name"]
    assert down2["network"] == up2["network"]
    assert down2["proxy_name"] == up2["proxy_name"]
    assert {up1["network"], up1["proxy_name"]}.isdisjoint(
        {up2["network"], up2["proxy_name"]}
    )
    # Neither name is the one `_drive_cell` would give a task of the same id.
    assert up1["network"] not in ("saffron-cells-sa-1", "saffron-cells-sa-2")
    assert up1["proxy_name"] != proxy.proxy_name("SA-1")
    assert up2["proxy_name"] != proxy.proxy_name("SA-2")

    # `cell_up`/`cell_down` are faked, so only `layer_cell`'s own pre-clean
    # shows here: one container per cell, and no network removal at all.
    assert removed_networks == []
    assert len(removed_containers) == 2
    assert removed_containers[0] != removed_containers[1]


# Runs as root in the layer's cell. Each probe goes through the prefix as the
# CLI calls it, `bash -c -l "'<prefix>' '<command>'"`, and one JSON object is printed.
_ROOT_PROBE = r"""
import glob, json, os, re, subprocess, sys, time
prefix = sys.argv[1]
def run(argv, **kw):
    return subprocess.run(argv, capture_output=True, text=True, **kw)
def bash(cmd):
    q = cmd.replace("'", "'\"'\"'")
    return run(["bash", "-c", "-l", f"'{prefix}' '{q}'"], cwd="/work")
SAFE = re.compile(r"^[A-Za-z0-9_./:=@+,-]+$")
def _y(args):
    return " ".join("''" if r == "" else r if SAFE.match(r)
                    else "'" + r.replace("'", "'\"'\"'") + "'" for r in map(str, args))
def b8o(e, t):
    return f"{_y([e])} {_y([t])}"
composite = "eval " + _y(["echo 'a'\"'\"'; id -u; echo '; id -u"]) + " && pwd -P >| /tmp/claude-ab12-cwd"
out = {"breakout": run(["bash", "-c", "-l", b8o(prefix, composite)], cwd="/work").stdout}
out["argc"] = [[r.returncode, r.stdout, r.stderr]
               for r in (run([prefix]), run([prefix, "id -u", "id -u"]))]
out["uid"] = bash("id -u").stdout.strip()
out["user"] = run(["id", "-u", "unprivileged"]).stdout.strip()
out["groups"] = bash("id -G").stdout.split()
out["status"] = bash("grep -E 'Cap|NoNewPrivs' /proc/self/status").stdout
out["home"] = bash('test -w "$HOME" && echo yes').stdout.strip()
out["token"] = bash("echo ${CLAUDE_CODE_OAUTH_TOKEN-unset}").stdout.strip()
out["root_token"] = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "unset")
out["path"] = bash("echo $PATH").stdout.strip()
out["pytest"] = bash("command -v pytest").stdout.strip()
out["git"] = bash("git -C /work log -1 --format=%H").stdout.strip()
out["read_work"] = bash("cat /work/a.txt").stdout.strip()
out["write_tmp"] = bash("echo t > /tmp/probe.txt && cat /tmp/probe.txt").stdout.strip()
out["copy_runs"] = bash("git clone -q /work /tmp/w && cd /tmp/w && echo two >> a.txt"
                        " && git status --porcelain && /opt/venv/bin/pytest --version").stdout
out["sysctl"] = {k: open(f"/proc/sys/fs/{k}").read().strip()
                 for k in ("protected_symlinks", "protected_regular")}
run(["sh", "-c", "cp /usr/bin/id /tmp/rid && chmod u+s /tmp/rid"], check=True)
out["setuid"] = bash("/tmp/rid -u").stdout.strip()
sdk = run([sys.executable, "-c", "import claude_agent_sdk, os; "
           "print(os.path.dirname(claude_agent_sdk.__file__))"], check=True).stdout.strip()
site = glob.glob("/opt/venv/lib/python*/site-packages")[0]
targets = ["/opt/saffron/agent_runner.py", "/opt/saffron/claude-code", prefix,
           sdk + "/__init__.py", "/opt/venv/pyvenv.cfg", site + "/probe.pth",
           "/opt/venv/bin/probe", "/agent-state/probe", "/work/probe",
           "/work/.git/config", "/etc/probe"]
out["writes"] = {t: bash(f"echo x >> {t}").stderr for t in targets}
out["cli"] = os.path.realpath("/opt/saffron/claude-code")
out["pipes"] = {}
for fd in (3, 0):
    r, w = os.pipe()
    os.set_inheritable(w, True)
    def onto_fd3(w=w):
        os.dup2(w, 3)
    cmd = "echo L >&3; echo L >&0; echo L > /proc/self/fd/3; echo L > /proc/self/fd/0; true"
    q = cmd.replace("'", "'\"'\"'")
    subprocess.run(["bash", "-c", "-l", f"'{prefix}' '{q}'"], cwd="/work",
                   stdin=w if fd == 0 else subprocess.DEVNULL,
                   preexec_fn=onto_fd3 if fd == 3 else None, close_fds=fd == 0,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sh", "-c", "echo ROOT >&3"], preexec_fn=onto_fd3, close_fds=False)
    os.close(w)
    out["pipes"][str(fd)] = os.read(r, 200).decode()
    os.close(r)
r, w = os.pipe()
pid = os.fork()
if pid == 0:
    os.close(r)
    os.dup2(w, 1)
    time.sleep(5)
    os._exit(0)
os.close(w)
bash(f"echo FORGED > /proc/{pid}/fd/1")
run(["sh", "-c", f"echo ROOT > /proc/{pid}/fd/1"])
time.sleep(0.3)
os.set_blocking(r, False)
out["stream"] = os.read(r, 200).decode()
print(json.dumps(out))
"""


@pytest.mark.cell
def test_a_spec_sessions_bash_cannot_write_what_root_runs(tmp_path, monkeypatch):
    """Enters a spec session's layer cell on this repository, as production
    does, and probes the Bash wrapper from inside it (Appendix I).

    The self-check's probe is read from the recorded `exec_` calls. It runs
    again through the wrapper, once as it is and once under an altered `PATH`.
    """
    import saffron.end_review as end_review
    from saffron.cell import runtime

    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-probe-not-a-token")
    seen: list[list[str]] = []
    real_exec = runtime.exec_

    def recording_exec(container, command, **kw):
        seen.append(list(command))
        return real_exec(container, command, **kw)

    monkeypatch.setattr(runtime, "exec_", recording_exec)
    repo = Path(__file__).resolve().parent.parent
    origin = tmp_path / "origin"
    origin.mkdir()

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=origin, check=True, capture_output=True, text=True
        )

    git("init", "-q", "-b", "main")
    (origin / "a.txt").write_text("one\n")
    git("add", "a.txt")
    git("-c", "user.email=t@e", "-c", "user.name=t", "commit", "-qm", "first")
    head = git("rev-parse", "HEAD").stdout.strip()
    mirror = tmp_path / "m.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(origin), str(mirror)], check=True
    )
    gates = tmp_path / "gates"
    (gates / ".saffron" / "gates").mkdir(parents=True)
    fields = end_review.LayerFields(
        spec_id="SY-1",
        branch="saffron/SY-1",
        pr_url="",
        base=head,
        head=head,
        known="",
        diff_base=head,
    )
    wrapper = implement.UNPRIVILEGED_BASH
    prefix = implement.agent_options(
        system_prompt="s",
        max_turns=1,
        budget_usd=1.0,
        tools=["Read", "Glob", "Grep", "Bash"],
    )["env"]["CLAUDE_CODE_SHELL_PREFIX"]
    assert prefix == wrapper
    odd_path = "PATH=/nonexistent:/root/x:/usr/bin"
    with end_review.layer_cell(
        fields,
        repo=repo,
        mirror=mirror,
        gates_dir=gates,
        thread_env={},
        spec_session=True,
    ) as container:
        probe = next(argv[1] for argv in seen if argv[0] == wrapper)
        done = runtime.exec_(container, [implement.PYTHON, "-c", _ROOT_PROBE, prefix])
        check = runtime.exec_(container, [wrapper, probe])
        odd = runtime.exec_(container, ["env", odd_path, wrapper, probe])
    assert done.returncode == 0, done.stderr
    got = json.loads(done.stdout)
    print(json.dumps(got, indent=1), check.stdout, odd.stdout, sep="\n")
    assert got["uid"] == got["user"] and got["uid"] not in ("", "0")
    assert "0" not in got["groups"] and got["home"] == "yes"
    assert "CapEff:\t0000000000000000" in got["status"]
    assert "CapPrm:\t0000000000000000" in got["status"]
    assert "NoNewPrivs:\t1" in got["status"]
    assert got["setuid"] == got["user"]
    assert got["token"] == "unset" and got["root_token"] == "sk-probe-not-a-token"
    assert got["git"] == head and got["read_work"] == "one"
    assert got["write_tmp"] == "t"
    assert got["copy_runs"].startswith(" M a.txt\npytest ")
    assert len(got["writes"]) == 11
    for target, stderr in got["writes"].items():
        assert "Permission denied" in stderr, target
    assert got["pipes"] == {"3": "ROOT\n", "0": "ROOT\n"}
    assert got["stream"] == "ROOT\n"
    assert check.returncode == 0, check.stderr
    assert "refused /opt/venv/bin\nrefused /opt/venv\n" in check.stdout
    for path in ("/opt/saffron", wrapper, got["cli"]):
        assert f"refused {path}\n" in check.stdout, path
    for path in ("/nonexistent", "/root/x"):
        assert f"skipped {path}\n" in odd.stdout, path
        assert f"missing {path}\n" not in odd.stdout, path
    for code, stdout, stderr in got["argc"]:
        assert code != 0 and stdout == "" and stderr == ""
    assert got["breakout"] == f"a'; id -u; echo \n{got['user']}\n"


_EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def _commit_tree(repo: Path, tree: str, parents: list[str], message: str) -> str:
    args = ["commit-tree", tree]
    for parent in parents:
        args += ["-p", parent]
    return _git(repo, *args, "-m", message).strip()


def _set_branch(repo: Path, name: str, sha: str) -> None:
    _git(repo, "update-ref", f"refs/heads/{name}", sha)


def _delete_branch(repo: Path, name: str) -> None:
    _git(repo, "update-ref", "-d", f"refs/heads/{name}")


def _resolver_origin(tmp_path: Path, monkeypatch) -> tuple[Path, str, str]:
    """A real, non-mirror origin for `branch_heads`'s own tests. `main`
    carries a root commit then a base commit, and each test branches off
    the base and moves branches on this origin afterward."""
    config = tmp_path / "gitconfig-resolver"
    config.write_text(
        "[diff]\n    noprefix = true\n"
        "[user]\n    name = Test\n    email = test@example.com\n"
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    origin = tmp_path / "resolver-origin"
    origin.mkdir()
    _git(origin, "init", "-q")
    _git(origin, "symbolic-ref", "HEAD", "refs/heads/main")

    def commit(filename: str, content: str) -> str:
        (origin / filename).write_text(content)
        _git(origin, "add", filename)
        _git(origin, "commit", "-q", "-m", f"msg {filename}")
        return _git(origin, "rev-parse", "HEAD").strip()

    root_sha = commit("root.txt", "root\n")
    base_sha = commit("base.txt", "base\n")
    return origin, root_sha, base_sha


def test_a_layer_whose_branch_head_cannot_be_resolved_errors_at_no_cost(
    tmp_path, monkeypatch
):
    """`branch_heads`'s resolver raises for a layer the walk cannot
    place. `_review_one_layer` and `review_joins` turn that into an
    `error` at cost 0 for every lens. The walk still reaches the layer
    below, and a failed fetch is never cached."""
    import saffron.end_review as end_review
    from saffron.phases import package as package_phase

    origin, root_sha, base_sha = _resolver_origin(tmp_path, monkeypatch)

    def branch_off(parent_sha: str, name: str, filename: str) -> str:
        _git(origin, "checkout", "-q", "-b", name, parent_sha)
        (origin / filename).write_text(f"{name}\n")
        _git(origin, "add", filename)
        _git(origin, "commit", "-q", "-m", f"msg {filename}")
        sha = _git(origin, "rev-parse", "HEAD").strip()
        _git(origin, "checkout", "-q", "main")
        return sha

    bot_sha = branch_off(base_sha, "saffron/BOT", "bot.txt")
    mid_sha = branch_off(base_sha, "saffron/MID", "mid.txt")
    top_sha = branch_off(base_sha, "saffron/TOP", "top.txt")
    orphan_branch_sha = branch_off(base_sha, "saffron/ORPHAN", "orphan.txt")
    rebased_branch_sha = branch_off(base_sha, "saffron/REBASED", "rebased.txt")
    base_branch_sha = branch_off(base_sha, "saffron/BASE", "base-layer.txt")
    child_sha = branch_off(base_sha, "saffron/CHILD", "child.txt")
    bot2_sha = branch_off(base_sha, "saffron/BOT2", "bot2.txt")
    mid2_sha = branch_off(base_sha, "saffron/MID2", "mid2.txt")
    top2_sha = branch_off(mid2_sha, "saffron/TOP2", "top2.txt")

    mirror = tmp_path / "resolver-mirror.git"
    subprocess.run(
        ["git", "clone", "--mirror", "-q", str(origin), str(mirror)], check=True
    )

    # Moved on the origin only, after the mirror is cloned, so the
    # resolver must fetch fresh to see any of this.
    _delete_branch(origin, "saffron/BOT")
    _delete_branch(origin, "saffron/TOP")

    root_tree = _git(origin, "rev-parse", f"{root_sha}^{{tree}}").strip()
    truly_orphan = _commit_tree(origin, root_tree, [], "unrelated history")
    _set_branch(origin, "saffron/ORPHAN", truly_orphan)

    rebased_tree = _git(origin, "rev-parse", f"{rebased_branch_sha}^{{tree}}").strip()
    rebased_below = _commit_tree(
        origin, rebased_tree, [root_sha], "rebased below build"
    )
    _set_branch(origin, "saffron/REBASED", rebased_below)

    _delete_branch(origin, "saffron/BASE")

    child_tree = _git(origin, "rev-parse", f"{child_sha}^{{tree}}").strip()
    child_orphan = _commit_tree(origin, child_tree, [], "disconnected child")
    _set_branch(origin, "saffron/CHILD", child_orphan)

    mid2_tree = _git(origin, "rev-parse", f"{mid2_sha}^{{tree}}").strip()
    mid2_orphan = _commit_tree(origin, mid2_tree, [], "disconnected middle")
    _set_branch(origin, "saffron/MID2", mid2_orphan)

    url = str(origin)

    fetch_calls: list[str] = []
    real_fetch = package_phase.fetch_parent_branch

    def spy_fetch(mirror_arg, url_arg, branch):
        fetch_calls.append(branch)
        return real_fetch(mirror_arg, url_arg, branch)

    monkeypatch.setattr(end_review.package_phase, "fetch_parent_branch", spy_fetch)

    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("errs", url, str(mirror), policy_sha="p" * 64)
    batch_a = ledger.create_batch(100.0)
    run_a = ledger.create_run(repo_id, base_sha=base_sha, batch_id=batch_a)
    batch_d = ledger.create_batch(100.0)
    run_d = ledger.create_run(repo_id, base_sha=base_sha, batch_id=batch_d)

    def task_with_push(run_id: int, spec_id: str, branch: str, pushed_sha: str) -> int:
        task_id = ledger.create_task(
            run_id, spec_id=spec_id, spec_sha="s" * 64, branch=branch
        )
        ledger.set_task_package(
            task_id, "READY_FOR_REVIEW", branch, pushed_sha, f"https://h/pull/{spec_id}"
        )
        return task_id

    bot = task_with_push(run_a, "ER-0001", "saffron/BOT", bot_sha)
    mid = task_with_push(run_a, "ER-0002", "saffron/MID", mid_sha)
    top = task_with_push(run_a, "ER-0003", "saffron/TOP", top_sha)
    ledger.record_stack_layer(bot, position=1, predecessor_task_id=None, generation=0)
    ledger.record_stack_layer(mid, position=2, predecessor_task_id=bot, generation=0)
    ledger.record_stack_layer(top, position=3, predecessor_task_id=mid, generation=0)

    orphan_task = task_with_push(run_a, "ER-0004", "saffron/ORPHAN", orphan_branch_sha)
    ledger.record_stack_layer(
        orphan_task, position=1, predecessor_task_id=None, generation=0
    )
    rebased_task = task_with_push(
        run_a, "ER-0005", "saffron/REBASED", rebased_branch_sha
    )
    ledger.record_stack_layer(
        rebased_task, position=1, predecessor_task_id=None, generation=0
    )
    base_task = task_with_push(run_a, "ER-0006", "saffron/BASE", base_branch_sha)
    child_task = task_with_push(run_a, "ER-0007", "saffron/CHILD", child_sha)
    ledger.record_stack_layer(
        child_task, position=1, predecessor_task_id=base_task, generation=0
    )

    bot2 = task_with_push(run_d, "ER-0008", "saffron/BOT2", bot2_sha)
    mid2 = task_with_push(run_d, "ER-0009", "saffron/MID2", mid2_sha)
    top2 = task_with_push(run_d, "ER-0010", "saffron/TOP2", top2_sha)
    ledger.record_stack_layer(bot2, position=1, predecessor_task_id=None, generation=0)
    ledger.record_stack_layer(mid2, position=2, predecessor_task_id=bot2, generation=0)
    ledger.record_stack_layer(top2, position=3, predecessor_task_id=mid2, generation=0)

    key_bot = ledger.record_key(bot)
    key_mid = ledger.record_key(mid)
    key_top = ledger.record_key(top)
    key_orphan = ledger.record_key(orphan_task)
    key_rebased = ledger.record_key(rebased_task)
    key_child = ledger.record_key(child_task)
    key_bot2 = ledger.record_key(bot2)
    key_mid2 = ledger.record_key(mid2)
    key_top2 = ledger.record_key(top2)
    assert (
        key_bot
        and key_mid
        and key_top
        and key_orphan
        and key_rebased
        and key_child
        and key_bot2
        and key_mid2
        and key_top2
    )

    resolve = end_review.branch_heads(mirror, url)

    # --- a gone layer branch, on a bottom layer and on one with a
    # predecessor ---
    with pytest.raises(ValueError, match="saffron/BOT"):
        resolve(ledger, key_bot)
    with pytest.raises(ValueError, match="saffron/TOP"):
        resolve(ledger, key_top)

    # --- no candidate the current head contains ---
    with pytest.raises(ValueError) as orphan_exc:
        resolve(ledger, key_orphan)
    orphan_message = str(orphan_exc.value)
    assert "saffron/ORPHAN" in orphan_message
    assert truly_orphan in orphan_message

    with pytest.raises(ValueError, match="saffron/REBASED"):
        resolve(ledger, key_rebased)

    # --- a stack base's branch gone, and the child's own head contains
    # neither candidate ---
    with pytest.raises(ValueError) as child_exc:
        resolve(ledger, key_child)
    child_message = str(child_exc.value)
    assert "saffron/CHILD" in child_message
    assert "saffron/BASE" in child_message
    assert "gone" in child_message

    # --- a failed fetch is never cached: each of the three resolutions
    # that need "saffron/BOT" fetches it again ---
    fetch_calls.clear()
    with pytest.raises(ValueError):
        resolve(ledger, key_bot)
    mid_fields = resolve(ledger, key_mid)
    with pytest.raises(ValueError):
        resolve(ledger, key_bot)
    assert fetch_calls.count("saffron/BOT") == 3
    assert mid_fields.base == f"{mid_sha}^"

    # --- integration: `error` at cost 0, the walk still reaches the
    # layer below, and the join errors too ---
    spec_mid = Spec(
        id="ER-0002",
        title="t",
        type="chore",
        body="body ER-0002",
        touches=["ER-0002.py"],
        forbidden=[],
        acceptance=[Criterion(claim="claim", witness="tests/test_a.py::t")],
    )
    agent_calls_a: list = []
    agent_a = _scripted(agent_calls_a, [_turn(_block([])), _turn(_block([]))])
    kwargs_a = _end_review_kwargs(mirror, _open_cell_double([]), agent_a)
    kwargs_a["resolve"] = end_review.branch_heads(mirror, url)

    stack_a = end_review.run_end_review(
        ledger, str(batch_a), 100.0, {"ER-0002": spec_mid}, **kwargs_a
    )
    assert len(agent_calls_a) == 2

    assert stack_a.join is not None
    assert stack_a.join.error is not None
    assert stack_a.join.cost_usd == 0.0
    join_row_a = ledger._db.execute(
        "SELECT * FROM end_reviews WHERE lens = 'join' AND task_key = ?", (key_top,)
    ).fetchone()
    assert join_row_a["status"] == "error"
    assert join_row_a["cost_usd"] == 0.0
    assert join_row_a["error"] is not None

    by_key_a = {layer.task_key: layer for layer in stack_a.layers}
    for key in (key_bot, key_top):
        assert by_key_a[key].reviews != []
        for r in by_key_a[key].reviews:
            assert r.cost_usd == 0.0
            assert r.error is not None
    assert by_key_a[key_mid].reviews != []
    for r in by_key_a[key_mid].reviews:
        assert r.error is None

    rows = {
        (row["task_key"], row["lens"]): row
        for row in ledger._db.execute("SELECT * FROM end_reviews").fetchall()
    }
    for key in (key_bot, key_top):
        for lens in ("spec", "standards"):
            row = rows[(key, lens)]
            assert row["status"] == "error"
            assert row["cost_usd"] == 0.0
    for lens in ("spec", "standards"):
        assert rows[(key_mid, lens)]["status"] == "reviewed"

    # --- the unplaceable layer sits in the middle of a three-layer
    # stack: the layer below it still resolves and is reviewed ---
    specs_d = {
        spec_id: Spec(
            id=spec_id,
            title="t",
            type="chore",
            body=f"body {spec_id}",
            touches=[f"{spec_id}.py"],
            forbidden=[],
            acceptance=[
                Criterion(claim="claim", witness=f"tests/test_{spec_id}.py::t")
            ],
        )
        for spec_id in ("ER-0008", "ER-0010")
    }
    agent_calls_d: list = []
    agent_d = _scripted(
        agent_calls_d,
        [_turn(_block([])), _turn(_block([])), _turn(_block([])), _turn(_block([]))],
    )
    kwargs_d = _end_review_kwargs(mirror, _open_cell_double([]), agent_d)
    kwargs_d["resolve"] = end_review.branch_heads(mirror, url)

    stack_d = end_review.run_end_review(
        ledger, str(batch_d), 100.0, specs_d, **kwargs_d
    )
    assert len(agent_calls_d) == 4

    assert stack_d.join is not None
    assert stack_d.join.error is not None
    join_row_d = ledger._db.execute(
        "SELECT * FROM end_reviews WHERE lens = 'join' AND task_key = ?", (key_top2,)
    ).fetchone()
    assert join_row_d["status"] == "error"
    assert join_row_d["cost_usd"] == 0.0
    assert join_row_d["error"] is not None

    by_key_d = {layer.task_key: layer for layer in stack_d.layers}
    assert by_key_d[key_mid2].reviews != []
    for r in by_key_d[key_mid2].reviews:
        assert r.error is not None
        assert r.cost_usd == 0.0
    for key in (key_top2, key_bot2):
        assert by_key_d[key].reviews != []
        for r in by_key_d[key].reviews:
            assert r.error is None

    ledger.close()


def _w1_origin(tmp_path: Path, monkeypatch) -> tuple[Path, str, str]:
    """A second real origin, built the same way `_resolver_origin` is, for
    the branch-head witness's own six stacks."""
    return _resolver_origin(tmp_path, monkeypatch)


def test_an_end_review_grades_each_layer_at_its_branch_head_after_package(
    tmp_path, monkeypatch
):
    """`run_end_review`, through `end_review.branch_heads`, opens each
    layer's cell, and the join's, at the branch head fetched when the
    end review runs. Each lens's diff and stated range start at the
    base the resolver's rule picks for that layer's own shape."""
    import saffron.end_review as end_review
    from saffron.phases import package as package_phase

    origin, root_sha, base_sha = _w1_origin(tmp_path, monkeypatch)

    def branch_from(parent_sha: str, name: str, filename: str, content: str) -> str:
        _git(origin, "checkout", "-q", "-b", name, parent_sha)
        (origin / filename).write_text(content)
        _git(origin, "add", filename)
        _git(origin, "commit", "-q", "-m", f"msg {filename}")
        sha = _git(origin, "rev-parse", "HEAD").strip()
        _git(origin, "checkout", "-q", "main")
        return sha

    def add_commit(branch: str, filename: str, content: str) -> str:
        _git(origin, "checkout", "-q", branch)
        (origin / filename).write_text(content)
        _git(origin, "add", filename)
        _git(origin, "commit", "-q", "-m", f"msg {filename}")
        sha = _git(origin, "rev-parse", "HEAD").strip()
        _git(origin, "checkout", "-q", "main")
        return sha

    def cherry_pick_onto(commit_sha: str, new_parent_sha: str) -> str:
        """`commit_sha`'s own diff, replayed onto `new_parent_sha`, so the
        result's tree is `new_parent_sha`'s plus that diff. A `commit-tree`
        reusing `commit_sha`'s own tree would drop whatever `new_parent_sha`
        added, which is not what a real rebase does."""
        _git(origin, "checkout", "-q", "-b", "tmp-cherry", new_parent_sha)
        _git(origin, "cherry-pick", commit_sha)
        sha = _git(origin, "rev-parse", "HEAD").strip()
        _git(origin, "checkout", "-q", "main")
        _git(origin, "branch", "-D", "tmp-cherry")
        return sha

    # --- built before the mirror is cloned ---
    a_u1 = branch_from(base_sha, "saffron/A-UNREBASED", "a-u1.txt", "a-u1\n")
    a_r1 = branch_from(base_sha, "saffron/A-REBASED", "a-r1.txt", "a-r1\n")
    a_m1 = branch_from(base_sha, "saffron/A-MERGED", "a-m1.txt", "a-m1\n")
    b_p1 = branch_from(base_sha, "saffron/B-PARENT", "b-p1.txt", "b-p1\n")
    b_c1 = branch_from(b_p1, "saffron/B-CHILD", "b-c1.txt", "b-c1\n")
    c_x = branch_from(base_sha, "tmp-c-x", "c-x.txt", "c-x\n")
    c_y = branch_from(c_x, "tmp-c-y", "c-y.txt", "c-y\n")
    c_child2 = branch_from(c_y, "saffron/C-CHILD2", "c-child2.txt", "c-child2\n")
    _delete_branch(origin, "tmp-c-x")
    _delete_branch(origin, "tmp-c-y")
    d_b1 = branch_from(base_sha, "saffron/D-BOT3", "d-b1.txt", "d-b1\n")
    d_m1 = branch_from(d_b1, "saffron/D-MID3", "d-m1.txt", "d-m1\n")
    d_t1 = branch_from(d_m1, "saffron/D-TOP3", "d-t1.txt", "d-t1\n")

    mirror = tmp_path / "w1-mirror.git"
    subprocess.run(
        ["git", "clone", "--mirror", "-q", str(origin), str(mirror)], check=True
    )
    url = str(origin)

    fetch_calls: list[str] = []
    default_calls: list[int] = []
    real_fetch = package_phase.fetch_parent_branch
    real_default = package_phase.fetch_default_branch

    def spy_fetch(mirror_arg, url_arg, branch):
        fetch_calls.append(branch)
        return real_fetch(mirror_arg, url_arg, branch)

    def spy_default(mirror_arg, url_arg):
        default_calls.append(1)
        return real_default(mirror_arg, url_arg)

    monkeypatch.setattr(end_review.package_phase, "fetch_parent_branch", spy_fetch)
    monkeypatch.setattr(end_review.package_phase, "fetch_default_branch", spy_default)

    ledger = Ledger(tmp_path / "ledger.db")
    repo_id = ledger.upsert_repo("w1", url, str(mirror), policy_sha="p" * 64)

    def new_run() -> tuple[int, int]:
        batch_id = ledger.create_batch(100.0)
        run_id = ledger.create_run(repo_id, base_sha=base_sha, batch_id=batch_id)
        return batch_id, run_id

    def task_with_push(run_id: int, spec_id: str, branch: str, pushed_sha: str) -> int:
        task_id = ledger.create_task(
            run_id, spec_id=spec_id, spec_sha="s" * 64, branch=branch
        )
        ledger.set_task_package(
            task_id, "READY_FOR_REVIEW", branch, pushed_sha, f"https://h/pull/{spec_id}"
        )
        return task_id

    def spec_for(spec_id: str) -> Spec:
        return Spec(
            id=spec_id,
            title="t",
            type="chore",
            body=f"body {spec_id}",
            touches=["*"],
            forbidden=[],
            acceptance=[
                Criterion(claim="claim", witness=f"tests/test_{spec_id}.py::t")
            ],
        )

    def run_one(batch_id: int, spec_id: str, resolve) -> tuple[Any, list[dict]]:
        """One single-layer batch's own end review, scripted to reply
        clean on both lenses, returning the stack and the agent calls."""
        stack, agent_calls, _cell_calls = run_batch(
            batch_id, [spec_id], resolve, replies=2
        )
        return stack, agent_calls

    def run_batch(
        batch_id: int, spec_ids: list[str], resolve, *, replies: int
    ) -> tuple[Any, list[dict], list[str]]:
        """A batch's own end review over every id in `spec_ids`. Replies
        clean `replies` times, and returns the stack, the agent calls,
        and the spec id each opened cell was given, in order."""
        agent_calls: list[dict] = []
        agent = _scripted(agent_calls, [_turn(_block([]))] * replies)
        cell_calls: list[str] = []
        kwargs = _end_review_kwargs(mirror, _open_cell_double(cell_calls), agent)
        kwargs["resolve"] = resolve
        stack = end_review.run_end_review(
            ledger,
            str(batch_id),
            100.0,
            {spec_id: spec_for(spec_id) for spec_id in spec_ids},
            **kwargs,
        )
        return stack, agent_calls, cell_calls

    # --- A: three bottom layers, each its own one-layer stack ---
    batch_u, run_u = new_run()
    unrebased = task_with_push(run_u, "W1-0001", "saffron/A-UNREBASED", a_u1)
    ledger.record_stack_layer(
        unrebased, position=1, predecessor_task_id=None, generation=0
    )
    key_unrebased = ledger.record_key(unrebased)
    assert key_unrebased is not None

    # The review commit lands on the origin after the mirror is cloned,
    # so only a fresh fetch can see it.
    a_u2 = add_commit("saffron/A-UNREBASED", "a-u2.txt", "a-u2\n")
    stack_u, calls_u = run_one(batch_u, "W1-0001", end_review.branch_heads(mirror, url))
    assert stack_u.join is None
    assert key_unrebased in stack_u.fields
    prompt_u = _flatten(calls_u[0]["options"]["system_prompt"])
    assert "+a-u1" in prompt_u
    assert "+a-u2" in prompt_u
    assert a_u2 in prompt_u

    batch_r, run_r = new_run()
    rebased = task_with_push(run_r, "W1-0002", "saffron/A-REBASED", a_r1)
    ledger.record_stack_layer(
        rebased, position=1, predecessor_task_id=None, generation=0
    )

    main2 = add_commit("main", "main2.txt", "main2\n")
    a_r1b = cherry_pick_onto(a_r1, main2)
    _set_branch(origin, "saffron/A-REBASED", a_r1b)
    stack_r, calls_r = run_one(batch_r, "W1-0002", end_review.branch_heads(mirror, url))
    assert stack_r.join is None
    prompt_r = _flatten(calls_r[0]["options"]["system_prompt"])
    assert "+a-r1" in prompt_r
    assert "main2" not in prompt_r
    assert main2 in prompt_r

    batch_m, run_m = new_run()
    merged = task_with_push(run_m, "W1-0003", "saffron/A-MERGED", a_m1)
    ledger.record_stack_layer(
        merged, position=1, predecessor_task_id=None, generation=0
    )

    m1_tree = _git(origin, "rev-parse", f"{a_m1}^{{tree}}").strip()
    main_merge = _commit_tree(origin, m1_tree, [main2, a_m1], "merge a-m1")
    _set_branch(origin, "main", main_merge)
    stack_m, calls_m = run_one(batch_m, "W1-0003", end_review.branch_heads(mirror, url))
    assert stack_m.join is None
    prompt_m = _flatten(calls_m[0]["options"]["system_prompt"])
    assert "+a-m1" in prompt_m
    assert f"{a_m1}^..{a_m1}" in prompt_m

    # --- B: a restacked layer outranks its predecessor's recorded head ---
    batch_b, run_b = new_run()
    parent = task_with_push(run_b, "W1-0004", "saffron/B-PARENT", b_p1)
    child_a = task_with_push(run_b, "W1-0005", "saffron/B-CHILD", b_c1)
    ledger.record_stack_layer(
        parent, position=1, predecessor_task_id=None, generation=0
    )
    ledger.record_stack_layer(
        child_a, position=2, predecessor_task_id=parent, generation=0
    )

    b_p2 = add_commit("saffron/B-PARENT", "b-p2.txt", "b-p2\n")
    b_c2 = cherry_pick_onto(b_c1, b_p2)
    _set_branch(origin, "saffron/B-CHILD", b_c2)
    # PARENT has no predecessor, so both walks resolve it and each needs
    # the default branch, fetched only once between the two.
    default_calls.clear()
    stack_b, calls_b, cell_calls_b = run_batch(
        batch_b,
        ["W1-0004", "W1-0005"],
        end_review.branch_heads(mirror, url),
        replies=5,
    )
    assert stack_b.join is not None
    assert stack_b.join.error is None
    assert len(default_calls) == 1
    # `cell_calls_b[0]`, the join's own open before any layer's, names
    # the top layer's spec, never the bottom's.
    assert cell_calls_b[0] == "W1-0005"
    # calls_b[0] is the join's own turn. The child's two lenses follow it,
    # since `review_stack` walks top down and the child is the top layer.
    prompt_b = _flatten(calls_b[1]["options"]["system_prompt"])
    assert "b-c1" in prompt_b
    assert "b-p2" not in prompt_b
    assert f"{b_p2}^..{b_c2}" not in prompt_b
    assert f"{b_p2}..{b_c2}" in prompt_b

    # --- C: a gone predecessor branch offers this layer's own pushed
    # head's parent before the predecessor's recorded head ---
    batch_c, run_c = new_run()
    base2 = task_with_push(run_c, "W1-0006", "saffron/C-BASE2", c_x)
    child2 = task_with_push(run_c, "W1-0007", "saffron/C-CHILD2", c_child2)
    ledger.record_stack_layer(
        child2, position=1, predecessor_task_id=base2, generation=0
    )

    stack_c, calls_c = run_one(batch_c, "W1-0007", end_review.branch_heads(mirror, url))
    assert stack_c.join is None
    prompt_c = _flatten(calls_c[0]["options"]["system_prompt"])
    assert "c-child2" in prompt_c
    assert "c-y" not in prompt_c
    assert "c-x" not in prompt_c
    assert f"{c_child2}^..{c_child2}" in prompt_c

    # --- D: the join's own range, fields, and fetching each branch once ---
    batch_d, run_d = new_run()
    bot3 = task_with_push(run_d, "W1-0008", "saffron/D-BOT3", d_b1)
    mid3 = task_with_push(run_d, "W1-0009", "saffron/D-MID3", d_m1)
    top3 = task_with_push(run_d, "W1-0010", "saffron/D-TOP3", d_t1)
    ledger.record_stack_layer(bot3, position=1, predecessor_task_id=None, generation=0)
    ledger.record_stack_layer(mid3, position=2, predecessor_task_id=bot3, generation=0)
    ledger.record_stack_layer(top3, position=3, predecessor_task_id=mid3, generation=0)
    # A review commit past the pushed head, so diff_base (base_sha)
    # differs from the current head's own parent, d_b1.
    add_commit("saffron/D-BOT3", "d-b1b.txt", "d-b1b\n")
    key_bot3 = ledger.record_key(bot3)
    key_mid3 = ledger.record_key(mid3)
    key_top3 = ledger.record_key(top3)
    assert key_bot3 and key_mid3 and key_top3

    fetch_calls.clear()
    agent_calls_d: list[dict] = []
    agent_d = _scripted(
        agent_calls_d, [_turn(_block([])), _turn(_block([])), _turn(_block([]))]
    )
    kwargs_d = _end_review_kwargs(mirror, _open_cell_double([]), agent_d)
    kwargs_d["resolve"] = end_review.branch_heads(mirror, url)
    specs_d = {
        "W1-0008": spec_for("W1-0008"),
        "W1-0009": spec_for("W1-0009"),
        "W1-0010": spec_for("W1-0010"),
    }
    # The join's cost (0.1) plus one layer's ceiling fits the reserve, but
    # a second layer's does not, so the walk stops after the top layer.
    stack_d = end_review.run_end_review(ledger, str(batch_d), 2.1, specs_d, **kwargs_d)

    assert stack_d.join is not None
    assert stack_d.join.error is None
    join_prompt = _flatten(agent_calls_d[0]["options"]["system_prompt"])
    assert f"{base_sha}..{d_t1}" in join_prompt
    # The range starts at diff_base (base_sha), so d_b1's own change
    # still shows. `head^..head` of the moved head would lose it.
    assert "+d-b1" in join_prompt

    assert key_bot3 in stack_d.fields
    assert key_mid3 in stack_d.fields
    assert key_top3 in stack_d.fields

    by_key_d = {layer.task_key: layer for layer in stack_d.layers}
    assert by_key_d[key_top3].reviews != []
    assert by_key_d[key_mid3].reviews == []
    assert by_key_d[key_bot3].reviews == []
    rows_d = {
        (row["task_key"], row["lens"]): row
        for row in ledger._db.execute(
            "SELECT * FROM end_reviews WHERE lens IN ('spec', 'standards')"
        ).fetchall()
    }
    for lens in ("spec", "standards"):
        assert rows_d[(key_top3, lens)]["status"] == "reviewed"
        assert rows_d[(key_mid3, lens)]["status"] == "not_reached"
        assert rows_d[(key_bot3, lens)]["status"] == "not_reached"

    for branch in ("saffron/D-BOT3", "saffron/D-MID3", "saffron/D-TOP3"):
        assert fetch_calls.count(branch) == 1

    # --- E: the join's stated base is the diff's own, not the row's
    # recorded `base`, which `branch_heads` never lets differ on its own ---
    batch_e, run_e = new_run()
    mid_e = task_with_push(run_e, "W1-0011", "saffron/D-MID3", d_m1)
    top_e = task_with_push(run_e, "W1-0012", "saffron/D-TOP3", d_t1)
    ledger.record_stack_layer(mid_e, position=1, predecessor_task_id=None, generation=0)
    ledger.record_stack_layer(
        top_e, position=2, predecessor_task_id=mid_e, generation=0
    )
    key_mid_e = ledger.record_key(mid_e)
    assert key_mid_e is not None

    real_resolve_e = end_review.branch_heads(mirror, url)

    def resolve_e(ledger_arg, task_key):
        fields = real_resolve_e(ledger_arg, task_key)
        if task_key == key_mid_e:
            # `diff_base` stays correct. Only `base` is corrupted, so the
            # prompt can only show the right range by reading `diff_base`.
            fields = dataclasses.replace(fields, base="deliberately-wrong-base")
        return fields

    agent_calls_e: list[dict] = []
    agent_e = _scripted(agent_calls_e, [_turn(_block([]))])
    kwargs_e = _end_review_kwargs(mirror, _open_cell_double([]), agent_e)
    kwargs_e["resolve"] = resolve_e
    join_e = end_review.review_joins(
        ledger,
        str(batch_e),
        10.0,
        {"W1-0011": spec_for("W1-0011"), "W1-0012": spec_for("W1-0012")},
        **kwargs_e,
    )
    assert join_e is not None
    assert join_e.error is None
    join_prompt_e = _flatten(agent_calls_e[0]["options"]["system_prompt"])
    assert "deliberately-wrong-base" not in join_prompt_e
    assert f"{d_m1}^..{d_t1}" in join_prompt_e

    ledger.close()
