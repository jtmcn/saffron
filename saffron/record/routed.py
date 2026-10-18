"""`RoutedRecord`: one `RefsRecord` per repo mirror, chosen per task.

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
        # Keyed on the mirror path, never on the repo name: two repo rows
        # sharing a name must never share a `RefsRecord`.
        self._records: dict[Path, RefsRecord] = {}

    def _record_for(self, task_key: str) -> tuple[RefsRecord, str]:
        mirror, origin = self._locate(task_key)
        record = self._records.get(mirror)
        if record is None:
            # No remote: every append is local, and the push below is the
            # only thing that ever reaches `origin`.
            record = RefsRecord(mirror)
            self._records[mirror] = record
        return record, origin

    def append(self, task_key: str, fact: Fact) -> None:
        record, _ = self._record_for(task_key)
        record.append(task_key, fact)

    def read(self, task_key: str) -> list[Fact]:
        record, _ = self._record_for(task_key)
        return record.read(task_key)

    def push(self, task_key: str) -> None:
        """Push `task_key`'s own ref to its origin, nothing else."""
        record, origin = self._record_for(task_key)
        record.push(task_key, origin)

    def task_keys(self) -> list[str]:
        raise RecordError(
            "a routed record answers for no repo on its own, "
            "the fold reads each repo's own RefsRecord instead (§10)"
        )

    def compare_and_swap(self, key: str, expected: str | None, new: str) -> bool:
        raise RecordError(
            "a routed record holds no values of its own, "
            "a value's home is a single repo's RefsRecord (§10)"
        )
