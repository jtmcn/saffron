from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from harness import lens_scoring
from saffron.agents.findings import Finding
from saffron.gates.contract import GateResult
from saffron.intake import Criterion, Mutant
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


def _review(*texts, read_head=lambda _p: None, record=None, claude_md=None):
    return review.run_review(
        "cell",
        diff=DIFF,
        read_head=read_head,
        spec_body="fix the gap",
        gates="- tests: pass (pytest 8.0)",
        context_md=CONTEXT_MD,
        claude_md=claude_md,
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
    assert set(review.LENSES) == {"correctness", "contract", "adequacy", "conventions"}


# Each lens's own framing sentence. The fourth one says "must", never
# "should", so the hedge the `prose` gate refuses stays out of the file.
_FRAMING = {
    "correctness": "Find the reason this change should not be merged",
    "contract": "Find the reason this change should not be merged",
    "adequacy": "Find the reason this change should not be merged",
    "conventions": "Find the reason this change must not be merged",
}


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
    assert _FRAMING[lens] in flat
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


# The text between the conventions prompt's `## Your remit` heading and the
# next heading, kept here rather than read off the file by path (see below).
_CONVENTIONS_REMIT = """
Yours is each hunk read against the standing instructions below, and against
the code and text it describes. Judge against the standing instructions in
this prompt, never a copy of them in the worktree. The host read them at this task's
base commit, before the implementer could touch them.

Ask four questions of every hunk:

- **Vocabulary.** Does each term carry the meaning the standing instructions
  give it, and avoid every term they rule against?
- **Invariants and conventions.** Does the hunk hold to each rule the
  standing instructions state?
- **One source.** Is a type, constant or helper the repository already
  defines imported, rather than restated? A constant restated is yours even
  when the two values agree today.
- **Said versus done.** Does each comment, docstring and citation say what
  the code or the cited text says? A comment or docstring that contradicts
  its code is yours. So is a citation to a section or line that does not say
  what the text claims.

The fourth question needs no standing instructions. Format, lint, types,
structure and sentence form each have a gate. Leave what they judge alone.
"""


def test_the_conventions_prompt_asks_its_four_questions_against_the_base_standards():
    """The conventions lens judges every hunk against the standing
    instructions this prompt carries, never a copy in the worktree the
    implementer could edit. Read through `review.lens_prompt`, not the
    file's own path. A mutant that points the `LENSES` entry at another
    prompt file must fail this witness, not pass it by accident."""
    prompt = review.lens_prompt(
        "conventions",
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        spec_body="fix the gap",
        diff=DIFF,
        gates="- tests: pass (pytest 8.0)",
    )
    flat = " ".join(prompt.split())
    assert "Find the reason this change must not be merged" in flat
    lines = prompt.splitlines()
    start = lines.index("## Your remit") + 1
    end = next(i for i in range(start, len(lines)) if lines[i].startswith("## "))
    remit = "\n".join(lines[start:end])
    assert " ".join(remit.split()) == " ".join(_CONVENTIONS_REMIT.split())


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
    hand-written list, so nothing else has to learn a third lens exists.

    Narrowed to what stays true once a fourth lens joins: the first three
    keys, in order. `test_the_declared_lenses_are_the_four_that_run` below
    covers the full set."""
    assert list(review.LENSES)[:3] == ["correctness", "contract", "adequacy"]


def test_the_declared_lenses_are_the_four_that_run():
    """A fourth lens is declared, keyed `conventions` rather than `standards`.
    The end review already declares a `standards` lens (ADR 7), and a shared
    name would feed its concerns back in as in-cell ones, qualified twice.
    `run_review` iterates `LENSES` rather than a second, hand-written list,
    so the fourth call gets the standing instructions like every other."""
    assert review.LENSES == {
        "correctness": "review-correctness.md",
        "contract": "review-contract.md",
        "adequacy": "review-adequacy.md",
        "conventions": "review-conventions.md",
    }
    assert list(review.LENSES) == ["correctness", "contract", "adequacy", "conventions"]
    record: list[dict] = []
    reviews = _review(
        _block([]),
        _block([]),
        _block([]),
        _block([]),
        record=record,
        claude_md="- Never collapse `error` into `fail`.\n",
    )
    assert [r.lens for r in reviews] == [
        "correctness",
        "contract",
        "adequacy",
        "conventions",
    ]
    assert len(record) == 4
    expected = review.lens_prompt(
        "conventions",
        context_md=CONTEXT_MD,
        claude_md="- Never collapse `error` into `fail`.\n",
        prompts_dir=PROMPTS,
        spec_body="fix the gap",
        diff=DIFF,
        gates="- tests: pass (pytest 8.0)",
    )
    assert record[3]["options"]["system_prompt"] == expected


def test_no_in_cell_lens_shares_a_name_with_an_end_review_lens():
    """A shared name between an in-cell lens and an end-review lens would feed
    every end-review finding of that name back in as an in-cell one. Two
    readers tell the two apart, `end_review._known_block` and
    `qualify._in_cell_concerns`, and both do it by name alone."""
    from saffron import end_review

    assert set(review.LENSES) == {"correctness", "contract", "adequacy", "conventions"}
    assert set(end_review.END_LENSES) == {"spec", "standards"}
    assert set(review.LENSES) & set(end_review.END_LENSES) == set()


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


# --- criterion probes: one fresh session per criterion (backlog item b-2750d5) ---


def _probe_text(edit, reason):
    return f"Here it is.\n<output>\n{json.dumps({'edit': edit, 'reason': reason})}\n</output>"


def _probe_agent(*turns, record=None):
    """Like `_lens_agent`, scripting one turn per `run_criterion_probes` call
    rather than per lens. An exception is raised. A scripted
    `implement.AttemptResult` passes through with its own cost. Anything else
    is wrapped as the session's raw text at the default cost."""
    scripted = iter(turns)

    def run(container, *, prompt, options, **kwargs):
        if record is not None:
            record.append({"prompt": prompt, "options": options})
        turn = next(scripted)
        if isinstance(turn, BaseException):
            raise turn
        if isinstance(turn, implement.AttemptResult):
            return turn
        return _turn(turn)

    return run


def test_a_session_that_answers_nothing_usable_is_recorded_and_the_next_is_still_asked():
    """Criterion 3: an `AgentFailed` session and one whose output the schema
    refuses each leave an entry naming what went wrong and no edit. Neither
    stops the loop, and neither is re-prompted the way a lens is."""
    first = Criterion(
        claim="the guard rejects a negative amount", witness="t.py::test_a"
    )
    second = Criterion(claim="the total never goes negative", witness="t.py::test_b")
    failed = implement.AgentFailed("cut off", _turn("", cost=0.3))

    record: list[dict] = []
    agent = _probe_agent(failed, "not a block at all", record=record)

    entries = review.run_criterion_probes(
        "cell",
        acceptance=[first, second],
        diff=DIFF,
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        max_turns=20,
        budget_usd=2.0,
        agent=agent,
        spec_id="SY-1",
        emit=lambda _e: None,
    )

    assert len(record) == 2, "the second criterion must still be asked"
    assert [e["witness"] for e in entries] == ["t.py::test_a", "t.py::test_b"]
    assert [e["claim"] for e in entries] == [first.claim, second.claim]
    assert entries[0]["edit"] is None
    assert "cut off" in entries[0]["error"]
    assert entries[0]["cost_usd"] == pytest.approx(0.3)
    assert entries[1]["edit"] is None
    assert entries[1]["error"] is not None
    assert "not the schema" in entries[1]["error"]
    # A refused session still spent its turn, and the task is charged for it.
    assert entries[1]["cost_usd"] == pytest.approx(0.1)


# --- wrong versions: one session per criterion that declares any (backlog item b-7e69d0) ---


def _wrong_version_block(versions):
    return f"Here it is.\n<output>\n{json.dumps({'versions': versions})}\n</output>"


def _expected_wrong_version_tail(numbered: str, claim: str) -> str:
    return (
        "## The diff\n\n"
        + DIFF
        + "\n\n## The wrong versions\n\n"
        + numbered
        + "\n\n## The claim\n\n"
        + claim
        + "\n"
    )


def test_each_criterion_with_wrong_versions_gets_one_session_that_turns_each_into_an_edit():
    """Criterion 3: `run_wrong_versions` buys one fresh session per criterion
    that declares wrong versions, in the spec's order, and none for one that
    declares none. Its prompt shows one claim and the diff, never a witness
    or another criterion's claim."""
    edit_a1 = {"file": "src/gap.py", "find": "amount < 0", "replace": "amount <= 0"}
    edit_a2 = {"file": "src/gap.py", "find": "log.info(total)", "replace": "pass"}
    edit_c = {
        "file": "src/gap.py",
        "find": "total = total",
        "replace": "total = total * 2",
    }

    a = Criterion(
        claim="the guard rejects a negative amount",
        witness="t.py::test_a",
        wrong_versions=[
            "the guard is removed",
            "the guard accepts zero",
            "the guard logs nothing",
        ],
    )
    b = Criterion(claim="the total is logged", witness="t.py::test_b")
    c = Criterion(
        claim="the total stays unchanged",
        witness="t.py::test_c",
        preserves=True,
        wrong_versions=["the total is doubled"],
    )

    record: list[dict] = []
    agent = _probe_agent(
        _turn(
            _wrong_version_block(
                [
                    {
                        "edit": edit_a1,
                        "reason": "removing the guard lets negatives through",
                    },
                    {"edit": None, "reason": "zero cannot be isolated as one edit"},
                    {"edit": edit_a2, "reason": "logging nothing still runs the guard"},
                ]
            ),
            cost=0.35,
        ),
        _turn(
            _wrong_version_block(
                [{"edit": edit_c, "reason": "doubling changes the preserved value"}]
            ),
            cost=0.15,
        ),
        record=record,
    )

    entries = review.run_wrong_versions(
        "cell",
        acceptance=[a, b, c],
        diff=DIFF,
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        max_turns=20,
        budget_usd=2.0,
        agent=agent,
        spec_id="SY-1",
        emit=lambda _e: None,
    )

    assert len(record) == 2  # b buys no session

    numbered_a = (
        "1. the guard is removed\n2. the guard accepts zero\n3. the guard logs nothing"
    )
    numbered_c = "1. the total is doubled"
    tail_a = _expected_wrong_version_tail(numbered_a, a.claim)
    tail_c = _expected_wrong_version_tail(numbered_c, c.claim)
    assert record[0]["options"]["system_prompt"].endswith(tail_a)
    assert record[1]["options"]["system_prompt"].endswith(tail_c)

    for call in record:
        prompt = call["options"]["system_prompt"]
        turn_prompt = call["prompt"]
        for witness in ("t.py::test_a", "t.py::test_b", "t.py::test_c"):
            assert witness not in prompt
            assert witness not in turn_prompt
    assert b.claim not in record[0]["options"]["system_prompt"]
    assert c.claim not in record[0]["options"]["system_prompt"]
    assert a.claim not in record[1]["options"]["system_prompt"]
    assert b.claim not in record[1]["options"]["system_prompt"]

    assert record[0]["options"]["tools"] == review.REVIEW_TOOLS
    assert record[0]["options"]["max_turns"] == 20
    assert record[0]["options"]["max_budget_usd"] == 2.0
    assert record[1]["options"]["tools"] == review.REVIEW_TOOLS
    assert record[1]["options"]["max_turns"] == 20
    assert record[1]["options"]["max_budget_usd"] == 2.0

    assert entries == [
        {
            "witness": "t.py::test_a",
            "claim": "the guard rejects a negative amount",
            "cost_usd": pytest.approx(0.35),
            "error": None,
            "versions": [
                {
                    "version": "the guard is removed",
                    "edit": edit_a1,
                    "reason": "removing the guard lets negatives through",
                },
                {
                    "version": "the guard accepts zero",
                    "edit": None,
                    "reason": "zero cannot be isolated as one edit",
                },
                {
                    "version": "the guard logs nothing",
                    "edit": edit_a2,
                    "reason": "logging nothing still runs the guard",
                },
            ],
        },
        {
            "witness": "t.py::test_c",
            "claim": "the total stays unchanged",
            "cost_usd": pytest.approx(0.15),
            "error": None,
            "versions": [
                {
                    "version": "the total is doubled",
                    "edit": edit_c,
                    "reason": "doubling changes the preserved value",
                },
            ],
        },
    ]

    # The criterion-probe session keeps its own view: one claim and the diff,
    # never the wrong versions a spec's author listed for it.
    probe_record: list[dict] = []
    probe_agent = _probe_agent(
        _probe_text(None, "no edit found"),
        _probe_text(None, "no edit found"),
        _probe_text(None, "no edit found"),
        record=probe_record,
    )
    review.run_criterion_probes(
        "cell",
        acceptance=[a, b, c],
        diff=DIFF,
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        max_turns=20,
        budget_usd=2.0,
        agent=probe_agent,
        spec_id="SY-1",
        emit=lambda _e: None,
    )
    assert len(probe_record) == 3
    for call in probe_record:
        prompt = call["options"]["system_prompt"]
        for version in (
            "the guard is removed",
            "the guard accepts zero",
            "the guard logs nothing",
            "the total is doubled",
        ):
            assert version not in prompt

    assert (
        review.describe_wrong_versions(entries)
        == "wrong versions: 4 declared, 3 expressed"
    )


def test_a_wrong_version_session_that_answers_nothing_usable_keeps_every_version():
    """Criterion 4: a failed session, a bad reply, and a mismatched count each
    keep every version, with a null edit and an empty reason. None of the
    four truncates, stops the loop, or re-prompts. Every later criterion is
    still asked."""
    c1 = Criterion(
        claim="claim one", witness="t.py::test_1", wrong_versions=["c1 v1", "c1 v2"]
    )
    c2 = Criterion(
        claim="claim two", witness="t.py::test_2", wrong_versions=["c2 v1", "c2 v2"]
    )
    c3 = Criterion(
        claim="claim three", witness="t.py::test_3", wrong_versions=["c3 v1", "c3 v2"]
    )
    c4 = Criterion(
        claim="claim four", witness="t.py::test_4", wrong_versions=["c4 v1", "c4 v2"]
    )

    failed = implement.AgentFailed("turn cut short", _turn("", cost=0.42))
    one_answer = _wrong_version_block(
        [
            {
                "edit": {"file": "src/gap.py", "find": "x", "replace": "y"},
                "reason": "one answer",
            }
        ]
    )
    three_answers = _wrong_version_block(
        [
            {
                "edit": {"file": "src/gap.py", "find": "p", "replace": "q"},
                "reason": "first",
            },
            {
                "edit": {"file": "src/gap.py", "find": "r", "replace": "s"},
                "reason": "second",
            },
            {
                "edit": {"file": "src/gap.py", "find": "t", "replace": "u"},
                "reason": "third",
            },
        ]
    )

    record: list[dict] = []
    agent = _probe_agent(
        failed, "not a block at all", one_answer, three_answers, record=record
    )

    entries = review.run_wrong_versions(
        "cell",
        acceptance=[c1, c2, c3, c4],
        diff=DIFF,
        context_md=CONTEXT_MD,
        claude_md=None,
        prompts_dir=PROMPTS,
        max_turns=20,
        budget_usd=2.0,
        agent=agent,
        spec_id="SY-1",
        emit=lambda _e: None,
    )

    assert len(record) == 4, "every criterion is asked, whatever the previous answer"
    assert entries == [
        {
            "witness": "t.py::test_1",
            "claim": "claim one",
            "cost_usd": pytest.approx(0.42),
            "error": "turn cut short",
            "versions": [
                {"version": "c1 v1", "edit": None, "reason": ""},
                {"version": "c1 v2", "edit": None, "reason": ""},
            ],
        },
        {
            "witness": "t.py::test_2",
            "claim": "claim two",
            "cost_usd": pytest.approx(0.1),
            "error": "not the schema: no <output> block in the response",
            "versions": [
                {"version": "c2 v1", "edit": None, "reason": ""},
                {"version": "c2 v2", "edit": None, "reason": ""},
            ],
        },
        {
            "witness": "t.py::test_3",
            "claim": "claim three",
            "cost_usd": pytest.approx(0.1),
            "error": "not the schema: 1 answers for 2 wrong versions",
            "versions": [
                {"version": "c3 v1", "edit": None, "reason": ""},
                {"version": "c3 v2", "edit": None, "reason": ""},
            ],
        },
        {
            "witness": "t.py::test_4",
            "claim": "claim four",
            "cost_usd": pytest.approx(0.1),
            "error": "not the schema: 3 answers for 2 wrong versions",
            "versions": [
                {"version": "c4 v1", "edit": None, "reason": ""},
                {"version": "c4 v2", "edit": None, "reason": ""},
            ],
        },
    ]


def test_a_wrong_versions_survivor_names_the_version_it_came_from():
    """`survivor_finding`'s optional `version` keyword (backlog item b-7e69d0).
    Given one, the claim names the wrong version that survived rather than
    reading the edit as the criterion's own. Without it, the claim is
    unchanged."""
    criterion = Criterion(
        claim="the guard rejects a negative amount", witness="t.py::a"
    )
    edit = Mutant(file="src/x.py", find="if x < 0:", replace="if False:")
    content = "def f(x):\n    if x < 0:\n        raise ValueError\n"

    plain = review.survivor_finding(criterion, edit, content)
    assert plain == Finding(
        lens="adequacy",
        severity="blocker",
        file="src/x.py",
        line=2,
        claim=(
            f"{review.HOST_FILED}t.py::a stayed green with the criterion's "
            "own edit applied to src/x.py. The claim was "
            "'the guard rejects a negative amount', and only that witness "
            "ran under the edit."
        ),
        probe=edit,
        probe_verdict="survived",
    )

    versioned = review.survivor_finding(
        criterion, edit, content, version="the guard is removed"
    )
    assert versioned == Finding(
        lens="adequacy",
        severity="blocker",
        file="src/x.py",
        line=2,
        claim=(
            f"{review.HOST_FILED}t.py::a stayed green with the spec's "
            "wrong version 'the guard is removed' applied to src/x.py as an "
            "edit. The claim was 'the guard rejects a negative amount', and "
            "only that witness ran under the edit."
        ),
        probe=edit,
        probe_verdict="survived",
    )
