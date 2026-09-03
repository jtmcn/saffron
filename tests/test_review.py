from __future__ import annotations

import json
from pathlib import Path

import pytest

from saffron.gates.contract import GateResult
from saffron.phases import implement, review

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
    And a resumed session would carry the implementer's transcript."""
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
    must never be the same value."""
    reviews = _review("I could not find anything wrong.", _block([]))
    assert reviews[0].error and reviews[0].error.startswith("not the schema")
    assert reviews[0].cost_usd == 0.1  # a failed extraction still cost money
    state, why = review.review_state(reviews)
    assert state == "REVIEWING"
    assert "correctness" in why


def test_a_severity_the_vocabulary_does_not_have_is_not_the_schema():
    reviews = _review(_block([_finding(severity="critical")]), _block([]))
    assert reviews[0].error


def test_a_lens_whose_session_failed_still_charges_what_it_spent():
    failed = implement.AgentFailed("max turns", _turn("", cost=0.4))
    reviews = _review(failed, _block([]))
    assert reviews[0].cost_usd == 0.4
    assert reviews[0].error
    assert review.review_state(reviews)[0] == "REVIEWING"


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
