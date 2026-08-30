import os

import pytest

from saffron.intake import SpecError, discover_specs, load_spec, parse_spec

VALID = """---
id: TE-9001
title: NWS forecast ingest has produced no rows since 2026-08-11
type: bug
priority: 2
depends_on: [TE-9000]
envelope:
  - thermal_edge/**
touches:
  - thermal_edge/weather/**
forbidden:
  - alembic/versions/**
budget_usd: 12
max_attempts: 4
risk: standard
---

## Context
Some prose.

## Acceptance criteria
- [ ] A regression test exists that fails on the current `main`
- [ ] The silent-success path is removed

## Out of scope
Kalshi sync errors.
"""


def test_parses_the_frontmatter():
    spec = parse_spec(VALID)
    assert spec.id == "TE-9001"
    assert spec.type == "bug"
    assert spec.priority == 2
    assert spec.touches == ["thermal_edge/weather/**"]
    assert spec.forbidden == ["alembic/versions/**"]
    assert spec.depends_on == ["TE-9000"]
    assert spec.budget_usd == 12
    assert spec.max_attempts == 4
    assert spec.risk == "standard"


def test_extracts_the_acceptance_criteria_as_a_checklist():
    spec = parse_spec(VALID)
    assert spec.acceptance_criteria == [
        "A regression test exists that fails on the current `main`",
        "The silent-success path is removed",
    ]


def test_the_body_survives_for_the_pr_body():
    assert "Kalshi sync errors." in parse_spec(VALID).body


def test_defaults_are_the_documented_ones():
    spec = parse_spec("---\nid: TE-1\ntitle: t\ntype: chore\n---\n")
    assert spec.priority == 3
    assert spec.risk == "standard"
    assert spec.max_attempts == 4
    assert spec.touches == []
    assert spec.acceptance_criteria == []


def test_a_missing_frontmatter_block_is_rejected():
    with pytest.raises(SpecError, match="frontmatter"):
        parse_spec("# Just a heading\n")


def test_an_unknown_type_is_rejected():
    with pytest.raises(SpecError):
        parse_spec("---\nid: TE-1\ntitle: t\ntype: epic\n---\n")


def test_an_unknown_risk_tier_is_rejected():
    with pytest.raises(SpecError):
        parse_spec("---\nid: TE-1\ntitle: t\ntype: bug\nrisk: critical\n---\n")


def test_an_unknown_frontmatter_key_is_rejected():
    """A typo'd key that is silently ignored is a spec that builds the wrong thing."""
    with pytest.raises(SpecError):
        parse_spec("---\nid: TE-1\ntitle: t\ntype: bug\ntouchs: [a]\n---\n")


def test_malformed_yaml_is_rejected():
    with pytest.raises(SpecError):
        parse_spec("---\nid: [unclosed\n---\n")


def test_a_reserved_body_key_is_rejected():
    with pytest.raises(SpecError, match="body"):
        parse_spec("---\nid: TE-1\ntitle: t\ntype: bug\nbody: nope\n---\n")


def test_a_reserved_acceptance_criteria_key_is_rejected():
    with pytest.raises(SpecError, match="acceptance_criteria"):
        parse_spec(
            "---\nid: TE-1\ntitle: t\ntype: bug\nacceptance_criteria: [nope]\n---\n"
        )


def test_load_spec_returns_a_stable_content_sha(tmp_path):
    path = tmp_path / "TE-9001-gap.md"
    path.write_text(VALID)
    spec, sha = load_spec(path)
    assert spec.id == "TE-9001"
    assert len(sha) == 64
    assert load_spec(path)[1] == sha


def test_editing_a_spec_moves_its_sha(tmp_path):
    path = tmp_path / "TE-9001-gap.md"
    path.write_text(VALID)
    _, before = load_spec(path)
    path.write_text(VALID + "\nAn added line.\n")
    _, after = load_spec(path)
    assert before != after


def test_an_id_that_is_a_url_scheme_is_rejected():
    """`id` reaches an href in the index; a javascript: id renders a live link."""
    with pytest.raises(SpecError):
        parse_spec("---\nid: 'javascript:alert(1)'\ntitle: t\ntype: bug\n---\n")


def test_an_id_that_traverses_the_filesystem_is_rejected():
    """`id` also reaches a path: out_dir / spec.id."""
    with pytest.raises(SpecError):
        parse_spec("---\nid: ../../etc/passwd\ntitle: t\ntype: bug\n---\n")


def test_the_acceptance_criteria_heading_is_matched_whatever_its_case():
    spec = parse_spec(
        "---\nid: TE-1\ntitle: t\ntype: bug\n---\n\n"
        "## Acceptance Criteria\n- [ ] It holds\n"
    )
    assert spec.acceptance_criteria == ["It holds"]


def test_a_missing_spec_path_is_a_specerror(tmp_path):
    with pytest.raises(SpecError, match="could not be read"):
        load_spec(tmp_path / "nope.md")


def test_an_unreadable_spec_path_is_a_specerror(tmp_path):
    if os.geteuid() == 0:
        pytest.skip("root reads everything")
    path = tmp_path / "TE-9001-gap.md"
    path.write_text(VALID)
    path.chmod(0o000)
    try:
        with pytest.raises(SpecError, match="could not be read"):
            load_spec(path)
    finally:
        path.chmod(0o644)


def test_a_non_string_frontmatter_key_is_a_specerror():
    """`on:` is YAML 1.1 for the boolean True, and ** on a non-string key
    raises TypeError before pydantic ever sees the mapping."""
    with pytest.raises(SpecError, match="invalid"):
        parse_spec("---\non: nightly\nid: TE-1\ntitle: t\ntype: bug\n---\n")


def test_a_non_utf8_spec_file_is_a_specerror(tmp_path):
    path = tmp_path / "TE-9002-bytes.md"
    path.write_bytes(b"---\nid: TE-9002\ntitle: \xff\xfe\ntype: bug\n---\n")
    with pytest.raises(SpecError, match="could not be read"):
        load_spec(path)


def test_a_ceiling_of_zero_is_refused_rather_than_reaching_the_loop():
    """These are read now. `max_attempts: 0` reaches `repair_loop`, skips
    `range(1, 1)` entirely and raises the unreachable assertion — a spec typo
    surfacing to the operator as an infrastructure abort."""
    for field in ("budget_usd", "max_attempts", "max_turns"):
        with pytest.raises(SpecError):
            parse_spec(
                "---\nid: SY-1\ntitle: One\ntype: feature\n"
                f"{field}: 0\n---\n\n## Acceptance criteria\n- [ ] it works\n"
            )


def test_a_declared_acceptance_block_parses_into_structured_criteria():
    spec = parse_spec(
        "---\nid: TE-1\ntitle: t\ntype: feature\n"
        "acceptance:\n"
        "  - claim: the gate reports skip with no witnesses\n"
        "    witness: tests/test_criteria.py::test_no_witnesses_skips\n"
        "  - claim: today's parse is unchanged\n"
        "    witness: tests/test_intake.py::test_extracts_the_acceptance_criteria_as_a_checklist\n"
        "    preserves: true\n"
        "---\n\nbody only\n"
    )
    assert [c.claim for c in spec.acceptance] == [
        "the gate reports skip with no witnesses",
        "today's parse is unchanged",
    ]
    assert (
        spec.acceptance[0].witness == "tests/test_criteria.py::test_no_witnesses_skips"
    )
    assert (spec.acceptance[0].preserves, spec.acceptance[1].preserves) == (False, True)


def test_a_spec_with_no_acceptance_block_parses_exactly_as_it_does_today():
    """Ten specs predate this key. Absent, nothing changes — and the markdown
    section still populates `acceptance_criteria`."""
    spec = parse_spec(
        "---\nid: TE-1\ntitle: t\ntype: bug\n---\n\n"
        "## Acceptance criteria\n- [ ] it works\n"
    )
    assert spec.acceptance == []
    assert spec.acceptance_criteria == ["it works"]


def test_a_spec_declaring_both_lists_is_refused_as_malformed():
    """Two lists of criteria with nothing keeping them in sync, and no way for
    `pr_body` to say which one it is ticking."""
    with pytest.raises(SpecError, match="both"):
        parse_spec(
            "---\nid: TE-1\ntitle: t\ntype: feature\n"
            "acceptance:\n"
            "  - claim: c\n    witness: t.py::test_w\n"
            "---\n\n## Acceptance criteria\n- [ ] it works\n"
        )


def test_an_unknown_key_inside_a_criterion_is_refused():
    """A typo in a witness key is a validation error, not a silent mis-parse —
    which is the whole reason the witness is not hung off the checklist line."""
    with pytest.raises(SpecError):
        parse_spec(
            "---\nid: TE-1\ntitle: t\ntype: feature\n"
            "acceptance:\n"
            "  - claim: c\n    witness: t.py::test_w\n    preserve: true\n"
            "---\n\nbody\n"
        )


def test_a_criterion_missing_its_witness_is_refused():
    with pytest.raises(SpecError):
        parse_spec(
            "---\nid: TE-1\ntitle: t\ntype: feature\n"
            "acceptance:\n  - claim: c\n---\n\nbody\n"
        )


def test_a_wrapped_acceptance_criterion_keeps_its_continuation_lines():
    """`_CRITERION` used to be line-anchored under re.MULTILINE, so a wrapped
    criterion kept only its first line — the exact shape that made SA-0005
    unsatisfiable, because the paths that made it so sat on continuation
    lines a refusal gate built on `acceptance_criteria` never saw."""
    spec = parse_spec(
        "---\nid: TE-1\ntitle: t\ntype: feature\n---\n\n"
        "## Acceptance criteria\n"
        "- [ ] An effective risk tier is computed once per attempt, derived\n"
        "      from paths that include `saffron/cli.py` and\n"
        "      `saffron/phases/package.py`, never from a second read\n"
        "- [ ] A second, unrelated criterion on one line\n"
    )
    assert spec.acceptance_criteria == [
        "An effective risk tier is computed once per attempt, derived "
        "from paths that include `saffron/cli.py` and "
        "`saffron/phases/package.py`, never from a second read",
        "A second, unrelated criterion on one line",
    ]
    assert "saffron/cli.py" in spec.acceptance_criteria[0]
    assert "saffron/phases/package.py" in spec.acceptance_criteria[0]


def test_discover_specs_orders_by_filename_not_by_priority(tmp_path):
    """A tie in priority must resolve the same way on every machine — by the
    scan's own order, which is filename, not directory-entry order."""
    (tmp_path / "b-second.md").write_text(
        "---\nid: TE-2\ntitle: t\ntype: chore\npriority: 1\n---\n"
    )
    (tmp_path / "a-first.md").write_text(
        "---\nid: TE-1\ntitle: t\ntype: chore\npriority: 9\n---\n"
    )
    specs, failures = discover_specs(tmp_path)
    assert failures == []
    assert [d.spec.id for d in specs] == ["TE-1", "TE-2"]
    assert [d.path.name for d in specs] == ["a-first.md", "b-second.md"]


def test_discover_specs_reports_a_malformed_spec_without_raising(tmp_path):
    (tmp_path / "a-good.md").write_text("---\nid: TE-1\ntitle: t\ntype: chore\n---\n")
    (tmp_path / "b-broken.md").write_text("no frontmatter here\n")
    (tmp_path / "c-good.md").write_text("---\nid: TE-3\ntitle: t\ntype: chore\n---\n")

    specs, failures = discover_specs(tmp_path)

    assert [d.spec.id for d in specs] == ["TE-1", "TE-3"]
    assert len(failures) == 1
    assert failures[0].path.name == "b-broken.md"
    assert "frontmatter" in failures[0].reason


def test_discover_specs_returns_the_spec_sha_alongside_each_spec(tmp_path):
    path = tmp_path / "a.md"
    path.write_text("---\nid: TE-1\ntitle: t\ntype: chore\n---\n")

    specs, _ = discover_specs(tmp_path)
    _, sha = load_spec(path)

    assert specs[0].spec_sha == sha


def test_discover_specs_on_an_empty_directory_returns_nothing(tmp_path):
    assert discover_specs(tmp_path) == ([], [])
