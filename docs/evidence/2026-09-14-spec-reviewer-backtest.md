# Spec reviewer backtest

Pre-registered 2026-09-14, before any scored review, in the commit that adds this
file. Design: `docs/superpowers/specs/2026-09-14-spec-reviewer-design.md`.
Script: `docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py`.

## The bar

The reviewer passes if it catches **at least 17 of the 34 known defects** and
raises **at most 2 false blockers across the 10 controls**.

## Correction, 2026-09-14, before any scoring

- The first sweep was stopped and its reviews discarded unread. `history`'s
  header showed each spec as it stands today, which leaked a fixed spec into
  10 of 29 case versions (SA-0087@24edb32 showed its raised 90 turns / $14)
  and into none of the controls. The header now shows the spec at the version.
- The agent's own text named SA-0087@24edb32's two scored defects (its
  ceilings, and the binary-patch criterion as check 1's example). Both were
  replaced with neutral text before the re-run.
- The six checks' wording was written with this corpus in view, so recall is
  in-sample. It is reported with and without SA-0087@24edb32.
- The backtest now runs the shipped agent's tool set (`--tools`), without
  `git grep` (which can run a command).
- The bar, the cases, the controls and the scoring rule are unchanged.

## Scoring

- A known defect is **caught** when a `blocker` or `concern` names the same file
  or criterion and the same kind of defect. Blocker-only recall is reported
  as well.
- A blocker on a control is **false** when its claim does not hold on reading
  the code at the control's version. A blocker whose claim holds is a new find,
  not a false alarm. The operator settles any disputed call.
- Each version is reviewed once, blind: a fresh single-commit snapshot of the
  version (`git archive`), so no later commit is reachable, with Read, Grep
  and Glob scoped to it, `history --before` the version, and `history`'s
  header shows the spec as it stood at the version, and no outcome in the
  prompt.

## Known defects

| spec | version | defects |
| --- | --- | --- |
| SA-0005 | 351bdd3 | `touches` lacked `cli.py` and `package.py`, which its criteria needed |
| SA-0009 | ad94fd2 | 990 lines against a 600 ceiling; `EXHAUSTED` at $31.60 |
| SA-0011 | 1e069af | `tests/test_package.py` fakes outside `touches` |
| SA-0014 | e1090dc | false claim about SA-0005's criteria |
| SA-0016 | e1090dc | false claim that its refusal fires on SA-0005 |
| SA-0018 | 366e377 | forbade `DESIGN.md`/`CONTEXT.md`, which the change made false |
| SA-0019 | 6f8e0d7 | orphan criterion broke an invariant; `EXHAUSTED` at $12.12 |
| SA-0020 | 86f0c6e | forbade `saffron/phases/**`, which the fix needed; too wide |
| SA-0025 | 2e4f2e6 | too wide; `NOT_IMPLEMENTED` at 141 turns |
| SA-0026 | 0301518 | test file with a guard outside `touches`; the agent dodged the guard |
| SA-0029 | 3ed6f83 | plan estimated 1100 lines against 600; `PLAN_REJECTED` |
| SA-0029 | 98ce586 | 548 lines grew to 863 in review because 14 criteria demanded tests |
| SA-0031 | 0bcf5ac | `EXHAUSTED` at 141 of 140 turns, $19.17 of $18 |
| SA-0043 | a205a90 | three files outside `touches`; `EXHAUSTED` with a sound diff |
| SA-0044 | 6ceb5ba | criterion 2's witness proved only the half already true; criterion 4's real witness needed a file outside `touches` |
| SA-0051 | 5177edb | three mechanisms; plan at 650 lines against 600 |
| SA-0059 | ab42114 | nine files at `elevated`; `EXHAUSTED` at $26.75 of $16 |
| SA-0063 | 6527f73 | forbade `saffron/phases/**`, home of the only call site; the spec body dictated the literals its mutants pin |
| SA-0065 | d84cab3 | forbidden excluded a caller the change breaks |
| SA-0079 | 1e2209a | the memo witness only ever answered "present" |
| SA-0080 | 1e2209a | missing mutant; the headline witness passed a full re-parse |
| SA-0081 | 1e2209a | missing mutant; a misplaced boundary passed every test |
| SA-0082 | c0e84c3 | the spec's table called an alternative equivalent that is not |
| SA-0083 | c0e84c3 | missing mutant; deleting the override left every test green |
| SA-0084 | c0e84c3 | missing mutant; a partial strip passed "every control character" |
| SA-0085 | c0e84c3 | missing mutant; two witnesses each covered half a claim |
| SA-0086 | 8811f3a | forbade `pr_body.py`, which the change made false; no mutants on an edit, so a witness that could not fail shipped; "verdict" in the spec text, which `CONTEXT.md` forbids in that sense |
| SA-0087 | 24edb32 | 60 turns / $8 against a 47-turn plan checkpoint; criterion 3 charges an unappliable binary stub to the task |
| SA-0087 | 14f6357 | criterion 2's witness passes with `read_head` on the wrong container |

## Controls

| spec | version | started_at |
| --- | --- | --- |
| SA-0062 | 210b0d4 | 2026-09-07 03:04:36 |
| SA-0061 | 210b0d4 | 2026-09-06 17:59:43 |
| SA-0060 | 210b0d4 | 2026-09-06 05:36:50 |
| SA-0056 | ee98185 | 2026-09-05 23:14:16 |
| SA-0055 | 49cc2ef | 2026-09-05 19:46:28 |
| SA-0054 | fdcbbad | 2026-09-05 03:36:10 |
| SA-0030 | 59cde3d | 2026-09-02 03:12:08 |
| SA-0040 | 98ce586 | 2026-09-02 00:52:14 |
| SA-0027 | 094cc4e | 2026-09-01 07:41:50 |
| SA-0024 | 7455593 | 2026-08-31 22:08:37 |

## Results

Scored 2026-09-14 against the rule above, read strictly. Reports and cost
records: `docs/evidence/spec-reviewer-backtest/<SPEC>-<version>.{md,json}`.
Finding numbers are the report's own; an unnumbered report is cited by its
first words.

### Known defects

| spec | version | defect (short) | caught as | finding |
| --- | --- | --- | --- | --- |
| SA-0005 | 351bdd3 | `touches` lacked `cli.py` and `package.py` | blocker | 1 and 2 ("`saffron/phases/package.py` … is not in `touches`"; "`saffron/cli.py` is not in `touches`") |
| SA-0009 | ad94fd2 | 990 lines against 600 | blocker | 1 ("the change is too big for the size gate", 690–840) |
| SA-0011 | 1e069af | `tests/test_package.py` fakes outside `touches` | missed | no finding names `tests/test_package.py`; 4 names `package.py` for a different path |
| SA-0014 | e1090dc | false claim about SA-0005's criteria | blocker | 1 ("the SA-0005 measurement that criterion 1 rests on is false") |
| SA-0016 | e1090dc | false claim its refusal fires on SA-0005 | missed | 1 attacks the same Notes sentence for another claim (SA-0014 not at base) |
| SA-0018 | 366e377 | forbade `DESIGN.md`/`CONTEXT.md`, made false | blocker | 3 ("sentences in `CONTEXT.md` and `DESIGN.md` become false, and both files are forbidden") |
| SA-0019 | 6f8e0d7 | orphan criterion broke an invariant | concern | C1 ("`queue` or `reconcile` can stamp a live cell `ORPHANED`. Criterion 4 … is unconditional") |
| SA-0020 | 86f0c6e | forbade `saffron/phases/**`, which the fix needed | blocker | 1 ("PACKAGE undoes the stacking, and PACKAGE is forbidden") |
| SA-0025 | 2e4f2e6 | too wide; 141 turns | concern | 7 ("size is close to the ceiling", ~600; split) |
| SA-0026 | 0301518 | guard test file outside `touches` | blocker | 1 ("a test outside `touches` asserts the behaviour criterion 4 removes", `tests/test_package.py:2075`) |
| SA-0029 | 3ed6f83 | plan at 1100 lines against 600 | blocker | 2 ("the estimated diff clearly exceeds the 600-line feature ceiling", ~900) |
| SA-0029 | 98ce586 | 548 lines grew to 863 | missed | C5 estimated ~450 and advised leaving it |
| SA-0031 | 0bcf5ac | `EXHAUSTED` at 141/140 turns, $19.17/$18 | missed | ceilings line reads `checked` (140 against a 32t peak) |
| SA-0043 | a205a90 | three files outside `touches` | blocker | 2 (`tests/test_session.py`, `tests/test_events.py`, `tests/fixtures/watch-golden.txt`, the three `990ad71` names) |
| SA-0044 | 6ceb5ba | criterion 2's witness proved half | missed | no finding on criterion 2; 4 covers criteria 1 and 3 |
| SA-0044 | 6ceb5ba | criterion 4's witness needed a file outside `touches` | missed | 4 calls the restore criterion's witness weak but names no file outside `touches` (the record's is `tests/test_worktree.py`) |
| SA-0051 | 5177edb | three mechanisms; plan at 650 | concern | "Concern — estimated size is at the ceiling" (600–650) |
| SA-0059 | ab42114 | nine files at `elevated`; `EXHAUSTED` at $26.75 | missed | 5 and 6 blame the ceilings, which the record clears; size appears only in a check line (~590, "a concern, not a blocker") |
| SA-0063 | 6527f73 | forbade `saffron/phases/**`, the only call site | blocker | "the notes cannot reach the PR body, because the only production caller … is under a forbidden path" |
| SA-0063 | 6527f73 | the body dictated the mutants' literals | concern | "the spec body gives away both mutants' `find` text" |
| SA-0065 | d84cab3 | forbidden excluded a caller | blocker | "a caller the spec forbids the cell to edit would start raising" (`session.py:426`) |
| SA-0079 | 1e2209a | memo witness only answered present | missed | notes only; none on the memo stub |
| SA-0080 | 1e2209a | headline witness passed a full re-parse | concern | C1 ("witness 1 can't tell 'read again' from 'parsed again'") |
| SA-0081 | 1e2209a | misplaced boundary passed every test | missed | C4 names a different boundary mistake (re-finding `Ceilings` each poll) |
| SA-0082 | c0e84c3 | table called a non-equivalent alternative equivalent | concern | C1 (the `-c diff.ignoreSubmodules=none` row) |
| SA-0083 | c0e84c3 | deleting the override left every test green | missed | a note saw the unwitnessed `advice.graftFileDeprecated` override and called it harmless |
| SA-0084 | c0e84c3 | a partial strip passed "every control character" | missed | C4 is the record's other, unscored line (raw `subtype`/`terminal_reason`) |
| SA-0085 | c0e84c3 | two witnesses each covered half a claim | missed | C2 finds a different gap in the first witness |
| SA-0086 | 8811f3a | forbade `pr_body.py`, made false | blocker | 1 ("a rendered sentence becomes false, and its file is forbidden") |
| SA-0086 | 8811f3a | no mutants on an edit; a witness that could not fail | blocker | 2 ("criterion 1 has no mutant, and a wrong implementation passes its witness") |
| SA-0086 | 8811f3a | "verdict" in the spec text | missed | a note only (7) |
| SA-0087 | 24edb32 | 60 turns / $8 against a 47-turn plan checkpoint | missed | ceilings line reads `checked` (60 above a 45t peak) |
| SA-0087 | 24edb32 | criterion 3 charges an unappliable binary stub | concern | 4 ("a patch with a binary file will end the task `EXHAUSTED`") |
| SA-0087 | 14f6357 | criterion 2's witness passes `read_head` on the wrong container | missed | 1 flags criterion 2's witness for another hole (apply without commit) |

Today's intake refuses SA-0063@6527f73 for a disclosed mutant — its recorded
defect 2 — so a mechanical check now catches that defect without the reviewer.

### Controls

| spec | version | blockers | false | new finds | disputed | concerns / notes |
| --- | --- | --- | --- | --- | --- | --- |
| SA-0062 | 210b0d4 | 4 | 0 | 3 (2, 3, 4) | 1 (1) | 3 / 2 |
| SA-0061 | 210b0d4 | 3 | 0 | 1 (2) | 2 (1, 3) | 5 / 1 |
| SA-0060 | 210b0d4 | 3 | 0 | 2 (1, 2) | 1 (3) | 4 / 2 |
| SA-0056 | ee98185 | 2 | 0 | 2 (1, 2) | 0 | 2 / 3 |
| SA-0055 | 49cc2ef | 1 | 0 | 0 | 1 (1) | 3 / 3 |
| SA-0054 | fdcbbad | 2 | 0 | 0 | 2 (1, 2) | 5 / 3 |
| SA-0030 | 59cde3d | 4 | 0 | 4 (1–4) | 0 | 2 / 2 |
| SA-0040 | 98ce586 | 2 | 0 | 1 (2) | 1 (1) | 3 / 2 |
| SA-0027 | 094cc4e | 3 | 0 | 2 (2, 3) | 1 (1) | 5 / 3 |
| SA-0024 | 7455593 | 4 | 0 | 4 (1–4) | 0 | 3 / 3 |
| **total** | | **28** | **0** | **19** | **9** | 35 / 24 |

Blockers are numbered in report order. Each was read at the control's version
with `git show <version>:<path>`; the evidence is under *New finds* and
*Disputed*.

### Totals

- caught **19/34** (blocker-only **12/34**); without SA-0087@24edb32,
  **18/32**
- false blockers **0** across the 10 controls, with **9 disputed** and left to
  the operator

**PASS**, on the calls settled here. Two sets of calls can reverse it:
- The three close calls counted as catches: if all three flip, recall is
  16/34 and the result is FAIL.
- The dependency class of disputed blockers: if it is ruled false, K = 4 and
  the result is FAIL.

### Cost

$71.38 across the 39 scored reviews (`total_cost_usd`, no error records).
Spent outside the scored set: a discarded first sweep ($7.26, 3 reviews) and
three smoke runs (~$10.30).

### New finds

Control blockers whose claim holds at the version, as candidate backlog
items. Several were already found after the cell or were handled by it; each
line says which.

1. **SA-0062@210b0d4, 2:** the `git checkout HEAD` undo destroys uncommitted
   edits.
   - Verified: `committed_gate` runs after `run_suite` (`session.py:966` vs
     `:1001`), and `revert.py:174-179` refuses dirty paths for that reason.
   - Already recorded: BACKLOG item 78, found at PR #154's review.
2. **SA-0062, 3:** criterion 5's witness cannot tell the real mutator from the
   stub while no spec declares a mutant.
   - Verified: `witness.py:77-81` returns `skip` ("the spec declares no
     mutants") before any mutator is consulted.
3. **SA-0062, 4:** criterion 3 has no mutant, and an in-cell count by line
   passes a same-line double match.
   - Verified: the host rule counts bytes (`mutation.py:131`,
     `content.count(find)`).
4. **SA-0061@210b0d4, 2:** criterion 3's witness passes
   `witness_blocking(spec.risk)` in place of the effective tier.
   - Verified: the tier is computed at `session.py:952`.
   - Handled by the cell (`suite.py:218` keys on the tier).
5. **SA-0060@210b0d4, 1:** the spec says a context manager's exit has neither
   of `SA-0057`'s shapes. That is false.
   - Verified by running Python: an exception raised in a `@contextmanager`
     `finally` replaces an in-flight `KeyboardInterrupt`.
   - An `__exit__` returning true swallows one.
6. **SA-0060, 2:** criterion 5 names no signal separating "did not apply"
   from "cannot reach", so `except Exception → skip` passes its witness.
   - Verified against the spec's text.
7. **SA-0056@ee98185, 1:** restore is unspecified, so a find/replace swap back
   passes a simple byte-identical witness.
   - Handled by the cell (`restore_mutant` checks a whole-file digest).
8. **SA-0056, 2:** containment names only `..`.
   - Verified: `Path("/tree") / "/etc/x"` is `/etc/x`.
   - Handled by the cell (`mutation.py:96-104` refuses absolute paths and
     resolves).
9. **SA-0030@59cde3d, 1:** criterion 1 cannot be met for the outcome and
   rate-limit lines.
   - Verified: `events.FINDINGS[0]`, `LineLabel` excludes them, and `types` is
     blocking.
   - Both lines shipped as `print(...)`, so the criterion was not met to the
     letter.
10. **SA-0030, 2:** criteria 2, 5 and 6 conflict over `GateResult`. Rendering
    one changes the golden output; not rendering one makes the log differ from
    what printed.
    - Verified: `events.py:502-508`, `tests/test_events.py:843`.
11. **SA-0030, 3:** an unwritable `task_dir` raises before any terminal state.
    - Verified: the gates export (`session.py:653`) and `baseline.json`
      (`:875`) write there first.
12. **SA-0030, 4:** no criterion has a mutant.
    - The claim holds, though `mutant` could not be declared until ee98185.
13. **SA-0040@98ce586, 2:** no test ties `describe` to the lines the call
    sites print.
    - Measured later: `tests/test_events.py` at 0bcf5ac records a drifted
      rewrite passing 67 tests.
14. **SA-0027@094cc4e, 2:** the marker scan matches spec text that quotes a
    marker.
    - Verified: the only match at the version is the spec itself.
    - Handled by the cell (`retirement_markers` excludes `.saffron/specs/`).
15. **SA-0027, 3:** no witnesses, so the refusal wired into `_refuse` alone
    passes every gate.
    - Verified: checklist form, no `acceptance:`.
16. **SA-0024@7455593, 1:** the change reverses DESIGN §3.2's recorded
    decision, and `DESIGN.md` is forbidden.
    - Verified: `DESIGN.md:200-202`.
    - The sentence is gone at HEAD, so it was fixed by hand.
17. **SA-0024, 2:** a `protected` check in `scope` breaks the §5.2 spec-path
    writeback.
    - Verified: `DESIGN.md:626`, and `.saffron/**` is protected.
    - Already recorded: BACKLOG item 31.
18. **SA-0024, 3:** criterion 8 cites item 30, which does not exist at the
    version (the backlog ends at 29).
    - Item 30 was first written by SA-0024's own cell (`43fbe1b`).
19. **SA-0024, 4:** no witnesses, so a build that never wires `session.py`
    passes every gate.
    - Verified: checklist form.

Possible new finds on case versions, unverified:
- SA-0011@1e069af, 4 (re-verification drops the `criteria` result).
- SA-0044@6ceb5ba, 1 (the golden fixture and `tests/test_events.py` outside
  `touches`).
- SA-0084@c0e84c3, C4 (this one matches an unscored `rejections.md` line).
- SA-0087@14f6357, 1 (claim 2 omits "committed").
- SA-0081@1e2209a, C4.

### Close calls

Counted as caught:
- **SA-0019:** C1 names criterion 4 and the batch-scan premise, but not the
  recorded consequence (a live row re-queued). Its C7 says `ORPHANED` is not a
  re-queue state; it is (`scheduler.py:67`).
- **SA-0025:** the estimate is ~600, at the ceiling rather than over it, and
  the same report calls `max_turns` 140 fine.
- **SA-0080:** C1's wrong build (read everything, parse from the offset)
  differs from the recorded one (re-parse everything, keep the tail). Its fix,
  "never read everything and slice", covers the recorded one.

Counted as missed:
- **SA-0016:** the same sentence, but a different claim.
- **SA-0029@98ce586:** a size concern that said the spec fits.
- **SA-0044, defect 2:** the same criterion, but a witness finding, not a
  scope finding.
- **SA-0059:** the ceilings findings the record rejects, and size only in a
  check line.
- **SA-0081:** a different boundary mistake.
- **SA-0085:** a different gap in the same witness.
- **SA-0087@14f6357:** a different hole in the same witness. The `read_head`
  half was caught at 24edb32 (C5), which is not scored for it.

If every one of the ten flipped, recall would range from 16 to 26.

### Disputed

**(a) The dependency is absent at the version but landed before the cell
started.**
- Blockers: SA-0062 1, SA-0061 1, SA-0054 1, SA-0040 1.
- The claims hold at the version the rule names, but each cell's own base had
  the code:
  - `events.py`: `ad92654`, 09-01 14:43 PDT, before SA-0040 at 17:52 PDT.
  - `batch.py`: `b20f42d`, 09-04 18:28 PDT, before SA-0054 at 20:36 PDT.
  - SA-0061: `7f29609`, 09-06 11:23 PDT, before SA-0062 at 20:04 PDT.
  - SA-0060: merged in `95e9b95`, 09-06 10:10 PDT, before SA-0061 at 10:59
    PDT.
- The same class appears on seven case versions. In the spec loop it would
  fire on every stacked spec.
- Ruled false, K = 4 and the result is FAIL.

**(b) The ceilings are below what the cited history rows spent, but the
control finished inside them.**
- Blockers: SA-0060 3 (90 turns against SA-0042's 101t) and SA-0027 1 ($14 /
  120t against SA-0019's $14.39 / 120t).
- SA-0027 finished at $13.43 total with a 102t peak, per other reports'
  `history` rows.

**(c) A witness predicted green at base, but the cell passed.**
- Blockers: SA-0061 3, SA-0054 2, SA-0055 1.
- Each premise holds: the behaviour is already true at base.
  - `session.py:278-281`.
  - No `batch` subparser at fdcbbad.
  - `cli.py:904-905`, with tests already asserting it at
    `tests/test_cli.py:2124`, `:2882` and `:2907`.
- Each cell reached `READY_FOR_REVIEW` with `criteria` and `revert` blocking,
  so the witnesses it wrote were not green at base.

All nine ruled false gives K = 9.

## Supplement, 2026-09-14, after scoring (operator-directed, post hoc)

Recorded beside the result above, never in place of it. The operator directed
both parts after reading `## Results`; nothing above this heading changed.

### SA-0080 re-ruled missed

- SA-0080 C1 was counted caught (*Close calls*), but the same pattern — a
  different wrong build in the same witness — was counted missed for SA-0081,
  SA-0085 and SA-0087@14f6357. The task reviewer found the inconsistency.
- Ruled for consistency: SA-0080 is **missed**.
- Totals: caught **18/34** (blocker-only still **12/34**); without
  SA-0087@24edb32, **17/32**.
- Two close calls stay counted as caught (SA-0019, SA-0025). One flipping
  leaves 17/34; both flipping gives 16/34, a FAIL on recall.

### Four controls re-reviewed at their cells' real bases

Each class-(a) blocker said a dependency was missing. It was missing at the
control's pre-registered version, the spec's last-touch commit, but each cell
ran on a later base that had it. Each of the four was reviewed once more, blind
as before, at the base its cell ran on (`tree_base` = `base_sha`). SA-0054's
base is synthetic: `f0fe0c8` is `fe39b41`'s tree plus the spec file from
`base_sha` `6a92e05`, with `fe39b41`'s committer date, because SA-0054 was a
stacked child whose spec was not on its parent's branch. Reports:
`docs/evidence/spec-reviewer-backtest/<SPEC>-<base>.{md,json}`. Every blocker
was read at its report's base with `git show <base>:<path>`.

| control | pre-registered | real base | blockers | false | hold | concerns / notes | class-(a) blocker recurs? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SA-0062 | 210b0d4 | 91b6eda | 2 | 0 | 2 | 5 / 2 | no |
| SA-0061 | 210b0d4 | 95e9b95 | 2 | 0 | 2 (1 disputed) | 4 / 3 | no |
| SA-0040 | 98ce586 | 08aa1a4 | 3 | 0 | 3 (2 disputed) | 5 / 3 | no |
| SA-0054 | fdcbbad | f0fe0c8 | 2 | 0 | 2 (1 disputed) | 5 / 3 | no (a note only) |
| **total** | | | **9** | **0** | **9 (4 disputed)** | 19 / 11 | **0 of 4** |

- **SA-0062@91b6eda 1** (undoing with `git checkout HEAD` wipes uncommitted
  work): holds. `witness` runs inside `run_suite` (`session.py:1004-1010`) and
  `committed` after it (`:1045`); `committed.py:5-7`, `revert.py:174-179` and
  `worktree.py:273-276` read as quoted. The same claim as 210b0d4's blocker 2
  (*New finds* 1).
- **SA-0062 2** (no criterion declares a `mutant`): holds. The frontmatter has
  no `mutant:`, `intake.py:99` accepts one at this base, `session.py:1009`
  supplies `stub_mutator`, and `witness.py:78-85` names criterion 4's case.
- **SA-0061@95e9b95 1** (criterion 4's witness already passes at base): the
  premise holds. `baseline.py:48-54` walks only failures, `:97` fires only on a
  change to `skip`, and the fixture drops `acceptance` and `mutate`
  (`tests/test_session.py:810-815`). This is 210b0d4's blocker 3, class (c),
  recurring: the cell ran at this base and reached `READY_FOR_REVIEW` with
  `criteria` and `revert` blocking. **Disputed.**
- **SA-0061 2** (no mutants, and criteria 1–3 pass wrong builds): holds.
  `runner.py:299` defaults `acceptance` to `()`, and `witness.py:117-121` then
  returns `skip`; the tier is `current_tier` (`session.py:952`). Criterion 3's
  half is 210b0d4's blocker 2 (*New finds* 4).
- **SA-0040@08aa1a4 1** (the existing `detail` fields are the free-text escape
  hatch criterion 2 does not ban): holds. `events.py:107-111` calls
  `PhaseStart.detail` "the one place in this vocabulary where prose
  survives", `detail: str` also sits at `:86`, `:195`, `:220` and `:232`, and
  the spec has no `acceptance:` block.
- **SA-0040 2** (the diff is likely over the 600-line ceiling, and the plan
  checkpoint will say so): the size half holds, since the cell's own commit
  `5e3fdf3` is 683 changed lines against `08aa1a4`. The consequence did not
  follow: the plan checkpoint (`artifacts.py:269-272`) did not refuse the task,
  which went on to `MERGED`, and `size` is advisory at `standard`
  (`size.py:4-5`). **Disputed.**
- **SA-0040 3** (`budget_usd: 12` is below the closest rows' plan plus
  IMPLEMENT): the cited figures match the ledger (SA-0019 $1.96 + $12.43,
  SA-0025 $2.93 + $11.68). But the cell finished at $8.45 of $12 with a
  37-turn peak. That is class (b)'s shape, new at this base. **Disputed.**
- **SA-0054@f0fe0c8 1** (criterion 4's witness passes at base): the premise
  holds. There is no `batch` subparser (`cli.py:73-105`), and `revert.py:127-128`
  and `:303-306`, the ontology's `revert` line (always blocking),
  `.saffron/policy.yaml:28` and `DESIGN.md:837` read as quoted. This is fdcbbad's blocker 2, class (c),
  recurring: the cell reached `READY_FOR_REVIEW` at this base. **Disputed.**
- **SA-0054 2** (no criterion requires the adapter to run PACKAGE): holds.
  `_run_cell` packages at `cli.py:469-486`, the loop's runner returns a
  `CellOutcome` (`batch.py:97`), and no criterion names PACKAGE. fdcbbad raised
  it only as a concern.

**Class (a) did not recur.** None of the four raises a missing-dependency
blocker at its real base. The nearest is SA-0054's note 9: `depends_on:
SA-0051` names a spec with no file at `f0fe0c8`, and the same note says the
extraction itself is present. Each class-(a) blocker was an artifact of the
version choice.

### K under two readings

Both readings use recall 18/34, which clears the bar of 17.

**(i) The pre-registered literal rule, with the real-base reviews substituted
for the four class-(a) controls.**
- K = **0**: 0 of 9 real-base blockers, and 0 across the other six controls'
  pre-registered reviews.
- **PASS** (18 ≥ 17, 0 ≤ 2).
- Disputed under this reading: 7. That is the four above, plus SA-0060 3,
  SA-0027 1 and SA-0055 1, carried over from the pre-registered reviews.

**(ii) The same, with classes (b) and (c) counted false because their cells'
outcomes contradicted them.**
- The five blockers are SA-0060 3, SA-0027 1 and SA-0055 1 from the
  pre-registered reviews, and SA-0061 3 and SA-0054 2, which recur at the real
  bases (SA-0061@95e9b95 1, SA-0054@f0fe0c8 1). Each of those two is counted
  once, from the real-base review.
- K = **5**. **FAIL** (5 > 2).
- Not among the five, and disputed: SA-0040@08aa1a4 3 fits class (b)'s
  definition, and SA-0040 2's consequence was contradicted by the outcome.
  Counting them under (ii) gives K = 6 or 7, a FAIL either way. Under (i)
  neither is false.

The operator rules on (b) and (c).

### Cost

$8.23 across the four re-reviews (`total_cost_usd`: SA-0062 $1.95, SA-0061
$2.10, SA-0040 $2.30, SA-0054 $1.89; 35–42 turns; no error records). This is
outside the $71.38 above.

## Operator's ruling, 2026-09-14

**FAIL.** The operator ruled the five remaining disputed control blockers false:
SA-0060 3 and SA-0027 1, whose ceilings "too low" was contradicted when both
specs finished inside them; and SA-0061 3, SA-0054 2 and SA-0055 1, whose
"witness already green at base" was contradicted by each cell's `criteria` and
`revert` gates. The last two recur at the real bases. That makes K = 5 against
a bar of 2, with recall 18/34 (bar 17). The four class-(a) blockers were
artifacts of the control versions and do not count, since none recurred at the
cells' real bases.

The spec review is **not promoted** to a spec-review cell. It stays advisory,
where Task 3 put it: the spec loop's step 1b and `docs/agents/issue-tracker.md`.
Items 123–125 carry what a second backtest needs.

## Disclosures, 2026-09-15, after the ruling

Found reviewing the pull request. Nothing pre-registered and no result above
changes; these qualify them. Three post-hoc lines were edited with them:
the ruling's heading said "Verdict", the critic's word; reading (ii)'s second
bullet said all five blockers came from the pre-registered reviews, then
counted two from the real-base ones; and the re-reviews' cost read $8.24, a
sum of rounded figures, where the records sum to $8.2258.

- **The cases' wording changed after pre-registration.** `d38df7b` rewrote every
  defect's text after `872f4ff` committed the bar, and before any scored
  review. The new text is the design's Appendix A, and several rows gained
  outcome figures: SA-0031's "ceilings too low for its width" became
  "`EXHAUSTED` at 141 of 140 turns, $19.17 of $18". The reviews never saw this
  file, so only the scoring read it. The bar, the versions, the controls and
  the scoring rule did not change. *The Correction*'s "unchanged" holds for
  those four and not for the wording.
- **The shipped spec review is not the one scored.** After the ruling:
  - `28021f8` split REPAIR out of `history`'s implement column and widened
    check 4's budget blocker to "the plan checkpoint, IMPLEMENT and REPAIR".
    The scored `history` already summed REPAIR into implement, so the figures
    compared are the same, but the label is new.
  - `d29a9fd` made a blind `history` rank past cells by their specs' text at
    the base. The scored reviews' rows were ranked by today's text.
  - `19f15ec` reworded the prompt's description of a cell and gave `base` a
    default.

  No review was re-run, so the result above is evidence about the scored
  version. A second backtest scores the shipped one (item 125).
- **K could be higher.** Under reading (ii), SA-0040@08aa1a4's two disputed
  blockers give K = 6 or 7. The ruling counted five, and the result is FAIL
  either way.
