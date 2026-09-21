"""Record -> ledger. Tasks, attempts, gate results and findings are rebuilt
from the task facts through `Ledger.fold_task`, so deleting those rows costs
nothing.

§ numbers here are `docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md`'s,
not `DESIGN.md`'s.

Batches and runs are not, yet: `create_run`, `finish_run`, `set_run_preflight`,
`create_batch`, `close_batch`, `attach_run_to_batch`, `attach_orphan_runs_to_batch`
and `upsert_repo` append no fact, so a rebuild has no `batches` row and leaves
`runs.batch_id`/`status`/`preflight`/`ended_at` unset — `Ledger.batch_spend`
joins `runs.batch_id`, so every batch reads as $0 spent. §5's gap, not fixed
here.

Replay, not snapshot: a task's state is what its facts add up to (§3).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from saffron.ledger import Ledger, UnplacedRebuttal
from saffron.record.contract import Fact, Record


class UnreadableTask(Exception):
    """A task the record cannot give back. Named apart from every other
    failure so `saffron fold` can price it: a task that did not make it into
    the ledger, never the fold itself breaking. `error` != `fail`."""


@dataclass
class Fold:
    """What one fold did. The skipped tasks are data rather than a printed
    line, because whether a partial rebuild is a success is the caller's to
    decide and `saffron fold` decides it by exit code."""

    folded: int = 0
    skipped: list[tuple[str, str]] = field(default_factory=list)


def fold(record: Record, ledger: Ledger, strict: bool = True) -> Fold:
    done = Fold()
    for key in _creation_order(record, ledger, strict, done):
        try:
            facts = _facts_of(record, key)
        except Exception as exc:
            ledger.fold_task(key, [])
            _skipped(key, exc, strict, done)
            continue
        try:
            ledger.fold_task(key, facts)
        except UnplacedRebuttal as exc:
            # The record's own defect, not the fold's: a rebuttal with
            # nothing to rebut is priced like a fact git cannot read.
            ledger.fold_task(key, [])
            _skipped(key, exc, strict, done)
            continue
        except Exception:
            # A fact the ledger cannot place is the fold's own gap, never a
            # record that cannot be read, so it aborts in both modes.
            ledger.fold_task(key, [])
            raise
        done.folded += 1
    return done


def _facts_of(record: Record, key: str) -> list[Fact]:
    """A backend owes a list of `Fact` opening on `task_created`, and the fold
    checks both here. Read at the seam, so a backend that breaks its contract
    is an unreadable task, and everything past this line is the fold's own."""
    facts = record.read(key)
    for entry in facts:
        if not isinstance(entry, Fact):
            raise ValueError(f"entry is not a fact: {entry!r}")
    if not any(f.kind == "task_created" for f in facts):
        # `next` on an empty generator raises a `StopIteration` that
        # stringifies to nothing, so the log says what is missing instead.
        raise ValueError("no task_created fact")
    return facts


def _skipped(key: str, exc: Exception, strict: bool, done: Fold) -> None:
    """`Exception`, not a named few: `RefsRecord.read` raises `RecordError`
    on a broken repository, which is the likeliest unreadable task there is
    (`tests/test_record_refs.py`), and a guard that misses it costs the night
    its whole ledger."""
    if strict:
        if isinstance(exc, UnreadableTask):
            raise exc
        raise UnreadableTask(f"task {key} is unreadable: {exc}") from exc
    done.skipped.append((key, f"{type(exc).__name__}: {exc}"))


def _creation_order(
    record: Record, ledger: Ledger, strict: bool, done: Fold
) -> list[str]:
    """Task keys oldest first, by the time their `task_created` fact was
    appended. A record key is random hex, and `ORDER BY t.task_id` is read as
    a chronology by `queue_lines` and `tasks_by_spec`, so folding in key order
    scatters a rebuilt ledger through time.

    A second read rather than a corpus held in memory: the 118 tasks measured
    on 2026-09-20 carry 33.9 MB of fact JSON, which parses into several times
    that as `Fact` objects. Batched reads put the whole two-pass fold at 9.94 s,
    so the pass costs about 5 s and the memory is the worse half of the trade
    (`docs/evidence/2026-09-20-fold-rebuild-time.md`)."""
    dated = []
    for key in sorted(record.task_keys()):
        try:
            facts = _facts_of(record, key)
        except Exception as exc:
            ledger.fold_task(key, [])
            _skipped(key, exc, strict, done)
            continue
        created = next(f for f in facts if f.kind == "task_created")
        dated.append((created.at, key))
    return [key for _, key in sorted(dated)]
