# REVIEW — §5.5's adversarial critic, built and run once

Commits: `9a62f37` (lens prompts), `a640e51` (the phase), `0adf0ae` (wiring).
Suite: 312 passed / 11 deselected, `-m cell` 11 passed, `make lint` clean.
Live spend: **$1.86** of the $2.00 authorised.

---

## The lenses, and how they are kept disjoint

Two lenses, one versioned prompt file each — `saffron/agents/prompts/review-correctness.md`
and `review-contract.md`. Prompts are source: a lens *is* its remit, so the remit
lives in a file that diffs, not in a string built at runtime.

**Lens 1 — correctness & data semantics.** What the changed code *computes*:
time (timezones, DST, naive/aware, market hours), boundaries (off-by-one,
inclusive/exclusive, empty and single-element input, chunk edges), missing data
(null/NaN/gap propagation, absence treated as zero), units and scale, order and
state (assumed sort order, shared mutation, idempotency), and evidence — a test
asserting less than the criterion, a test that would pass identically before the
change, a fixture that is the only input the new code is right for.

**Lens 2 — contract & schema.** Every promise the change makes to something
outside itself: declared interfaces (signature, default, keyword, raised
exception, a new required argument), serialization and persistence formats,
schema and migration reversibility, contracts stated in prose (docstring,
README, ontology), and compatibility across a boundary the suite cannot cross —
the suite runs one version of everything at once, so anything requiring old and
new to coexist is invisible to it and visible to this lens.

Disjointness is kept three ways, all in the prompt text:

1. Each file has a **"Not yours"** section naming the other lens's territory
   explicitly and telling the critic not to mention it — the boundary is stated,
   not left to judgement.
2. Each file names the **blast-radius lens** as owning callers and downstream
   breakage, so neither declared lens drifts into it.
3. A **one-sentence edge test**, inverted between the two files: *if fixing the
   defect means changing what the code computes it is lens 1; if it means
   holding an interface or a stored format stable it is lens 2.*

Both prompts carry §5.5's framing verbatim, closing clause included, plus all
three severities with `note` explained as existing "so that filing everything as
a `concern` is visibly wrong."

**Lens 3 (blast radius) is not built.** §5.5 runs it at `risk: elevated` only,
and `run_one_cell` reads no risk tier — `CellSpec` has no `risk` field and
`policy.yaml` has no `elevate_on`. Declaring the lens here would run it on every
task, which is a different design from the one §5.6 states. A `ponytail:` comment
in `review.py` says so and names the condition for adding it.

## The phase

`saffron/phases/review.py`:

- **Host-invoked, one fresh session per lens.** `run_review` loops over `LENSES`
  itself. No subagent: the model decides when to spawn one, so a lens set
  requested in a prompt varies by task with no error when a lens is skipped.
- **`resume` is never passed.** The critic never sees the implementer's
  transcript. Because a fresh session inherits nothing, the spec body, the diff,
  the gate results (with each gate's `tool`, or "passed" and "never ran" read
  alike) and the acceptance criteria all go in explicitly.
- **Read-only tools** — `["Read", "Glob", "Grep"]` through `agent_options`'
  positive `tools` list, which is the list that *withholds*; `allowed_tools`
  only auto-approves, so a denylist would still offer the critic every built-in
  the runtime later adds.
- **Findings come back through the extraction turn**, validated host-side with
  Pydantic. The emitted schema has no `lens` field — the host stamps it, because
  a lens that names its own lens can file inside another remit and still look
  clean.
- **Everything is anchored** via `findings.anchor`; drops are kept with
  `anchored=False` and the per-lens drop rate is on the watch line.
- **A lens that failed or emitted the wrong shape is an `error`, never an empty
  findings list.** A lens that did not run must not read as a clean review.

## The terminal-state decision

§5.5 routes any single blocker to REBUT, and REBUT does not exist. The choice:

- **No anchored blocker, no lens error → `READY_FOR_REVIEW`**, with the concern
  count on the watch line and every finding in `findings.json`.
- **An anchored blocker → the task stops at `REVIEWING`**, the state §3.3
  already gives the phase. The pipeline genuinely halted mid-machine; saying so
  is honest, where `READY_FOR_REVIEW` would report an outcome the task has not
  earned — principle 34 with a state name. It also needs no invented state and
  no half-built REBUT.
- **A lens that errored → `REVIEWING` too**, because an unrun lens must not read
  as a clean review. `review_state` returns `(state, why)` and the caller
  watches the reason, so the two never collapse into one indistinguishable line
  — the same mistake the budget-stop/EXHAUSTED pair already documents.

An **unanchored** blocker routes nowhere: a hallucination must not stop a task.

Review cost is added to the task's total but is deliberately **not** gated on
the host spend ceiling — Appendix K is the argument that a green diff nobody
reviewed is the product this factory exists not to ship.

---

## The live run against SA-0004

`~/.saffron/batches/v0/SA-0004/patch.diff` (962 lines) applied to a tree at its
`base_sha` `4895e8b`. Same phase code as the cell path — the same prompt files,
extraction, Pydantic validation, anchoring and drop-rate accounting — with the
`claude` CLI (`--bare`, read-only tools, `--permission-mode dontAsk`) standing
in for the in-cell agent runner, and the head gate results restated from
Appendix K because the batch dir kept only the baseline suite.

**Fidelity gaps, stated because they are the honest caveats:** the CLI has no
`tools` withhold flag, so the read-only list went through
`--allowed-tools`/`--disallowed-tools`; and the two lenses ran on **different
models** — correctness on `opus` ($1.17), contract on `sonnet` ($0.69), because
after the first lens the remaining authorisation was $0.83 and a second opus run
would have blown the ceiling. §5.5 permits per-lens models; this particular
split was forced by budget, not chosen.

Combined outcome: `('REVIEWING', '1 blocker(s) — REBUT does not exist yet, so
the task stops here rather than claiming READY_FOR_REVIEW')`.

### Drop rate

| lens | findings | anchored | drop rate | cost |
|---|---|---|---|---|
| correctness | 4 | 4 | **0%** | $1.17 |
| contract | 1 | 1 | **0%** | $0.69 |

Every cited line was real and inside a hunk. Nothing was dropped, so this run
says nothing about the reconciler's discard path beyond that it did not fire
falsely — the unit tests cover the drop cases.

### Verbatim findings

#### correctness — `blocker` — `saffron/gates/core/integrity.py:288` (anchored)

> The `test-removed` check is a net line-count comparison (`len(entry.removed) > len(entry.added)`), which fails open on the exact move the gate exists to catch: an attempt that deletes a failing 4-line test and adds any 4+ lines to the same file — a stub test, blank lines, a comment — yields removed(4) <= added(4) and the gate returns `pass`. Worse, the failure message at line 293 ("test file shrank: N lines removed, M added") is fed back to the agent verbatim by the repair loop (DESIGN.md §5.4), so it states the evasion recipe. It also fires in the opposite direction on ordinary net-negative edits — removing a `@pytest.mark.skip` line from a test file (removed 1, added 0), the very repair the `suppression-added` check is meant to provoke, is reported as `test-removed`. No fixture covers the mixed case: every test-file fixture is either removed>added (TEST_FUNCTION_REMOVED, DELETED_TEST_FILE) or removed==added / removed==0, so the suite is green on a check that is trivially bypassed.

#### correctness — `concern` — `saffron/gates/core/integrity.py:253` (anchored)

> DESIGN.md §5.4 specifies the gate-config rule as "any edit to gate configuration, *unless `touches` explicitly includes it*", and `_gate_config_failures` has no such exemption — it takes only the diff and the patterns, so any match is unconditionally a failure. With Saffron's own declared `gate_config: ["pyproject.toml", ".saffron/**"]`, this collides with §5.2: every bug task writes its ratified `touches` back into `.saffron/specs/…` as the first commit on its own branch, and §5.2 adds that spec path to `touches` precisely so the commit is legal. That commit matches `.saffron/**`, so once wired, every bug task in this repo fails a blocking gate on a commit the design mandates. The fixtures only ever match `pyproject.toml` and `.saffron/gates/tests`, so nothing in the suite exercises an authorised gate-config path.

#### correctness — `note` — `saffron/gates/core/integrity.py:69` (anchored)

> The `FileDiff` docstring justifies detecting deletion via `new_path is None` as working "without trusting a mode line that an empty-file deletion does not always carry", but the reasoning is inverted: `deleted file mode` is emitted for every deletion, while an empty file's deletion is exactly the case where git emits *no* `---`/`+++ /dev/null` pair and no hunk at all. For such a diff both paths come from the `diff --git` line, `was_test` and `is_test` are both true, `removed` and `added` are both empty, and the gate returns `pass` on a deleted test file. Low impact (the file was empty), but the stated rationale would mislead the next reader into keeping the weaker signal.

#### correctness — `note` — `tests/test_integrity.py:388` (anchored)

> `assert "override" not in result.failures[0].message` cannot fail for any implementation: the message at integrity.py:323 interpolates the *token* (`'# type: ignore'`), never the matched line text, so neither "override" nor "arg-type" can ever appear in it. The comment above it presents this as proof that the reported failure is the added `# type: ignore[override]` rather than the removed `# type: ignore[arg-type]`, and it establishes nothing of the kind — an implementation that scanned `removed` instead of `added` would produce exactly one `suppression-added` failure here and pass this test identically. The test's only real discriminating assertion is the preceding single-element list comparison.

#### contract — `concern` — `saffron/gates/core/integrity.py:329` (anchored)

> DESIGN.md §5.4 defines the `integrity` gate's gate-config/test/suppression checks as failing 'unless `touches` explicitly includes it' — i.e. a task whose declared `touches` names the changed gate-config or test path is not gaming, it's doing declared work. `integrity_gate(diff, patterns)` has no `touches` parameter at all, so `_gate_config_failures` (line 249) and `_test_removal_failures` (line 267) unconditionally fail any matching change regardless of what the task was scoped to do. Nothing in the module docstring discloses this as a deferred exemption — it calls out the one exception it does implement ('Detecting a loosened assertion is deliberately absent', line 15) but is silent about this second one from the same section, so a reader has no signal that a legitimate task (e.g. one whose spec touches `.saffron/gates/tests` or `pyproject.toml` on purpose) will always be reported as an integrity violation once this gate is wired in.

### Caught vs missed, against Appendix K

| Appendix K defect | verdict |
|---|---|
| "An existing test was removed" inferred from net line count | **Caught**, as the blocker, with two details K does not state: the failure message hands the agent the evasion recipe, and no fixture covers the mixed case |
| The gate fails its own PR — §5.4's `touches` exemption omitted | **Caught twice**, by both lenses, as `concern` rather than `blocker`. Different argument from K's: not "sixteen violations on its own diff" but "§5.2's ratified-spec commit fails a blocking gate on every bug task" |
| The same comparison fails a legitimate `parametrize` consolidation | **Partially caught.** The blocker names the wrong-in-both-directions property and gives a different net-negative example (removing a `@pytest.mark.skip` line); it never reaches the parametrize case K names |
| `\ No newline at end of file` mishandled, aborting the task | **Missed.** Neither lens read the hunk-consumption code closely enough, and no prompt line pushes a critic toward "what does the *usual* input look like" (K's principle 46) |
| The agent can disable the gate from inside the cell (`git config diff.srcPrefix`) | **Missed, and out of remit.** It lives in `export_patch` in `session.py`, outside the diff entirely — blast-radius territory, and lens 3 is not declared |
| Five of eleven mutants survived the agent's own tests | **Adjacent.** Both `note`s are in that family: a test that cannot fail, and a docstring rationale that is backwards. Neither lens does mutation, and `revert` is the mechanism §5.4 assigns |

**Two findings that are not in Appendix K at all** — the empty-file-deletion hole
and the assertion at `test_integrity.py:388` that no implementation can fail —
and both are true. Filed as `note`s, which is the right severity and is direct
evidence the third level is doing its job rather than inflating the concern
count.

### What this says about the prompts

- The **no-manufacture clause holds**: five findings across two lenses, every one
  checkable at the line it cites, zero drops, and the cheaper lens filed one
  finding rather than padding.
- The **severity split holds**: one blocker, two concerns, two notes, and the
  notes are exactly the true-but-trivial category the level exists for.
- **Disjointness partly failed.** Both lenses filed the missing `touches`
  exemption. It is arguably contract-shaped (the gate contradicting §5.4's
  stated contract) and the correctness lens should have left it alone, so the
  "Not yours" section is not tight enough on *a specification the code
  disagrees with*. Untuned and reported as it ran: one honest run.
- Nothing here was tuned after seeing the output. The prompts are exactly what
  the commits contain.
