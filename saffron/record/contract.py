"""The record's whole backend-agnostic surface: what a fact is, and what a
backend must do with one.

The record holds facts, never events — `saffron/events.py` owns that word for
the `events.jsonl` stream, and the two are deliberately separate — §8 of
`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md`,
not `DESIGN.md` §8.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from typing import Any, Protocol

# Closed, and one entry per thing the ledger's tables hold today. A kind that
# is not here cannot be appended, so the fold never meets one it cannot place.
KINDS = (
    "task_created",
    "task_state",
    "task_package",
    "task_push",
    "task_merged_head",
    "task_policy",
    "attempt_opened",
    "attempt_closed",
    "gate_result",
    "finding",
    "rebuttal",
    "decision",
    "run_created",
    "run_finished",
    "run_preflight",
    "batch_created",
    "batch_closed",
    "repo_upserted",
    "stack_layer",
    "end_review",
    "qualification",
)


def new_task_key() -> str:
    """The record's own identity for a task, minted at creation. The ledger's
    `task_id` cannot serve: it is an autoincrement the fold mints, so it would
    name a ref by a number that only exists after the ref has been read."""
    return secrets.token_hex(16)


class RecordError(RuntimeError):
    """A backend failed, carrying the reason the tool gave. git says why on
    stderr, and `CalledProcessError` prints only the argv, so a refused push
    read the same as a missing repository."""

    def __init__(self, message: str, *, returncode: int = 0, stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class StaleWriter(RecordError):
    """A remote refused a non-fast-forward push, so another host appended to
    this ref first. Named apart from every other failure because §3 rests on
    that refusal, and the retry §5 defers needs one thing to catch."""


@dataclass(frozen=True)
class Fact:
    kind: str
    task_key: str
    at: str
    repo: str
    batch_key: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"unknown fact kind: {self.kind!r}")
        # Refused here rather than at the backend, so a payload git cannot
        # carry fails while the caller still holds what it was trying to say.
        try:
            json.dumps(self.payload)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"payload is not JSON: {exc}") from exc

    def to_json(self) -> str:
        return json.dumps(
            {
                "kind": self.kind,
                "task_key": self.task_key,
                "at": self.at,
                "repo": self.repo,
                "batch_key": self.batch_key,
                "payload": self.payload,
            },
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, raw: str) -> Fact:
        data = json.loads(raw)
        missing = {"kind", "task_key", "at", "repo"} - set(data)
        if missing:
            raise ValueError(f"fact is missing {sorted(missing)}")
        return cls(
            kind=data["kind"],
            task_key=data["task_key"],
            at=data["at"],
            repo=data["repo"],
            batch_key=data.get("batch_key"),
            payload=data.get("payload", {}),
        )


def check_filed_under(task_key: str, fact: Fact) -> None:
    """A fact names its own task, so filing it under another key would make
    the ref and its contents disagree and the fold trust the ref."""
    if fact.task_key != task_key:
        raise ValueError(
            f"fact claims task {fact.task_key!r}, filed under {task_key!r}"
        )


class Record(Protocol):
    """Four operations and no git in any signature.

    ponytail: `compare_and_swap` is called by nothing and every backend pays
    for it. It is the seam a cross-host budget needs, specified now so a later
    backend does not reshape the fold to add it (§2 of the record design).
    """

    def append(self, task_key: str, fact: Fact) -> None: ...

    def read(self, task_key: str) -> list[Fact]: ...

    def task_keys(self) -> list[str]: ...

    def compare_and_swap(self, key: str, expected: str | None, new: str) -> bool: ...
