"""The frontmatter model refuses what the spec says it refuses, naming the field."""

import pytest
from pydantic import ValidationError

from records.kinds import KINDS, BacklogItem

MINIMAL = {"id": 7, "title": "Seven", "status": "open"}


def test_a_minimal_open_item_validates():
    item = BacklogItem.model_validate(MINIMAL)
    assert item.tier is None
    assert item.specs == [] and item.prs == [] and item.cites == []
    assert item.by_hand is False


def test_an_unknown_key_is_refused_not_ignored():
    with pytest.raises(ValidationError, match="evidence"):
        BacklogItem.model_validate({**MINIMAL, "evidence": ["x.md"]})


@pytest.mark.parametrize("status", ["done", "superseded", "wontfix"])
def test_a_closed_item_needs_a_closed_date(status):
    with pytest.raises(ValidationError, match="closed"):
        BacklogItem.model_validate(
            {**MINIMAL, "status": status, "prs": [1], "superseded_by": 8}
        )


@pytest.mark.parametrize("status", ["done", "wontfix"])
def test_a_closed_item_names_what_closed_it(status):
    with pytest.raises(ValidationError, match="specs, prs or commits"):
        BacklogItem.model_validate(
            {**MINIMAL, "status": status, "closed": "2026-09-14"}
        )


def test_a_superseded_item_names_its_successor():
    with pytest.raises(ValidationError, match="superseded_by"):
        BacklogItem.model_validate(
            {**MINIMAL, "status": "superseded", "closed": "2026-09-14", "prs": [1]}
        )


def test_an_open_item_may_not_carry_a_closed_date():
    with pytest.raises(ValidationError, match="closed"):
        BacklogItem.model_validate({**MINIMAL, "closed": "2026-09-14"})


def test_tier_is_zero_to_three_or_null():
    with pytest.raises(ValidationError, match="tier"):
        BacklogItem.model_validate({**MINIMAL, "tier": 4})
    assert BacklogItem.model_validate({**MINIMAL, "tier": 0}).tier == 0


def test_a_spec_id_has_the_spec_shape():
    with pytest.raises(ValidationError, match="specs"):
        BacklogItem.model_validate({**MINIMAL, "specs": ["87"]})


def test_a_citation_carries_its_section_sign():
    with pytest.raises(ValidationError, match="cites"):
        BacklogItem.model_validate({**MINIMAL, "cites": ["5.4"]})


def test_superseded_by_is_refused_on_an_item_that_is_not_superseded():
    with pytest.raises(ValidationError, match="superseded_by"):
        BacklogItem.model_validate({**MINIMAL, "superseded_by": 8})


def test_an_item_may_not_close_before_it_was_filed():
    with pytest.raises(ValidationError, match="filed"):
        BacklogItem.model_validate(
            {
                **MINIMAL,
                "status": "done",
                "prs": [1],
                "filed": "2026-09-14",
                "closed": "2026-09-13",
            }
        )


@pytest.mark.parametrize("field", ["prs", "related"])
def test_a_pr_or_related_number_is_at_least_one(field):
    with pytest.raises(ValidationError, match=field):
        BacklogItem.model_validate({**MINIMAL, field: [0]})


def test_a_commit_sha_has_the_hex_shape():
    with pytest.raises(ValidationError, match="commits"):
        BacklogItem.model_validate({**MINIMAL, "commits": ["xyz"]})
    assert BacklogItem.model_validate({**MINIMAL, "commits": ["4ba8bdf"]}).commits == [
        "4ba8bdf"
    ]


def test_an_unquoted_commit_sha_hints_to_quote_it():
    # An all-digit sha with no quotes arrives as an int.
    with pytest.raises(ValidationError, match="quote"):
        BacklogItem.model_validate({**MINIMAL, "commits": [1234567]})


def test_backlog_is_a_registered_kind():
    kind = KINDS["backlog"]
    assert kind.directory == "docs/backlog"
    assert kind.model is BacklogItem
