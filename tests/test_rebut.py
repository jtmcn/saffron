from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from saffron.agents.findings import Finding
from saffron.phases import implement, rebut, review

PROMPTS = Path(rebut.__file__).resolve().parents[1] / "agents" / "prompts"
CONTEXT_MD = (Path(rebut.__file__).resolve().parents[2] / "CONTEXT.md").read_text()

DIFF = """diff --git a/src/gap.py b/src/gap.py
--- a/src/gap.py
+++ b/src/gap.py
@@ -1,2 +1,2 @@
-def gap(series):
+def gap(series, tz="UTC"):
     return series
"""

OPTIONS = implement.agent_options(system_prompt="s", max_turns=5, budget_usd=1.0)

# The spec text every `contradicted`-verdict witness shares. Two lines, the
# second wrapped with a two-space indent, as real markdown would wrap it.
_CONTRADICTION_SPEC = (
    "Only a `MERGED` or `REJECTED` newest task unstacks a child.\n"
    "\n"
    "The resolver stacks on no row when the newest task\n"
    "  is outside the waiting states.\n"
)
# The second line, rejoined onto one line with a single space where it wrapped.
_VALID_REBUTTAL_QUOTE = (
    "The resolver stacks on no row when the newest task is outside the waiting states."
)
# The first line, with a leading space, a tab after `MERGED`, and a
# trailing newline. All three collapse under the host's check.
_VALID_FINDING_QUOTE = " Only a `MERGED`\tor `REJECTED` newest task unstacks a child.\n"


def _blocker(lens="correctness", **kwargs) -> Finding:
    base = Finding(
        lens=lens,
        severity="blocker",
        file="src/gap.py",
        line=1,
        claim="the tz default is wrong",
        anchored=True,
    )
    # Validated, not copied: `model_copy` skips validation, so an
    # override the model would reject builds silently.
    return Finding.model_validate(base.model_dump() | kwargs)


def _turn(text="", cost=0.1, structured_output=None):
    return implement.AttemptResult(
        session_id="sess-1",
        subtype="success",
        terminal_reason="completed",
        num_turns=1,
        cost_usd_est=cost,
        text=text,
        structured_output=structured_output,
    )


def _block(payload):
    """An `<output>` block, for the witnesses that prove it is never read."""
    return f"Done.\n<output>\n{json.dumps(payload)}\n</output>"


def _rebuttals(*entries):
    return _turn(structured_output={"rebuttals": list(entries)})


def _verdicts(*entries):
    return _turn(structured_output={"verdicts": list(entries)})


def _fixed(finding=1, argument="committed the fix"):
    return {"finding": finding, "action": "fixed", "argument": argument}


def _argued(finding=1, argument="the default is set by the caller"):
    return {"finding": finding, "action": "argued", "argument": argument}


def _verdict(finding=1, verdict="withdrawn", reason="r"):
    return {"finding": finding, "verdict": verdict, "reason": "r" + reason}


def _contradicted(finding, rebuttal_quote, finding_quote, reason="the lines disagree"):
    return {
        "finding": finding,
        "verdict": "contradicted",
        "reason": reason,
        "rebuttal_quote": rebuttal_quote,
        "finding_quote": finding_quote,
    }


def _agent(*texts, record=None):
    scripted = iter(texts)

    def run(container, *, prompt, options, **kwargs):
        if record is not None:
            record.append(
                {
                    "container": container,
                    "prompt": prompt,
                    "options": options,
                    "kwargs": kwargs,
                }
            )
        turn = next(scripted)
        if isinstance(turn, BaseException):
            raise turn
        return turn if isinstance(turn, implement.AttemptResult) else _turn(turn)

    return run


# --- backlog item 117: `blocker_lines` shows a survived probe ---


def test_a_blocker_whose_probe_survived_names_the_probe_to_the_implementer():
    """Criterion 5: a probe the tests did not notice is shown to the
    implementer as the edit it missed; a blocker whose probe was `unproven`
    — or that carries none — is shown exactly as it always was."""
    survived = _blocker(
        lens="adequacy",
        claim="the guard never rejects a negative amount",
        probe_verdict="survived",
        probe={"file": "src/gap.py", "find": "if amount < 0:", "replace": "if False:"},
    )
    unproven = _blocker(
        lens="adequacy",
        claim="the other guard never rejects an empty series",
        probe_verdict="unproven",
        probe={"file": "src/gap.py", "find": "if not series:", "replace": "if False:"},
    )
    lines = rebut.blocker_lines([(1, survived), (2, unproven)]).splitlines()
    assert "if amount < 0:" in lines[0]
    assert "if False:" in lines[0]
    assert "src/gap.py" in lines[0]
    assert "if not series:" not in lines[1]
    assert "if False:" not in lines[1]


def _run(
    *texts,
    blockers=None,
    acceptance=(),
    moved=True,
    gates=None,
    record=None,
    gate_suites=None,
    critic_container=None,
    critic_calls=None,
    critic_container_name="critic-cell",
    diff=None,
    reviewed_diff=None,
    spec_body="fix the gap",
):
    def _rerun_gates():
        if gate_suites is not None:
            gate_suites.append(True)
        return gates

    def _default_critic_container():
        # Distinct from "cell" by default, so no test accidentally proves
        # the two are the same container.
        if critic_calls is not None:
            critic_calls.append(True)
        return critic_container_name

    return rebut.run_rebut(
        "cell",
        blockers=blockers if blockers is not None else [_blocker()],
        acceptance=list(acceptance),
        options=OPTIONS,
        session_id="sess-1",
        spec_body=spec_body,
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        max_turns=20,
        budget_usd=2.0,
        head_moved=lambda: moved,
        rerun_gates=_rerun_gates,
        critic_container=critic_container or _default_critic_container,
        diff=diff or (lambda _critic: DIFF),
        agent=_agent(*texts, record=record),
        spec_id="SY-1",
        reviewed_diff=reviewed_diff if reviewed_diff is not None else DIFF,
        emit=lambda _e: None,
    )


def test_a_claimed_fix_with_no_commit_and_no_argument_does_not_advance():
    """§4.3 at the phase where an agent has the strongest incentive to claim it
    is done: HEAD moved, or an explicit recorded argument — and "I fixed it" is
    neither. Nothing is bought after the measurement fails."""
    gate_suites: list[bool] = []
    critic_calls: list[bool] = []
    record: list[dict] = []
    result = _run(
        "I have addressed the findings.",
        _rebuttals(_fixed()),
        moved=False,
        record=record,
        gate_suites=gate_suites,
        critic_calls=critic_calls,
    )
    assert result.state == "REBUTTING"
    assert "committed nothing" in result.why
    assert result.verdicts == []
    assert gate_suites == []  # HEAD did not move; the suite would answer twice
    assert critic_calls == []  # nothing to verdict, no cell built to verdict it in
    assert len(record) == 2  # the attempt and its extraction turn, no verdict


def test_a_fix_that_commits_and_a_lens_that_withdraws_is_ready_for_review():
    result = _run("Fixed.", _rebuttals(_fixed()), _verdicts(_verdict()), moved=True)
    assert result.state == "READY_FOR_REVIEW"
    assert "every blocker withdrawn" in result.why
    assert [r.action for r in result.rebuttal.rebuttals] == ["fixed"]


def test_an_argument_with_no_commit_is_a_legitimate_rebuttal():
    """§5.6: arguing is an outcome, not a failure to fix. It reaches the
    operator whether or not the critic is persuaded."""
    result = _run(
        "The finding is wrong.",
        _rebuttals(_argued()),
        _verdicts(_verdict(verdict="withdrawn")),
        moved=False,
    )
    assert result.state == "READY_FOR_REVIEW"
    assert result.moved is False


def test_an_argument_the_critic_still_confirms_is_a_recorded_disagreement():
    """No state for "the critic was right": adjudication is the operator's, and
    the disagreement is what §5.6 says makes the phase worth having."""
    result = _run(
        "The finding is wrong.",
        _rebuttals(_argued()),
        _verdicts(_verdict(verdict="confirmed")),
        moved=False,
    )
    assert result.state == "READY_FOR_REVIEW"
    assert "1 blocker(s) confirmed" in result.why
    assert "adjudicate" in result.why


def test_gates_red_after_the_rebuttal_exhausts_without_reopening_repair():
    record: list[dict] = []
    critic_calls: list[bool] = []
    result = _run(
        "Fixed.",
        _rebuttals(_fixed()),
        moved=True,
        gates="EXHAUSTED",
        record=record,
        critic_calls=critic_calls,
    )
    assert result.state == "EXHAUSTED"
    assert "does not re-enter the repair loop" in result.why
    # The rebuttal is kept, and no verdict session was bought for a dead task.
    assert [r.action for r in result.rebuttal.rebuttals] == ["fixed"]
    assert len(record) == 2
    assert critic_calls == []  # a red re-run ends it before a cell is built


def test_an_errored_gate_after_the_rebuttal_is_not_the_tasks_failure():
    critic_calls: list[bool] = []
    result = _run(
        "Fixed.",
        _rebuttals(_fixed()),
        moved=True,
        gates="GATE_ERROR",
        critic_calls=critic_calls,
    )
    assert result.state == "GATE_ERROR"
    assert critic_calls == []


def test_each_lens_verdicts_its_own_blockers_and_never_resumes():
    """The critic must see the argument and never the session that wrote it."""
    record: list[dict] = []
    result = _run(
        "Fixed both.",
        _rebuttals(_fixed(1), _fixed(2)),
        _verdicts(_verdict(1)),
        _verdicts(_verdict(2)),
        blockers=[_blocker(), _blocker(lens="contract")],
        record=record,
    )
    assert result.state == "READY_FOR_REVIEW"
    assert [v.lens for v in result.verdicts] == ["correctness", "contract"]
    assert [v.verdicts[0].finding for v in result.verdicts] == [1, 2]
    # The implementer resumes; both verdict sessions are fresh and read-only.
    assert record[0]["kwargs"]["resume"] == "sess-1"
    for call in record[2:]:
        assert call["kwargs"].get("resume") is None
        assert "Bash" not in call["options"]["tools"]
    assert "Bash" in record[0]["options"]["tools"]


def test_the_verdict_sessions_never_run_in_the_rebuttals_container():
    """`run_rebut` takes one container for the rebuttal turn and a second,
    zero-argument callable for the critic's. Hand it two distinct names and
    assert which turns ran where (CONTEXT.md §5, backlog item 118)."""
    record: list[dict] = []
    critic_calls: list[bool] = []
    result = _run(
        "Fixed.",
        _rebuttals(_fixed()),
        _verdicts(_verdict()),
        record=record,
        critic_calls=critic_calls,
    )
    assert result.state == "READY_FOR_REVIEW"
    assert critic_calls == [True]  # built once, after the rebuttal and re-run
    containers = [call["container"] for call in record]
    # Rebuttal, extraction, verdict — the last never the same as the first two.
    assert containers == ["cell", "cell", "critic-cell"]


def test_the_diff_a_verdict_session_reads_comes_from_the_critic_container():
    """Criterion 2's second half: a build that threads the critic container
    into the verdict sessions alone, while `diff` still reads the rebuttal's
    own container, would pass the test above and leave this one false (item
    118 records the identical omission in `SA-0087`'s own second criterion).
    `diff` is called with whatever `critic_container()` returned, and its
    result must reach the verdict session's own prompt."""
    record: list[dict] = []
    result = _run(
        "Fixed.",
        _rebuttals(_fixed()),
        _verdicts(_verdict()),
        record=record,
        diff=lambda critic: f"a diff read from {critic}",
    )
    assert result.state == "READY_FOR_REVIEW"
    assert "a diff read from critic-cell" in record[2]["options"]["system_prompt"]


def test_run_rebut_hands_the_verdict_session_the_diff_its_lens_reviewed():
    """Criterion 1 through `run_rebut`, which is what the spec's Notes ask for:
    the prompt-level witness calls `verdict_prompt` directly, so `run_rebut`'s
    own threading is unwitnessed here — dropping it, or swapping the two
    kwargs at its call site, left this whole file green."""
    record: list[dict] = []
    result = _run(
        "Fixed.",
        _rebuttals(_fixed()),
        _verdicts(_verdict()),
        record=record,
        reviewed_diff="the diff the lens reviewed",
        diff=lambda _critic: "the diff after the rebuttal",
    )
    assert result.state == "READY_FOR_REVIEW"
    prompt = record[2]["options"]["system_prompt"]
    assert (
        "## The diff your findings were filed against\n\nthe diff the lens reviewed"
        in prompt
    )
    assert "## The diff, after the rebuttal\n\nthe diff after the rebuttal" in prompt


def test_the_critic_patch_exceptions_are_imported_from_worktree_alone():
    """Backlog items 148/149: `CriticPatchRejected`, `CriticPatchEmpty` and
    `CriticPatchUnrepresentable` live once, in `saffron.cell.worktree`, below
    both the supervisor and this phase. Every importer in `saffron/` and in
    `tests/` names that module. `session` and `rebut` bind its own classes
    rather than defining copies. Nothing in `saffron/` reaches for one from
    inside a function."""
    import ast

    from saffron.cell import session, worktree
    from saffron.cell.worktree import (
        CriticPatchEmpty,
        CriticPatchRejected,
        CriticPatchUnrepresentable,
    )
    from saffron.phases import rebut as rebut_module

    names = {"CriticPatchRejected", "CriticPatchEmpty", "CriticPatchUnrepresentable"}
    root = Path(__file__).resolve().parents[1]
    worktree_path = root / "saffron" / "cell" / "worktree.py"
    session_path = root / "saffron" / "cell" / "session.py"
    rebut_path = root / "saffron" / "phases" / "rebut.py"

    class_homes: dict[str, list[Path]] = {name: [] for name in names}
    module_scope: dict[str, list[tuple[Path, str]]] = {name: [] for name in names}
    function_scope: dict[str, list[tuple[Path, str]]] = {name: [] for name in names}
    bad_attributes: list[tuple[Path, str, str]] = []

    for base in (root / "saffron", root / "tests"):
        for path in sorted(base.rglob("*.py")):
            tree = ast.parse(path.read_text(), filename=str(path))
            # ast gives no parent links. Telling a top-level import from a
            # function-local one needs one, so map each child's up front.
            parent_of: dict[int, ast.AST] = {}
            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    parent_of[id(child)] = parent

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name in names:
                    class_homes[node.name].append(path)
                elif isinstance(node, ast.ImportFrom):
                    at_module_scope = isinstance(parent_of.get(id(node)), ast.Module)
                    for alias in node.names:
                        if alias.name in names:
                            record = (path, node.module or "")
                            bucket = module_scope if at_module_scope else function_scope
                            bucket[alias.name].append(record)
                elif isinstance(node, ast.Attribute) and node.attr in names:
                    value = node.value
                    if isinstance(value, ast.Name) and value.id != "worktree":
                        bad_attributes.append((path, value.id, node.attr))

    for name in names:
        assert class_homes[name] == [worktree_path], (
            f"{name} must be defined only in {worktree_path}, found in "
            f"{class_homes[name]}"
        )

    for name in names:
        for path, module in module_scope[name] + function_scope[name]:
            assert module == "saffron.cell.worktree", (
                f"{path} imports {name} from {module!r}, not saffron.cell.worktree"
            )
        for path, _module in function_scope[name]:
            assert not path.is_relative_to(root / "saffron"), (
                f"{path} imports {name} inside a function"
            )

    for name in names:
        assert (session_path, "saffron.cell.worktree") in module_scope[name], (
            f"session.py must import {name} from worktree at module scope"
        )
    for name in ("CriticPatchRejected", "CriticPatchUnrepresentable"):
        assert (rebut_path, "saffron.cell.worktree") in module_scope[name], (
            f"rebut.py must import {name} from worktree at module scope"
        )

    assert bad_attributes == [], (
        f"found access to {bad_attributes} off a module other than worktree"
    )

    # `session` and `rebut` bind worktree's own classes, not copies: read
    # through each module's own `__dict__`, never a dotted access to it.
    session_names = vars(session)
    rebut_names = vars(rebut_module)
    assert session_names["CriticPatchRejected"] is CriticPatchRejected
    assert session_names["CriticPatchEmpty"] is CriticPatchEmpty
    assert session_names["CriticPatchUnrepresentable"] is CriticPatchUnrepresentable
    assert rebut_names["CriticPatchRejected"] is CriticPatchRejected
    assert rebut_names["CriticPatchUnrepresentable"] is CriticPatchUnrepresentable
    assert worktree.CriticPatchRejected is CriticPatchRejected

    assert issubclass(CriticPatchEmpty, CriticPatchRejected)
    assert issubclass(CriticPatchUnrepresentable, RuntimeError)
    assert not issubclass(CriticPatchUnrepresentable, CriticPatchRejected)

    assert (
        CriticPatchRejected("boom").reason("a critic cell")
        == "the exported patch did not apply in a critic cell — boom"
    )
    assert (
        CriticPatchRejected("boom").reason("a critic cell", "the post-rebuttal patch")
        == "the post-rebuttal patch did not apply in a critic cell — boom"
    )
    assert CriticPatchEmpty("boom").reason("a critic cell") == "boom"


def test_a_post_rebuttal_patch_that_will_not_apply_ends_exhausted():
    """§5.5, unchanged at REBUT: a bad patch is the agent's problem, produced
    as a `RebutResult` — the rebuttal turn and gate re-run are already paid
    for, so the exception must not escape uncharged."""
    from saffron.cell.worktree import CriticPatchRejected

    def _critic_container():
        raise CriticPatchRejected("error: patch does not apply")

    result = _run("Fixed.", _rebuttals(_fixed()), critic_container=_critic_container)
    assert result.state == "EXHAUSTED"
    assert "did not apply" in result.why


def test_a_post_rebuttal_patch_with_no_change_ends_exhausted_and_says_so():
    # Backlog item 132's REBUT half: an empty patch is not one that did not apply.
    from saffron.cell.worktree import CriticPatchEmpty

    def _critic_container():
        raise CriticPatchEmpty("the attempt's commits net to no change")

    result = _run("Fixed.", _rebuttals(_fixed()), critic_container=_critic_container)
    assert result.state == "EXHAUSTED"
    assert "net to no change" in result.why
    assert "did not apply" not in result.why


def test_a_post_rebuttal_binary_change_ends_gate_error():
    """§5.5's one carve-out: a binary change the export cannot carry is
    Saffron's own ceiling, charged to nobody."""
    from saffron.cell.worktree import CriticPatchUnrepresentable

    def _critic_container():
        raise CriticPatchUnrepresentable("fatal: cannot apply binary patch")

    result = _run("Fixed.", _rebuttals(_fixed()), critic_container=_critic_container)
    assert result.state == "GATE_ERROR"


def test_a_lens_that_leaves_a_blocker_unverdicted_has_not_withdrawn_it():
    """The one direction this phase must never guess in: a missing verdict is a
    missing answer, not a withdrawal."""
    result = _run(
        "Fixed both.",
        _rebuttals(_fixed(1), _fixed(2)),
        _verdicts(_verdict(1)),
        blockers=[_blocker(), _blocker(line=2)],
    )
    assert result.state == "REBUTTING"
    assert "asked about [1, 2]" in result.verdicts[0].error
    assert "unjudged" in result.why


def test_a_verdict_that_is_not_the_schema_is_not_a_clean_verdict():
    result = _run("Fixed.", _rebuttals(_fixed()), "I still think it is wrong.")
    assert result.state == "REBUTTING"
    assert result.verdicts[0].error.startswith("not the schema")


def test_a_commit_stands_even_when_the_rebuttal_was_not_recorded():
    """The measurement is HEAD *or* an argument. A commit the extraction turn
    failed to describe is still a commit."""
    result = _run("Fixed.", "no output block here", _verdicts(_verdict()), moved=True)
    assert result.state == "READY_FOR_REVIEW"
    assert result.rebuttal.error.startswith("not the schema")


def test_a_rebuttal_turn_that_failed_charges_what_it_spent_and_buys_no_extraction():
    record: list[dict] = []
    result = _run(
        implement.AgentFailed("max turns", _turn("", cost=0.4)),
        moved=False,
        record=record,
    )
    assert result.state == "REBUTTING"
    assert result.cost_usd == 0.4
    assert len(record) == 1


def test_the_phase_charges_every_turn_it_bought():
    result = _run("Fixed.", _rebuttals(_fixed()), _verdicts(_verdict()))
    # rebuttal, extraction, one verdict session.
    assert result.cost_usd == pytest.approx(0.3)


def test_an_empty_argument_is_not_an_argument():
    result = _run("Fixed.", _rebuttals(_argued(argument="")), moved=False)
    assert result.state == "REBUTTING"
    assert result.rebuttal.error.startswith("not the schema")


def test_the_record_keeps_the_finding_the_rebuttal_and_the_verdict_apart():
    """§4.1's three judgements must not collapse. The ledger has no `findings`
    table, so this artifact is the only place they are written down."""
    blockers = [_blocker()]
    result = _run(
        "Fixed.",
        _rebuttals(_fixed()),
        _verdicts(_verdict(verdict="confirmed")),
        blockers=blockers,
    )
    record = result.as_dict(blockers)
    assert record["blockers"][0]["claim"] == "the tz default is wrong"
    assert record["rebuttal"]["rebuttals"][0]["action"] == "fixed"
    assert record["verdicts"][0]["verdicts"][0]["verdict"] == "confirmed"
    assert "adjudication" not in json.dumps(record)  # the operator's, in GitHub


def test_the_verdict_prompt_carries_the_argument_the_finding_and_the_new_diff():
    """A fresh session inherits nothing (§5.5), so everything it judges on is
    passed explicitly — including the vocabulary, which a resumed implementer
    would already hold and this session does not."""
    turn = rebut.RebuttalTurn(
        rebuttals=[
            rebut.Rebuttal(finding=1, action="argued", argument="the caller sets it")
        ]
    )
    prompt = rebut.verdict_prompt(
        "correctness",
        blockers=[(1, _blocker())],
        rebuttal=turn,
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        spec_body="fix the gap",
        reviewed_diff=DIFF,
        diff=DIFF,
    )
    assert "1. [correctness] src/gap.py:1 — the tz default is wrong" in prompt
    assert "the caller sets it" in prompt
    assert "def gap(series, tz=" in prompt
    assert "fix the gap" in prompt
    assert "**Verdict**:" in prompt  # CONTEXT.md §5's vocabulary


def test_the_verdict_prompt_carries_the_diff_its_blockers_were_filed_against():
    """The prompt must carry two diffs, not one — the tree the blocker's line
    number was filed against, and the tree as it now stands after the
    rebuttal — and say, by heading, which is which. A critic told only "the
    diff below" when two sit below cannot tell them apart (this spec)."""
    turn = rebut.RebuttalTurn(
        rebuttals=[
            rebut.Rebuttal(finding=1, action="fixed", argument="committed the fix")
        ]
    )
    after_rebuttal = (
        "diff --git a/src/gap.py b/src/gap.py\n"
        "--- a/src/gap.py\n+++ b/src/gap.py\n@@ -1,2 +1,2 @@\n"
        '-def gap(series, tz="UTC"):\n+def gap(series, tz="America/New_York"):\n'
        "     return series\n"
    )
    prompt = rebut.verdict_prompt(
        "correctness",
        blockers=[(1, _blocker())],
        rebuttal=turn,
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        spec_body="fix the gap",
        reviewed_diff=DIFF,
        diff=after_rebuttal,
    )
    # Each diff sits under its own heading — not merely present somewhere in
    # the prompt, which a caller that swapped `reviewed_diff` and `diff`
    # would also satisfy while recreating the exact bug this spec fixes.
    assert f"## The diff your findings were filed against\n\n{DIFF}" in prompt
    assert f"## The diff, after the rebuttal\n\n{after_rebuttal}" in prompt
    # Named by heading, not by position — the sentence must still be true if
    # the blocks are ever reordered for prompt caching (out of scope here).
    # Wrap-insensitive: the template is prose and rewraps, but which heading
    # the numbers belong to is the whole claim, so it stays pinned literally.
    assert (
        'from the tree under the heading "The diff your findings were filed '
        'against", not the tree under "The diff, after the rebuttal"'
    ) in " ".join(prompt.split())
    # The other half of the same fix: "What to emit" said "the diff below" with
    # two diffs below it. Reverting that clause left the whole suite green.
    assert (
        'the diff under "The diff, after the rebuttal" below is the change as '
        "it now stands"
    ) in " ".join(prompt.split())


def test_the_verdict_prompt_carries_the_repo_s_claude_md():
    """The verdict session is a fresh critic session, like REVIEW's, and gets
    the same standing instructions for the same reason (§5.3)."""
    turn = rebut.RebuttalTurn(
        rebuttals=[
            rebut.Rebuttal(finding=1, action="argued", argument="the caller sets it")
        ]
    )
    prompt = rebut.verdict_prompt(
        "correctness",
        blockers=[(1, _blocker())],
        rebuttal=turn,
        context_md=CONTEXT_MD,
        claude_md="- Never collapse `error` into `fail`.\n",
        prompts_dir=PROMPTS,
        spec_body="fix the gap",
        reviewed_diff=DIFF,
        diff=DIFF,
    )
    assert "## This repository's standing instructions" in prompt
    assert "- Never collapse `error` into `fail`." in prompt


def test_a_verdict_session_is_shown_only_its_own_lens_arguments():
    """`run_verdict` requires the verdict set to match the blockers exactly, so
    an argument about another lens's finding invites a verdict it did not ask
    for — and fails the whole phase on prompt shape, not on disagreement."""
    turn = rebut.RebuttalTurn(
        rebuttals=[
            rebut.Rebuttal(finding=1, action="argued", argument="mine to answer"),
            rebut.Rebuttal(finding=2, action="fixed", argument="the contract lens"),
        ]
    )
    prompt = rebut.verdict_prompt(
        "correctness",
        blockers=[(1, _blocker())],
        rebuttal=turn,
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        spec_body="fix the gap",
        reviewed_diff=DIFF,
        diff=DIFF,
    )
    assert "mine to answer" in prompt
    assert "the contract lens" not in prompt


def test_the_rebuttal_turns_are_capped_at_the_critic_budget_not_the_task_one():
    """These two turns resume the IMPLEMENT session, whose `max_budget_usd` is
    the whole task budget. Uncapped, REBUT re-spends it after REVIEW already
    has — the overrun the critic cap was introduced to close."""
    record: list[dict] = []
    _run("Fixed.", _rebuttals(_fixed()), _verdicts(_verdict()), record=record)
    assert OPTIONS["max_budget_usd"] == 1.0  # what IMPLEMENT was given
    # The rebuttal turn and its extraction turn, both under `budget_usd=2.0`.
    assert [call["options"]["max_budget_usd"] for call in record[:2]] == [2.0, 2.0]
    # And the implementer's tools are untouched by the override.
    assert "Bash" in record[0]["options"]["tools"]


def _result(*, rebuttal, verdicts, moved=True):
    return rebut.RebutResult(
        state="READY_FOR_REVIEW",
        why="",
        rebuttal=rebuttal,
        verdicts=verdicts,
        moved=moved,
        cost_usd=0.0,
    )


def test_sustained_blockers_is_zero_when_rebut_never_ran():
    """No `RebutResult` at all — REVIEW found no anchored blocker, or the task
    stopped before REBUT. Nothing to sustain."""
    assert rebut.sustained_blockers(None) == 0


def test_sustained_blockers_is_zero_when_the_rebuttal_turn_errored():
    """An errored rebuttal turn (§4.3) recorded no rebuttal at all, so there is
    no `argued` half to pair a verdict against — even if a verdict exists."""
    result = _result(
        rebuttal=rebut.RebuttalTurn(error="the model errored"),
        verdicts=[
            rebut.LensVerdicts(
                lens="correctness",
                verdicts=[rebut.Verdict(finding=1, verdict="confirmed", reason="r")],
            )
        ],
    )
    assert rebut.sustained_blockers(result) == 0


def test_sustained_blockers_is_zero_for_a_blocker_verdicted_but_never_rebutted():
    """`run_verdict` requires a verdict for every blocker it is shown, but
    nothing requires the implementer to have rebutted every one — the
    rebuttal is the implementer's own JSON, unchecked for completeness. A
    finding with no rebuttal entry has no `argued` half, so it must not count,
    whatever the verdict says."""
    result = _result(
        rebuttal=rebut.RebuttalTurn(rebuttals=[]),
        verdicts=[
            rebut.LensVerdicts(
                lens="correctness",
                verdicts=[rebut.Verdict(finding=1, verdict="confirmed", reason="r")],
            )
        ],
    )
    assert rebut.sustained_blockers(result) == 0


def test_sustained_blockers_on_sa_0005s_real_shape():
    """`SA-0005`: three blockers filed, two anchored (so numbered 1 and 2 —
    the third, unanchored, never reaches REBUT and carries no number). Both
    anchored blockers were confirmed: finding 1 was argued, finding 2 was
    fixed and committed. `anchored_concerns` reads `0` for this task; this
    function must read `1`, not `2` — a confirmed *fix* is work already done,
    not a sustained disagreement."""
    result = _result(
        rebuttal=rebut.RebuttalTurn(
            rebuttals=[
                rebut.Rebuttal(
                    finding=1, action="argued", argument="the finding is wrong"
                ),
                rebut.Rebuttal(finding=2, action="fixed", argument="committed the fix"),
            ]
        ),
        verdicts=[
            rebut.LensVerdicts(
                lens="correctness",
                verdicts=[
                    rebut.Verdict(finding=1, verdict="confirmed", reason="still wrong"),
                    rebut.Verdict(
                        finding=2, verdict="confirmed", reason="the fix is real"
                    ),
                ],
            )
        ],
    )
    assert rebut.sustained_blockers(result) == 1


def test_sustained_blockers_takes_the_first_answer_to_a_duplicated_finding():
    """Nothing constrains the extracted rebuttals to one entry per finding, and
    `session.py` records the first answer for exactly that reason. A `fixed`
    followed by a stray `argued` is a fixed blocker in the ledger, so it must
    not read as sustained here — otherwise the two disagree about the same
    task and the queue ranks on the one nobody measured."""
    result = _result(
        rebuttal=rebut.RebuttalTurn(
            rebuttals=[
                rebut.Rebuttal(finding=1, action="fixed", argument="committed the fix"),
                rebut.Rebuttal(
                    finding=1, action="argued", argument="on reflection, no"
                ),
            ]
        ),
        verdicts=[
            rebut.LensVerdicts(
                lens="correctness",
                verdicts=[
                    rebut.Verdict(
                        finding=1, verdict="confirmed", reason="the fix is real"
                    )
                ],
            )
        ],
    )
    assert rebut.sustained_blockers(result) == 0


def test_unkept_fixes_is_zero_when_rebut_never_ran():
    """No `RebutResult` at all — nothing to attribute an unkept fix to."""
    assert rebut.unkept_fixes(None) == 0


def test_unkept_fixes_is_zero_when_the_rebuttal_turn_errored():
    """An errored rebuttal turn recorded no rebuttal at all, so there is no
    `fixed` half to pair a verdict against — even if a verdict exists."""
    result = _result(
        rebuttal=rebut.RebuttalTurn(error="the model errored"),
        verdicts=[
            rebut.LensVerdicts(
                lens="correctness",
                verdicts=[rebut.Verdict(finding=1, verdict="confirmed", reason="r")],
            )
        ],
        moved=False,
    )
    assert rebut.unkept_fixes(result) == 0


def test_unkept_fixes_is_zero_for_a_blocker_verdicted_but_never_rebutted():
    """No rebuttal entry for the finding means no `fixed` half to pair a
    verdict against, whatever the verdict says."""
    result = _result(
        rebuttal=rebut.RebuttalTurn(rebuttals=[]),
        verdicts=[
            rebut.LensVerdicts(
                lens="correctness",
                verdicts=[rebut.Verdict(finding=1, verdict="confirmed", reason="r")],
            )
        ],
        moved=False,
    )
    assert rebut.unkept_fixes(result) == 0


def test_unkept_fixes_is_zero_when_head_moved():
    """§6's floor: `moved` is one bit for the whole rebuttal, so a task whose
    HEAD moved cannot be attributed to a single claimed fix, even when the
    finding that claimed it was confirmed."""
    result = _result(
        rebuttal=rebut.RebuttalTurn(
            rebuttals=[rebut.Rebuttal(finding=1, action="fixed", argument="committed")]
        ),
        verdicts=[
            rebut.LensVerdicts(
                lens="correctness",
                verdicts=[
                    rebut.Verdict(finding=1, verdict="confirmed", reason="still wrong")
                ],
            )
        ],
        moved=True,
    )
    assert rebut.unkept_fixes(result) == 0


def test_unkept_fixes_on_a_confirmed_blocker_whose_fix_never_committed():
    """A blocker the implementer claimed to fix, confirmed by the critic
    anyway, with no commit landing — the shape §6 names: a promise nobody
    kept, distinct from a sustained argument."""
    result = _result(
        rebuttal=rebut.RebuttalTurn(
            rebuttals=[
                rebut.Rebuttal(finding=1, action="fixed", argument="committed the fix"),
                rebut.Rebuttal(
                    finding=2, action="argued", argument="the finding is wrong"
                ),
            ]
        ),
        verdicts=[
            rebut.LensVerdicts(
                lens="correctness",
                verdicts=[
                    rebut.Verdict(finding=1, verdict="confirmed", reason="still wrong"),
                    rebut.Verdict(finding=2, verdict="confirmed", reason="unpersuaded"),
                ],
            )
        ],
        moved=False,
    )
    assert rebut.unkept_fixes(result) == 1
    assert rebut.sustained_blockers(result) == 1


def test_unkept_fixes_takes_the_first_answer_to_a_duplicated_finding():
    """`fixed` then a stray `argued` on the same finding: the first answer
    was `fixed`, and it must count here — not last-wins, which would read it
    as merely argued and drop it from this count."""
    result = _result(
        rebuttal=rebut.RebuttalTurn(
            rebuttals=[
                rebut.Rebuttal(finding=1, action="fixed", argument="committed the fix"),
                rebut.Rebuttal(
                    finding=1, action="argued", argument="on reflection, no"
                ),
            ]
        ),
        verdicts=[
            rebut.LensVerdicts(
                lens="correctness",
                verdicts=[
                    rebut.Verdict(finding=1, verdict="confirmed", reason="still wrong")
                ],
            )
        ],
        moved=False,
    )
    assert rebut.unkept_fixes(result) == 1


# --- backlog b-4e0868: REBUT's two turns read `structured_output`, not text ---


def test_the_rebuttal_extraction_turn_asks_for_the_schema_and_records_its_structured_output():
    record: list[dict] = []
    # Text disagrees with structured_output on purpose: it argues finding 1,
    # while the value marks it fixed. Only the value must be read.
    extracted = _turn(
        text=_block({"rebuttals": [_argued()]}),
        structured_output={"rebuttals": [_fixed()]},
    )
    result = _run("Fixed.", extracted, _verdicts(_verdict()), record=record)
    assert result.state == "READY_FOR_REVIEW"
    assert [r.action for r in result.rebuttal.rebuttals] == ["fixed"]
    assert len(record) == 3
    assert record[0]["options"].get("output_format") is None
    assert record[1]["options"]["output_format"] == {
        "type": "json_schema",
        "schema": rebut._Rebuttals.model_json_schema(),
    }
    without_format = {
        k: v for k, v in record[1]["options"].items() if k != "output_format"
    }
    assert without_format == record[0]["options"]


def test_each_verdict_session_asks_for_the_schema_and_records_its_structured_output():
    blockers = [_blocker(lens=lens) for lens in review.LENSES]
    fixes = [_fixed(n) for n in (1, 2, 3, 4)]
    # Each verdict session's text confirms its finding, and its
    # structured_output withdraws it instead. Only the value must be read.
    verdict_turns = [
        _turn(
            text=_block({"verdicts": [_verdict(n, verdict="confirmed")]}),
            structured_output={"verdicts": [_verdict(n, verdict="withdrawn")]},
        )
        for n in (1, 2, 3, 4)
    ]
    record: list[dict] = []
    result = _run(
        "Fixed all four.",
        _rebuttals(*fixes),
        *verdict_turns,
        blockers=blockers,
        record=record,
    )
    assert result.state == "READY_FOR_REVIEW"
    assert len(record) == 6  # rebuttal, extraction, four verdict sessions
    assert len(result.verdicts) == 4
    for lens_verdicts in result.verdicts:
        assert [v.verdict for v in lens_verdicts.verdicts] == ["withdrawn"]
    for call in record[2:]:
        options = dict(call["options"])
        output_format = options.pop("output_format")
        assert output_format == {
            "type": "json_schema",
            "schema": rebut._Verdicts.model_json_schema(),
        }
        expected = implement.agent_options(
            system_prompt=options["system_prompt"],
            max_turns=20,
            budget_usd=2.0,
            tools=review.REVIEW_TOOLS,
        )
        assert options == expected


def test_a_conventions_blocker_is_verdicted_by_a_session_of_its_own():
    """A conventions blocker gets a verdict at REBUT from a fresh session of
    its own. It sees only its own blocker, after the correctness lens's
    verdict session runs. `run_rebut` walks `review.LENSES` order, not
    filing order, so a conventions blocker filed first still runs after
    correctness's."""
    conventions_blocker = _blocker(lens="conventions", claim="a comment lies")
    correctness_blocker = _blocker(lens="correctness")
    record: list[dict] = []
    result = _run(
        "Fixed both.",
        _rebuttals(_fixed(1), _fixed(2)),
        _verdicts(_verdict(2, verdict="withdrawn")),
        _verdicts(_verdict(1, verdict="withdrawn")),
        blockers=[conventions_blocker, correctness_blocker],
        record=record,
    )
    assert result.state == "READY_FOR_REVIEW"
    assert [v.lens for v in result.verdicts] == ["correctness", "conventions"]
    assert [v.finding for v in result.verdicts[0].verdicts] == [2]
    assert [v.finding for v in result.verdicts[1].verdicts] == [1]
    conventions_call = record[-1]
    expected = rebut.verdict_prompt(
        "conventions",
        blockers=[(1, conventions_blocker)],
        rebuttal=result.rebuttal,
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        spec_body="fix the gap",
        reviewed_diff=DIFF,
        diff=DIFF,
    )
    assert conventions_call["options"]["system_prompt"] == expected


def test_a_rebuttal_turn_without_a_valid_structured_output_is_not_the_schema():
    for bad_value in (
        None,
        {"rebuttals": [{"finding": 1, "action": "maybe", "argument": "a"}]},
        json.dumps({"rebuttals": [{"finding": 1, "action": "fixed", "argument": "a"}]}),
    ):
        record: list[dict] = []
        extracted = _turn(
            text=_block({"rebuttals": [_argued()]}), structured_output=bad_value
        )
        result = _run("Fixed.", extracted, moved=False, record=record)
        assert result.state == "REBUTTING"
        assert result.rebuttal.error is not None
        assert result.rebuttal.error.startswith("not the schema")
        assert result.rebuttal.rebuttals == []
        assert result.rebuttal.error in result.why
        assert len(record) == 2


def test_a_verdict_session_without_a_valid_structured_output_is_not_the_schema():
    for bad_value in (
        None,
        {"verdicts": [{"finding": 1, "verdict": "maybe", "reason": "r"}]},
        json.dumps(
            {"verdicts": [{"finding": 1, "verdict": "withdrawn", "reason": "r"}]}
        ),
    ):
        record: list[dict] = []
        verdict_turn = _turn(
            text=_block({"verdicts": [_verdict(verdict="confirmed")]}),
            structured_output=bad_value,
        )
        result = _run(
            "Fixed.", _rebuttals(_fixed()), verdict_turn, moved=True, record=record
        )
        assert result.state == "REBUTTING"
        (lens_verdicts,) = result.verdicts
        assert lens_verdicts.verdicts == []
        assert lens_verdicts.error is not None
        assert lens_verdicts.error.startswith("not the schema")
        assert len(record) == 3


def test_unkept_fixes_does_not_count_an_argued_first_answer_stray_fixed_later():
    """The mirror duplicate: `argued` first, then a stray `fixed`. First
    answer wins `argued`, so this must read `0` here — not membership over
    every entry, which would see the trailing `fixed` and count it."""
    result = _result(
        rebuttal=rebut.RebuttalTurn(
            rebuttals=[
                rebut.Rebuttal(
                    finding=1, action="argued", argument="the finding is wrong"
                ),
                rebut.Rebuttal(finding=1, action="fixed", argument="committed anyway"),
            ]
        ),
        verdicts=[
            rebut.LensVerdicts(
                lens="correctness",
                verdicts=[
                    rebut.Verdict(finding=1, verdict="confirmed", reason="still wrong")
                ],
            )
        ],
        moved=False,
    )
    assert rebut.unkept_fixes(result) == 0


# --- b-ab4b33: a lens that reads the spec disagreeing with itself contradicts
# rather than withdraws the blocker it filed ---


def test_a_blocker_argued_from_one_spec_line_against_another_is_contradicted_and_counted_apart():
    correctness = _blocker()
    adequacy = _blocker(lens="adequacy", line=2)
    second_correctness = _blocker(line=3)

    # Case 1: one correctness blocker, argued, HEAD unmoved, contradicted.
    result = _run(
        "The finding rests on the wrong line.",
        _rebuttals(_argued()),
        _verdicts(
            _contradicted(1, _VALID_REBUTTAL_QUOTE, _VALID_FINDING_QUOTE, "disagree")
        ),
        blockers=[correctness],
        moved=False,
        spec_body=_CONTRADICTION_SPEC,
    )
    assert result.state == "READY_FOR_REVIEW"
    assert result.why == (
        "0 blocker(s) confirmed after the rebuttal, 1 on spec lines that "
        "contradict each other, 1 argued — recorded disagreement, yours to "
        "adjudicate"
    )
    (lens_verdicts,) = result.verdicts
    assert lens_verdicts.verdicts == [
        rebut.Verdict(
            finding=1,
            verdict="contradicted",
            reason="disagree",
            rebuttal_quote=_VALID_REBUTTAL_QUOTE,
            finding_quote=_VALID_FINDING_QUOTE,
        )
    ]
    record = result.as_dict([correctness])
    assert all(v["quote_failures"] == [] for v in record["verdicts"])

    # Case 2: blocker 1 the same, blocker 2 an adequacy blocker fixed and
    # confirmed, HEAD unmoved. The unkept-fix suffix joins the new clause.
    result = _run(
        "The finding rests on the wrong line.",
        _rebuttals(_argued(1), _fixed(2)),
        _verdicts(
            _contradicted(1, _VALID_REBUTTAL_QUOTE, _VALID_FINDING_QUOTE, "disagree")
        ),
        _verdicts(_verdict(2, verdict="confirmed", reason="still wrong")),
        blockers=[correctness, adequacy],
        moved=False,
        spec_body=_CONTRADICTION_SPEC,
    )
    assert result.state == "READY_FOR_REVIEW"
    assert result.why == (
        "1 blocker(s) confirmed after the rebuttal, 1 on spec lines that "
        "contradict each other, 1 argued — recorded disagreement, yours to "
        "adjudicate (a fix was claimed for some of them and no commit was made)"
    )
    record = result.as_dict([correctness, adequacy])
    assert all(v["quote_failures"] == [] for v in record["verdicts"])

    # Case 3: two correctness blockers argued and withdrawn, one adequacy
    # blocker fixed and contradicted on the same valid quotes, HEAD moved.
    result = _run(
        "Two arguments, one fix.",
        _rebuttals(_argued(1), _argued(3), _fixed(2)),
        _verdicts(_verdict(1, verdict="withdrawn"), _verdict(3, verdict="withdrawn")),
        _verdicts(
            _contradicted(2, _VALID_REBUTTAL_QUOTE, _VALID_FINDING_QUOTE, "disagree")
        ),
        blockers=[correctness, adequacy, second_correctness],
        moved=True,
        spec_body=_CONTRADICTION_SPEC,
    )
    assert result.state == "READY_FOR_REVIEW"
    assert result.why == (
        "0 blocker(s) confirmed after the rebuttal, 1 on spec lines that "
        "contradict each other, 2 argued — recorded disagreement, yours to "
        "adjudicate"
    )
    record = result.as_dict([correctness, adequacy, second_correctness])
    assert all(v["quote_failures"] == [] for v in record["verdicts"])

    # The claim's "and the two quotes differ" is load-bearing: the same
    # quote on both sides must fail the check instead of standing.
    same_quote = _run(
        "The finding rests on the wrong line.",
        _rebuttals(_argued()),
        _verdicts(
            _contradicted(1, _VALID_REBUTTAL_QUOTE, _VALID_REBUTTAL_QUOTE, "disagree")
        ),
        blockers=[correctness],
        moved=False,
        spec_body=_CONTRADICTION_SPEC,
    )
    assert same_quote.state == "READY_FOR_REVIEW"
    (same_quote_lens,) = same_quote.verdicts
    assert same_quote_lens.verdicts == [
        rebut.Verdict(finding=1, verdict="confirmed", reason="disagree")
    ]
    assert same_quote_lens.quote_failures == [
        {
            "finding": 1,
            "reason": "the two quotes are the same spec text",
            "rebuttal_quote": _VALID_REBUTTAL_QUOTE,
            "finding_quote": _VALID_REBUTTAL_QUOTE,
        }
    ]


_INVALID_QUOTE = "a quote that never appears in the shared spec text"
_ANOTHER_INVALID_QUOTE = "another quote that never appears in the shared spec text"
_LOWERCASED_FINDING_QUOTE = (
    "Only a `merged` or `rejected` newest task unstacks a child."
)
_WRAPPED_REBUTTAL_QUOTE = "The resolver stacks on no row when the newest task\n  is outside the waiting states."

# label, rebuttal_quote, finding_quote, the check's reason.
_QUOTE_FAILURE_CASES = [
    (
        "a",
        _INVALID_QUOTE,
        _VALID_FINDING_QUOTE,
        "the rebuttal's quote is not in the spec text",
    ),
    (
        "b",
        _VALID_REBUTTAL_QUOTE,
        _LOWERCASED_FINDING_QUOTE,
        "the finding's quote is not in the spec text",
    ),
    (
        "c",
        _VALID_REBUTTAL_QUOTE,
        _WRAPPED_REBUTTAL_QUOTE,
        "the two quotes are the same spec text",
    ),
    (
        "d",
        " \n\t",
        _VALID_FINDING_QUOTE,
        "the rebuttal's quote is not in the spec text",
    ),
    (
        "e",
        _INVALID_QUOTE,
        _ANOTHER_INVALID_QUOTE,
        "the rebuttal's quote is not in the spec text",
    ),
    (
        "f",
        _INVALID_QUOTE,
        _VALID_FINDING_QUOTE,
        "the rebuttal's quote is not in the spec text",
    ),
    (
        "g",
        _INVALID_QUOTE,
        _INVALID_QUOTE,
        "the rebuttal's quote is not in the spec text",
    ),
    ("h", _VALID_REBUTTAL_QUOTE, " \t", "the finding's quote is not in the spec text"),
]


def test_a_contradicted_verdict_whose_quotes_fail_the_check_is_read_as_confirmed_and_recorded():
    blocker1 = _blocker(lens="correctness", line=1)
    blocker2 = _blocker(lens="contract", line=2)
    # Both arguments hold case (a)'s failing rebuttal quote word for word, so a
    # check that reads `spec_body` joined with the rebuttal would wrongly find it.
    argument_1 = f"On finding 1, the caller sets it: {_INVALID_QUOTE}"
    argument_2 = f"On finding 2, the same holds: {_INVALID_QUOTE}"

    for label, rebuttal_quote, finding_quote, reason in _QUOTE_FAILURE_CASES:
        swapped = label == "f"
        failing_finding = 1 if swapped else 2
        withdrawn_finding = 2 if swapped else 1
        failing_lens = "correctness" if swapped else "contract"
        withdrawn_lens = "contract" if swapped else "correctness"
        failing_verdict = _contradicted(
            failing_finding, rebuttal_quote, finding_quote, "still wrong"
        )
        withdrawn_verdict = _verdict(withdrawn_finding, verdict="withdrawn")
        correctness_turn = _verdicts(failing_verdict if swapped else withdrawn_verdict)
        contract_turn = _verdicts(withdrawn_verdict if swapped else failing_verdict)

        result = _run(
            "Two arguments filed.",
            _rebuttals(
                _argued(1, argument=argument_1), _argued(2, argument=argument_2)
            ),
            correctness_turn,
            contract_turn,
            blockers=[blocker1, blocker2],
            moved=False,
            spec_body=_CONTRADICTION_SPEC,
        )
        assert result.state == "READY_FOR_REVIEW", label
        assert result.why == (
            "1 blocker(s) confirmed after the rebuttal, 2 argued — recorded "
            "disagreement, yours to adjudicate"
        ), label
        lenses = {v.lens: v for v in result.verdicts}
        assert lenses[failing_lens].verdicts == [
            rebut.Verdict(
                finding=failing_finding, verdict="confirmed", reason="still wrong"
            )
        ], label
        assert lenses[withdrawn_lens].verdicts == [
            rebut.Verdict(finding=withdrawn_finding, verdict="withdrawn", reason="rr")
        ], label
        by_lens = {
            v["lens"]: v for v in result.as_dict([blocker1, blocker2])["verdicts"]
        }
        assert by_lens[withdrawn_lens]["quote_failures"] == [], label
        assert by_lens[failing_lens]["quote_failures"] == [
            {
                "finding": failing_finding,
                "reason": reason,
                "rebuttal_quote": rebuttal_quote,
                "finding_quote": finding_quote,
            }
        ], label

    # Two spec lines that differ only in case are two quotes, not one.
    result = _run(
        "Two arguments filed.",
        _rebuttals(_argued(1, argument=argument_1), _argued(2, argument=argument_2)),
        _verdicts(_verdict(1, verdict="withdrawn")),
        _verdicts(_contradicted(2, _LOWERCASED_FINDING_QUOTE, _VALID_FINDING_QUOTE)),
        blockers=[blocker1, blocker2],
        moved=False,
        spec_body=_CONTRADICTION_SPEC + _LOWERCASED_FINDING_QUOTE,
    )
    contract = next(v for v in result.verdicts if v.lens == "contract")
    assert [v.verdict for v in contract.verdicts] == ["contradicted"]
    assert contract.quote_failures == []


def test_a_contradicted_verdict_missing_a_quote_is_read_as_confirmed_and_recorded():
    base = {"finding": 1, "verdict": "contradicted", "reason": "still wrong"}
    # label, the verdict dict the lens gives, the check's reason, the two
    # quotes as `quote_failures` must record them.
    rows = [
        (
            "a",
            base | {"finding_quote": _VALID_FINDING_QUOTE},
            None,
            _VALID_FINDING_QUOTE,
        ),
        (
            "b",
            base | {"rebuttal_quote": _VALID_REBUTTAL_QUOTE},
            _VALID_REBUTTAL_QUOTE,
            None,
        ),
        (
            "c",
            base | {"rebuttal_quote": _VALID_REBUTTAL_QUOTE, "finding_quote": None},
            _VALID_REBUTTAL_QUOTE,
            None,
        ),
        (
            "d",
            base | {"rebuttal_quote": "", "finding_quote": _VALID_FINDING_QUOTE},
            "",
            _VALID_FINDING_QUOTE,
        ),
        (
            "e",
            base | {"rebuttal_quote": _VALID_REBUTTAL_QUOTE, "finding_quote": ""},
            _VALID_REBUTTAL_QUOTE,
            "",
        ),
    ]
    reasons = {
        "a": "the rebuttal's quote is not in the spec text",
        "b": "the finding's quote is not in the spec text",
        "c": "the finding's quote is not in the spec text",
        "d": "the rebuttal's quote is not in the spec text",
        "e": "the finding's quote is not in the spec text",
    }

    for label, verdict_dict, rebuttal_quote, finding_quote in rows:
        result = _run(
            "Argued.",
            _rebuttals(_argued()),
            _verdicts(verdict_dict),
            blockers=[_blocker()],
            moved=False,
            spec_body=_CONTRADICTION_SPEC,
        )
        assert result.state == "READY_FOR_REVIEW", label
        assert result.why == (
            "1 blocker(s) confirmed after the rebuttal, 1 argued — recorded "
            "disagreement, yours to adjudicate"
        ), label
        (lens_verdicts,) = result.verdicts
        assert lens_verdicts.error is None, label
        assert lens_verdicts.verdicts == [
            rebut.Verdict(finding=1, verdict="confirmed", reason="still wrong")
        ], label
        assert lens_verdicts.quote_failures == [
            {
                "finding": 1,
                "reason": reasons[label],
                "rebuttal_quote": rebuttal_quote,
                "finding_quote": finding_quote,
            }
        ], label

    # The sixth row: a verdict value outside the three accepted is still not
    # the schema, and the task halts unjudged.
    result = _run(
        "Argued.",
        _rebuttals(_argued()),
        _verdicts({"finding": 1, "verdict": "overruled", "reason": "?"}),
        blockers=[_blocker()],
        moved=False,
        spec_body=_CONTRADICTION_SPEC,
    )
    assert result.state == "REBUTTING"
    (lens_verdicts,) = result.verdicts
    assert lens_verdicts.verdicts == []
    assert lens_verdicts.error is not None
    assert (
        result.why == "['correctness'] produced no verdict — the rebuttal is unjudged"
    )


def test_a_contradicted_blocker_counts_as_sustained_or_unkept_like_a_confirmed_one():
    # action, HEAD moved, verdict, expected sustained_blockers, expected unkept_fixes.
    rows = [
        ("argued", True, "contradicted", 1, 0),
        ("fixed", False, "contradicted", 0, 1),
        ("argued", True, "withdrawn", 0, 0),
    ]
    for action, moved, verdict_value, sustained, unkept in rows:
        result = _result(
            rebuttal=rebut.RebuttalTurn(
                rebuttals=[
                    rebut.Rebuttal.model_validate(
                        {"finding": 1, "action": action, "argument": "the argument"}
                    )
                ]
            ),
            verdicts=[
                rebut.LensVerdicts(
                    lens="correctness",
                    verdicts=[
                        rebut.Verdict.model_validate(
                            {"finding": 1, "verdict": verdict_value, "reason": "r"}
                        )
                    ],
                )
            ],
            moved=moved,
        )
        case = (action, moved, verdict_value)
        assert rebut.sustained_blockers(result) == sustained, case
        assert rebut.unkept_fixes(result) == unkept, case


# --- backlog b-cd5fd2: a `preserves` criterion's guarded blocker cannot be
# withdrawn by pointing outside the diff ---

_WITHDRAWAL_ARGUMENT = "the line sits outside my diff, so it is not mine to answer"

_WITHDRAWAL_HOST_SENTENCE = (
    "The host kept this blocker: its criterion is `preserves`, so it holds "
    "over the whole file, and no committed fix answered it. The lens withdrew it:"
)


def _host_filed(witness, tail="the criterion's own edit"):
    return f"{review.HOST_FILED}{witness} stayed green with {tail}"


def test_a_withdrawn_host_filed_blocker_on_a_preserves_criterion_stands_only_after_a_committed_fix():
    """Criterion 1: a lens cannot withdraw a host-filed blocker on a `preserves`
    criterion's survivor after the implementer argues the line is outside the diff. It stands
    only when the blocker's first answer was `fixed` and HEAD moved. That
    holds whether the blocker came from the criterion's own edit or a wrong
    version, and a shared witness prefix does not fool the guard."""
    from saffron.intake import Criterion

    preserved = Criterion(
        claim="the total is unchanged", witness="t.py::test_a", preserves=True
    )
    extended = Criterion(claim="the total stays sorted", witness="t.py::test_a_b")

    b1 = _blocker(lens="adequacy", claim=_host_filed("t.py::test_a"))
    b2 = _blocker(lens="adequacy", claim=_host_filed("t.py::test_a", "a wrong version"))
    b3 = _blocker(lens="adequacy", claim=_host_filed("t.py::test_a"))
    b4 = _blocker(lens="adequacy", claim=_host_filed("t.py::test_a"))
    b5 = _blocker(lens="adequacy", claim=_host_filed("t.py::test_a_b"))
    b6 = _blocker(lens="adequacy", claim="t.py::test_a stayed green with any edit")
    b7 = _blocker(lens="adequacy", claim=_host_filed("t.py::test_a"))
    b8 = _blocker()
    blockers_1 = [b1, b2, b3, b4, b5, b6, b7, b8]

    result_1 = _run(
        "I have answered every finding.",
        _rebuttals(
            _argued(1, _WITHDRAWAL_ARGUMENT),
            _argued(2, _WITHDRAWAL_ARGUMENT),
            _fixed(3, "fixed it"),
            _argued(5, _WITHDRAWAL_ARGUMENT),
            _argued(6, _WITHDRAWAL_ARGUMENT),
            _argued(7, _WITHDRAWAL_ARGUMENT),
            _argued(8, _WITHDRAWAL_ARGUMENT),
        ),
        _verdicts(_verdict(8, reason="8")),
        _verdicts(
            _verdict(1, reason="1"),
            _verdict(2, reason="2"),
            _verdict(3, reason="3"),
            _verdict(4, reason="4"),
            _verdict(5, reason="5"),
            _verdict(6, reason="6"),
            _verdict(7, verdict="confirmed", reason="7"),
        ),
        blockers=blockers_1,
        acceptance=[preserved, extended],
        moved=False,
    )

    assert result_1.state == "READY_FOR_REVIEW"
    assert result_1.why == (
        "5 blocker(s) confirmed after the rebuttal, 6 argued — recorded "
        "disagreement, yours to adjudicate (a fix was claimed for some of "
        "them and no commit was made)"
    )

    correctness_1 = next(v for v in result_1.verdicts if v.lens == "correctness")
    assert correctness_1.verdicts == [
        rebut.Verdict(finding=8, verdict="withdrawn", reason="r8")
    ]

    adequacy_1 = next(v for v in result_1.verdicts if v.lens == "adequacy")
    assert adequacy_1.verdicts == [
        rebut.Verdict(
            finding=1, verdict="confirmed", reason=f"{_WITHDRAWAL_HOST_SENTENCE} r1"
        ),
        rebut.Verdict(
            finding=2, verdict="confirmed", reason=f"{_WITHDRAWAL_HOST_SENTENCE} r2"
        ),
        rebut.Verdict(
            finding=3, verdict="confirmed", reason=f"{_WITHDRAWAL_HOST_SENTENCE} r3"
        ),
        rebut.Verdict(
            finding=4, verdict="confirmed", reason=f"{_WITHDRAWAL_HOST_SENTENCE} r4"
        ),
        rebut.Verdict(finding=5, verdict="withdrawn", reason="r5"),
        rebut.Verdict(finding=6, verdict="withdrawn", reason="r6"),
        rebut.Verdict(finding=7, verdict="confirmed", reason="r7"),
    ]

    as_dict_1 = result_1.as_dict(blockers_1)
    by_lens_1 = {v["lens"]: v for v in as_dict_1["verdicts"]}
    assert by_lens_1["correctness"]["withdrawal_refusals"] == []
    assert by_lens_1["adequacy"]["withdrawal_refusals"] == [
        {"finding": n, "withdrawn_reason": f"r{n}"} for n in range(1, 5)
    ]

    # Run 2, HEAD moved: blocker 1 stands, since its only answer is `fixed`.
    # Blocker 3 is argued first and `fixed` second, so the first answer wins.
    blockers_2 = [b1, b2, b3, b4]
    result_2 = _run(
        "Here is my second answer.",
        _rebuttals(
            _fixed(1, "fixed it"),
            _argued(2, _WITHDRAWAL_ARGUMENT),
            _argued(3, _WITHDRAWAL_ARGUMENT),
            _fixed(3, "fixed it too"),
        ),
        _verdicts(
            _verdict(1, reason="1"),
            _verdict(2, reason="2"),
            _verdict(3, reason="3"),
            _verdict(4, reason="4"),
        ),
        blockers=blockers_2,
        acceptance=[preserved, extended],
        moved=True,
    )

    assert result_2.state == "READY_FOR_REVIEW"
    assert result_2.why == (
        "3 blocker(s) confirmed after the rebuttal, 2 argued — recorded "
        "disagreement, yours to adjudicate"
    )

    (adequacy_2,) = result_2.verdicts
    assert adequacy_2.lens == "adequacy"
    assert adequacy_2.verdicts == [
        rebut.Verdict(finding=1, verdict="withdrawn", reason="r1"),
        rebut.Verdict(
            finding=2, verdict="confirmed", reason=f"{_WITHDRAWAL_HOST_SENTENCE} r2"
        ),
        rebut.Verdict(
            finding=3, verdict="confirmed", reason=f"{_WITHDRAWAL_HOST_SENTENCE} r3"
        ),
        rebut.Verdict(
            finding=4, verdict="confirmed", reason=f"{_WITHDRAWAL_HOST_SENTENCE} r4"
        ),
    ]

    as_dict_2 = result_2.as_dict(blockers_2)
    (adequacy_2_dict,) = as_dict_2["verdicts"]
    assert adequacy_2_dict["withdrawal_refusals"] == [
        {"finding": n, "withdrawn_reason": f"r{n}"} for n in range(2, 5)
    ]


def test_a_lens_blocker_quoting_the_host_text_mid_claim_stays_withdrawn():
    """The guard reads the start of a claim only. This lens blocker quotes
    the host's text after a word of its own. It is withdrawn as the lens
    says, and no refusal is recorded."""
    from saffron.intake import Criterion

    preserved = Criterion(
        claim="the total is unchanged", witness="t.py::test_a", preserves=True
    )
    quoting = _blocker(lens="adequacy", claim="see " + _host_filed("t.py::test_a"))
    result = _run(
        "I have answered every finding.",
        _rebuttals(_argued(1, _WITHDRAWAL_ARGUMENT)),
        _verdicts(_verdict(1, reason="1")),
        blockers=[quoting],
        acceptance=[preserved],
        moved=False,
    )

    (adequacy,) = result.verdicts
    assert adequacy.verdicts == [
        rebut.Verdict(finding=1, verdict="withdrawn", reason="r1")
    ]
    (adequacy_dict,) = result.as_dict([quoting])["verdicts"]
    assert adequacy_dict["withdrawal_refusals"] == []


def _between(text: str, start: str, end: str) -> str:
    begin = text.index(start) + len(start)
    stop = text.index(end, begin)
    return text[begin:stop]


def _first_paragraph(section: str) -> str:
    return " ".join(section.strip().split("\n\n", 1)[0].split())


def _bullets(section: str) -> list[str]:
    return [
        " ".join(item.split())
        for item in re.findall(r"(?ms)^- (.+?)(?=\n- |\n\n|\Z)", section)
    ]


def test_the_verdict_prompts_offer_contradicted_and_ask_for_both_quotes():
    turn = rebut.RebuttalTurn(
        rebuttals=[
            rebut.Rebuttal(finding=1, action="argued", argument="the caller sets it")
        ]
    )
    prompt = rebut.verdict_prompt(
        "correctness",
        blockers=[(1, _blocker())],
        rebuttal=turn,
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        spec_body="fix the gap",
        reviewed_diff=DIFF,
        diff=DIFF,
    )

    instruction = _between(prompt, "## Your instruction", "## Your findings")
    assert _first_paragraph(instruction) == (
        "For each finding, answer `confirmed`, `withdrawn` or `contradicted`."
    )
    assert _bullets(instruction) == [
        "`confirmed` — the finding still stands. The fix does not address it, "
        "or the argument is wrong, or nothing was done about it. Say "
        "concretely why.",
        '`withdrawn` — you were wrong, or the change under "The diff, after '
        'the rebuttal" resolves it.',
        '`contradicted`: two lines of the spec under "The task" disagree. '
        "The rebuttal's argument rests on one of them, and your finding "
        "rests on the other. Quote both, each copied exactly. The host "
        "looks for both quotes in that spec. It reads your answer as "
        "`confirmed` when it cannot find one, or when the two are the same "
        "text.",
    ]

    emit = _between(
        prompt, "## What to emit", "## The diff your findings were filed against"
    )
    assert _bullets(emit) == [
        "`finding` (integer) — the number of the finding, exactly as listed above.",
        "`verdict` (string): `confirmed`, `withdrawn` or `contradicted`.",
        "`reason` (string) — one or two sentences. If you are confirming, why "
        "the fix or the argument does not settle it; if you are withdrawing, "
        "what changed your mind.",
        "`rebuttal_quote` (string): required with `contradicted`. The spec "
        "text the rebuttal's argument rests on.",
        "`finding_quote` (string): required with `contradicted`. The spec "
        "text your finding rests on.",
    ]

    assert " ".join(rebut.VERDICT_TURN_PROMPT.split()) == (
        "For each of your findings, answer `confirmed`, `withdrawn` or "
        "`contradicted` now, given the rebuttal. Read whatever you need to. "
        "You hold no tool that can change anything. Answer now in the "
        "required structured format."
    )
