# Four adequacy vacuity probes, and which of them anyone has actually run

`docs/BACKLOG.md` item 91. The adequacy lens's pass-1 corpus run named four vacuity probes
(`CONTEXT.md` §4's term for a find-and-replace edit a lens names) and the original 2026-09-09
spike applied all four at their fixture heads, reporting all four green. That spike's own
record lives only in a scratch session ledger, not under `docs/evidence/`, and is the entire
evidential basis for `docs/superpowers/specs/2026-09-09-mutation-verified-capability-design.md`.
This file is the record item 91 asks for.

**Provenance, stated plainly, per mutation:**

- `pr_body.py:391` (`f76931df`, SA-0063) and `batch.py:72` (`91f56c69`, SA-0050) — reported
  independently reproduced during review of this branch on 2026-09-09, to the figures below.
  **Not re-run for this file.** No command transcript or full suite-output line for that
  review reproduction was found under `docs/evidence/`, in this task's session records
  (`.superpowers/sdd/2026-09-09-mutation-verified-capability/`), or anywhere else in this
  repository — only the summary figures, already public in `docs/BACKLOG.md` item 91 and the
  design spec. Where the spec itself quotes exact query text and an exact traceback (the
  `batch.py:72` case), that quote is reproduced below and attributed to the spec, not
  measured again here.
- `create_run` / `batch_id` (`ledger.py:364`) and `batches.status` / `NOT NULL` (`ledger.py:43`)
  — both at `f9f007c4`, SA-0045 — **reproduced in this task**, 2026-09-09, in a detached
  worktree at `/tmp/spike-f9f007c4`. Full command, output, and dirty-file proof below.
- The original spike's own four runs (all fixture heads) are not independently recorded
  anywhere; this file does not attempt to reconstruct them.

---

## 1. `create_run` inserts `None` for `batch_id` — `f9f007c4` (SA-0045)

**Reproduced in this task, 2026-09-09.**

**Recorded claim** (`~/.saffron/lens-scoring/corpus-calibration/SA-0045/run-1.json`, `adequacy`
lens, `saffron/ledger.py:364`, verbatim):

> create_run's new batch_id parameter is threaded into the INSERT, but no test anywhere in the
> repo ever calls create_run with a non-None batch_id and checks it lands in the row — every
> call site (tests/test_ledger.py, test_cli.py, test_package.py, test_scheduler.py,
> test_reconcile.py, saffron/cell/session.py, saffron/replay.py) either omits the argument or
> the one new test only exercises the default-None path. The smallest edit that keeps every
> current test green while breaking the feature is hardcoding the insert tuple to
> `(repo_id, base_sha, None)` regardless of the batch_id argument — no gate or test in this
> diff would notice, and the bug would only surface once SA-0049 starts passing real batch_id
> values.

**Edit applied**, `saffron/ledger.py`, inside `create_run` (line 367 before the edit):

```diff
-            (repo_id, base_sha, batch_id),
+            (repo_id, base_sha, None),
```

**Setup:**

```
git worktree add --detach /tmp/spike-f9f007c4 f9f007c4
```

`git -C /tmp/spike-f9f007c4 status --porcelain` after the edit:

```
 M saffron/ledger.py
```

**Command:**

```
cd /tmp/spike-f9f007c4 && uv run pytest -q
```

**Suite output, final line, verbatim:**

```
1250 passed, 20 deselected in 87.23s (0:01:27)
```

Matches the ledger's recorded `1250 passed` exactly. File restored (`git checkout --
saffron/ledger.py`) before the next mutation; `git status --porcelain` reported clean.

---

## 2. `batches.status` gains `NOT NULL` — `f9f007c4` (SA-0045)

**Reproduced in this task, 2026-09-09.**

**Recorded claim** (`~/.saffron/lens-scoring/corpus-calibration/SA-0045/run-1.json`, `adequacy`
lens, `saffron/ledger.py:43`, verbatim):

> The schema comment asserts the CHECK is deliberately satisfied by NULL so a still-running
> batch's row (status unset) is valid, but no test ever inserts a batches row with
> status omitted/NULL. Adding `NOT NULL` to the status column would keep
> test_a_batch_status_outside_the_four_stop_reasons_is_rejected and the other batches tests
> green (they always supply a valid status) while breaking the documented ability to record a
> batch before it has ended, which the eventual writer in SA-0049 depends on.

**Edit applied**, `saffron/ledger.py`, in the `batches` table's `SCHEMA` string (line 43 before
the edit):

```diff
-    status        TEXT CHECK (status IN ('DRAINED', 'BUDGET', 'UNTIL', 'INFRASTRUCTURE'))
+    status        TEXT NOT NULL CHECK (status IN ('DRAINED', 'BUDGET', 'UNTIL', 'INFRASTRUCTURE'))
```

Applied in the same worktree as mutation 1, after restoring `saffron/ledger.py` to the
unmutated `f9f007c4` state. `git -C /tmp/spike-f9f007c4 status --porcelain` after the edit:

```
 M saffron/ledger.py
```

**Command:**

```
cd /tmp/spike-f9f007c4 && uv run pytest -q
```

**Suite output, final line, verbatim:**

```
1250 passed, 20 deselected in 77.68s (0:01:17)
```

Matches the ledger's recorded `1250 passed` exactly. File restored and worktree removed
(`git worktree remove --force /tmp/spike-f9f007c4`) after this run.

**Both `f9f007c4` claims reproduce to the recorded figure. Neither differs.**

---

## 3. Drop `run_id > ?` from the query at `batch.py:72` — `91f56c69` (SA-0050)

**Reported reproduced during review on 2026-09-09. Not re-run for this file.**

**Recorded claim** (`~/.saffron/lens-scoring/corpus-calibration/SA-0050/run-1.json`, `adequacy`
lens; the finding itself anchors at `tests/test_batch.py:365`, and its text names the edit at
`saffron/batch.py:72` — verbatim):

> No test exercises the scoping condition `_attach_runs_minted_since` (batch.py:72) exists
> for: excluding pre-existing `batch_id IS NULL` runs left behind by `saffron cell` or
> `replay.py`. Every ledger fixture in this file is fresh per test, and the only
> exception-path test (`test_a_crash_after_real_spend_still_counts_against_the_next_budget_gate`)
> never seeds an unrelated orphan run before the crash. Changing the query at batch.py:72 from
> `WHERE run_id > ? AND batch_id IS NULL` to `WHERE batch_id IS NULL` (dropping the
> `run_id > ?` filter, leaving `high_water` unused) would keep every test in this file green,
> yet in production it would silently fold an unrelated pre-existing run's spend into the
> batch the first time a real ledger (which the module's own docstring says accumulates such
> rows) hits a crash — exactly the corruption the docstring says this scoping prevents.

The design spec (`docs/superpowers/specs/2026-09-09-mutation-verified-capability-design.md`,
"Caching: no" precursor section on `collateral`) already carries a more detailed measurement
than the bare `1292 passed` in `docs/BACKLOG.md` item 91, quoted here verbatim rather than
re-derived:

> SA-0050's recorded adequacy claim names its edit as dropping `run_id > ?` from the query at
> `batch.py:72`. Applied literally at `91f56c69` —
> `"SELECT run_id FROM runs WHERE run_id > ? AND batch_id IS NULL"` becomes
> `"SELECT run_id FROM runs WHERE batch_id IS NULL"`, leaving the `(high_water,)` binding in
> place — the suite goes **2 failed, 1290 passed** with
> `sqlite3.ProgrammingError: Incorrect number of bindings supplied` at `batch.py:71`. The
> *intended* mutation, which also removes the binding, survives green at **1292 passed**.

So the figure `docs/BACKLOG.md` item 91 and the design spec's table report (`1292 passed`) is
the *intended* edit — the claim's find-and-replace with the now-unused `(high_water,)` binding
also removed, not merely the `WHERE` clause change applied word-for-word. Applied literally,
without also dropping the binding, the same edit is a `collateral` failure (`2 failed, 1290
passed`), not a survived vacuity. Applying a claim's edit as-intended rather than literally
changes the outcome, which is exactly why the two `f9f007c4` claims above were applied by
reading each claim in full rather than by guessing at an edit judged equivalent to it.

This document does not carry a command transcript or a full pytest summary line for either
the literal or the intended `91f56c69` run — those numbers are the spec's, not this task's.

---

## 4. `safe = neutralize(text)` → `safe = text` at `pr_body.py:391` — `f76931df` (SA-0063)

**Reported reproduced during review on 2026-09-09. Not re-run for this file.**

**Recorded claim** (`~/.saffron/lens-scoring/corpus-calibration/SA-0063/run-1.json`, `adequacy`
lens; the finding itself anchors at `tests/test_report.py:108`, and its text names the edit at
`saffron/report/pr_body.py:391` — verbatim):

> test_notes_cannot_move_a_status_or_a_gate_result puts '@maintainer' and 'Fixes #12' into the
> notes text but only asserts that the body content *before* the notes heading is unaffected
> (`head == plain`); it never inspects the rendered notes section itself for the zero-width
> neutralization `_notes` is supposed to apply. Replacing `safe = neutralize(text)` with
> `safe = text` at saffron/report/pr_body.py:391 leaves every notes test (including this one
> and test_notes_render_as_the_implementers_own_and_unadjudicated) green while '@maintainer'
> and 'Fixes #12' reach GitHub verbatim in the notes section — the exact mention/auto-close
> side effect acceptance criterion 2 requires be neutralized, and nothing in the diff's tests
> would catch its silent removal.

`docs/BACKLOG.md` item 91 and the design spec's table both give only the bare figure
(`1502 passed`) for this one — no query text, no traceback, no fuller detail exists in either
document to quote. This file carries the same bare figure and no more: no command, no full
suite-output line, and no independent verification of `1502` beyond the two documents that
already assert it.

---

## Summary

| Vacuity probe | Fixture head | Recorded (spike) | This file | Who / when |
|---|---|---|---|---|
| `pr_body.py:391` | `f76931df` (SA-0063) | 1502 passed | 1502 passed, unverified here | review, 2026-09-09 |
| `batch.py:72` | `91f56c69` (SA-0050) | 1292 passed | 1292 passed (intended edit), unverified here; literal edit is 2 failed, 1290 passed per the spec | review, 2026-09-09 |
| `create_run`/`batch_id` | `f9f007c4` (SA-0045) | 1250 passed | **1250 passed, 20 deselected in 87.23s** | this task, 2026-09-09 |
| `batches.status`/`NOT NULL` | `f9f007c4` (SA-0045) | 1250 passed | **1250 passed, 20 deselected in 77.68s** | this task, 2026-09-09 |

The two `f9f007c4` claims reproduce to the recorded figure exactly. The two reported reproduced
during review are transcribed here, not re-verified — this file does not have their command or
output, only the summary already public in `docs/BACKLOG.md` and the design spec (plus, for
`91f56c69`, the fuller quote above). The original spike's own runs, for all four, remain
unrecorded anywhere.
