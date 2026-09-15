---
id: 83
title: A mutant that matches at the base commit kills the task before it starts
status: done
tier: 1
specs: [SA-0063, SA-0064]
prs: []
commits: []
cites: [§2.1, §5.4]
related: [69, 82]
---

## Problem

**Status: done, 2026-09-08 (#166).** `run_witness` hoists
`tests_result.collected` and hands it to `witness_gate`, which sets a criterion
aside as unproven *before* `mutate` when its witness is not in that list —
nothing is written for a question that cannot be answered. Compared, never
parsed: an opaque string against a list the repo's own `tests` gate produced,
so the gate still knows no framework (§2.1). Answered per criterion, unlike
`run_witness`'s subset probe, which must condemn the whole gate.

**On the question this item asked to settle at the same time** — whether the
witness gate should run at base at all, since §5.4 already requires a
non-`preserves` witness to fail there: it still runs. Not asking is only
correct for the `preserves` case read backwards, and the gate has a second job
at base that survives the argument — a mutant that matches at base is exactly
what item 82's advice produces, and a spec whose mutant matches nothing there
is a spec whose mutant is pinned on text the task itself invents. Skipping the
base run would lose both signals to save a pass that now costs nothing. Left
running deliberately, recorded here rather than reopened.

Measured 2026-09-07, running `SA-0064`. Exit 2, `PREFLIGHT_FAILED`, no agent
turn bought and nothing exported:

```
baseline: … witness=error …
baseline errored in ['witness'] — the toolchain is broken, not the code
summary: the `tests` gate errored under
  tests/test_session.py::test_a_protected_path_alone_asks_for_notes's mutant
  — pytest exited 4 with no parsed failures
```

Declared mutants are applied at the **base commit** as well as at head.
That criterion's mutant named text already in `saffron/cell/session.py`, so at
base it applied cleanly — and then the gate ran the witness that mutant is
supposed to kill, which does not exist at base, because writing it is the task.
`pytest` exits 4 for a node id it cannot collect, the gate reads an exit it
cannot parse as `error`, and `error` aborts the attempt (§5.4). Charged to
nobody, which is the one mercy.

**This is the ordinary shape of a bug-fix spec, not an exotic one.** A spec that
edits existing code pins its mutant on existing code and declares a new witness
for it. Every such spec dies at baseline. `SA-0063` survived only because both
of its mutants named text that did not exist at base either — they matched zero
times, the gate reported `skip`, and nothing ran. The mechanism has therefore
never been exercised by a mutant that matches at base, and the first one to try
it took the task down.

It also closes off the escape route item **82** recommends. That item's advice —
pin text the existing code already determines, so nothing has to be disclosed —
produces exactly this combination. As things stand a spec author can have an
honest mutant or a runnable spec.

**Done looks like** a witness the suite cannot collect reported as `skip` rather
than `error`: "there is no witness to kill" is unproven, not broken, and it is
the *expected* state at base for every new test. `run_witness`'s pre-flight
probe already exists to tell "this repo's `tests` gate cannot be filtered" apart
from "the mutant killed its witness" (item **69**), and this is a third case it
does not name. Worth deciding at the same time whether the witness gate should
run at base at all: for a non-`preserves` witness the answer looks like no by
construction — §5.4 already requires such a witness to fail at base — and the
cheapest correct fix may be to not ask the question rather than to widen the
answer.
