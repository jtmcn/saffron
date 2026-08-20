from saffron.gates.baseline import NewFailure
from saffron.gates.contract import Failure, GateResult
from saffron.intake import parse_spec
from saffron.report.index import QueueLine, render_index, sort_key
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
