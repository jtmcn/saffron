import json
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from saffron.record.contract import KINDS, Fact, new_task_key
from saffron.record.memory import MemoryRecord


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


def test_reading_a_task_with_no_facts_gives_an_empty_log():
    assert MemoryRecord().read("a" * 32) == []


def test_facts_read_back_in_append_order():
    record = MemoryRecord()
    first = a_fact(kind="task_created")
    second = a_fact(kind="task_state", payload={"state": "IMPLEMENTING"})
    record.append(first.task_key, first)
    record.append(second.task_key, second)
    assert record.read(first.task_key) == [first, second]


def test_appending_the_same_fact_twice_keeps_both():
    # Append-only means append-only: two identical gate results are two runs
    # of one gate, not one run recorded twice.
    record = MemoryRecord()
    fact = a_fact(kind="gate_result")
    record.append(fact.task_key, fact)
    record.append(fact.task_key, fact)
    assert len(record.read(fact.task_key)) == 2


def test_task_keys_lists_every_task_appended_to():
    record = MemoryRecord()
    for key in ("a" * 32, "b" * 32):
        record.append(key, a_fact(task_key=key))
    assert sorted(record.task_keys()) == ["a" * 32, "b" * 32]


def test_compare_and_swap_sets_an_absent_key():
    record = MemoryRecord()
    assert record.compare_and_swap("budget", None, "1.50") is True


def test_compare_and_swap_refuses_a_stale_writer():
    record = MemoryRecord()
    record.compare_and_swap("budget", None, "1.50")
    assert record.compare_and_swap("budget", "1.50", "2.00") is True
    assert record.compare_and_swap("budget", "1.50", "9.99") is False


def test_a_refused_swap_leaves_the_value_alone():
    record = MemoryRecord()
    record.compare_and_swap("budget", None, "1.50")
    record.compare_and_swap("budget", "wrong", "9.99")
    assert record.compare_and_swap("budget", "1.50", "2.00") is True


def test_reading_an_absent_task_does_not_register_it():
    record = MemoryRecord()
    record.read("nonexistent-key")
    assert record.task_keys() == []
