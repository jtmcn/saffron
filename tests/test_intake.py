import pytest

from saffron.intake import Spec, SpecError, load_spec, parse_spec

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
