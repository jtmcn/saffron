# Shipped specs

Specs whose work is in `main`. They live here rather than in `.saffron/specs/`
because `intake.discover_specs` globs `*.md` non-recursively, so a spec in this
directory is not offered to the scan — while the record it carries stays in the
tracker and in `git log`.

**Why this directory exists.** The scan filters a spec out when the ledger holds
a task for it at the current `spec_sha` in a done state (`DESIGN.md` §4.2.1).
Two things defeat that filter, and both were measured on 2026-08-31:

- **Work that predates task recording.** The ledger holds no task at all for
  `SA-0001` through `SA-0012` bar `SA-0009`, though `DESIGN.md`'s own status line
  reports `SA-0001` built and cites `SA-0004`'s run at $3.88 across 65 turns.
  A filter keyed on rows cannot filter on rows that were never written.
- **A spec edited after its task merged.** `SA-0014`'s task merged at `spec_sha`
  `0ed4293`; the file reads `5162dee` today, because `bf5a93e` corrected a
  sentence in it. §4.2.1 keys on `spec_sha` deliberately so a *rewritten* spec
  runs again — nothing distinguishes a rewrite from a typo fix.

Together they offered ten finished specs as candidates. At roughly $13 a cell
that is about $130 of work already in the tree.

**Retiring is not a ledger write.** Recording a task for work that never ran
through a cell would put a false row in the audit trail, which is the one thing
the ledger may not contain. Moving the file states the same fact where it costs
nothing.

| Spec | Evidence the work is in `main` |
|---|---|
| `SA-0001` | `ontology/saffron.ttl`, `ontology/queries/` (5 `.rq`), `RATIONALE.md`, `shapes/`, six tests under `tests/ontology/` |
| `SA-0002` | `saffron/gates/core/size.py`, `tests/test_size.py` |
| `SA-0003` | `attempts` table in the ledger schema; 27 references in `saffron/ledger.py` |
| `SA-0004` | `saffron/gates/core/integrity.py`, `tests/test_integrity.py` |
| `SA-0005` | `effective_risk` and advisory gates wired in `cell/session.py`; a live baseline suite reports `size=pass` |
| `SA-0006` | `size_gate(diff, spec_type, touches, …)` takes `touches`, and `size.py` carries the binary-section handling |
| `SA-0007` | `phases/package.py` passes `outcome.effective_risk` and `advisory_gates`, and the queue line's `risk` is the effective tier |
| `SA-0008` | `rebut.sustained_blockers()`; `QueueLine.sustained`, ranked by `sort_key` |
| `SA-0010` | `rebut.unkept_fixes()`; `QueueLine.unkept`, ranked in the same bucket |
| `SA-0011` | `saffron/gates/core/criteria.py`, `tests/test_criteria.py`, `Criterion` parsing in `intake.py` |
| `SA-0014` | `discover_specs()` exists; its task is `MERGED` at an older `spec_sha` |

`SA-0009` is not here: its task is `EXHAUSTED`, which the filter already reads,
so the scan does not offer it.

**Do not edit a spec in this directory.** An edit moves its `spec_sha`, and the
sha is what the ledger's rows are keyed on.
