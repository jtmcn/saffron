from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from harness import lens_scoring
from saffron.agents.findings import Finding
from saffron.gates.contract import GateResult
from saffron.intake import Mutant
from saffron.phases import implement, review
from saffron.phases.review import LensReview

PROMPTS = Path(review.__file__).resolve().parents[1] / "agents" / "prompts"
CONTEXT_MD = (Path(review.__file__).resolve().parents[2] / "CONTEXT.md").read_text()

DIFF = """diff --git a/src/gap.py b/src/gap.py
--- a/src/gap.py
+++ b/src/gap.py
@@ -1,2 +1,2 @@
-def gap(series):
+def gap(series, tz="UTC"):
     return series
"""


def _turn(text, cost=0.1):
    return implement.AttemptResult(
        session_id="lens-1",
        subtype="success",
        terminal_reason="completed",
        num_turns=1,
        cost_usd_est=cost,
        text=text,
    )


def _block(findings):
    return f"Here it is.\n<output>\n{json.dumps({'findings': findings})}\n</output>"


def _finding(**kwargs):
    base = {"file": "src/gap.py", "line": 1, "severity": "concern", "claim": "c"}
    return base | kwargs


def _agent(*texts, record=None):
    scripted = iter(texts)

    def run(container, *, prompt, options, **kwargs):
        if record is not None:
            record.append({"prompt": prompt, "options": options, "kwargs": kwargs})
        # Falls back to a clean review for any lens beyond the ones a test
        # scripted explicitly — the same shape `test_session.py`'s harness
        # uses, so a test that only cares about one or two lenses need not
        # name every lens declared in `review.LENSES`.
        text = next(scripted, _block([]))
        if isinstance(text, BaseException):
            raise text
        return _turn(text)

    return run


def _review(*texts, read_head=lambda _p: None, record=None):
    return review.run_review(
        "cell",
        diff=DIFF,
        read_head=read_head,
        spec_body="fix the gap",
        gates="- tests: pass (pytest 8.0)",
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        max_turns=20,
        budget_usd=2.0,
        agent=_agent(*texts, record=record),
        spec_id="SY-1",
        emit=lambda _e: None,
    )


def test_the_critic_holds_no_tool_that_can_change_anything():
    """The implementer gets Write/Edit/Bash; a critic that can run a command can
    edit the thing it is judging, and `tools` is what withholds (§5.3)."""
    options = implement.agent_options(
        system_prompt="s", max_turns=5, budget_usd=1.0, tools=review.REVIEW_TOOLS
    )
    assert options["tools"] == ["Read", "Glob", "Grep"]
    assert options["allowed_tools"] == options["tools"]
    for tool in ("Bash", "Write", "Edit"):
        assert tool not in options["tools"]


def test_the_implementer_keeps_its_own_tools():
    options = implement.agent_options(system_prompt="s", max_turns=5, budget_usd=1.0)
    assert "Bash" in options["tools"]


def test_every_declared_lens_runs_once_and_never_resumes():
    """§5.5: the host drives the lens set, because a model asked to delegate
    produces a set that varies by task with no error when a lens is skipped.
    And a resumed session would carry the implementer's transcript. (All
    outputs here are well-formed, so this is the happy path specifically —
    the schema-repair re-prompt's own single, narrow resume is covered by
    the re-prompt tests below.)"""
    record: list[dict] = []
    reviews = _review(_block([]), _block([]), record=record)
    assert [r.lens for r in reviews] == list(review.LENSES)
    assert len(record) == len(review.LENSES)
    assert all(call["kwargs"].get("resume") is None for call in record)
    # Different lenses, not the same one twice — every declared lens gets its
    # own prompt, whatever the count.
    assert len({call["options"]["system_prompt"] for call in record}) == len(
        review.LENSES
    )


def test_a_lens_that_finds_nothing_is_a_clean_review():
    reviews = _review(_block([]), _block([]))
    assert [r.findings for r in reviews] == [[] for _ in review.LENSES]
    assert review.review_state(reviews)[0] == "READY_FOR_REVIEW"


def test_findings_are_stamped_with_the_lens_that_filed_them():
    """The critic never names its own lens: a lens that could would be able to
    file inside another remit and still look clean."""
    reviews = _review(_block([_finding()]), _block([]))
    assert [f.lens for f in reviews[0].findings] == ["correctness"]


def test_a_finding_the_host_cannot_anchor_is_kept_and_not_counted():
    reviews = _review(
        _block([_finding(severity="blocker"), _finding(file="ghost.py", line=9)]),
        _block([]),
    )
    correctness = reviews[0]
    assert [f.anchored for f in correctness.findings] == [True, False]
    assert correctness.drop_rate == pytest.approx(0.5)


def test_an_unanchored_blocker_routes_nowhere():
    """A hallucinated blocker must not stop a task — the drop is the whole
    point of reconciling findings against the diff (§5.5)."""
    reviews = _review(
        _block([_finding(file="ghost.py", line=9, severity="blocker")]), _block([])
    )
    state, why = review.review_state(reviews)
    assert state == "READY_FOR_REVIEW"
    assert "0 concern" in why


def test_an_anchored_blocker_routes_to_rebut():
    """Any single anchored blocker routes onward — no vote, because the lenses
    are disjoint by construction (§5.5)."""
    reviews = _review(_block([_finding(severity="blocker")]), _block([]))
    state, why = review.review_state(reviews)
    assert state == "REBUTTING"
    assert "1 blocker" in why


def test_notes_are_excluded_from_the_number_the_queue_sorts_on():
    reviews = _review(
        _block([_finding(severity="note"), _finding(severity="concern")]), _block([])
    )
    state, why = review.review_state(reviews)
    assert state == "READY_FOR_REVIEW"
    assert "1 concern" in why


def test_output_that_is_not_the_schema_is_an_incomplete_review_not_a_clean_one():
    """§4.3 again: a lens that produced nothing and a lens that found nothing
    must never be the same value. Two malformed turns in a row (the retry
    below also fails) so this exercises the terminal case, not the recovery."""
    reviews = _review(
        "I could not find anything wrong.",
        "I could not find anything wrong.",
        _block([]),
    )
    assert reviews[0].error and reviews[0].error.startswith("not the schema")
    assert reviews[0].cost_usd == 0.2  # both attempts' cost, summed
    state, why = review.review_state(reviews)
    assert state == "REVIEWING"
    assert "correctness" in why


def test_a_severity_the_vocabulary_does_not_have_is_not_the_schema():
    reviews = _review(
        _block([_finding(severity="critical")]),
        _block([_finding(severity="critical")]),
        _block([]),
    )
    assert reviews[0].error


def test_a_lens_whose_session_failed_still_charges_what_it_spent():
    failed = implement.AgentFailed("max turns", _turn("", cost=0.4))
    reviews = _review(failed, _block([]))
    assert reviews[0].cost_usd == 0.4
    assert reviews[0].error
    assert review.review_state(reviews)[0] == "REVIEWING"


def _lens_agent(*texts, record=None, costs=None):
    """Like `_agent`, but scoped to one `run_lens` call rather than a whole
    `run_review` pass, and with per-call cost control — the re-prompt tests
    need the first and second attempt to carry distinct, summable costs."""
    scripted = iter(texts)
    cost_iter = iter(costs) if costs is not None else None

    def run(container, *, prompt, options, **kwargs):
        if record is not None:
            record.append({"prompt": prompt, "options": options, "kwargs": kwargs})
        text = next(scripted)
        cost = next(cost_iter) if cost_iter is not None else 0.1
        if isinstance(text, BaseException):
            raise text
        return _turn(text, cost=cost)

    return run


def _run_lens(agent, lens="correctness", **kwargs):
    return review.run_lens(
        "cell",
        lens=lens,
        system_prompt="s",
        max_turns=20,
        budget_usd=kwargs.pop("budget_usd", 2.0),
        agent=agent,
        spec_id="SY-1",
        emit=lambda _e: None,
        **kwargs,
    )


def test_a_malformed_first_output_is_reprompted_once_and_recovers():
    """Mirrors `session.py`'s `PlanNotSchema` re-prompt (§5.3): same shape,
    applied to a lens's own output instead of the plan turn's."""
    record: list[dict] = []
    agent = _lens_agent(
        "I could not find anything wrong.",
        _block([_finding()]),
        record=record,
        costs=[0.3, 0.2],
    )
    result = _run_lens(agent)
    assert result.error is None
    assert [f.claim for f in result.findings] == ["c"]
    assert result.cost_usd == pytest.approx(0.5)  # both attempts, summed
    assert len(record) == 2


def test_the_reprompt_resumes_the_failed_session_with_the_error_in_its_prompt():
    record: list[dict] = []
    agent = _lens_agent("I could not find anything wrong.", _block([]), record=record)
    _run_lens(agent)
    assert len(record) == 2
    assert record[0]["kwargs"].get("resume") is None
    assert record[1]["kwargs"]["resume"] == "lens-1"  # `_turn`'s fixed session_id
    assert "no <output> block in the response" in record[1]["prompt"]


def test_a_lens_that_fails_twice_says_a_reprompt_was_attempted():
    """One re-prompt, never a loop: a second bad turn is terminal, and the
    error names that a re-prompt happened so a reader of the record can tell
    one bad turn from two."""
    agent = _lens_agent("still not json", "still not json either", costs=[0.3, 0.2])
    result = _run_lens(agent)
    assert result.error and result.error.startswith("not the schema")
    assert "re-prompt" in result.error
    assert result.cost_usd == pytest.approx(0.5)  # both attempts, summed


def test_a_well_formed_first_output_never_reprompts():
    """The happy path must cost exactly one call — a re-prompt that fires
    when nothing is wrong would double the price of every clean review."""
    record: list[dict] = []
    agent = _lens_agent(_block([]), record=record)
    result = _run_lens(agent)
    assert result.error is None
    assert len(record) == 1


def test_a_reprompt_does_not_fire_without_meaningful_budget_left():
    """Constraint: nothing meaningful left after the first attempt means the
    schema error returns as-is, exactly as it did before this change existed.

    The discriminating case, not the degenerate one: budget 2.0, a first turn
    that cost 1.5, leaving 0.5 remaining — budget is not exhausted (remaining
    > 0), but it is less than what the failed turn itself spent, which is the
    shipped rule (`remaining < attempt.cost_usd_est`). A `remaining <= 0`
    rule would wrongly retry here, so this is what would catch that mutant.
    The agent is scripted to blow up if called a second time, which would
    surface as a StopIteration rather than a clean assertion failure."""
    record: list[dict] = []
    agent = _lens_agent("not json", record=record, costs=[1.5])
    result = _run_lens(agent, budget_usd=2.0)
    assert result.error and result.error.startswith("not the schema")
    assert "re-prompt" not in result.error
    assert result.cost_usd == pytest.approx(1.5)
    assert len(record) == 1


def test_an_adequacy_lens_report_becomes_a_finding_that_holds_its_probe():
    """The feature's spine, driven end to end for the one lens that has it:
    the block through `_parse_report`'s per-lens model, `model_dump()`, and
    `Finding(**kwargs)`'s coercion of the nested edit. Every other `run_lens`
    test is a `correctness` lens, which never carries the field at all, so
    this path was covered only in pieces."""
    probe = {"file": "src/gap.py", "find": 'tz="UTC"', "replace": "tz=None"}
    result = _run_lens(_lens_agent(_block([_finding(probe=probe)])), lens="adequacy")

    assert result.error is None
    (finding,) = result.findings
    assert finding.lens == "adequacy"
    assert finding.probe == Mutant(**probe)
    # And out the far side: `reviews_from_json` rebuilds this before every
    # paid pass, so a probe that does not survive `as_dict` is a probe the
    # corpus driver never sees.
    assert result.as_dict()["findings"][0]["probe"] == probe


def test_the_blast_radius_lens_is_not_declared():
    """BACKLOG item 6, settled by #34: the third lens is test adequacy, not
    blast radius — that plan is retired, not merely deferred, and a lens
    wired here would run on every task with no risk tier to gate it."""
    assert set(review.LENSES) == {"correctness", "contract", "adequacy"}


@pytest.mark.parametrize("lens", sorted(review.LENSES))
def test_each_lens_prompt_carries_the_framing_that_makes_it_a_critic(lens):
    prompt = review.lens_prompt(
        lens,
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        spec_body="fix the gap",
        diff=DIFF,
        gates="- tests: pass (pytest 8.0)",
    )
    # Normalized: the prompt file is wrapped, and the clause spans two lines.
    flat = " ".join(prompt.split())
    assert "Find the reason this change should not be merged" in flat
    assert "do not manufacture one" in flat
    for severity in ("`blocker`", "`concern`", "`note`"):
        assert severity in prompt
    # A fresh session inherits nothing, so all four inputs are passed or absent.
    assert "fix the gap" in prompt
    assert "def gap(series, tz=" in prompt
    assert "pytest 8.0" in prompt
    assert "**Lens**:" in prompt  # CONTEXT.md §5's vocabulary
    # The `<output>` contract, for every lens rather than only the one that
    # shipped last: a prompt that loses a field name produces findings the
    # host cannot anchor, and it still reads like a critic while doing it.
    for field in ("`file`", "`line`", "`severity`", "`claim`"):
        assert field in prompt


@pytest.mark.parametrize("lens", sorted(review.LENSES))
def test_each_lens_prompt_carries_the_repo_s_claude_md(lens):
    prompt = review.lens_prompt(
        lens,
        context_md=CONTEXT_MD,
        claude_md="- Never collapse `error` into `fail`.\n",
        prompts_dir=PROMPTS,
        spec_body="fix the gap",
        diff=DIFF,
        gates="- tests: pass (pytest 8.0)",
    )
    assert "## This repository's standing instructions" in prompt
    assert "- Never collapse `error` into `fail`." in prompt


def test_the_lenses_declare_disjoint_remits():
    """Lenses are disjoint by construction — that is why one blocker routes
    onward and why there is no vote. Each names the other's territory as not
    its own rather than leaving the boundary to judgement."""
    correctness = (PROMPTS / review.LENSES["correctness"]).read_text()
    contract = (PROMPTS / review.LENSES["contract"]).read_text()
    adequacy = (PROMPTS / review.LENSES["adequacy"]).read_text()
    assert "migration reversibility" in correctness.split("Not yours.")[1]
    assert "timezones" in contract.split("Not yours.")[1]
    assert "timezones" in adequacy.split("Not yours.")[1]
    assert "migration reversibility" in adequacy.split("Not yours.")[1]
    for text in (correctness, contract):
        assert "blast-radius lens" in text.split("Not yours.")[1]
        assert "test-adequacy lens" in text.split("Not yours.")[1]
    assert "blast-radius lens" in adequacy.split("Not yours.")[1]


def test_the_declared_lenses_are_the_three_that_run():
    """A third lens is declared, and its remit is whether the suite would
    notice the code being wrong. `review.py` gains one entry in `LENSES` and
    one prompt file; `run_review` iterates the mapping rather than a second,
    hand-written list, so nothing else has to learn a third lens exists."""
    assert set(review.LENSES) == {"correctness", "contract", "adequacy"}
    reviews = _review(_block([]), _block([]), _block([]))
    assert [r.lens for r in reviews] == list(review.LENSES)


def test_exactly_one_prompt_claims_the_test_adequacy_remit():
    """§5.5's no-voting rule rests on the remits being disjoint by
    construction. The `Evidence` bullet that used to sit in the correctness
    lens's own remit list — naming a test that would pass identically before
    this change — belongs to the adequacy lens now, and moving it rather than
    copying it means the phrase appears in exactly one prompt file."""
    texts = {
        lens: " ".join((PROMPTS / path).read_text().split())
        for lens, path in review.LENSES.items()
    }
    for phrase in (
        "pass identically before this change",
        # Shared framing until #34's review: §5.5's instruction paragraph named
        # this lens's remit in the *first* thing all three lenses read, above
        # the `Not yours.` list meant to take it back. Whole file, not the
        # remit half — the defect was in the half a split-based check cannot
        # see.
        "a test that passes for the wrong reason",
    ):
        carriers = [lens for lens, text in texts.items() if phrase in text.lower()]
        assert carriers == ["adequacy"], (phrase, carriers)
    # And it left the correctness lens's own remit, not just its Not-yours list.
    correctness_remit = texts["correctness"].split("Not yours.")[0]
    assert "pass identically before this change" not in correctness_remit.lower()


def test_the_adequacy_prompt_demands_a_checkable_mutation():
    """The lens holds no tool that can run anything, so it cannot mutate a
    line and watch a test fail — it can only name the edit that would keep
    the suite green, which is what makes a finding checkable in one command
    by someone who can run it, rather than a claim about coverage the lens
    has no way to have confirmed.

    Asserted against the whole remit, not two stock phrases: the prompt *is*
    the deliverable here, and a 15-line stub carrying only those two phrases
    passed an earlier version of this test — a witness that reads as coverage
    of the acceptance criterion and is not, which is the exact defect this
    lens exists to file.
    """
    # Normalized like its sibling above: the file is wrapped at 79 columns, so
    # a legal reflow must not fail an assertion about what the prompt says.
    flat = " ".join((PROMPTS / review.LENSES["adequacy"]).read_text().split())
    assert "no tool that can run anything" in flat
    # The demand itself, not merely the word for it.
    assert "name the smallest concrete edit" in flat
    assert "keep the test passing while the behaviour it claims to cover breaks" in flat
    assert "checkable in one command" in flat
    # And the shapes it is told to look for. Each is a distinct way a test
    # passes without exercising the change; a prompt naming fewer is a
    # narrower lens than the criterion asked for, and says so nowhere.
    for shape in (
        "pass identically before this change",
        "assertion on a value the code under test never reads",
        "constructs the value it then asserts",
        "structural assertion over source text",
        "witness whose setup is the only input",
    ):
        assert shape in flat, shape


def test_an_adequacy_finding_without_a_probe_is_not_the_schema():
    """The field is required where it means something. An adequacy finding that
    names no edit is the hunch about coverage the prompt already refuses — and
    the corpus's second number cannot be computed from it."""
    reported = {"file": "a.py", "line": 1, "severity": "concern", "claim": "c"}
    with pytest.raises(ValidationError):
        review.reported_model("adequacy").model_validate(reported)


def test_a_correctness_finding_carries_no_probe_field_at_all():
    """Only adequacy's defect class is expressible as an edit that keeps the
    suite green. A timezone bug is not, so requiring one there would push the
    lens toward manufacturing it — which its own prompt forbids."""
    reported = {"file": "a.py", "line": 1, "severity": "concern", "claim": "c"}
    assert review.reported_model("correctness").model_validate(reported)
    with pytest.raises(ValidationError):
        review.reported_model("correctness").model_validate(
            reported | {"probe": {"file": "a.py", "find": "x", "replace": "y"}}
        )


def test_a_finding_recorded_before_probes_existed_still_loads():
    """`lens_scoring.reviews_from_json` rebuilds every fixture's recorded
    findings with `Finding(**f)`, and `calibrate_corpus` runs that before every
    paid pass. A required `probe` on `Finding` would make eight shipped
    fixtures unloadable and refuse to start every future pass."""
    # Typed `Any`, like the `json.loads` result `reviews_from_json` unpacks the
    # same way — a concrete `dict[str, str | int]` literal makes `ty` compare
    # every field's type against the union of values actually present, not the
    # per-key types the runtime dict lacks a static key for.
    old: dict[str, Any] = {
        "lens": "adequacy",
        "severity": "note",
        "file": "a.py",
        "line": 1,
        "claim": "c",
    }
    assert Finding(**old).probe is None


def test_a_probe_survives_the_round_trip_through_as_dict():
    """The host keeps what the lens said, or the corpus scores a pass against a
    field that silently became `None` between the cell and the record."""
    probe = Mutant(file="a.py", find="x", replace="y")
    finding = Finding(
        lens="adequacy", severity="note", file="a.py", line=1, claim="c", probe=probe
    )
    written = LensReview(lens="adequacy", findings=[finding]).as_dict()
    assert written["findings"][0]["probe"] == {
        "file": "a.py",
        "find": "x",
        "replace": "y",
    }
    assert (
        lens_scoring.reviews_from_json(json.dumps([written]))[0].findings[0].probe
        == probe
    )


def test_the_gate_results_reach_the_critic_with_the_tool_that_ran():
    """ "Passed" and "never ran" are the same JSON without `tool` (§5.4), and a
    critic told the gates passed is being told exactly that."""
    summary = review.gate_summary(
        [
            GateResult(gate="tests", status="pass", tool="pytest 8.0", summary="31 ok"),
            GateResult(gate="types", status="skip"),
        ]
    )
    assert "tests: pass (pytest 8.0) — 31 ok" in summary
    assert "types: skip (no tool reported)" in summary
