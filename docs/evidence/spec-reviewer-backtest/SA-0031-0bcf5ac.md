# Pre-flight review: SA-0031 (four phase modules still speak prose)

SA-0031 can't run from `0bcf5ac`. The spec is written on top of SA-0030's migration, and that migration isn't in this commit. Four more fixes are needed after it is re-cut.

## Findings

1. **Blocker — SA-0030 is not at this base, so the spec's premise is false and its criteria contradict each other.**
   - **Evidence:**
     - `grep emit|_phase_watch|to_watch saffron/` (excluding `events.py`) finds nothing.
     - `saffron/cell/session.py:583` still has `run_one_cell(... watch: Callable[[str], None] = print`, with about 70 `watch(` lines in the file.
     - `saffron/events.py:19`: "Nothing here emits an `Event` yet".
     - `tests/test_events.py:3`: "No emission: `SA-0030`/`SA-0031` migrate those…".
   - **What depends on SA-0030:**
     - The context at spec:45 says "`SA-0030` migrated the supervisor and left an adapter".
     - Criteria spec:130 ("the one `SA-0030` built"), spec:134–137 ("both `_phase_watch` constructions go") and spec:154 all name code that doesn't exist here.
   - **The contradiction:** spec:121–122 says "no signature in `saffron/` still carries a `watch` parameter". At this base that means migrating all of `session.py` (signatures at :337, :445, :528, :583, :617). But spec:182–184 says "`SA-0030` migrated that file's own `watch` lines and this spec must not revisit them."
   - The history row says SA-0030 was MERGED on 2026-09-02, so `0bcf5ac` comes before that merge, or isn't on its line. The claims about SA-0030's code (spec:95–105: "eight", `_phase_watch`, `to_watch`) are **unverified**.
   - **Fix:** re-cut from a commit that contains SA-0030's merge and re-review there. Note that `cli.py:328` bases a real cell on the live `fetch_default_branch`, not on this snapshot.

2. **Blocker — the `re-verify:` line can't become an event without breaking a rule.**
   - **The line:** `saffron/phases/package.py:508` `watch(f"re-verify: {label} suite at {sha[:12]}")`.
   - **What forbids each way out:**
     - spec:120 requires "Every `watch(...)` in the four phase modules … is an `emit(<Event>)`".
     - spec:192 forbids "Changing any message".
     - spec:36 forbids `saffron/events.py`.
   - **Why no event kind fits:**
     - `PhaseStart` renders `f"{event.label}: {event.detail}"` (`events.py:484`), but `label: LineLabel` (`:141`) is a Literal that has no `"re-verify"` (`:63–73`).
     - Every other kind adds its own prefix (`preflight:`, `agent:`, `teardown:` …).
     - `events.py:659–665` (FINDINGS) records this exact line as one that "resisted typing".
   - **What each option costs the cell:**
     - `label="re-verify"` should fail `types: { blocking: true }` (`.saffron/policy.yaml`, which runs `ty check`). That ty flags it is **unverified**, but it is ordinary Literal checking.
     - Adding `# ty: ignore` is in `integrity.suppressions`.
     - Rewording the line breaks spec:192.
   - **Fix:** exempt this line in the spec and say what it becomes, or un-forbid `events.py` so a `LineLabel` value can be added. Once finding 1 is fixed, check whether SA-0030 hit the same wall on `session.py:1415`/`:1433` (FINDINGS[0]).

3. **Blocker — spec:177–179 asks for something the cell can neither do nor report.** The criterion reads: "run `uv run pytest -m cell` against them explicitly, and say in the pull request body that you did".
   - **The cell can't run those tests.** They need a cell runtime: `tests/test_package_cell.py:15` `pytestmark = pytest.mark.cell`, and `tests/test_agent_runner.py:168` `runtime.run_detached(...)`. The cell image has none: `.saffron/Dockerfile:3` `FROM saffron/cell-base:python`, adding only `procps` (`:10`). CLAUDE.md: "`uv run pytest -m cell   # needs apple/container`".
   - **The agent can't write in the PR body.** `render_pr_body` (`saffron/report/pr_body.py:59–78`) builds it on the host from spec, results and reviews; no parameter takes agent-written text.
   - The criterion is therefore unmet, or the agent makes a false claim.
   - **Fix:** make it an operator step before ratifying: `uv run pytest -m cell tests/test_package_cell.py tests/test_agent_runner.py`.

4. **Blocker — none of the 12 criteria has a witness or a mutant, and the change edits existing code.**
   - The criteria are a markdown `## Acceptance criteria` section (spec:119) with no `acceptance:` frontmatter, which `saffron/intake.py:94–95` treats as the other form. So the `criteria` gate has nothing to check.
   - **Wrong implementations the tests the criteria describe would pass:**
     - *Criterion 1:* rename `watch` to another string callable, e.g. `say:`, and keep passing prose. The grep for `watch` passes and the adapter survives under a new name.
     - *Criterion 8:* once `_describe` is deleted, "renders identically to the line `_describe` produced" (spec:149–150) can only compare against literals the same agent typed. This drift has already been measured (`tests/test_events.py:896–898`): "rewriting the `gates: attempt …` branch and its `_CASES` literal together passed 67 tests."
     - *Criterion 10:* drop the not-a-dict guard at `implement.py:252–254`. A non-JSON raw-line test still passes, and a JSON array gets logged as `Agent(event=…)`.
   - **Fix:** add an `acceptance:` block with one witness per criterion.
     - Criterion 8: freeze the 11 parity inputs from `test_events.py:753–771`, with the outputs `implement._describe` gives at base, into the spec as literals.
     - Criterion 10: the raw-quarantine test must include a JSON non-dict.
     - Name a mutant per criterion in its claim; `Criterion` (`intake.py:53–57`, `extra="forbid"`) has no `mutant` field.

5. **Blocker at this base, fine once finding 1 is fixed — size.**
   - **At this base:** criterion 1 pulls in SA-0030's whole migration. That was measured at 787 changed lines (history row). Adding SA-0031's own ~720 gives ~1500, well over `refactor: 1000` (`saffron/gates/core/size.py:25`).
   - **SA-0031 alone, about 720 lines:**

     | Part | Lines |
     |---|---|
     | 17 call sites, each becoming a multi-line `emit(Kind(timestamp=…, spec_id=…, …))`, plus the 17 deletions | ~117 |
     | 39 `watch` parameter/pass-through tokens in the phases, plus `cli.py`, as old and new lines | ~80 |
     | Deleting `_describe` (`implement.py:182–210`) and the parity test (`test_events.py:744–773`) | ~60 |
     | `cli.py` fan-out | ~25 |
     | `session.py` adapters and keyword sites (**unverified**) | ~30 |
     | 58 `watch=` test sites (40 in the seven files, 18 in `test_session.py`) | ~116 |
     | Rewriting string assertions (`test_implement.py:216`, `:343`, `:457`, …) | ~30 |
     | About 7 new tests | ~230 |

6. **Concern — criterion 1's "a test greps the package" will hit the word `watch` in files the cell can't edit.** `events.py:7`, `:179` and `:446–448` (forbidden), and `runtime.py:314` (forbidden). **Fix:** say the test matches parameter declarations (`watch:` / `watch=`), not the word.

7. **Concern — FAMILIES pins symbol names the cell must not rename.**
   - `tests/test_events.py:709–728` checks, via the AST, that every `where` in `events.FAMILIES` names a real function.
   - `events.py:576–580` cites `phases/implement.py:_consume` and `run_agent`, plus `package`, `reverify`, `run_review`, `run_rebut` and `cli.py:_resolve_stacked_on`.
   - Inlining `_consume` during the migration breaks a blocking test that no permitted edit can fix.
   - **Fix:** add a note to the spec telling the agent to keep these names.

8. **Concern — `events.py`'s docstrings assign SA-0031 work that the spec forbids.**
   - `events.py:392–400` says "`SA-0031` deletes this copy … `SA-0031` must pick one deliberately rather than inherit whichever copy it deletes last". The file is forbidden (spec:36).
   - Once `_describe` is gone, `_when(None) == "unknown"` wins by default, and the "verbatim" docstrings (`:412–413`, `:445–448`) become stale.
   - `implement.when` has to stay, because `session.py:1436` uses it.
   - **Fix:** state that choice in the spec, and accept or allow fixing the stale docstrings.

9. **Concern — the plan doc will say the opposite of what the spec does.**
   - `docs/superpowers/plans/2026-08-31-operator-visibility.md:109–111`: "restated as an acceptance criterion in `SA-0031`: **the `emit` default stays in `session.py`.** `cli.py:393` calls `run_one_cell` with no `emit` argument and must keep doing so."
   - Spec:125–126 has `cli.py` pass `emit` to `run_one_cell`. The spec's own notes acknowledge the reversal (spec:207–214), but the plan file isn't in `touches`.
   - This is historical prose, so it is left to the operator whether to update it.

10. **Note — the counts are right; one symbol description is off.** Verified against base:
    - 5/8/1/1 call sites in the phase modules, and 6/12/14/7 tokens.
    - `cli.py` `:226`, `:292`, `:297`.
    - Test `watch=` counts of 21/7/7/2/1/1/1, and 18 in `test_session.py`.
    - Both files the spec calls cell-marked really are (`test_agent_runner.py:180` sits inside a `@pytest.mark.cell` test).
    - The "11 before SA-0030" is also right: `plan_checkpoint` 3, `run_one_cell` 1, `_drive_cell` 7.
    - Correction: `_repair` isn't a top-level symbol. It is nested inside `_drive_cell` (`session.py:1234`).

11. **Note — the spec doesn't say where `spec_id` comes from.** Every event kind requires `timestamp` and `spec_id` (`events.py:99–100` etc.), but `run_agent`, `run_lens`, `run_review` and `reverify` never receive a spec id. Either `emit` stamps them or signatures grow, and the spec says neither. This decides how much of the size estimate is signature churn.

## Checks

1. checked: criteria vs invariants — read all 12 criteria against the CLAUDE.md invariants (`error` ≠ `fail`, cell untrusted, the raw-line quarantine) and the `events.Agent` and `EventLog` docstrings. No conflicts; the spec cites no `DESIGN.md` sections.
2. found: scope reaches the change — findings 1, 8, 9. No callers exist outside `saffron/` and `tests/` (git grep came back empty).
3. found: witness/mutant discipline — finding 4.
4. checked: ceilings vs history — the only comparable row is SA-0030. `max_turns` 140 against a peak of 32t (not `error_max_turns`). $18 against $8.10 for plan plus implement, $10.56 in total. That row ended in `error`, so its spend is a floor.
5. found: size vs ceiling — finding 5.
6. found: claims about current code — findings 1 and 10. Every count in the spec was re-measured and holds at base, apart from the session.py/SA-0030 claims covered in finding 1.

## Assessment

Not runnable from `0bcf5ac`. It becomes runnable once it is re-cut onto a commit containing SA-0030's merge, re-reviewed there, and findings 2–4 are fixed.