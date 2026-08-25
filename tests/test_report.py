import fcntl
import json
from dataclasses import asdict
from unittest import mock

from saffron.agents.findings import Finding
from saffron.gates.baseline import NewFailure
from saffron.gates.contract import Failure, GateResult
from saffron.intake import parse_spec
from saffron.phases.rebut import (
    LensVerdicts,
    RebutResult,
    Rebuttal,
    RebuttalTurn,
    Verdict,
)
from saffron.phases.review import LensReview
from saffron.report.index import QueueLine, append_queue_line, render_index, sort_key
from saffron.report.pr_body import render_pr_body

SPEC = parse_spec(
    """---
id: TE-9001
title: Settle on the end-of-day CLI
type: bug
touches:
  - thermal_edge/weather/**
---

## Acceptance criteria
- [ ] A regression test exists that fails on the current `main`
- [ ] The intraday snapshot path is removed
"""
)

RESULTS = [
    GateResult(gate="format", status="pass", summary="clean", duration_ms=1200),
    GateResult(
        gate="types",
        status="fail",
        failures=[Failure(file="a.py", line=8, code="arg-type", message="bad arg")],
        summary="1 error in 1 file",
        duration_ms=45000,
    ),
    GateResult(gate="coverage", status="skip", summary="not declared"),
    GateResult(gate="tests", status="error", summary="toolchain missing"),
]


def body():
    return render_pr_body(
        SPEC,
        RESULTS,
        [
            NewFailure(
                "types",
                Failure(file="a.py", line=8, code="arg-type", message="bad arg"),
            )
        ],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=180,
        removed=22,
        transcript_path="~/.saffron/batches/1/thermal-edge/1",
    )


def test_the_pr_body_opens_with_the_spec():
    assert "TE-9001" in body()
    assert "Settle on the end-of-day CLI" in body()


def test_acceptance_criteria_render_as_an_unchecked_checklist():
    assert "- [ ] A regression test exists that fails on the current `main`" in body()


def test_the_gate_table_holds_every_result_with_its_status_in_backticks():
    rendered = body()
    for gate, status in [
        ("format", "pass"),
        ("types", "fail"),
        ("coverage", "skip"),
        ("tests", "error"),
    ]:
        assert f"| `{gate}` | `{status}` |" in rendered


def test_new_failures_are_reported_separately_from_the_gate_table():
    rendered = body()
    assert "New failures" in rendered
    assert "a.py:8" in rendered
    assert "arg-type" in rendered


def test_an_errored_gate_is_called_errored_and_never_failed():
    rendered = body()
    errored = [line for line in rendered.splitlines() if "toolchain missing" in line]
    assert errored
    assert not any("failed" in line.lower() for line in errored)


def test_a_clean_run_says_so_rather_than_rendering_an_empty_section():
    rendered = render_pr_body(
        SPEC,
        [GateResult(gate="lint", status="pass")],
        [],
        base_sha="a",
        head_sha="b",
        added=1,
        removed=0,
        transcript_path="/t",
    )
    assert "No new failures" in rendered
    assert "New failures" not in rendered


def test_the_diff_stat_and_shas_are_recorded():
    rendered = body()
    assert "+180/−22" in rendered
    assert "a" * 40 in rendered


def test_the_header_reports_the_effective_risk_not_the_specs_declared_risk():
    """§5.6: SPEC never declares `risk`, so it defaults to `standard` — the
    header must still say `elevated` when that is what governed the run."""
    assert SPEC.risk == "standard"
    rendered = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
        effective_risk="elevated",
    )
    assert "risk `elevated`" in rendered
    assert "risk `standard`" not in rendered


def test_omitting_the_effective_risk_falls_back_to_the_specs_own():
    """Existing callers that have not computed a tier yet see no change."""
    rendered = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
    )
    assert "risk `standard`" in rendered


def test_an_advisory_gate_is_marked_in_the_gate_table():
    """A `size` fail at `standard` reads as a contradiction on an otherwise
    green pull request unless its own row says it never blocked (§5.6)."""
    rendered = render_pr_body(
        SPEC,
        [GateResult(gate="size", status="fail", summary="too big")],
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
        advisory_gates=["size"],
    )
    assert "| `size` | `fail` |" in rendered
    assert "(advisory) too big" in rendered


def test_a_gate_absent_from_advisory_gates_is_not_marked():
    rendered = body()
    assert "(advisory)" not in rendered


def line(**overrides):
    defaults = dict(
        repo="thermal-edge",
        spec_id="TE-9001",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=None,
        concerns=0,
        added=180,
        removed=22,
        link="pr_body.md",
        note="",
        risk="standard",
    )
    return QueueLine(**{**defaults, **overrides})


def test_the_index_holds_one_line_per_task():
    rendered = render_index([line(), line(spec_id="TE-9002")], header={"tasks": "2"})
    assert rendered.count("TE-900") == 2
    assert "thermal-edge" in rendered


def test_states_render_in_backticked_caps():
    assert "<code>READY_FOR_REVIEW</code>" in render_index([line()], header={})


def test_cost_is_rendered_as_unknown_rather_than_zero_in_v0():
    """A column named for a measurement it cannot make is how an estimate
    becomes a fact (DESIGN.md §4.1). v0 spends nothing, so it claims nothing."""
    assert "$0" not in render_index([line()], header={})


def test_a_skipped_repo_sorts_above_everything():
    lines = [line(state="READY_FOR_REVIEW"), line(state="SKIPPED", spec_id="—")]
    assert sorted(lines, key=sort_key)[0].state == "SKIPPED"


def test_scope_review_sorts_above_ready_for_review():
    lines = [line(state="READY_FOR_REVIEW"), line(state="SCOPE_REVIEW")]
    assert sorted(lines, key=sort_key)[0].state == "SCOPE_REVIEW"


def test_merge_failed_sorts_above_elevated_risk():
    lines = [
        line(state="READY_FOR_REVIEW", risk="elevated"),
        line(state="MERGE_FAILED"),
    ]
    assert sorted(lines, key=sort_key)[0].state == "MERGE_FAILED"


def test_within_a_state_more_concerns_sorts_higher():
    lines = [line(concerns=0, spec_id="A"), line(concerns=3, spec_id="B")]
    assert sorted(lines, key=sort_key)[0].spec_id == "B"


def test_the_header_is_rendered():
    assert "trailing accept rate" in render_index(
        [line()], header={"trailing accept rate": "—"}
    )


def test_a_queue_line_field_cannot_smuggle_markup_into_the_index():
    """Every QueueLine field is rendered into HTML, so every one is escaped."""
    rendered = render_index([line(note="<script>alert(1)</script>")], header={})
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_a_measured_zero_is_not_rendered_as_unmeasured():
    """`—` means "not measured"; a gate that finished inside a millisecond,
    or a failure reported at line 0, measured something."""
    rendered = render_pr_body(
        SPEC,
        [
            GateResult(
                gate="lint",
                status="fail",
                duration_ms=0,
                failures=[Failure(file="a.py", line=0, code="E501")],
            )
        ],
        [NewFailure("lint", Failure(file="a.py", line=0, code="E501"))],
        base_sha="a",
        head_sha="b",
        added=1,
        removed=0,
        transcript_path="/t",
    )
    assert "| 0.0s |" in rendered
    assert "a.py:0" in rendered


def test_a_pipe_in_a_gate_message_does_not_split_the_table_row():
    """Gate messages carry pipes routinely — a shell echo, a ruff rule, an
    assertion diff. Both tables are four columns, so every row has five."""
    rendered = render_pr_body(
        SPEC,
        [GateResult(gate="lint", status="fail", summary="ran `grep x | wc -l`")],
        [
            NewFailure(
                "lint",
                Failure(
                    file="a.py", line=1, code="E1", message="grep -n x | cut -d: -f1"
                ),
            )
        ],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
    )
    rows = [line for line in rendered.splitlines() if line.startswith("|")]
    assert rows
    for row in rows:
        assert row.count("|") - row.count("\\|") == 5


def test_every_state_the_driver_can_produce_ranks_above_ordinary():
    """A task that could not pass its own gates, or one whose cell died, must
    not sort in among reviewable outcomes (§3.3)."""
    from saffron.report.index import _ORDINARY, _STATE_RANK

    for state in ("EXHAUSTED", "ORPHANED", "NOT_IMPLEMENTED", "GATE_ERROR"):
        assert _STATE_RANK[state] < _ORDINARY, state


def _finding(**kw):
    base = dict(
        lens="correctness",
        severity="blocker",
        file="a.py",
        line=3,
        claim="the tz default is wrong",
        anchored=True,
    )
    return Finding(**{**base, **kw})


def test_a_finding_cannot_close_an_issue_or_notify_an_account():
    """§5.7's other half. `Fixes #1` in a PR *body* closes issue 1 on merge and
    `@someone` notifies a real account — and a correctness lens quoting
    `@pytest.mark.skip` is the ordinary case, not a contrived one."""
    body = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
        reviews=[
            LensReview(
                lens="correctness",
                findings=[
                    _finding(
                        claim="Fixes #1 by skipping it; ask @someone about @pytest"
                    )
                ],
            )
        ],
    )

    # The triggers are broken...
    assert "Fixes #1" not in body
    assert "@someone" not in body
    assert "@pytest" not in body
    # ...and the sentence around them still reads.
    assert "by skipping it; ask" in body
    assert "someone" in body
    # The human-authored title is not model-authored text and is left alone.
    assert SPEC.title in body


def test_disagreements_sort_above_the_gate_table():
    """§6: disagreements first, because that is where your judgment is worth
    the most."""
    body = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
        reviews=[LensReview(lens="correctness", findings=[_finding()])],
    )
    assert body.index("Disagreements") < body.index("### Gates")


def test_the_body_renders_two_columns_never_adjudication():
    """rebut.py keeps `verdict` and `rebuttal`; `adjudication` is the
    operator's, and it happens in GitHub against the PR this phase creates.
    test_rebut.py asserts it is absent from the record — rendering it here is
    chronologically impossible."""
    body = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
        reviews=[LensReview(lens="correctness", findings=[_finding()])],
    )
    assert "adjudication" not in body.lower()


def test_a_pipe_in_a_finding_claim_does_not_break_the_table():
    """`|` is likelier in a model-authored claim than in a gate message, and
    the findings and disagreements tables were never covered."""
    rendered = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
        reviews=[
            LensReview(
                lens="correctness",
                findings=[_finding(claim="a | b splits the row")],
            )
        ],
    )
    for section_header in ("### Disagreements", "### Findings"):
        lines = rendered.split(section_header, 1)[1].splitlines()
        header = next(line for line in lines if line.startswith("|"))
        columns = header.count("|") - header.count("\\|")
        row = next(line for line in lines if "splits the row" in line)
        assert row.count("|") - row.count("\\|") == columns


def test_an_unanchored_finding_still_appears():
    """`anchored = False` is kept, never dropped: drop rate per lens is the
    signal that a lens is badly prompted (§5.5)."""
    body = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
        reviews=[LensReview(lens="schema", findings=[_finding(anchored=False)])],
    )
    assert "the tz default is wrong" in body
    row = next(line for line in body.splitlines() if "the tz default is wrong" in line)
    assert row.rstrip().endswith("| no |")


def test_the_test_file_diff_is_shown_separately():
    """§7's second countermeasure for gate gaming. Filtered by the repo's
    declared `integrity.test_paths` — not one line of language knowledge in
    core (§2.1)."""
    diff = (
        "diff --git a/tests/test_x.py b/tests/test_x.py\n"
        "--- a/tests/test_x.py\n+++ b/tests/test_x.py\n"
        "@@ -1,3 +0,0 @@\n-def test_x():\n-    assert thing()\n"
        "diff --git a/saffron/x.py b/saffron/x.py\n"
        "--- a/saffron/x.py\n+++ b/saffron/x.py\n@@ -1 +1 @@\n-a\n+b\n"
    )
    body = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=2,
        transcript_path="/t",
        test_paths=["tests/**"],
        diff=diff,
    )
    assert "Test files changed" in body
    assert body.index("Test files changed") < body.index("### Gates")
    assert "def test_x" in body


def test_a_triple_backtick_in_the_diff_cannot_close_the_block():
    """A git context line for a pre-existing fence renders as one space plus
    three backticks, and CommonMark closes a three-backtick block on that. The
    agent cannot author the context line, only edit next to one."""
    diff = (
        "diff --git a/tests/test_x.py b/tests/test_x.py\n"
        "--- a/tests/test_x.py\n+++ b/tests/test_x.py\n"
        "@@ -1,3 +1,3 @@\n"
        ' """\n'
        " ```\n"
        "+@everyone Fixes #12\n"
    )
    body = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
        test_paths=["tests/**"],
        diff=diff,
    )
    fenced = body.split("````diff\n", 1)[1].split("\n````", 1)[0]
    assert "+@everyone Fixes #12" in fenced


def test_the_body_says_which_tree_the_gates_ran_on():
    skipped = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
        verified_on="base",
    )
    assert "base had not moved" in skipped
    rerun = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
        verified_on="packaged",
    )
    assert "packaged commit" in rerun


def test_the_header_line_carries_attempt_count_and_cost():
    singular = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
        attempts=1,
        spent_usd=2.5,
    )
    assert "1 attempt " in singular
    assert "$2.50" in singular
    plural = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
        attempts=3,
        spent_usd=0,
    )
    assert "3 attempts" in plural


def test_disagreement_rows_attribute_the_right_rebuttal_to_the_right_blocker():
    """Row N must carry blocker N's own rebuttal and verdict, not just any
    row and any rebuttal. `_disagreements` numbers `anchored_blockers(reviews)`
    from 1 and looks up `RebutResult` by that same number — if the selection
    rule ever drifts from the one `rebut.py` numbered against, this catches
    the silent mis-attribution rather than just noticing rows exist."""
    reviews = [
        LensReview(
            lens="correctness",
            findings=[_finding(claim="blocker one claim", file="a.py", line=1)],
        ),
        LensReview(
            lens="contract",
            findings=[_finding(claim="blocker two claim", file="b.py", line=2)],
        ),
    ]
    rebut_result = RebutResult(
        state="READY_FOR_REVIEW",
        why="test",
        rebuttal=RebuttalTurn(
            rebuttals=[
                Rebuttal(finding=1, action="argued", argument="rebuttal one text"),
                Rebuttal(finding=2, action="fixed", argument="rebuttal two text"),
            ]
        ),
        verdicts=[
            LensVerdicts(
                lens="correctness",
                verdicts=[
                    Verdict(finding=1, verdict="confirmed", reason="verdict one text")
                ],
            ),
            LensVerdicts(
                lens="contract",
                verdicts=[
                    Verdict(finding=2, verdict="withdrawn", reason="verdict two text")
                ],
            ),
        ],
        moved=True,
        cost_usd=0.0,
    )
    body = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="/t",
        reviews=reviews,
        rebut_result=rebut_result,
    )
    rows = [
        line
        for line in body.splitlines()
        if line.startswith("| 1 ") or line.startswith("| 2 ")
    ]
    row1 = next(r for r in rows if r.startswith("| 1 "))
    row2 = next(r for r in rows if r.startswith("| 2 "))
    assert "blocker one claim" in row1
    assert "rebuttal one text" in row1
    assert "verdict one text" in row1
    assert "blocker two claim" not in row1
    assert "rebuttal two text" not in row1
    assert "blocker two claim" in row2
    assert "rebuttal two text" in row2
    assert "verdict two text" in row2
    assert "blocker one claim" not in row2


def test_a_second_task_joins_the_first_without_an_orchestrator(tmp_path):
    """Appending rather than rewriting is what lets sub-project C arrive later."""
    first = QueueLine(
        repo="saffron",
        spec_id="SA-0005",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=6.4,
        concerns=0,
        added=10,
        removed=2,
        link="https://github.com/o/r/pull/7",
    )
    second = QueueLine(
        repo="saffron",
        spec_id="SA-0006",
        state="MERGE_FAILED",
        attempts=2,
        cost_usd_est=3.1,
        concerns=1,
        added=4,
        removed=0,
        link="",
        note="conflicts with #7",
    )
    # What `package()` passes: one task's spend, both times.
    append_queue_line(tmp_path, first, header={"spend": "$6.40"})
    append_queue_line(tmp_path, second, header={"spend": "$3.10"})

    stored = json.loads((tmp_path / "queue.json").read_text())
    assert [row["spec_id"] for row in stored] == ["SA-0005", "SA-0006"]
    html = (tmp_path / "index.html").read_text()
    # MERGE_FAILED ranks above an ordinary green task (§6's sort order)
    assert html.index("SA-0006") < html.index("SA-0005")
    # The header is the batch's spend, not the last caller's: two rows of $6.40
    # and $3.10 read $9.50, or the morning surface understates the night.
    assert "spend <strong>$9.50</strong>" in html


def test_a_pull_request_link_is_not_labelled_artifacts(tmp_path):
    """index.py:113 captioned every link `artifacts`; §6's own mock shows
    `→ PR #211`. Repointing `link` at a PR without relabelling mislabels it."""
    line = QueueLine(
        repo="saffron",
        spec_id="SA-0005",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=6.4,
        concerns=0,
        added=10,
        removed=2,
        link="https://github.com/o/r/pull/7",
    )
    append_queue_line(tmp_path, line, header={})
    html = (tmp_path / "index.html").read_text()
    assert "PR #7" in html
    assert ">artifacts<" not in html


def test_a_corrupt_queue_json_does_not_wedge_the_append(tmp_path):
    """Invalid JSON in queue.json is dropped; the new line still lands."""
    store = tmp_path / "queue.json"
    store.write_text("{this is not valid json")
    line = QueueLine(
        repo="saffron",
        spec_id="SA-0005",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=6.4,
        concerns=0,
        added=10,
        removed=2,
        link="",
    )
    append_queue_line(tmp_path, line, header={})
    stored = json.loads((tmp_path / "queue.json").read_text())
    assert len(stored) == 1
    assert stored[0]["spec_id"] == "SA-0005"
    assert "SA-0005" in (tmp_path / "index.html").read_text()


def test_a_queue_json_of_the_wrong_shape_does_not_wedge_the_append(tmp_path):
    """Valid JSON but not a list is dropped; the new line still lands."""
    store = tmp_path / "queue.json"
    store.write_text('{"not": "a list"}')
    line = QueueLine(
        repo="saffron",
        spec_id="SA-0005",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=6.4,
        concerns=0,
        added=10,
        removed=2,
        link="",
    )
    append_queue_line(tmp_path, line, header={})
    stored = json.loads((tmp_path / "queue.json").read_text())
    assert len(stored) == 1
    assert stored[0]["spec_id"] == "SA-0005"


def test_prior_rows_survive_an_append(tmp_path):
    """The tolerance read cannot silently become "always start empty" —
    that would pass both corruption tests while destroying the feature."""
    first = QueueLine(
        repo="saffron",
        spec_id="SA-0005",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=6.4,
        concerns=0,
        added=10,
        removed=2,
        link="",
    )
    second = QueueLine(
        repo="saffron",
        spec_id="SA-0006",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=3.1,
        concerns=0,
        added=4,
        removed=0,
        link="",
    )
    append_queue_line(tmp_path, first, header={})
    append_queue_line(tmp_path, second, header={})
    stored = json.loads((tmp_path / "queue.json").read_text())
    assert [row["spec_id"] for row in stored] == ["SA-0005", "SA-0006"]


def test_a_queue_json_with_wrong_schema_rows_does_not_wedge_the_append(tmp_path):
    """A list of dicts with wrong schema (malformed rows) is dropped before
    writing. Two successive appends prove the malformed row was not persisted."""
    store = tmp_path / "queue.json"
    # Pre-populate with valid JSON that is a list of dicts, but rows have wrong schema
    store.write_text(
        json.dumps(
            [
                {
                    "repo": "saffron",
                    "spec_id": "SA-0001",
                    # Missing required fields: state, attempts, concerns, etc.
                }
            ]
        )
    )
    first = QueueLine(
        repo="saffron",
        spec_id="SA-0005",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=6.4,
        concerns=0,
        added=10,
        removed=2,
        link="",
    )
    second = QueueLine(
        repo="saffron",
        spec_id="SA-0006",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=3.1,
        concerns=0,
        added=4,
        removed=0,
        link="",
    )
    # First append should succeed (malformed row dropped, new row added)
    append_queue_line(tmp_path, first, header={})
    stored = json.loads((tmp_path / "queue.json").read_text())
    assert len(stored) == 1
    assert stored[0]["spec_id"] == "SA-0005"
    # Second append should also succeed, proving malformed row wasn't persisted
    append_queue_line(tmp_path, second, header={})
    stored = json.loads((tmp_path / "queue.json").read_text())
    assert [row["spec_id"] for row in stored] == ["SA-0005", "SA-0006"]


def test_a_queue_json_row_with_wrong_value_types_does_not_wedge_the_append(tmp_path):
    """A row with correct keys but unrenderable value types (e.g., dict instead
    of float) structurally passes but fails during render. Two successive appends
    prove the unrenderable row was not persisted."""
    store = tmp_path / "queue.json"
    # Pre-populate with valid JSON, dict with correct keys but wrong value type
    # (cost_usd_est should be float, but is a dict)
    store.write_text(
        json.dumps(
            [
                {
                    "repo": "saffron",
                    "spec_id": "SA-0001",
                    "state": "READY_FOR_REVIEW",
                    "attempts": 1,
                    "cost_usd_est": {"bad": "type"},  # Should be float or None
                    "concerns": 0,
                    "added": 1,
                    "removed": 0,
                    "link": "",
                }
            ]
        )
    )
    first = QueueLine(
        repo="saffron",
        spec_id="SA-0005",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=6.4,
        concerns=0,
        added=10,
        removed=2,
        link="",
    )
    second = QueueLine(
        repo="saffron",
        spec_id="SA-0006",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=3.1,
        concerns=0,
        added=4,
        removed=0,
        link="",
    )
    # First append should succeed (unrenderable row dropped)
    append_queue_line(tmp_path, first, header={})
    stored = json.loads((tmp_path / "queue.json").read_text())
    assert len(stored) == 1
    assert stored[0]["spec_id"] == "SA-0005"
    # Second append should also succeed, proving the unrenderable row wasn't persisted
    append_queue_line(tmp_path, second, header={})
    stored = json.loads((tmp_path / "queue.json").read_text())
    assert [row["spec_id"] for row in stored] == ["SA-0005", "SA-0006"]


def test_a_queue_json_row_that_breaks_the_sort_does_not_wedge_the_append(tmp_path):
    """`sort_key` negates `attempts`, and runs before `_row` ever does — so a
    validator built on `_row` alone let this row through and wedged the render.
    Two successive appends prove it was never persisted."""
    (tmp_path / "queue.json").write_text(
        json.dumps(
            [
                {
                    "repo": "saffron",
                    "spec_id": "SA-0001",
                    "state": "READY_FOR_REVIEW",
                    "attempts": "many",  # `-line.attempts` raises on a str
                    "cost_usd_est": 1.0,
                    "concerns": 0,
                    "added": 1,
                    "removed": 0,
                    "link": "",
                }
            ]
        )
    )
    first = QueueLine(
        repo="saffron",
        spec_id="SA-0005",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=6.4,
        concerns=0,
        added=10,
        removed=2,
        link="",
    )
    second = QueueLine(
        repo="saffron",
        spec_id="SA-0006",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=3.1,
        concerns=0,
        added=4,
        removed=0,
        link="",
    )
    append_queue_line(tmp_path, first, header={})
    stored = json.loads((tmp_path / "queue.json").read_text())
    assert [row["spec_id"] for row in stored] == ["SA-0005"]
    append_queue_line(tmp_path, second, header={})
    stored = json.loads((tmp_path / "queue.json").read_text())
    assert [row["spec_id"] for row in stored] == ["SA-0005", "SA-0006"]


def _diff_of(lines: list[str]) -> str:
    return (
        "diff --git a/tests/test_x.py b/tests/test_x.py\n"
        "--- a/tests/test_x.py\n"
        "+++ b/tests/test_x.py\n"
        f"@@ -1,1 +1,{len(lines)} @@\n"
    ) + "".join(f"{line}\n" for line in lines)


def test_a_huge_test_diff_does_not_push_the_body_past_githubs_limit():
    """GitHub rejects a body over 65,536 characters, and `gh pr create` then
    fails *after* the push — a branch with no pull request and no queue line.
    The diff is the section that grows with the change, so it is the one that
    gives way; provenance and the gate table must survive."""
    rendered = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=9000,
        removed=0,
        transcript_path="~/.saffron/batches/1",
        test_paths=["tests/**"],
        diff=_diff_of([f"+assert x == {n}" for n in range(9000)]),
    )
    assert len(rendered) <= 65_536
    assert "truncated" in rendered
    assert "### Provenance" in rendered and "### Gates" in rendered
    # A cut mid-block must still close its fence, or every section after it
    # renders as code.
    assert rendered.count("````") % 2 == 0


def test_a_four_backtick_context_line_cannot_escape_the_fence():
    """A context line carries one leading space and CommonMark closes a fence
    indented up to three, so four backticks in a test file closed the block —
    and the rest of the diff left the fence and stopped being inert."""
    rendered = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=0,
        transcript_path="~/.saffron/batches/1",
        test_paths=["tests/**"],
        diff=_diff_of([" ````", "+# ping @someone, Fixes #12"]),
    )
    fence = rendered.split("diff\n", 1)[0].rsplit("\n", 1)[-1]
    assert set(fence) == {"`"} and len(fence) > 4
    # Both the line that used to close the block and everything after it are
    # still inside it. GitHub parses neither a mention nor a closing keyword
    # in a fence, so nothing here needs rewriting — the fence is the control.
    fenced = rendered.split(fence + "diff\n", 1)[1].split("\n" + fence, 1)[0]
    assert " ````" in fenced and "@someone" in fenced and "Fixes #12" in fenced


def test_re_running_a_spec_replaces_its_row_rather_than_doubling_it(tmp_path):
    """The operator's normal response to MERGE_FAILED is to run the spec again.
    Two rows sort into different bands, and the stale MERGE_FAILED (rank 2)
    lands *above* the fresh READY_FOR_REVIEW — the morning page showing a spec
    they already resolved as still needing them (§6)."""
    failed = QueueLine(
        repo="saffron",
        spec_id="SA-0005",
        state="MERGE_FAILED",
        attempts=2,
        cost_usd_est=6.4,
        concerns=0,
        added=0,
        removed=0,
        link="",
    )
    fresh = QueueLine(
        repo="saffron",
        spec_id="SA-0005",
        state="READY_FOR_REVIEW",
        attempts=1,
        cost_usd_est=3.1,
        concerns=0,
        added=4,
        removed=0,
        link="",
    )
    # Same spec id, a different repo: the batch tree holds several, and ids are
    # unique only within one.
    elsewhere = QueueLine(**{**asdict(fresh), "repo": "thermal-edge"})

    append_queue_line(tmp_path, failed, header={})
    append_queue_line(tmp_path, elsewhere, header={})
    index = append_queue_line(tmp_path, fresh, header={})

    stored = json.loads((tmp_path / "queue.json").read_text())
    assert [(row["repo"], row["state"]) for row in stored] == [
        ("thermal-edge", "READY_FOR_REVIEW"),
        ("saffron", "READY_FOR_REVIEW"),
    ]
    assert "MERGE_FAILED" not in index.read_text()
    # The header counts the rows that survived, not every append.
    assert "tasks <strong>2</strong>" in index.read_text()
    assert "spend <strong>$6.20</strong>" in index.read_text()


def test_the_append_holds_a_lock_for_the_whole_read_modify_write(tmp_path):
    """Two tasks appending at once otherwise lose whichever row was read first.
    Probed from inside the critical section, because a lock taken and released
    around only the write reads identically from outside."""
    held = []

    def _probe(path):
        # A second open() is a distinct file description, so `flock` treats it
        # as another holder even in this process.
        with (tmp_path / ".queue.lock").open("w") as other:
            try:
                fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held.append(False)
            except BlockingIOError:
                held.append(True)
        return []

    with mock.patch("saffron.report.index._existing_queue_rows", _probe):
        append_queue_line(
            tmp_path,
            QueueLine(
                repo="saffron",
                spec_id="SA-0005",
                state="READY_FOR_REVIEW",
                attempts=1,
                cost_usd_est=1.0,
                concerns=0,
                added=1,
                removed=0,
                link="",
            ),
            header={},
        )
    assert held == [True]


def test_a_v0_batch_tree_keeps_its_rows_across_the_store_rename(tmp_path):
    """v0 wrote `lines.json`. Renamed with no migration, every prior task
    vanishes from `index.html` and the old file is left with no reader."""
    (tmp_path / "lines.json").write_text(
        json.dumps(
            [
                asdict(
                    QueueLine(
                        repo="saffron",
                        spec_id="SA-0001",
                        state="READY_FOR_REVIEW",
                        attempts=1,
                        cost_usd_est=2.0,
                        concerns=0,
                        added=1,
                        removed=0,
                        link="",
                    )
                )
            ]
        )
    )
    index = append_queue_line(
        tmp_path,
        QueueLine(
            repo="saffron",
            spec_id="SA-0002",
            state="READY_FOR_REVIEW",
            attempts=1,
            cost_usd_est=1.0,
            concerns=0,
            added=1,
            removed=0,
            link="",
        ),
        header={},
    )
    stored = json.loads((tmp_path / "queue.json").read_text())
    assert [row["spec_id"] for row in stored] == ["SA-0001", "SA-0002"]
    assert "SA-0001" in index.read_text()
    assert not (tmp_path / "lines.json").exists()


def test_a_long_backtick_run_cannot_evict_the_gate_table(tmp_path):
    """The fence is cell-authored and unbounded — a context line of 5,000
    backticks needs a 5,001-character fence at each end. Sized against a fixed
    reserve, the diff overshot its budget and the body's last-resort clamp paid
    for it out of the *end*: the gate table, the findings and the provenance,
    which are the sections that must survive (§5.7)."""
    for run in (0, 33, 5_000, 20_000):
        lines = [f"+assert x == {n}" for n in range(9000)]
        lines[5] = " " + "`" * run  # a context line, one leading space
        rendered = render_pr_body(
            SPEC,
            RESULTS,
            [],
            base_sha="a" * 40,
            head_sha="b" * 40,
            added=9000,
            removed=0,
            transcript_path="~/.saffron/batches/1",
            test_paths=["tests/**"],
            diff=_diff_of(lines),
        )
        assert len(rendered) <= 65_536, run
        assert "### Gates" in rendered and "### Provenance" in rendered, run
        fence = rendered.split("diff\n", 1)[0].rsplit("\n", 1)[-1]
        assert len(fence) > run, run
        assert rendered.count(fence + "\n") == 1, run  # opened and closed


def test_a_byte_inside_an_added_line_cannot_end_the_test_stanza_early():
    """One raw separator byte in a `+` line used to shatter it, and the
    fragment after the byte read as a stanza header — so the section stopped
    there and the deletion below it never reached the body a human reads."""
    diff = (
        "diff --git a/tests/test_x.py b/tests/test_x.py\n"
        "--- a/tests/test_x.py\n+++ b/tests/test_x.py\n"
        "@@ -1,3 +1,2 @@\n"
        "+x = 1\x0cdiff --git a/src/decoy.py b/src/decoy.py\n"
        "-def test_kept_me_honest():\n"
        "-    assert thing()\n"
    )
    body = render_pr_body(
        SPEC,
        RESULTS,
        [],
        base_sha="a" * 40,
        head_sha="b" * 40,
        added=1,
        removed=2,
        transcript_path="/t",
        test_paths=["tests/**"],
        diff=diff,
    )
    assert "-def test_kept_me_honest():" in body
    assert "-    assert thing()" in body
