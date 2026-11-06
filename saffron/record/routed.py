"""`RoutedRecord`: one `RefsRecord` per mirror and origin, chosen per task.

`repos.name` is not unique, so a fact cannot find its mirror by name alone.
Two rows can share one name and differ in origin and mirror. The caller
passes a lookup from a task's own key to that task's mirror and origin. It is
read fresh on every append rather than cached against the key. A task's
facts then always land where its own run says to.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from saffron.record.contract import Fact, RecordError
from saffron.record.refs import RefsRecord


class RoutedRecord:
    def __init__(self, locate: Callable[[str], tuple[Path, str]]) -> None:
        self._locate = locate
        # Keyed on mirror and origin, never on the repo name. Two repo rows
        # can share a name or a mirror, and each fetches from its own origin.
        self._records: dict[tuple[Path, str], RefsRecord] = {}
        # Kept in append order. `setdefault` leaves a kept key in place, so
        # a key appended three times is pushed once (§3 of the record design).
        self._kept: dict[str, None] = {}

    def _record_for(self, task_key: str) -> tuple[RefsRecord, str]:
        mirror, origin = self._locate(task_key)
        record = self._records.get((mirror, origin))
        if record is None:
            # `push()` below is the only write to `origin`. A later fact on a
            # ref this mirror lacks reads `origin` first.
            record = RefsRecord(mirror, origin=origin)
            self._records[(mirror, origin)] = record
        return record, origin

    def append(self, task_key: str, fact: Fact) -> None:
        record, _ = self._record_for(task_key)
        record.append(task_key, fact)
        self._kept.setdefault(task_key, None)

    def read(self, task_key: str) -> list[Fact]:
        record, _ = self._record_for(task_key)
        return record.read(task_key)

    def push(self, task_key: str) -> None:
        """Push `task_key`'s own ref to its origin, nothing else.

        Drops `task_key` from the kept set first, whether the push below
        lands or raises: a key whose push failed is kept again only once a
        later fact lands on it.
        """
        self._kept.pop(task_key, None)
        record, origin = self._record_for(task_key)
        record.push(task_key, origin)

    def push_unpushed(self) -> list[tuple[str, Exception]]:
        """Push every kept key once, through `push`, in append order.

        Never raises for a push: a refusal is caught and returned beside
        its key instead, so a command's exit can report every refusal
        rather than stopping at the first.
        """
        refused: list[tuple[str, Exception]] = []
        for key in list(self._kept):
            try:
                self.push(key)
            except Exception as exc:
                refused.append((key, exc))
        return refused

    def task_keys(self) -> list[str]:
        raise RecordError(
            "a routed record answers for no repo on its own, "
            "the fold reads each repo's own RefsRecord instead (§4 of the record design)"
        )

    def compare_and_swap(self, key: str, expected: str | None, new: str) -> bool:
        raise RecordError(
            "a routed record holds no values of its own, "
            "a value's home is a single repo's RefsRecord (§10 of the record design)"
        )
