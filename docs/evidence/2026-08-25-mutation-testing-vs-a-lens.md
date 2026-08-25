# Would the tests catch this code being wrong? — one defect, four candidates

Research record for issue #33, under map #25, against `docs/BACKLOG.md` item 6.
The question: is *"would the tests catch this code being wrong"* something a
prompted lens can answer, or does it need a mutation-testing tool?

Everything below is dated 2026-08-25 and was run on this machine (darwin,
11 cores, idle unless noted) against this repository. **Measured** and
**reasoned** are labelled per claim, per `CLAUDE.md`.

The four candidate answers the ticket names are prompt / tool / coverage / none.
A fifth exists and the ticket does not mention it: `DESIGN.md` §5.4's `revert`
gate, which is specified, unbuilt, and was written to answer exactly this
question. It is covered in section 6.

**Recommendation: prompt** — but not for the reason the ticket expects. A tool
does find this defect (`mutmut`, measured, 74 s). It just cannot be run in a
gate loop here. Section 7.

---

## 1. The motivating defect, reproduced

`SA-0002` (commit `e15f6e3`, merged as PR #15) added `saffron/gates/core/size.py`
— 97 lines — and `tests/test_size.py` — 147 lines, 16 tests. Inside
`_changed_lines`, line 51 resets the header flag at each new file block:

```python
count = 0
in_headers = True                    # line 48: before the first "@@"
for line in split_lines(diff):
    if line.startswith("diff --git "):
        in_headers = True            # line 51: a new file block
        continue
```

**Measured.** Deleting line 51 at `e15f6e3` leaves all 16 tests passing
(`16 passed in 0.05s`). Every test fixture builds a single-file diff, so the
reset is never the line that matters; on a two-file diff the second file's
`--- a/path` / `+++ b/path` are counted as content, two lines per file.

That is the defect the ticket exists for. Sections 2–5 ask each candidate
whether it finds it.

---

## 2. Coverage — the cheapest option, and it reports nothing

This was the single most decision-relevant question in the ticket. The answer is
a clean negative.

**Measured**, at `e15f6e3`:

```
coverage run --branch --source=saffron.gates.core.size -m pytest tests/test_size.py

Name                         Stmts   Miss Branch BrPart  Cover   Missing
saffron/gates/core/size.py      26      0     12      1    97%   58->49
```

Zero missed statements. One partial branch, `58->49`, is the back-edge out of
`count += 1` at the bottom of the loop — not the header reset. Line 51 is
executed by every single-file test in the file.

A diff-scoped coverage gate computes *(lines the diff added) ∩ (lines no test
executed)*. On this diff that intersection is **empty**, so the gate reports
nothing at all — not a weaker version of the finding, no finding.

**Reasoned**, and the general form: the defect is not an unexecuted line, it is
an executed line whose *effect* no test observes. Coverage cannot see that
distinction by construction, and it is the distinction the whole question is
about. Coverage is the cheap 80% of a different question ("did the diff add dead
code?"), which is worth having and is not this.

`DESIGN.md` §5.4 already rules `coverage` advisory at every tier, on the separate
argument that a blocking coverage gate rewards tests that execute without
asserting. This measurement is a second, independent reason and it points the
same way.

**One correction to `docs/BACKLOG.md`, item 6**, which is where this ticket comes
from. It calls line 51 "the uncovered line". Measured, it is covered — every one
of the 16 tests executes it. Nothing downstream turns on the word, but the word
is the whole reason coverage looked like the cheap option, and it is not.

---

## 3. The mutation-testing landscape, as it stands

**Measured**, from PyPI's JSON API and the GitHub API on 2026-08-25:

| Tool | Latest release | Repo last pushed | Verdict |
|---|---|---|---|
| `mutmut` 3.7.0 | 2026-07-31 | 2026-08-17 | alive |
| `cosmic-ray` 8.7.0 | 2026-08-09 | 2026-08-09 | alive |
| `mutahunter` 1.3.2 | 2025-04-17 | 2025-04-17 | 16 months stale |
| `mutatest` 3.1.0 | 2022-02-20 | 2023-02-17 | dormant |
| `pytest-mutagen` 1.3 | 2020-07-24 | — | dead |
| `mutpy` 0.6.1 | 2019-11-17 | — | dead |

Nothing has displaced the two. `mutahunter` is the interesting near-miss — it
generates mutants with an LLM through `litellm`, which is the hybrid this ticket
is implicitly asking about — and it has not been touched since April 2025 and
needs a second provider key inside the loop. Not a candidate.

What each needs to run: `cosmic-ray` needs a TOML config naming a `module-path`
and a `test-command`, and keeps its session in a SQLite file. `mutmut` needs
`source_paths` in `setup.cfg`/`pyproject.toml`, copies the project into a
`mutants/` directory, and depends on `libcst` (a Rust toolchain if no wheel
exists for the architecture — its README calls out `x86_64-darwin`).

### 3.1 Diff scoping — the binding constraint

The ticket is right that this decides the cost question, and the answer is that
**one of the two can do it**.

**`cosmic-ray`: yes.** It ships `cr-filter-git` and `cr-filter-lines` as console
entry points. `cr-filter-git` runs `git diff --relative -U0 <branch> .`, parses
`@@` headers into a set of added line numbers per file, and marks `SKIPPED`
every mutation whose `start_pos`–`end_pos` row range does not intersect that set
(source: `cosmic_ray/tools/filters/git.py`, 8.7.0).

**Measured**, on `main` at `f4829ad` with `module-path = "saffron"`:

| Step | Result |
|---|---|
| `cosmic-ray init` over the whole package | **5091 mutants**, 4.99 s |
| `cr-filter-git`, base = PR #24's merge-base | 1.89 s |
| remaining | **39 mutants**, all in `saffron/gates/core/size.py` |

A 131× reduction, in under seven seconds. So "a mutation run over all of
`saffron/` does not fit a gate loop" is true and is not the constraint it looked
like — the scoping exists and it is one extra command.

One detail in that table is a finding rather than a footnote. PR #24 changed
**two** source files: `saffron/gates/core/size.py` and 15 lines of
`saffron/cell/session.py`. All 39 mutants the filter kept are in the first. The
behaviour-carrying line in the second is

```python
blocking="size" not in advisory_gates,
```

and `cosmic-ray` generated **zero** mutants for it (measured; `session.py` has
704 mutants in total and none between lines 650 and 730 other than on untouched
lines). The reason is in the source: `ComparisonOperators` in
`cosmic_ray/operators/comparison_operator_replacement.py` enumerates
`== != < <= > >= is "is not"` and **not** `in` / `not in`, and cosmic-ray has no
string-literal operator either. `mutmut` would mutate it — its `_keyword_mapping`
carries `In`↔`NotIn` — so the two catalogues have complementary holes rather
than a shared floor.

That line is the entire point of PR #24, and the review-fix commit that followed
it (`accd8eb`, "the blocking switch bought less than its test claimed") is a
test-adequacy defect *on that switch*. The one tool that can scope to changed
lines had nothing to say about the only changed line that mattered.

**`mutmut`: no, not to lines.** Its finest selector is a mutant-name glob —
`mutmut run "my_module.my_function*"` — plus `only_mutate` / `do_not_mutate`
path globs and `mutate_only_covered_lines`. Verified against the CLI in the
installed `mutmut/__main__.py` (commands `run`, `results`, `show`, `apply`,
`browse`, `tests_for_mutant`, `print_time_estimates`, `export_cicd_stats`;
`run` takes only `--max-children` and mutant-name globs) and against the README.
Scoping to a diff therefore means mapping changed lines to changed *functions*
and passing their names — coarser, but workable. One further limit: mutmut 3
only mutates code **inside functions** (its README: "If you want to mutate code
outside of functions, you can try using mutmut 2"), so module-level constants
are invisible to it. That matters below.

### 3.2 Output, and whether a survivor anchors to a diff line

**Yes, for both, and comfortably.** `cosmic-ray`'s session is a SQLite database:
`mutation_specs` carries `module_path`, `operator_name`, `occurrence`,
`start_pos_row/col`, `end_pos_row/col` and `definition_name`; `work_results`
carries the outcome and a **unified diff of the mutation itself**. Reporters:
`cr-report`, `cr-html`, `cr-xml`, `cr-rate`. `mutmut show <mutant>` likewise
prints a diff, and mutant names are `module.function__mutmut_N`.

A survivor is therefore `(file, line, minus/plus)`, which is precisely what
§5.5's anchoring needs. **Anchoring is not the obstacle here.**

---

## 4. Would mutation testing have caught the defect? `mutmut` yes, `cosmic-ray` no

This section reverses a conclusion an earlier draft of this record reached from
the operator catalogues alone. Running the tools contradicted it, which is the
house rule working.

**Measured**, from source. `cosmic-ray` 8.7.0's operators
(`cosmic_ray/operators/`): binary, comparison and unary operator replacement,
boolean replacer, break/continue, exception replacer, keyword replacer, no-op,
number replacer, remove-decorator, variable inserter and replacer,
zero-iteration-for-loop. `mutmut` 3.7.0's operator table
(`mutmut/mutation/mutators.py`): number, **string**, name (`True`↔`False`,
`deepcopy`→`copy`), assignment to `None`, augmented assignment, unary-op
removal, dict-kwarg rename, call-argument removal, string-method swaps, lambda,
keyword mapping, operator swap, match-case dropping.

**Neither ships a statement-deletion operator**, and the defect is a statement
deletion — which is where the reasoning stopped, and where it was wrong.

### 4.1 `cosmic-ray` misses it

The nearest mutant it has for line 51 is `True`→`False`. **Measured**: killed —
9 of the 16 tests fail, because on a single-file diff `in_headers = False` at
the `diff --git` line lets the very next two header lines be counted. The
defective line reports clean.

**Measured**, `cosmic-ray` against `size.py` at `e15f6e3` with
`test-command = "python -m pytest tests/test_size.py -q"`: 30 mutants, 6.16 s,
**7 survivors** —

- 6 × `NumberReplacer` on `_CEILINGS = {"bug": 300, "feature": 600, "refactor": 1000}`
  at line 15. They survive because every ceiling test reads its expected value
  out of `_CEILINGS` itself (`ceiling = _CEILINGS["bug"]`), so no test pins
  §5.4's table. A real finding — and one `mutmut` cannot produce, since line 15
  is module-level.
- 1 × `ReplaceTrueWithFalse` at **line 48** — the *initializer*, one line above
  the defect, surviving because line 51 masks it.

So `cosmic-ray` points at line 48 when the defect is at line 51, and the finding
it files is a different untested behaviour that happens to be this one's mirror.
It found a neighbour, not the thing.

### 4.2 `mutmut` finds it, through the string operator

`mutmut` mutates string literals, `cosmic-ray` does not — and the statement that
was deleted lives inside a branch whose guard *is* a string literal. Mutating
`"diff --git "` to `"DIFF --GIT "` kills the branch entirely, which is the same
observable change as deleting its body.

**Measured**, twice. `mutmut` reports it: `x__changed_lines__mutmut_7` and
`__mutmut_8` both **survive**. And applied by hand at `e15f6e3`:

```
if line.startswith("DIFF --GIT "):     # branch now dead
16 passed in 0.05s
```

That is the defect, found by a tool, with a line number and a diff. The earlier
draft's "no tool generates this mutant" was false.

`mutmut` at `e15f6e3`, whole module: **70 mutants, 74.24 s** end to end
(including the coverage stats pass), **10 survivors**. Two of the ten are the
defect; three more point at the same `in_headers` pair from the other side
(`True`→`None`, `True`→`False` on the initializer, `False`→`None` on the `@@`
branch); five are in `size_gate`.

### 4.3 Cost, and what each run actually cost here

`DESIGN.md` §5.4 already rejects mutation testing on cost, in `revert`'s own
paragraph:

> This replaces mutation testing, which was the obvious choice and doesn't fit:
> `mutmut` reruns the suite per mutant, a Timescale-backed suite takes minutes
> per run, and 15 mutants is an hour inside a 2-core cell competing with two
> siblings inside an 8-hour window that also has to fit 10–15 tasks. It would
> break N3 outright.

One clause of that is now out of date: `mutmut` 3 does **not** rerun the suite
per mutant. It collects coverage stats once, then runs only the tests that reach
the mutated function, in parallel. The conclusion survives for `cosmic-ray` and
not for `mutmut`.

**Measured** on this repository:

| Run | Mutants | Wall clock | Survivors |
|---|---|---|---|
| `uv run pytest -q` (the baseline) | — | **55.76 s** | 646 passed, 16 deselected |
| `cosmic-ray exec`, 39 diff-scoped mutants of PR #24, full suite as test-command, `local` distributor | 39 | **1444 s (24 min 4 s)** | 11 |
| `mutmut run "saffron.gates.core.size.*"` at `e15f6e3` (`tests/test_size.py` as the test set) | 70 | **74.2 s** | 10 |
| `mutmut run "saffron.gates.core.size.*"` at `f4829ad` (the whole suite as the test set) | 122 | **274.5 s** | 12 |

`cosmic-ray`'s `local` distributor is sequential — its own docstring says so —
so that 24 minutes is 37 s per mutant, and parallelism means standing up the
`http` distributor plus `cr-http-workers` inside the loop. Against §7.1's
budget (~45–60 min per task, ~8 h per batch, N3), that is roughly a doubling of
a task's wall clock for the review of one patch, in a 2-core cell competing with
siblings. `mutmut`'s numbers fit the window comfortably.

**So cost is not the argument any more.** Two other things are.

**The survivor sets are mostly noise.** Of `cosmic-ray`'s 11 survivors on PR
#24's diff, **10 are the same annotation** — `def _unreadable_declared_path(...) -> str | None:`
— with the `|` mutated as a bitwise operator into `//`, `-`, `^`, `&`, `/`, `+`,
`%`, `*`, `>>`, `<<`. No test can kill any of them. One survivor is real: `or`
→ `and` on `binary.group(2) or binary.group(1) or ""`, which is the deleted-file
fallback the lens also flagged (§5). So 24 minutes bought one finding and ten
things to discard, and every one of the eleven anchors under §5.5 — the noise
would arrive as findings. `mutmut` filters invalid mutants with an optional
`type_check_command`, which is the shape of the fix, and it is one more thing to
configure per repo.

**`mutmut` does not run on this repository as it stands.** Its execution model
copies the project into `mutants/` and rewrites every source file into mutation
trampolines. Measured, three configuration iterations to get past it:

1. `tests/test_agent_runner.py` loads `images/agent_runner.py` → `also_copy`.
2. `tests/test_context.py` reads `CONTEXT.md` from the repo root → `also_copy`
   again, plus `DESIGN.md`, `.saffron/`, `docs/`.
3. `tests/test_saffron_gates.py` runs Saffron's own `format` gate over the tree
   and gets `37 files would be reformatted`, because the tree it is now gating
   is mutmut's rewritten copy. There is no `also_copy` for this one — the run
   above deselects the test.

That third is structural, not a config nit: a repo whose suite gates its own
tree cannot run `mutmut` over that suite without excluding the part that does
the gating. It is fixable, and fixing it means a repo declaring which of its own
tests to switch off — the kind of per-repo configuration §2.1 keeps pushing out
of core.

---

## 5. Would a prompted lens have caught it? Three times out of three

**Measured.** A fresh `claude -p --model sonnet` session, no tools, given a
test-adequacy remit and `SA-0002`'s diff verbatim (10.5 KB) — the shape §5.5
already uses for a lens: host-invoked, fresh, sees only what it is handed. The
prompt names no file, line, or defect; it asks, for each behaviour the source
hunks add, whether removing or inverting it would fail a test in the diff, and
tells the session to say so and stop if everything is covered.

n = 3. **All three named the defect.** Verbatim, trial 2:

> `saffron/gates/core/size.py:50-52` — the `in_headers = True` reset on a new
> `diff --git ` block is untested; no test builds a diff touching more than one
> file, so removing the reset (which would let a second file's
> `--- a/`/`+++ b/` lines get miscounted as content) wouldn't fail anything.

That is the defect, the reason it is invisible, and the input that exposes it.
Trial 1 added the generalisation — "`_diff()` always emits exactly one
`diff --git` block" — and trial 3 restated it. Every finding in every trial
cited a file and a line inside a diff hunk, so all of them anchor under §5.5
without the second, identifier-based anchoring target.

The other findings across the three trials, all of which check out against
`tests/test_size.py`: `Failure(file="")` never asserted (3/3); the fail-path
`Failure.message` text never asserted (2/3); the pass-path summary never
asserted (1/3); no fixture contains a context line, so a gate that counted every
non-header line would pass (1/3); the `split_lines`-over-`splitlines` rationale
has no test feeding it a raw `\r` (1/3).

Neither existing lens raised any of this on the real `SA-0002` review — which is
what the ticket records — but neither was asked to: §5.5's lens 1 is correctness
and data semantics, lens 2 is contract and schema. The evidence says the remit
was missing, not that the mechanism cannot answer.

**Control, measured.** The same prompt against `SA-0006`'s factory commit
(`9163213`, 308 diff lines), n = 2. Neither trial said "everything is covered";
both produced specific anchored findings — the `binary.group(1)` deleted-file
fallback is never exercised (2/2), glob patterns in `touches` are never tested
(1/2), the `session.py` wiring change has no test in the diff (1/2), two binary
blocks in one diff are never tested (1/2). Independently: the review-fix commit
that followed, `accd8eb`, is itself a test-adequacy defect on that same patch —
"The session test passed only because the default test policy is `gates: {}`,
which makes integrity skip: green for a reason unrelated to what it asserted" —
which is the category the lens was pointing into.

Worth putting beside §3.1: the `session.py` wiring line the lens flagged in that
control is the same line `cosmic-ray` could not generate a single mutant for.
The two candidates disagreed about the most consequential line in that patch,
and only one of them said anything.

**What this does not establish.** n = 5 sessions total, one repo, two diffs, one
file each. Sonnet, not whatever a real lens would run. The prompt was written
after the defect was known: it names nothing specific, but I cannot rule out
that I chose a framing that suits it — the control on an unrelated diff is the
partial answer to that, not a complete one. And no false-positive rate was
measured. The control shows the lens does not stay silent, which is the failure
mode §5.5 warns about ("a critic prompted to find problems will always find
problems"); whether its findings are *worth* the operator's adjudication is the
drop-rate-and-adjudication question §5.5 already has machinery for, and one this
ticket cannot settle.

---

## 6. The option the ticket does not name: `revert`

`DESIGN.md` §5.4 specifies a `revert` gate — "the anti-theater gate, and the
best cost/value ratio in the system": stash the source hunks, keep the test
hunks, run only the new and changed tests, require them to **fail**. One extra
test run. §5.5 says outright that "lens #3 in a naive design would be 'test
quality' — but the `revert` gate now answers that mechanically and for free",
and §11 already ruled this exact trade: *test quality → `revert`, rejected
alternative mutation testing, "coarser signal; fits the window, costs one test
run"*.

Two things follow, and they cut in opposite directions.

**It is not built.** §5.4 says so in passing ("a test still collected but gutted
belongs to `revert`, which is not built yet") and §9 lists it under v1. So the
mechanism the design leans on for this question does not exist yet, which is
part of why the question keeps coming back.

**It would not have caught `SA-0002` either.** *Reasoned, not measured:*
`SA-0002` added source and tests together, so stashing the source hunks makes
all 16 new tests fail loudly and the gate reports green. `revert` operates at
whole-patch granularity — it catches a test that tests nothing, not one untested
line inside a change that is otherwise well tested. That is a real gap in the
design's current answer, and it is worth recording on #34 whatever it decides
about the lens.

---

## 7. Recommendation: **prompt**

Build the third lens as a prompted lens with a test-adequacy remit. Do not add a
mutation-testing tool now. Do not make a coverage gate answer this.

This is a narrower recommendation than the one this record set out to make.
`mutmut` *does* find the defect, measured, in 74 seconds — so the case against
the tool is not that it cannot see this, and any argument that says so is wrong.
The case is that neither live tool is usable in a gate loop as it stands, and
the lens is.

The four facts that decide it:

1. **Diff-scoped coverage reports nothing on the motivating defect.** Measured:
   26 statements, 0 missed, one unrelated partial branch. The defect is an
   executed line whose effect no test observes, and coverage cannot see that
   distinction by construction. The cheap 80% is 0% here, and this is the
   cleanest negative in the record.
2. **The tool that can scope to a diff and the tool that finds the defect are
   different tools.** Measured. `cosmic-ray` has `cr-filter-git` (5091 → 39
   mutants in seven seconds, survivors carrying file, line and diff) and misses
   the defect, because it has no string-literal operator — and on the next patch
   along it produced no mutant at all for `not in`, the operator that patch
   existed to add. `mutmut` has the string operator that finds it and cannot
   scope below a function, needs three rounds of `also_copy` configuration to
   run on this repository at all, and still needs one of Saffron's own tests
   deselected because its `mutants/` copy fails the repo's own `format` gate.
   Neither hole is fatal on its own; there is no configuration in which one tool
   has neither.
3. **What the runs return is mostly triage.** Measured: `cosmic-ray`'s 24-minute
   run on PR #24's diff returned 11 survivors, **10 of which are the single
   annotation `str | None`** mutated as a bitwise operator, killable by nothing.
   Every one of the 11 anchors under §5.5, so the noise arrives as findings.
   `mutmut` at `e15f6e3` returned 10 survivors of which 2 are the defect. A lens
   whose output needs a second filter before it reaches the operator is a lens
   with an unbuilt component.
4. **A prompted lens named the defect, its cause, and its exposing input, 3/3.**
   Measured, from the diff alone, at the cost of one fresh session — the cost
   §5.5 has already budgeted for a third lens at `risk: elevated`. It is the
   weakest evidence in the record (n = 5 sessions, one repo, two diffs, a prompt
   written after the defect was known), and it is the cheapest thing to try, the
   only one that needs no per-repo configuration, and the only candidate that
   also said something about the `not in` switch on the neighbouring patch.

The ticket's premise — "a critic that reads the diff without mutating it cannot"
— is contradicted. What was missing on `SA-0002` was a lens with that remit, not
a mechanism.

**Three things to carry into #34.**

- Give the lens the diff and see whether that is enough. The five trials worked
  from the diff alone; whether handing it the repo's full test file helps is a
  cheap experiment once the lens exists, and it is the obvious first tuning knob.
- The lens's failure mode is the opposite of coverage's. Coverage under-reports
  and cannot be gamed by prose; a lens over-reports and its findings are claims.
  §5.5's drop rate and the `note`/`concern` split are already the instruments —
  watch both from the first live run. The prompt in the method section says
  nothing about severity, and a test-adequacy lens has more true-but-trivial
  findings available to it than either existing lens.
- `revert` (§6) is still worth building and would not have caught this. The two
  are not substitutes: `revert` asks whether the new tests test *anything*, and
  this lens asks whether they test *each thing*.

**The condition under which this flips.** §11 already anticipates it — "if gate
wall-clock stops being the constraint, mutation sampling on `risk: elevated`
diffs becomes affordable and is strictly stronger." Wall-clock is no longer the
binding constraint for `mutmut`: 74 s on the file, 274 s on the module, both
inside §7.1's window. What binds now is that `mutmut` cannot scope to changed
lines and cannot run over a suite that gates its own tree. If either is fixed —
upstream, or by a repo declaring which of its own tests to exclude — `mutmut`
becomes the stronger answer on this defect and should be revisited. Reach for
`mutmut`, not `cosmic-ray`: the string operator is what found this, and
`cosmic-ray`'s missing `in`/`not in` and its annotation noise are two more holes
to fill on top of the one that matters.


---

## Method, and how to re-run this

Worktrees at `e15f6e3` (the `SA-0002` factory commit) and `f4829ad` (`main`);
tools installed with `uv pip install mutmut cosmic-ray`; nothing was written to
the working tree of the repository itself.

```
# the defect, reproduced
git worktree add --detach /tmp/sa0002 e15f6e3
sed -i '' '51d' /tmp/sa0002/saffron/gates/core/size.py
uv run --directory /tmp/sa0002 python -m pytest tests/test_size.py -q   # 16 passed

# coverage on the same tree, unmodified
uv run --directory /tmp/sa0002 --with coverage python -m coverage run \
    --branch --source=saffron.gates.core.size -m pytest tests/test_size.py
uv run --directory /tmp/sa0002 --with coverage python -m coverage report -m

# the same defect via the guard string, which is what mutmut finds
sed -i '' 's/"diff --git "/"DIFF --GIT "/' /tmp/sa0002/saffron/gates/core/size.py
uv run --directory /tmp/sa0002 python -m pytest tests/test_size.py -q   # 16 passed

# diff-scoped mutation over main
cosmic-ray init cr.toml session.sqlite        # module-path = "saffron"
cr-filter-git --config cr.toml session.sqlite # branch = the patch's merge-base
cosmic-ray exec cr.toml session.sqlite
cr-report session.sqlite

# mutmut, scoped to one module
#   [tool.mutmut] source_paths = ["saffron/"]
#   also_copy = ["images/", "docs/", ".saffron/", "CONTEXT.md", "DESIGN.md", ...]
#   pytest_add_cli_args_test_selection = ["tests/", "-k", "not fast_gates_name_their_tool"]
mutmut run "saffron.gates.core.size.*"
mutmut results
mutmut show saffron.gates.core.size.x__changed_lines__mutmut_7
```

The lens trials were `claude -p --model sonnet` fed a single file containing the
remit below followed by `git show e15f6e3 --format=''` (or `9163213` for the
control). It holds no repository-specific knowledge, and #34 should treat it as
a starting point rather than a prompt to ship — it has had no tuning at all, and
§5.5's severity distinction is missing from it entirely.

```
You are a review lens with one remit and no other: **would the tests in this
diff catch this code being wrong?**

You see only the diff below. You have no tools. Do not review the code for
correctness, style, or contract. For each distinct behaviour the source hunks
add, ask: if that behaviour were removed or inverted, would some test in this
diff fail? Report every place where the answer is no.

Report only findings you can point at a specific line of the diff for. Output
each finding as one line: `<file>:<line> — <what is untested, and the input
that would expose it>`. If every behaviour is covered, say so and stop; do not
manufacture a finding.

--- DIFF ---
```
