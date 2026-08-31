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

Together they offered eleven finished specs as candidates. At roughly $13 a
cell that is about $145 of work already in the tree.

`SA-0012` is worth its own sentence: it declares its criteria as a frontmatter
`acceptance:` block with witnesses rather than as markdown boxes, which is the
stronger form `SA-0011` built. A count that reads the markdown list alone
reports it as having none — it has three, and all three pass.

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
| `SA-0012` | `_spec()` in `tests/test_package.py` builds a real `Spec` through `parse_spec`; all three declared witnesses exist and pass. The `SimpleNamespace` uses that remain there stand for `CellOutcome` and a fixture bundle, not for `Spec` |
| `SA-0020` | The dependency gate: `_dependency_refusal` in `saffron/scheduler.py`, admitting a parent that `MERGED` and naming what it read otherwise. Implemented by hand, so **no cell task records it** — which is why the scan kept offering it, and is itself the gap noted below |
| `SA-0011` | `saffron/gates/core/criteria.py`, `tests/test_criteria.py`, `Criterion` parsing in `intake.py` |
| `SA-0014` | `discover_specs()` exists; its task is `MERGED` at an older `spec_sha` |

`SA-0009` is not here: its task is `EXHAUSTED`, which the filter already reads,
so the scan does not offer it.

**A third cause, found on 2026-08-31 when `SA-0020` shipped.** Work done *by
hand* writes no task at all — cells are the only thing that creates one. So a
spec a human implemented looks exactly like a spec nobody has run, and its
dependents stay refused however plainly its code sits in `main`. The gate asks
whether the parent's work is in the default branch and answers from a record of
cell runs; for a repo where humans and cells both commit, those are different
questions. Retiring the spec here says what the ledger cannot.

**Do not edit a spec in this directory.** An edit moves its `spec_sha`, and the
sha is what the ledger's rows are keyed on.
