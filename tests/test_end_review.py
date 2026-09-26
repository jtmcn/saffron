"""The end review's two lenses: `LayerFields`, the prompt filler and
`review_layer`. `saffron.end_review` is imported inside every test body
here, never at module scope. It does not exist at this spec's own tree
base, and a module-scope import would fail collection under `revert`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from saffron.agents import context
from saffron.agents.findings import Finding
from saffron.intake import Criterion, Mutant
from saffron.ledger import Ledger
from saffron.phases import implement, review

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
