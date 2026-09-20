"""An in-memory `Record`. Tests use it wherever git is not what is under test,
so a fold test does not need a repository to prove the fold."""

from __future__ import annotations

from collections import defaultdict

from saffron.record.contract import Fact


class MemoryRecord:
    def __init__(self) -> None:
        self._facts: dict[str, list[Fact]] = defaultdict(list)
        self._values: dict[str, str] = {}

    def append(self, task_key: str, fact: Fact) -> None:
        self._facts[task_key].append(fact)

    def read(self, task_key: str) -> list[Fact]:
        return list(self._facts.get(task_key, []))

    def task_keys(self) -> list[str]:
        return list(self._facts)

    def compare_and_swap(self, key: str, expected: str | None, new: str) -> bool:
        if self._values.get(key) != expected:
            return False
        self._values[key] = new
        return True
