from __future__ import annotations

import json
from pathlib import Path

import pytest

from saffron.agents.findings import Finding
from saffron.phases import implement, rebut

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


def _blocker(lens="correctness", **kwargs):
    base = {
        "lens": lens,
        "severity": "blocker",
        "file": "src/gap.py",
        "line": 1,
        "claim": "the tz default is wrong",
        "anchored": True,
    }
    return Finding(**(base | kwargs))


def _turn(text, cost=0.1):
    return implement.AttemptResult(
        session_id="sess-1",
        subtype="success",
        terminal_reason="completed",
        num_turns=1,
        cost_usd_est=cost,
        text=text,
    )


def _block(payload):
    return f"Done.\n<output>\n{json.dumps(payload)}\n</output>"


def _rebuttals(*entries):
    return _block({"rebuttals": list(entries)})


def _verdicts(*entries):
    return _block({"verdicts": list(entries)})


def _fixed(finding=1, argument="committed the fix"):
    return {"finding": finding, "action": "fixed", "argument": argument}


def _argued(finding=1, argument="the default is set by the caller"):
    return {"finding": finding, "action": "argued", "argument": argument}


def _verdict(finding=1, verdict="withdrawn", reason="r"):
    return {"finding": finding, "verdict": verdict, "reason": "r" + reason}


def _agent(*texts, record=None):
    scripted = iter(texts)

    def run(container, *, prompt, options, **kwargs):
        if record is not None:
            record.append({"prompt": prompt, "options": options, "kwargs": kwargs})
        turn = next(scripted)
        if isinstance(turn, BaseException):
            raise turn
        return turn if isinstance(turn, implement.AttemptResult) else _turn(turn)

    return run


def _run(
    *texts,
    blockers=None,
    moved=True,
    gates=None,
    record=None,
    gate_suites=None,
):
    def _rerun_gates():
        if gate_suites is not None:
            gate_suites.append(True)
        return gates

    return rebut.run_rebut(
        "cell",
        blockers=blockers if blockers is not None else [_blocker()],
        options=OPTIONS,
        session_id="sess-1",
        spec_body="fix the gap",
        context_md=CONTEXT_MD,
        prompts_dir=PROMPTS,
        max_turns=20,
        budget_usd=2.0,
        head_moved=lambda: moved,
        rerun_gates=_rerun_gates,
        diff=lambda: DIFF,
        agent=_agent(*texts, record=record),
        watch=lambda _line: None,
    )


def test_a_claimed_fix_with_no_commit_and_no_argument_does_not_advance():
    """§4.3 at the phase where an agent has the strongest incentive to claim it
    is done: HEAD moved, or an explicit recorded argument — and "I fixed it" is
    neither. Nothing is bought after the measurement fails."""
    gate_suites: list[bool] = []
    record: list[dict] = []
    result = _run(
        "I have addressed the findings.",
        _rebuttals(_fixed()),
        moved=False,
        record=record,
        gate_suites=gate_suites,
    )
    assert result.state == "REBUTTING"
    assert "committed nothing" in result.why
    assert result.verdicts == []
    assert gate_suites == []  # HEAD did not move; the suite would answer twice
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
    result = _run(
        "Fixed.",
        _rebuttals(_fixed()),
        moved=True,
        gates="EXHAUSTED",
        record=record,
    )
    assert result.state == "EXHAUSTED"
    assert "does not re-enter the repair loop" in result.why
    # The rebuttal is kept, and no verdict session was bought for a dead task.
    assert [r.action for r in result.rebuttal.rebuttals] == ["fixed"]
    assert len(record) == 2


def test_an_errored_gate_after_the_rebuttal_is_not_the_tasks_failure():
    result = _run("Fixed.", _rebuttals(_fixed()), moved=True, gates="GATE_ERROR")
    assert result.state == "GATE_ERROR"


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
        prompts_dir=PROMPTS,
        spec_body="fix the gap",
        diff=DIFF,
    )
    assert "1. [correctness] src/gap.py:1 — the tz default is wrong" in prompt
    assert "the caller sets it" in prompt
    assert "def gap(series, tz=" in prompt
    assert "fix the gap" in prompt
    assert "**Verdict**:" in prompt  # CONTEXT.md §5's vocabulary


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
        prompts_dir=PROMPTS,
        spec_body="fix the gap",
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
