import json
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from saffron.record.contract import KINDS, Fact, new_task_key


def a_fact(**over: Any) -> Fact:
    base: dict[str, Any] = {
        "kind": "task_created",
        "task_key": "a" * 32,
        "at": "2026-09-20T00:00:00Z",
        "repo": "saffron",
        "batch_key": None,
        "payload": {"spec_id": "SA-0099"},
    }
    return Fact(**(base | over))


def test_a_task_key_is_32_hex_characters():
    key = new_task_key()
    assert len(key) == 32
    assert set(key) <= set("0123456789abcdef")


def test_two_task_keys_never_collide():
    assert len({new_task_key() for _ in range(1000)}) == 1000


def test_a_fact_round_trips_through_json():
    fact = a_fact()
    assert Fact.from_json(fact.to_json()) == fact


def test_a_fact_of_an_unknown_kind_is_refused():
    with pytest.raises(ValueError, match="unknown fact kind"):
        a_fact(kind="wat")


def test_every_declared_kind_is_accepted():
    for kind in KINDS:
        assert a_fact(kind=kind).kind == kind


def test_a_fact_refuses_a_payload_json_cannot_carry():
    # A payload that fails to serialise must fail at append, not at fold time,
    # where the only record of the task is what could not be written.
    with pytest.raises(ValueError, match="payload"):
        a_fact(payload={"when": object()})


def test_a_fact_is_frozen():
    with pytest.raises(FrozenInstanceError):
        a_fact().kind = "task_state"  # type: ignore


def test_from_json_refuses_a_missing_field():
    partial = json.dumps({"kind": "task_created", "task_key": "a" * 32})
    with pytest.raises(ValueError, match="missing"):
        Fact.from_json(partial)
