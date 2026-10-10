# Rejections

`DESIGN.md` §8's flywheel input, for this repo as a target of itself. One line of
*why* per rejection, triaged into exactly one bucket, and what became of it.

**Reread this monthly, not weekly.** At 6–12 pull requests a week you get 2–6
rejections; week-over-week accept rate on n≈8 swings ±20 points from two tasks
and means nothing. The reading is a habit, not a report — each reread appends
its own dated section at the bottom.

**Buckets, cheapest first** (`CONTEXT.md` §9). **1** a gate, if it is mechanically
checkable. **2** a line in `CLAUDE.md`, if it is judgement the agent could apply
given context. **3** a critic lens amendment, if it is a defect class gates cannot
catch. A rule's whole life is a migration toward bucket 1.

**Every entry dated before 2026-09-09 is backfilled**, reconstructed from
`git log --grep='^review-fix(SA-'`, the eight-pull-request table in
`docs/superpowers/plans/2026-09-07-trusting-the-queue.md`, and the backlog items
each round filed. They were not written at rejection time. A record that does not
say which of its lines came after the fact has the same defect as an estimate
stored in a column named for a measurement.

**Landings are one of three words**, so a reread is a grep (§8): **Landed** — a
gate's name, or a backlog item marked done; **Open** — with the item that tracks
it, if one does; **Inert** — landed somewhere nothing reads. **No bucket** marks a
rejection that names a mechanism which does not exist: it becomes a spec, not a
rule, and *exactly one of three* is not available for it.

**Adding one:** append under today's date — one line of why, the bucket, and its
landing. An entry dated on or after 2026-09-09 was written when the rejection was.

---

## 2026-09-04 — `SA-0045`, `SA-0048` (fixes landed via #123)

- Two tests named a behaviour they did not guard, and the adequacy lens showed
  neither would have noticed the code being wrong.
  **Bucket 1** — **Landed:** `witness`, which mechanises exactly this question;
  declared by `SA-0058`, which found it built and reachable by nothing. Item 80 is
  why a spec author still cannot declare a mutant safely.
- A preflight failure that takes the whole batch down was skippable by its caller.
  **Bucket 2** — `error` ≠ `fail` is already a `CLAUDE.md` invariant, and this is
  the judgement it exists to supply. **Landed:** the line every phase reads, from
  `fix(session): the implementer never saw the repo's CLAUDE.md, so bucket 2 had
  no reader` (IMPLEMENT) and `fix(review): no lens was shown the invariants it
  judged a diff against` (the lenses).

## 2026-09-05 — `SA-0055` (#131)

- An assertion guarding the regression could not see it.
  **Bucket 1** — **Landed:** `witness`.

## 2026-09-05 — `SA-0056` (#135)

- The guard against a moved tree was dead for the default mutant.
  **Bucket 1** — **Landed:** `witness`.

## 2026-09-05 — `SA-0057` (#136)

- A `return` inside a `finally` swallowed the operator's Ctrl-C, in a core gate.
  **Bucket 1, and the gate does not exist.** ruff selects `B`, and B012 does not
  see a `return` nested inside a `try` inside a `finally`. CPython 3.14 does: this
  was the only file under `saffron/` emitting
  `SyntaxWarning: 'return' in a 'finally' block`. **Open:** item 96 — which found
  the obvious gate would pass in the cell, whose interpreter is 3.12 and has no
  such warning.
- The fix for the swallowed interrupt was itself unwitnessed — three branches
  mutated to `pass` with the file green.
  **Bucket 1** — **Landed:** `witness`.

## 2026-09-05 — `SA-0058` (#139)

- A pre-flight probe's docstring claimed it proved subset filtering when it proved
  only tolerance, so `witness` reported `pass` for a claim nothing checked.
  **Bucket 3** — a claim the code does not support is the contract lens's subject.
  **Open.**

## 2026-09-05 — `SA-0060` (#148)

- "could not restore" was said about a mutant that was never applied — the loudest
  thing that gate says, said falsely.
  **Bucket 3** — correctness. **Open.**

## 2026-09-06 — `SA-0058` (#139), after its review-fix

- `witness` is built, wired, and cannot run — the `tree` it needs does not exist
  in a cell.
  **No bucket** — a missing mechanism, not a rule. **Landed:** item 71. The plan's
  footnote credits items 71–73 to `SA-0059`; item 71 itself says it was found
  reviewing #139, and the item is the primary record.

## 2026-09-06 — `SA-0060`, second round (#148)

- The commit that corrected four comments left three wrong, one of them twenty
  lines above its own correction.
  **Bucket 1, partly built** — a citation guard exists, and shipped shadowing 347
  of the citations it claimed to check (corrected 2026-09-09). Prose that no guard
  reaches is item 87's class. **Open:** item 87.

## 2026-09-06 — `SA-0061` (#150)

- Half of §5.6's elevation rule went unguarded — the by-path half, which is the
  one an operator is most likely to hit.
  **Bucket 1** — **Landed:** `witness`.
- Four comments the `witness` wiring falsified, and no queued spec can reach them.
  **Bucket 1** — item 87's class. **Open:** item 75.
- An agent has no channel to record a fact it is forbidden to fix.
  **No bucket** — a missing mechanism, not a rule. Became `SA-0063` and
  `SA-0064`. **Landed:** item 74.

## 2026-09-06 — `SA-0062` (#154)

- A failed write left the worktree truncated, and a mutant unrestored: two
  critical fixes on one diff, against **0 blockers** from REVIEW.
  **Bucket 3** — and the rejection that turned the lens itself into something
  measured: item 79 built the fixture corpus and a baseline of `3/12`, which
  measures the lens without amending it. **Open:** item 79.
- `witness` mutates before `committed` runs, and the spec that built it says the
  opposite.
  **Bucket 1** — done in code; the `DESIGN.md` sentence is still owed.
  **Open:** item 78.

## 2026-09-07 — `SA-0063` (#158)

- The mutant a witness is judged by is withheld from the prompt and left in the
  worktree.
  **Bucket 1** — **Open:** item 80. #166 landed the detection (item 85); stripping
  the worktree copy waits on a decision about which copy is authoritative.
- The guard against a spec refused on its own criteria never sees 31 of 53 specs.
  **Bucket 1** — **Landed:** item 81, 2026-09-08. The diagnosis was wrong and the
  fix landed anyway.
- A mutant can pin the text a spec dictates or the text an agent writes, never
  both.
  **Bucket 1** — **Landed:** item 82, 2026-09-08 — `intake.py` refuses such a
  mutant at parse.
- A mutant that matches at the base commit kills the task before it starts.
  **Bucket 1** — **Landed:** item 83, #166. The eight-pull-request table does not
  attribute this one to a round; it is placed with its cluster.
- `revert` judges a witness whose subject the spec forbids.
  **Bucket 1** — **Landed:** item 84, #166. Arrived through the notes channel item
  74 built, in `SA-0064`'s own `notes.json` — the first rejection this repo
  collected by mechanism rather than by hand.

## 2026-09-07 — `SA-0064` (#160)

- A test's name promised one claim and it makes two, so a maintainer deleting the
  second half is pointed at the wrong phase.
  **Bucket 3** — naming a test for what it proves. **Open.**
- The host runs one copy of a spec and the cell reads another.
  **Bucket 1** — **Landed:** item 85, #166.
- The notes channel's two rendering-side safety properties are unwitnessed.
  **Bucket 1** — `witness`. **Open:** item 86.

## Round not recorded — prose cluster

- Two prose claims about the core gate set went stale where no guard reaches.
  **Bucket 1** — **Open:** item 87. No round in the record attributes it; a
  rejection whose pull request cannot be cited is itself worth noticing.

## 2026-09-14 — `SA-0078` (#243)

- The fix's comment named IMPLEMENT for the REPAIR turn its message reaches, and
  called itself the one place the edit could leak when the `unproven` note is
  another; a later test argument and a backlog citation were stale the same way.
  **Bucket 3** — a comment's claim checked against the code it describes. **Open.**
- A nine-line cross-reference comment above one call. The operator's terse-comment
  rule lives in a `CLAUDE.md` no cell reads; three of this stack's four diffs broke it.
  **Bucket 2** — the rule, in the repo's own `CLAUDE.md`. **Open.**
- A mutant that does not apply still carries its `find` text into the critic's prompt
  through the `unproven` note.
  **Bucket 1** — **Open:** item 114.

## 2026-09-14 — `SA-0082` (#244)

- The submodule witness passed with the flag swapped for `-c diff.ignoreSubmodules=none`,
  which the spec's own table called equivalent and a committed `.gitmodules` defeats.
  **Bucket 1** — `witness`, had the spec declared that mutant. **Open.**
- A docstring quoted a count measured on the probe script's fixture for a test that
  builds a different one, and named the host's git where the read runs on the cell's.
  **Bucket 3** — a measured number checked against what it was measured on. **Open.**
- `tests/test_package.py` restates `DIFF_FLAGS` — five flags of eleven — under a
  fixture that says it is shaped exactly like `export_patch`'s output.
  **Bucket 1** — a structure rule refusing a second definition. **Open:** item 89.
- The same `.gitmodules` hides a gitlink from PACKAGE's scope listing and the
  mirror's `changed_files`, neither of which carries the flag.
  **Bucket 1** — **Open:** item 115.

## 2026-09-14 — `SA-0083` (#246)

- The `advice.graftFileDeprecated` override had no witness: deleting it left every
  test green.
  **Bucket 1** — `witness`, one mutant per pinned line. **Open.**
- An eleven-line comment beside neighbours of two or three. The same rule as
  `SA-0078`'s second line.
  **Bucket 2** — **Open.**

## 2026-09-14 — `SA-0079` (#245)

- The memo witness's stub only ever answered present, so a memo that forgets an
  absent answer — the case `probe()`'s docstring gives as its reason — passed.
  **Bucket 1** — `witness`, a second declared mutant. **Open.**
- The hang witness left a `sleep 300` running for five minutes on every run.
  **Bucket 1** — a suite-level check for processes a test leaves behind. **Open.**
- REBUT fixed the adequacy blocker and kept the lens's counterexample in the
  comment as "`probe()`'s own 60s bound", which `probe()` does not have.
  **Bucket 3** — the rebuttal verdict reads the comment as well as the code. **Open.**
- `_call`'s timeout kills only the runtime's own process, so one that forks leaves its
  children running.
  **No bucket** — **Open:** item 116.

## 2026-09-14 — `SA-0080` (#247)

- The witness for "nothing already read is read or parsed again" failed at base only
  because base's count-based slice dropped an event: a follower re-parsing the whole
  log each poll and keeping its tail passed it and the full suite.
  **Bucket 1** — `witness`, had the spec declared a mutant for its headline claim. **Open.**
- The offset reader's comment claimed `read_log`'s per-line tolerance for an
  undecodable line; `read_log` decoded the whole file and raised on one bad byte.
  **Bucket 3** — a comment's claim checked against the code it describes. **Open.**
- The implementer proved its witness failed at base by checking base's source out
  into `/work`, ran out of turns before restoring it, and its first attempt's gates
  failed on its own dirty tree.
  **Bucket 2** — a `CLAUDE.md` line: prove a witness against base somewhere other than
  the worktree being packaged. **Open.**

## 2026-09-14 — `SA-0081` (#248)

- The two-task fixture left the newest task live, so a cut after the last `Terminal`
  instead of at the last `Ceilings` passed every test while rendering nothing once
  that task finishes.
  **Bucket 1** — `witness`, a declared mutant on the boundary's own line. **Open.**
- `follow`'s docstring called the first poll's events "that first batch"; a batch is
  a night.
  **Bucket 3** — a closed-vocabulary word used in another sense. **Open.**
- The pass-through witness's fake gave the new keyword a default, so a caller that
  omitted it passed; the flag's help text carried the spec's design note to operators.
  **Bucket 3** — a fake that cannot fail the way its docstring says. **Open.**

## 2026-09-14 — `SA-0084` (#249)

- Both control-byte witnesses ran every code point through the helper directly and
  handed the renderer only ESC and BEL, so a render stripping just those two passed
  the criteria that say "every control character".
  **Bucket 1** — `witness`, a mutant that narrows the strip. **Open.**
- One `Terminal` branch still printed the runtime's own `subtype` and
  `terminal_reason` raw — the two fields the agent-event renderer already cleans.
  **Bucket 1** — a structure rule: every `describe` branch interpolating an event
  field goes through the cleaner. **Open.**
- The new bound's comment called its reasoning measured and stated the measurement
  backwards — 160 "already clips" a 91-character line from a render the bound never
  touches — citing the backlog for an instruction that was the spec's.
  **Bucket 3** — a measured number checked against what it was measured on. **Open.**
- The clip's docstring contradicted itself on which fields pass through it, and the
  diff called cell-written text "model-authored", where "model" names an identifier.
  **Bucket 3** — **Open.**

## 2026-09-14 — `SA-0085` (#250)

- The new baseline line was prefixed `criteria:`, reading as a `criteria` gate result
  on the event whose line above reports `criteria=skip`.
  **Bucket 3** — a line family named after a gate that did not run. **Open.**
- The shared rule's docstring said `_judge` asks it after a witness has failed, when
  it asks after the witness passed at head; two docstrings promised a failure on the
  first attempt that `witness-failed` pre-empts whenever head fails the witness.
  **Bucket 3** — a comment's claim checked against the code it describes. **Open.**
- The first witness's "before the first turn" was anchored on a line logged after the
  first turn, so the naming could be held past it; and its "unreadable baseline" case
  covered only the half any implementation passes, not failures keyed off node ids.
  **Bucket 1** — `witness`, a mutant per clause of the claim. **Open.**

## 2026-09-14 — `SA-0086` (#255)

- Re-verifying every packaged commit sent every body down `pr_body.py`'s
  `"packaged"` branch. Its reason, "because the base moved", is false on the
  unmoved-base path most tasks take. The file was forbidden, and the review fixed
  it there by operator decision.
  **Bucket 3** — a changed value's consumers, read for what they now say. **Open** — item 118.
- The unmoved-base witness stubbed `reverify` with `lambda **_k` and never read its
  arguments, so re-verifying the cell's own head passed all 136 tests.
  **Bucket 1** — `witness`, a declared mutant on `packaged_sha`; the spec declared none. **Open.**
- The stacked-child note has no witness: `tree_base` → `base_sha` in the `moved`
  test survived the whole file.
  **Bucket 1** — `witness`, the same kind of mutant. **Open** — item 121.
- Three comments called the cell's gate results a "verdict", and two test comments
  still tied re-verification to a moved base. The rewritten docstring retold
  Appendix Q instead of citing §5.7, and its parameter carried `tree_base` under
  the name `base_sha`.
  **Bucket 3** — a closed-vocabulary word used in another sense, and comments read
  against the rule the diff changed. **Open** — the spec's own text says "verdict" (item 118).

---

## First reading — 2026-09-09

*Corrected 2026-09-10.* The first version counted five entries open whose items
had landed on 2026-09-08 (81–85 — read off the backlog's tier index, which keeps
done items, rather than their Status lines), omitted item 71's entry, said nine
specs for eleven, and dated `SA-0062` a day late. The counts below are
re-derived from the file — `grep -c '^  \*\*Bucket 1'` and its siblings, and
`grep -c` on each bolded landing word. The item-96 paragraph was added the same
day.

The backfill's own output, and the first time §8's two heuristics have been read
off counts rather than impression. Twenty-four rejections across eleven specs.

| Bucket | Count | |
|---|---:|---|
| 1 — a gate | 17 | 10 landed (5 by `witness`, 5 as items 81–85), 7 open |
| 2 — `CLAUDE.md` | 1 | landed in every phase |
| 3 — a lens | 4 | all open |
| No bucket | 2 | both became work, both landed |

**"If most rejections keep landing in bucket 3, your gates are too weak" does not
fire.** Seventeen of twenty-four are mechanically checkable, and ten of those
seventeen have landed. Bucket 1 is where rejections close. The seven it leaves
open are a queue, and the backlog ranks one of them (item 80) tier 1.

**Bucket 3 is the one that has not moved.** Four entries, none landed. Item 79
made the lens measurable — a corpus and a `3/12` baseline — which is the
precondition for amending one, not an amendment.

**Bucket 2 has one entry and it is inert.** Item 7 means no rejection can be
answered by a `CLAUDE.md` line today, so the middle of the flywheel is not merely
underused — it is disconnected. One sample is not a rate, but the count cannot
grow while the bucket has no reader.

**One bucket-1 destination was named here and filed nowhere** *(added
2026-09-10)*, and filing it (item 96) found that the obvious version is a trap.
CPython 3.14 names the Ctrl-C defect at compile time. Ruff's four `finally` rules
don't, and neither do CPython 3.12 or 3.13 — and the cell runs 3.12.14. A compile
gate declared the ordinary way would pass the one defect it exists to catch.

**`witness` is the flywheel working, and it has a cost.** Five rejections about
tests that guard nothing were answered by one gate, which is §8's `revert`
precedent repeating. Wiring it produced rejections of its own: items 71, 78, 80,
82, 83 and 84 are each `witness` unable to run, mutating in the wrong order, or
judged by a mutant that cannot be declared safely. Four of the six have landed;
78's `DESIGN.md` sentence and 80's stripping are open. That is not an argument
against promotion — it is the cost of it, and it belongs in the reading rather
than in a footnote.

## 2026-09-15 — `SA-0087` (#274)

Three lenses raised two concerns between them, both adequacy, both about a
witness that cannot fail; the independent review found six more. The two the
critic did raise are not repeated here.

- `git add -A` in the critic cell re-ran the clean filters the patch's own
  `.gitattributes` installs, so the agent could end its own task as
  infrastructure — `ORPHANED`, exit 2, charged to nobody, no lens run, and
  re-queued. Measured: a `working-tree-encoding=UTF-16` attribute committed
  after the file it names leaves `git apply` at 0 and `git add` at 128.
  **Bucket 3** — an agent-controlled input that reaches an uncharged end; no
  gate reads which exception a control path raises. **Open.**
- Four more witnesses passed under mutants that break what they claim: the
  teardown one was satisfied by `critic_cell`'s own pre-clean, which removes the
  same three names before anything is created; the creation one asserted a
  container *name*, so deleting `prepare_worktree` entirely survived; the commit
  had no test at all; and the new commit-failure classification had none either.
  **Bucket 1** — `witness`, had the spec declared those mutants. **Open:** item
  80 is why a spec author still cannot declare one safely.
- The critic cell's `git apply` and `git commit` bypass `worktree._git`, so none
  of the pins items 102, 103 and 110 bought reach them.
  **Bucket 1** — a structure rule refusing a raw `runtime.exec_` git call
  outside `worktree.py`. **Open:** item 136.
- `cell_up`'s docstring still said a second caller cannot get a *nearly*
  isolated cell, with `critic_cell` — that second caller — directly below it.
  **Bucket 3** — a comment's claim checked against the code it describes, the
  same line as `SA-0078`'s first. **Open.**
- The `MAX_ARG_STRLEN` comment named "this same image" for a figure measured
  against `saffron/cell-base:python`, and the `ponytail:` marker sat mid-sentence
  where every declaring marker in `saffron/` starts its own line.
  **Bucket 3** for the measurement's subject; **Bucket 1** for the marker, whose
  placement is mechanically checkable. **Open.**
- `EXHAUSTED` gained a third way in — the exported patch did not apply — that
  neither `CONTEXT.md` §6 nor `DESIGN.md` §3.3 describes, while `GATE_ERROR`'s
  arrow was widened for the critic cell in the same revision.
  **Bucket 1** — the vocabulary test, which already reads the closed sets.
  **Open:** item 132.
- Three live sentences say the lenses still run in the implementer's cell, each
  scoped to all of `SA-0087`–`SA-0089`, so no single spec's `scope` gate catches
  them going false; and `session.py` now carries three copies of the teardown
  closure and two of the leak-report loop `cell_down` records the cost of
  paraphrasing.
  **Bucket 1** — a structure rule for the duplication; the sentences are
  **Bucket 3**. **Open:** items 133 and 134.
- The critic cell shares its network with the implementer's container, which is
  not torn down until after REVIEW, so the rootfs guarantee is established and
  the network one is not.
  **No bucket** — it names a probe that does not exist. **Open:** item 135,
  behind item 127.


## 2026-09-16 — `SA-0088`–`SA-0092` (fixes landed on #277, #278, #279, #282, #284)

Five specs in one loop, stack #285. The three in-cell lenses filed **one** blocker
across five cells; the two independent seats filed **twelve**, and eight of those
mutants passed the *entire* default suite. Every line below is a rejection the
lenses did not raise.

- Three of item 118's four slices shipped the same omission: a witness that
  records the fact its criterion turns on and never asserts it. `SA-0088` read
  which container the verdict diff came from and asserted only where the session
  ran; `SA-0089` never read `cell.execs` for the gate-only cell, so deleting the
  patch apply made the lenses' table a measurement of the bare base tree;
  `SA-0091` could take a second export from the implementer's own `.git`. Each
  left the whole suite green. `SA-0087` was amended for this exact shape and both
  later specs carry the corrective note.
  **Bucket 1** — the `criteria` gate knows a criterion's claim and its witness;
  what it cannot yet ask is whether the witness *reads* the seam the claim names.
  **Open:** items 140, 141, 148, 149, 150.
- A teardown witness satisfied by the pre-clean. `critic_cell` and
  `_gate_cell_suite` both remove their names before creating anything, so
  membership and ordering hold with the whole `finally` deleted; only a count of
  two can tell. `tests/test_session.py` explains this in a comment one screen
  above the witness that then did not do it.
  **Bucket 1** — a rule, or a shared assertion helper, for teardown witnesses on
  a lifecycle that pre-cleans. **Open:** item 140.
- Direction words and boundary cases witnessed in one direction only. `SA-0092`'s
  ceilings line read "above by 0t" at exactly the threshold its only consumer
  calls a blocker, and hardcoding both direction words passed 2075 tests.
  **Bucket 3** — a lens that asks, of any rendered comparison, whether both
  directions and the equality case are observed. **Open:** item 123.
- An env carried from policy, witnessed against a policy that declares none, so
  `env={}` and `env=dict(thread_env)` were indistinguishable; and two assertions
  that read as the credential check while being tautologies against `== {}`.
  **Bucket 2** — a `CLAUDE.md` line: a witness for "carries X and nothing else"
  needs a non-empty X. **Open.**
- Prompt prose judged as prose rather than as contract. `SA-0091`'s `withdrawn`
  rule — the sentence that licenses a withdrawal — still said "the diff" with two
  diffs below it, and reverting the "What to emit" disambiguation passed the
  entire suite. The spec named the second sentence and not the first.
  **Bucket 3** — the lenses read `saffron/agents/prompts/**` as text; nothing
  asks whether an instruction is true of every prompt the code can render.
  **Open.**
- Comments asserting the opposite of the code beside them: `_judge`'s said
  `latest` is kept because "the critic is shown the gate results" in the same
  revision that stopped showing it, and four new comments cited `CONTEXT.md` §5
  and item 118 for a claim neither source makes. Same line as `SA-0078`'s first
  and the `cell_up` docstring above it.
  **Bucket 3** — a comment's claim checked against the code it describes. **Open.**
- An operator-facing message naming the wrong cell on the exit-2 path:
  `_apply_and_commit_patch` said "in the critic cell" once the gate-only cell
  reached it first. The sibling message one screen away was fixed in the same
  diff, so the author saw the class and missed this member.
  **Bucket 1** — mechanically checkable: a message naming a cell inside a helper
  with more than one caller. **Open:** item 142, which is where the vocabulary
  for the third cell has to land first.
- The loop's own tooling rejected three times, which is new: `size` measured a
  stacked child against the default branch and reported a 176-line overrun that
  was 123 lines of headroom; `pattern` showed a salvage starting and never its
  outcome; and editing a spec with an open pull request silently refused its
  dependents and dropped its pull request from the stack.
  **Bucket 1** for all three. **Open:** items 137, 138, 139.

## 2026-09-17 — `SA-0093`, `SA-0094`, `SA-0095` (stack #308: #303, #305, #307)

- A witness for "given a name, it uses that network" checked which networks
  were created and removed, never which one the container was put on. The
  whole default suite passed with `prepare_worktree` handed another network,
  which is Appendix I's failure exactly. Three clean lenses preceded it (#303).
  **Bucket 3** — the adequacy lens asks what a witness observes, not what the
  claim says the code does to the cell. **Open.**
- Three lines the refactor moved had no test that could see them move: REBUT's
  critic cell getting the proxied env, the unreadable-proxy raise, and the
  Gate-only cell's network going last and into `created` (#303).
  **No bucket** — a guard for a property already true at base cannot be written
  in a cell, because `revert` fails any new test that passes without its
  source. The review wrote them. **Open:** item 159.
- `critic_cell` choosing Gate-only or critic names from `network is None`,
  against `CONTEXT.md`'s "it is not the critic cell" (#303). Kept.
  **Bucket 3.** **Open:** item 155.
- A pre-clean witness with one `saffron-` holder, listed first, so a filter
  narrower than the prefix or a first-holder-only loop passed (#305).
  **Bucket 3** — same class as the first line. **Open.**
- `networks_on_subnet`'s docstring still said it "only ever adds detail to an
  error" in the diff that made a pre-clean act on its answer (#305); and #307's
  new comment said a `GATE_ERROR` REVIEW keeps "the table its lenses were
  shown" above a branch where no lens runs.
  **Bucket 3** — a comment's claim checked against the code it describes, as
  on 2026-09-16. **Open.**
- A witness for "every result the suite produced" checked the list had more
  than one entry, and drove clean and aborted suites but not the drifted one
  its claim names; the indent was unpinned too (#307). The adequacy lens raised
  the subset half; the drifted case and the indent were the seats'.
  **Bucket 3.** **Open.**
- New comments of seven to thirteen lines restating the spec, and "the gate
  cell" and "a SIGKILLed run" in new lines, in all three.
  **Bucket 2** for the length — no line in this repo's `CLAUDE.md` says it.
  **Bucket 1** for the words — the retired-vocabulary hook does not list them.
  **Open:** item 156 for the words.

## 2026-09-17 — `SA-0096`, `SA-0097`, `SA-0098` (stack #320 ← #321 ← #323)

- A witness for "the reason carries no part of the find text" ended its absent
  find text on `MISSING`, not on the token the spec said to put at both ends,
  so a reason leaking the tail passed (#320). Three clean lenses preceded it.
  **Bucket 3** — the adequacy lens asks what a witness observes, and a
  token placed only at one end observes half the claim. **Open.**
- New docstrings that misstated the code beside them: #320 routed the leak
  through REPAIR, which `repair_prompt` says never sees a gate summary; #323
  left `Agent` calling `detail` host-only while `_clean`'s now said otherwise,
  and said `cell_up` carries runtime output when its one emitter writes a
  container name; #321 named one of `DIFF_FLAGS`'s two reasons where the spec
  said to name each.
  **Bucket 3** — a comment's claim checked against the code it describes, as
  on 2026-09-16. **Open.**
- #323's witnesses drove steps no emitter uses (`container` for a denial,
  `proxy_start`), where the spec names `proxy_denied` and spec drift.
  **Bucket 3.** **Open.**
- "a REBUT-round lens" in a new test docstring (#320), and new comments of four
  lines where the spec asked for a short one (#321).
  **Bucket 1** for the word — `terms` neither lists it nor reads Python.
  **Open:** item 174. **Bucket 2** for the length. **Open.**

## 2026-09-18 — `SA-0104`, `SA-0099`, `SA-0100`, `SA-0103`, `SA-0105` (stack #335 ← #338 ← #339 ← #342 ← #340)

- A witness for a claim about the value a row keeps, or the note it carries,
  that started from a state every wrong implementation also leaves: a refused
  write asserted `None` on a row that was already `None`, so a refusal that
  cleared the row passed (#338). The preserves witness for "no backfill" never
  read the column (#338). No test pinned an unpushed row's note, so an empty or
  invented note passed (#339). Each probe survived every test until the seats'
  review commit.
  **Bucket 3** — the adequacy lens asks what a witness observes. The spec
  review predicted the #338 backfill gap before the cell ran. **Open.**
- Four docstrings and comments still describing the one-argument write the
  diff replaced (#335). #342 said an import was local to keep it out of `revert`'s
  collection when the name was not new, and #339 cited a `CONTEXT.md` gap
  and section that do not exist.
  **Bucket 3** — a comment's claim checked against the code it describes, as
  on 2026-09-16 and 2026-09-17. **Open.**
- A chunk size 23% under a cap measured once, on a cell runtime the comment
  does not name, where the same runtime wedged a cell on an oversize exec
  before (#335). The operator chose 64 KiB.
  **Bucket 3** — a margin against a single measurement is a judgement the
  critic did not make. **Open:** item b-bc9951.
- New comments of 7 to 18 lines in all five pull requests, including an
  18-line docstring where #340's spec asked for "a short comment on the read".
  Every one was cut by a review commit.
  **Bucket 2** — the third loop running with this rejection, and still no line
  in this repo's `CLAUDE.md` says it. **Open:** item b-122686.
- A branch 14 lines over its `size` ceiling, most of it six hand-built test
  doubles differing in two fields (#339). The review folded them into one
  builder and landed at 293.
  **Bucket 1** — `size` measured it, and nothing reaches the cell before
  PACKAGE to say so. **Open.**
- A `warned` flag beside a before/after comparison that already warns once,
  because the flag it compares never resets (#342). Every probe of either guard
  alone survived.
  **Bucket 3.** **Open.**

## 2026-09-19 — `SA-0101`, `SA-0102`, `SA-0107`, `SA-0108`, `SA-0106` (stack #351 ← #360 ← #355 ← #366 ← #353)

Every line below was fixed in the pull request's review commit: `13f3dfa`
(#351), `1be044a` (#360), `5bce64a` (#355), `5b838d4` (#366) and `9a8e7c4`
(#353). Not listed, because the critic raised them: #351's stale "ten kinds"
counts and its `bool` and `None` reopen times, #355's kept docstring and its
same-second span, and #366's per-reason lines.

**#351 (`SA-0101`)**

- `when()`'s docstring still named a caller the diff removed and a truthiness
  guard the diff replaced, and `TaskOutcome`'s docstring cited the
  `FINDINGS[0]` entry the same diff deleted.
  **Bucket 3** — a comment's claim checked against the code it describes, the
  fourth loop running. **Open.**
- A reported reopen time of `0` now renders, where the old guard printed none.
  The pull request called it a behaviour change, and no test drove it.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- The spend a rate-limited outcome writes to the event log was never asserted,
  only the spend it returns.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.

**#353 (`SA-0106`)**

- Criterion 1's witness passed a start line printed after the runner call,
  and criterion 3's fake ignored the rescan's return, so a dropped rescan
  passed. Three lenses were clean with no findings.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- Five over-limit docstrings grew (`run_batch` from 33 lines to 53), three new
  comment blocks were added, and three older comments lost their reasons,
  item 70's among them, so the per-file count stayed level.
  **Bucket 1** — `prose` measured it and counts per file. **Open:** item
  b-044ae7.
- "a task *this same run* left in flight", where the thing meant is the batch.
  **Bucket 1** for the word — `terms` does not read Python. **Open:** item 174.
- False claims in `_batch_runner`'s docstring, checked against the code by the
  delegate.
  **Bucket 3** — a comment's claim checked against the code. **Open.**

**#355 (`SA-0107`)**

- The spec lookup read `.saffron/specs/` and missed `done/`, so 75 of 76
  merged tasks were left out. Found only by running the module over a copy of
  the real ledger.
  **Bucket 1, and the gate does not exist.** **Open:** item b-a8270f.
- Every task got an authored `Phase` and an `Attempt` with `n=1`, which
  Appendix T forbids and the spec's notes named.
  **Bucket 3** — the contract lens reads the spec's notes against the diff.
  **Open.**
- Plan-only and diff-only tampering were not told apart, a missing plan had no
  witness, the sibling chain's kinds were never asserted, and nothing checked
  that a mismatched `Diff` stays a finding's subject.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- A task left out still left triples in the graph.
  **Bucket 3** — the adequacy lens asks what a failed path leaves behind, as
  item 79 found. **Open.**
- `_SPEC_TYPES` restated the shapes' closed set in Python.
  **Bucket 1** — a test can compare the two. **Open:** item b-60d804.
- The projection was written in place, so a failed write could leave half a
  file.
  **Bucket 3.** **Open.**

**#360 (`SA-0102`)**

- The attempt witness passed a rebuttal set that borrowed attempt 2's gates, a
  skipped gate carrying a count, and a passing gate without its zero.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- `describe`'s `GateResult` comment said where the kind is emitted, not what
  its rendered line leaves out. The comment on `against: "rebuttal"` having no
  owner named no item (item 160).
  **Bucket 3** — a comment's claim checked against the code. **Open.**

**#366 (`SA-0108`)**

- The walk took its pull request from the caller, not the ledger, and nothing
  witnessed the ledger read. The break line's task id had no witness either.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- The module and `_chains` docstrings restated the spec.
  **Bucket 2** — `CLAUDE.md` says it since #346, and the cell read it. **Open:**
  item b-044ae7 for the gate half.

## 2026-09-19 — `SA-0109`, `SA-0110` (the spec loop's run 9; fixes in #375, #377)

**#375 (`SA-0109`)**

- A probe cell that failed to come up left `_probe_adequacy` as an exception,
  past every handler, so the task reached no state and a completed, paid REVIEW
  was never written. The spec's own `## Problem` says that case leaves every
  finding as filed. Three lenses were clean.
  **Bucket 3** — a spec body's stated behaviour with no criterion is exactly
  what a contract lens is for. **Open:** item b-a70ec1 is its sibling gap.
- Nothing pinned `probes.json`'s entry shape: its `findings` list, each
  finding's filed severity and all four baseline fields could be emptied with
  no test noticing.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- The REVIEW line labelled `probes:` counted findings while `probes.json`
  counts distinct edits, so the two disagreed on the one path no witness
  covered.
  **Bucket 3** — a rendered line checked against the record it summarises.
  **Open.**
- `probe_verdict` restated the `Verdict` literal that `saffron/probe.py`
  defines and the same diff already imported, and its docstring named one
  reader where the diff adds two.
  **Bucket 2** — `CLAUDE.md`'s "One source", and a comment's claim checked
  against the code. **Open:** item b-044ae7 for the gate half.

**#377 (`SA-0110`)**

- Two witness modules bound `KINDS["adr"]` at module scope, so the reverted run
  raised at import and `revert` reported `skip`: the anti-theater gate checked
  nothing for the whole diff. The spec had a section ordering the lazy lookup.
  **Bucket 1** — a `skip` caused by a collection error is the gate's own
  success condition misread. **Open:** item 50.
- The `--status` witness passed an ADR status, which argparse refuses before
  the branch under test runs, and its assertion matched the usage line. The
  probe dropping that half of the guard survived.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- Two criteria planted only half the cases their claims list — the
  `superseded_by` side of "either side", and no id set starting above 1 — so
  three probes survived.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- `ADR_REQUIRED` restated four of five strings from `ADR_SECTIONS`, and
  `check_adr_supersession` rebuilt the `_ids` helper inline.
  **Bucket 2** — `CLAUDE.md`'s "One source". **Open.**

## 2026-09-19 — `SA-0111`, `SA-0112` (fixes landed via #381, #382)

Run 10 of the spec loop. The in-cell adequacy lens raised one blocker per cell
and the host's probe survived both, so each was real and each was fixed inside
the cell. Neither is a rejection. These are what the two independent seats found
after that.

- `record_merged_head` with its `self._db.commit()` deleted survived all 2465
  tests: every witness reads the column back through `ledger._db`, the same
  connection holding the uncommitted row, so durability was unpinned on a
  change whose whole subject is durability.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- Criterion 2 claims a merge with no usable head "still moves the task to
  `MERGED`" and its witness asserted only the in-memory bucket. A mutant that
  appended the bucket and skipped `set_task_state` left the row
  `READY_FOR_REVIEW` while `reconcile` reported it merged, and died only in a
  file outside the spec's `touches`.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- The `merged_head_sha` comment sits below its column against house style for a
  measured SQLite reason the code did not state. The implementer measured it
  and put it only in the pull request's unadjudicated notes, where no gate,
  lens or future reader of `ledger.py` looks.
  **Bucket 2** — `CLAUDE.md`'s "A measured fact beats a reasoned one, and the
  comment says which". **Open:** item b-63ac52 carries the channel half.
- The rewritten `head_moved` comment said what the code does and dropped the
  why the old one carried.
  **Bucket 2** — `CLAUDE.md`'s "A comment is one or two lines naming the
  non-obvious why". **Open.**
- `SA-0111`'s Out of scope ordered three statements into the pull request body
  and none arrived, while the implementer's notes asserted they had.
  **No bucket** — the cell has no channel that reaches the body. **Open:** item
  b-63ac52.
- `_select_rows(limit=12)` made a third spelling of `history`'s row limit, so
  editing the parser default moved `history` alone and left `check` judging 12.
  Measured: at a parser default of 3, `history` printed 3 rows, `check` still
  judged 12, and all 83 tests in the file passed. On the spec's own criterion 2,
  which exists to make the two agree.
  **Bucket 2** — `CLAUDE.md`'s "One module drives a task", in its small form.
  **Open.**
- `(item 145)` cited twice, in a docstring and a test comment, as the source of
  the row-parity rule. 145 is `done`, closed 2026-09-16, `specs: [SA-0092]`,
  and is about check 4's wording. `tests/records/check.py` asserts only that a
  cited item exists, and its `LIVE_SURFACES` does not scan `.claude/` at all.
  **Bucket 1** — a citation check that reads the claim, not just the id.
  **Open:** item b-6a9707 carries the surface half.
- `cmd_check`'s docstring called its exit status a verdict, which
  `CONTEXT.md:285` puts on an `_Avoid_` line and `CONTEXT.md:430-432` reserves
  for the critic. The `terms` gate returns nothing for a `.py` path.
  **Bucket 1** — `terms` reaching Python under `.claude/`. **Open:** item
  b-6a9707.
- The concern said a remainder "may not cover" a cost the same function
  computes exactly, and the docstring omitted the clause the spec asked for.
  **Bucket 2** — a hedge on a measured number. **Open.**

## 2026-09-21, `SA-0113`, `SA-0114`, `SA-0115` (the spec loop's run 11, fixes in #403, #404, #406)

Run 11 of the spec loop. The in-cell adequacy lens raised one blocker per cell,
the host's probe survived each, and each was fixed inside the cell. Those are not
rejections. These are what the two independent seats found after that, each
verified by the delegate before it was fixed or kept.

- `SA-0113` (#403): four witnesses passed with their behaviour broken. A witness
  id appended to the turn prompt, a refused session charged zero, the probes run
  outside the critic cell, and an error entry that drops its claim all survived.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- `SA-0113` (#403): the probe prompt told its session it could not see which
  test guards a claim, while the diff it holds carries every witness. The
  witness docstring made the same claim.
  **Bucket 2**, a claim stronger than the code. **Open.**
- `SA-0114` (#404): no witness sent an anchored bare citation through the
  past-end report, so skipping that check for one passed all three witnesses.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- `SA-0114` (#404): two comments cited "(item 2)" and "(item 5)" meaning the
  spec's own list, in a file where "(item N)" names a backlog item. Both
  resolved, to unrelated finished work, so `check_item_citations` passed them.
  **Bucket 2.** **Open.**
- `SA-0114` (#404): `cite`'s moved-text half was four for four false on its own
  spec, since it matches quoted text as a substring.
  **No bucket**, it needs a better matcher. **Open:** item b-61993a.
- `SA-0115` (#406): thirteen mutants survived all three witnesses. Six were cases
  the spec named and the fixture left out, among them `.iterdir()` and
  `os.scandir` on the parent, a committed file rewritten on disk, the order of
  the output, and a function-local `import os`.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- `SA-0115` (#406): two unresolvable calls on one line printed as one line, since
  `unresolved` was keyed by path and line, against "one line per call".
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- All three pull requests carried em-dashes, semicolons or docstring sentences
  over 25 words in new Python comments, which `CLAUDE.md` forbids. The `prose`
  gate reads no word rule in a `.py` file.
  **Bucket 1**, the `prose` gate reaching Python. **Open:** item b-440f17.

## 2026-09-21, `SA-0116`, `SA-0117` (the spec loop's run 12, fixes in #416, #418)

Run 12 of the spec loop. `SA-0116`'s adequacy lens raised two blockers and the
cell fixed both in REBUT. `SA-0117`'s lens raised one note, on `spec_id`. Those
are not rejections. These are what the two independent seats found after that.
The delegate verified each one before it was fixed or kept.

- `SA-0116` (#416): no witness checked that the three headings print in order,
  or that the first prints with no line under it. Reversing them passed.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- `SA-0116` (#416): the ordinal witness compared against today's date, so a run
  across midnight fails, against a spec note that said so.
  **Bucket 2**, a test that reads the clock. **Open.**
- `SA-0116` (#416): a spec whose file name and `id` disagree raised a bare
  `StopIteration`, against "every other invocation exits 0".
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- `SA-0116` (#416): the fixture patched `SPECS_DIR`, which nothing reads, and
  its docstring claimed every helper read it.
  **Bucket 2**, a claim stronger than the code. **Open.**
- `SA-0117` (#418): five witnesses could not fail for their rule. Gate results
  on the first attempt, a run found without `base_sha`, attempt `n` fixed at 1,
  a write that appends again, and a fold that stops at a broken task all passed.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- `SA-0117` (#418): criterion 7's witness read `updated_at` alone, so the run
  and attempt times it also claims passed when fixed to a constant.
  **Bucket 1, and the gate does not exist.** **Open:** item b-2750d5.
- `SA-0117` (#418): `UnreadableTask` moved into `ledger.py`, and `fold.py`
  re-exported it to `cli.py` and the tests, against the spec's "`fold()` keeps"
  it. The `no-reexport` rule reads only aliases and `__all__`.
  **Bucket 1**, the rule reaching a plain re-import. **Open.**
- `SA-0117` (#418): the finding-id map had no `ponytail:` comment, though the
  spec asked for one, and the comment the diff deleted on `repos.policy_sha`
  had no replacement.
  **Bucket 2**, `CLAUDE.md`'s `ponytail:` convention. **Open.**
- `SA-0117` (#418): a test passed `verdict="w"`, outside the closed set
  `confirmed` and `withdrawn`.
  **Bucket 1**, a typed verdict at the ledger. **Open.**
- `SA-0117` (#418): the SQL was packed onto long lines to pass `size`. Kept by
  the operator.
  **Bucket 1**, the `size` gate's unit. **Open:** item b-89ec93.
- Both pull requests carried em-dashes, semicolons or long docstring sentences
  in new Python comments.
  **Bucket 1**, the `prose` gate reaching Python. **Open:** item b-440f17.

## 2026-09-22, `SA-0118` to `SA-0122` (the spec loop's run 13, fixes in #431, #433, #434, #435, #436)

Run 13 of the spec loop. The in-cell adequacy lens caught `SA-0118`'s sha1
literal, which step 1b had flagged and the delegate deferred. That is not a
rejection. These are what the two independent seats found after each cell. The
delegate verified each one before it was fixed or kept.

- `SA-0119` (#431): new Python comments carried em-dashes.
  **Bucket 1**, the `prose` gate reaching Python. **Open:** item b-440f17.
- `SA-0119` (#431): a docstring credited `revert` with an order of checks it
  does not make.
  **Bucket 2**, a claim stronger than the code. **Open.**
- `SA-0118` (#433): moving `.git/info/attributes` aside and back passed the
  witnesses of criteria 1 to 3. A review commit added an mtime sentinel.
  **Bucket 1**, the spec's arrangement. **Landed:** item b-2750d5's criterion
  probes, by #434, after this cell ran.
- `SA-0118` (#433): docstrings still named the worktree's own config, which the
  diff stopped reading.
  **Bucket 2**, a comment the diff made false. **Open.**
- `SA-0118` (#433): one docstring sentence ran to 43 words.
  **Bucket 1**, the `prose` gate reaching Python. **Open:** item b-440f17.
- `SA-0120` (#434): four wrong implementations passed criterion 1's witness.
  They were drop-rate rules keyed on verdict and on probe, a strip limited to
  `adequacy`, an unasserted lens field and a hard-coded line. Two were step 1b
  findings from round 4, deferred to the Spec seat by rule.
  **Bucket 1.** **Landed:** item b-2750d5, in this pull request.
- `SA-0120` (#434): new prose called a criterion probe a "declared mutant", and
  carried em-dashes, semicolons and sentences over 25 words.
  **Bucket 1**, the `prose` gate reaching Python. **Open:** item b-440f17.
- `SA-0121` (#435): the rewritten `pinned_diff` docstring named config keys the
  flags override, where the measurement was of flag values.
  **Bucket 2**, a comment saying the opposite of the code, whose meaning no gate
  reads. **Open.**
- `SA-0122` (#436): neither witness pinned the `probe` or `reason` values, and
  each left default-valued fields that only the other checked.
  **Bucket 1.** **Landed:** item b-2750d5, by #434.
- `SA-0122` (#436): a `_drive` docstring inverted what `baseline_raises` does.
  **Bucket 2**, a comment saying the opposite of the code. **Open.**
- `SA-0122` (#436): new comments carried em-dashes.
  **Bucket 1**, the `prose` gate reaching Python. **Open:** item b-440f17.

## 2026-09-22, `SA-0123` and `SA-0124` (the spec loop's run 14, fixes in #451, #459)

Run 14 of the spec loop. `SA-0123` ended `EXHAUSTED` before REVIEW ran, so no
in-cell lens saw it. `SA-0124`'s three lenses raised nothing. These are what
the two independent seats found after each cell. The delegate verified each
one before it was fixed or kept.

- `SA-0123` (#451): criterion 1's ledger with no record checked its times only
  after the last write. A `set_task_state` that stamped `datetime('now')` with
  no record attached survived, since later writes overwrote it.
  **Bucket 1**, the spec's arrangement. **Landed:** a review commit on #451.
- `SA-0123` (#451): the diff was 1001 changed lines against a ceiling of 1000.
  **Bucket 1.** **Landed:** `size`, which caught it. Review brought it to 999.
- `SA-0123` (#451): two lookups were written twice, and `create_task` on an
  unknown run raised `TypeError`.
  **Bucket 2**, one source and a clear error. **Landed:** a review commit on
  #451.
- `SA-0123` (#451): three comments and docstrings were false after the change.
  **Bucket 2**, a comment the diff made false. Fixed in a review commit on #451,
  with no gate that reads it. **Open.**
- `SA-0123` (#451): new Python comments carried em-dashes, semicolons and a
  hedge.
  **Bucket 1**, the `prose` gate reaching Python. **Open:** item b-440f17.
- `SA-0123` (#451): three new witnesses read rows through `ledger._db`, which
  the spec forbade.
  **Bucket 2.** **Open:** item b-49329e.
- `SA-0124` (#459): criterion 3's witness read no fact payload. A writer that
  left a key out when its value was `None` passed.
  **Bucket 1**, the spec's arrangement. **Landed:** a review commit on #459.
- `SA-0124` (#459): criterion 4 compared with `==`, so a migration that added
  `REAL` columns passed with 3.0 and 4.0.
  **Bucket 1.** **Landed:** a review commit on #459.
- `SA-0124` (#459): new Python comments carried em-dashes and docstring
  sentences of over 40 words.
  **Bucket 1**, the `prose` gate reaching Python. **Open:** item b-440f17.
- `SA-0124` (#459): a test docstring called a raw `UPDATE` "a fact".
  **Bucket 2**, vocabulary no gate reads in Python. **Open.**

## 2026-09-23, `SA-0125` to `SA-0131` (the spec loop's run 15, stack #484)

Run 15 of the spec loop. These are what the two independent seats found after
each cell and the in-cell critic did not raise, or raised below blocker. The
delegate verified each one before it was fixed or kept.

- `SA-0125` (#473): criterion 3's first run asserted only that the plan was
  not rejected, so a checkpoint that raised after its advisory line passed.
  **Bucket 1**, the spec's arrangement. **Landed:** a review commit on #473.
- `SA-0125` (#473): the advisory line never named its tier as the plan's
  forecast, which the claim asked for.
  **Bucket 1.** **Landed:** a review commit on #473.
- `SA-0125` (#473): `plan_checkpoint`'s docstring grew from 14 to 18 lines.
  **Bucket 1**, the `prose` gate reaching Python. **Open:** item b-440f17.
- `SA-0125` (#473): `judge_estimate` restates `size`'s failure message.
  **Bucket 2**, one source. **Open:** item b-a90136.
- `SA-0127` (#476): `revert` read `uncollected` names it never handed, so a
  never-handed key turned a `skip` into a blocking `fail`. The contract lens
  raised it as a concern.
  **Bucket 1.** **Landed:** a review commit on #476.
- `SA-0127` (#476): no witness drove an errored or unenumerated run that fills
  `uncollected`. The adequacy lens's probe on it was counted killed by an
  unrelated format test.
  **Bucket 1**, the probe runner. **Landed:** a review commit on #476.
  **Open:** item b-19b255.
- `SA-0127` (#476): the new attribute docstring carried a semicolon and an
  em-dash, and a new five-line comment joined an old block.
  **Bucket 1**, the `prose` gate reaching Python. **Open:** item b-440f17.
- `SA-0126` (#478): the re-queue cap's state and repo terms had no witness. A
  re-queued `RATE_LIMITED` task could settle the next cut.
  **Bucket 1**, the spec's arrangement. **Landed:** a review commit on #478.
- `SA-0126` (#478): six test docstrings said a first cut "settles"
  `ORPHANED`, and "retry cap" used a word on two _Avoid_ lines.
  **Bucket 2**, vocabulary no gate reads in Python. **Landed:** a review commit
  on #478.
- `SA-0130` (#480): the new prompt step forbade every wrong version, so it
  overrode `CLAUDE.md`'s one run of a new test against unfixed code.
  **Bucket 2**, the meaning of prompt text. **Landed:** a review commit on #480.
- `SA-0130` (#480): the step had no blank line before it, so its witness read
  step 3's "host".
  **Bucket 1.** **Landed:** a review commit on #480.
- `SA-0131` (#481): a scan reading only each spec's oldest row passed
  criterion 1, and no case reached `merge-base`'s error branch.
  **Bucket 1**, the spec's arrangement. **Landed:** a review commit on #481.
- `SA-0131` (#481): the git helper restated `git_mirror._run` without its
  missing-binary wrap.
  **Bucket 2**, one source. **Landed:** a review commit on #481.
- `SA-0128` (#483): criterion 2's cross-file case moved different tokens, so
  one stream for the whole diff passed it.
  **Bucket 1.** **Landed:** a review commit on #483.
- `SA-0128` (#483): the bound comment credited its measurement to the wrong
  side of the bound, and three new docstrings ran long past the gate's net
  count.
  **Bucket 1**, the `prose` gate reaching Python. **Landed:** a review commit
  on #483. **Open:** item b-440f17.
- `SA-0128` (#483): repair pinned three test ids to the old ceilings to keep
  `census` green.
  **Bucket 2.** **Open:** item b-f30189.

## 2026-09-25, `SA-0133` to `SA-0140` (the spec loop's run 16, stack #507 to #505)

Run 16 of the spec loop. These are what the two independent seats found after
each cell and the in-cell critic did not raise, or raised below blocker. The
delegate verified each one before it was fixed or kept. `SA-0129` (#502) was
taken by hand, so no critic ran on it and it has no lines here.

- `SA-0140` (#501): witness 1 let a prompt file sized under the threshold
  pass, so a wrong bound survived.
  **Bucket 1**, the spec's arrangement. **Landed:** a review commit on #501.
- `SA-0140` (#501): no witness drove the runner's unlink when the session
  raised.
  **Bucket 1.** **Landed:** a review commit on #501.
- `SA-0140` (#501): a test module docstring described the old behaviour.
  **Bucket 3**, a claim no gate reads. **Landed:** a review commit on #501.
- `SA-0140` (#501): the new tests restated helpers the suite already holds.
  **Bucket 2**, one source. **Landed:** a review commit on #501.
- `SA-0139` (#504): a module docstring called a base survivor "not
  inherited", against `CONTEXT.md`.
  **Bucket 2**, vocabulary no gate reads in Python. **Landed:** a review
  commit on #504.
- `SA-0139` (#504): the subtraction lost its counting rationale, which the
  cell cut to fit the docstring limit.
  **Bucket 2**, a `CLAUDE.md` invariant. **Landed:** a review commit on #504.
- `SA-0139` (#504): `_counts` named something other than what it returns.
  **Bucket 2.** **Landed:** a review commit on #504.
- `SA-0139` (#504): `is_no_progress`'s docstring was false.
  **Bucket 3**, a claim no gate reads. **Landed:** a review commit on #504.
- `SA-0137` (#505): an empty-tree `attr.tree` pin passed the witness and
  dropped the repo's committed attributes.
  **Bucket 1**, the spec's arrangement. **Landed:** a review commit on #505.
- `SA-0137` (#505): the pin's comment limited the hazard to global config.
  **Bucket 3**, a claim no gate reads. **Landed:** a review commit on #505.
- `SA-0137` (#505): `harness/recovery.py`'s `pinned_diff` lacks the same pin.
  **Bucket 2**, one source. **Open:** item b-9ead75.
- `SA-0134` (#507): a `file_at` `GitError` caught as unresolved passed every
  witness.
  **Bucket 1.** **Landed:** a review commit on #507.
- `SA-0134` (#507): a bare `"040000"` literal named no mode.
  **Bucket 2.** **Landed:** a review commit on #507.
- `SA-0135` (#510): no witness pinned that an empty `consumes` calls nothing.
  **Bucket 1.** **Landed:** a review commit on #510.
- `SA-0135` (#510): a docstring bullet was false.
  **Bucket 3**, a claim no gate reads. **Landed:** a review commit on #510.
- `SA-0133` (#512): a `Preflight` event was called a fact.
  **Bucket 2**, vocabulary no gate reads in Python. **Landed:** a review
  commit on #512.
- `SA-0133` (#512): a `hashlib` call restated `artifacts.hash_artifact`.
  **Bucket 2**, one source. **Landed:** a review commit on #512.
- `SA-0133` (#512): the new tests restated helpers the suite already holds.
  **Bucket 2**, one source. **Landed:** a review commit on #512.
- `SA-0133` (#512): a `FAMILIES` row named no shape the log renders.
  **Bucket 1.** **Landed:** a review commit on #512.
- `SA-0133` (#512): `_drive`'s docstring grew from 15 to 19 lines and the
  `prose` gate counted no new hit.
  **Bucket 1**, the `prose` gate. **Open:** item b-e88930. A review commit
  on #512 cut the docstring back.
- `SA-0133` (#512): criterion 4's witness never read the `CLAUDE.md` digest.
  The critic raised it, and a probe killed through another test demoted it.
  **Bucket 1**, the probe runner. **Landed:** a review commit on #512, and
  item b-19b255 by #515.
- `SA-0136` (#514): no witness pinned `run_task`'s `has_commit` guard.
  **Bucket 1.** **Landed:** a review commit on #514.
- `SA-0136` (#514): the `Refused` and `run_task` docstrings misdescribed
  them.
  **Bucket 3**, a claim no gate reads. **Landed:** a review commit on #514.
- `SA-0136` (#514): `saffron/cli.py` checks inline whether a commit exists,
  which `has_commit` now does.
  **Bucket 2**, one source. **Open:** item b-79d951.
- `SA-0138` (#515): criterion 2 could not see `uncounted` truncated on the
  unproven path.
  **Bucket 1**, the spec's arrangement. **Landed:** a review commit on #515.
- `SA-0138` (#515): the unproven reason merged ADR 0003's two cases.
  **Bucket 3.** **Landed:** a review commit on #515.
- `SA-0138` (#515): the module and `added_tests` docstrings were false.
  **Bucket 3**, a claim no gate reads. **Landed:** a review commit on #515.
- `SA-0138` (#515): criterion 4's witness passed with `base_results` set to
  `latest.results`. The critic raised it, and a probe killed through another
  test demoted it.
  **Bucket 1**, the probe runner. **Landed:** a review commit on #515, and
  item b-19b255 by #515.

## 2026-09-25, `SA-0141` (the spec loop's run 17, #519)

- `SA-0141` (#519): repair pinned the old prompt text into test ids so
  `census` saw the same names.
  **Bucket 1**, `census`. **Open:** item b-f30189. A review commit made the
  ids the prompt names.
- `SA-0141` (#519): a slot test kept two cases the spec said to drop and
  inverted their assertion, for the same gate.
  **Bucket 1**, `census`. **Open:** item b-f30189. **Landed:** a review
  commit on #519 dropped them.
- `SA-0141` (#519): nothing witnessed the drive double copying
  `structured_output` onto its result line, as the spec's notes asked.
  **Bucket 1**, the spec's arrangement. **Landed:** a review commit on #519.

## 2026-09-26, `SA-0142` to `SA-0159` (the spec loop's run 18, stack #531)

- `SA-0142` (#522): no witness put an unmet `depends_on` entry first and a met
  one after it, so readiness read from the last entry alone passed every test.
  **Bucket 1**, `witness`. **Landed:** a review commit on #522.
- `SA-0142` (#522): `build_queue`'s docstring grew five lines past the
  ten-line rule, and `_stack_order` cited §4.2 for the rule §4.2 contradicts.
  **Bucket 1**, `prose`. **Open:** item b-044ae7. **Landed:** a review commit.
- `SA-0143` (#523): the refusal witness keyed lines by their first token, so
  a duplicated line or a dropped padding passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #523.
- `SA-0143` (#523): `run_task`'s new docstring broke three prose rules, and
  the repair turn rewrote an older comment so the file's count went flat.
  **Bucket 1**, `prose`. **Open:** item b-044ae7. **Landed:** a review commit.
- `SA-0143` (#523): one fact was held three ways, with tags that read as task
  states.
  **Bucket 3**, contract. **Landed:** a review commit on #523.
- `SA-0144` (#524): nothing witnessed that a plain `saffron batch` still asks
  for the ordinary queue order.
  **Bucket 1**, `witness`. **Landed:** a review commit on #524.
- `SA-0144` (#524): `revert` skipped both new witnesses, since the `tests`
  gate reads a flag error in captured output as its own.
  **Bucket 1**, `tests`. **Open:** item b-76f08d.
- `SA-0144` (#524): an unrequested and false four-line docstring paragraph
  grew past the ten-line rule, and a test restated a helper.
  **Bucket 1**, `prose`. **Open:** item b-044ae7. **Landed:** a review commit.
- `SA-0145` (#525): `record_stack_layer` wrote an unknown predecessor as a
  stack's first layer.
  **Bucket 3**, correctness. **Landed:** a review commit on #525.
- `SA-0145` (#525): a five-line SQL comment sat in the `SCHEMA` string, and
  `run_batch`'s docstring grew five lines.
  **Bucket 1**, `prose`. **Open:** items b-43061c and b-044ae7. **Landed:** a
  review commit on #525.
- `SA-0146` (#526): the Standards prompt judged a repo's words against
  Saffron's own glossary, the wrong version the spec named.
  **Bucket 3**, contract. **Landed:** a review commit on #526.
- `SA-0146` (#526): four wrong versions passed criterion 2's witness, one of
  them because it checked a constant's name and not its value.
  **Bucket 1**, `witness`. **Landed:** a review commit on #526.
- `SA-0153` (#527): both raises the witness drove were `RuntimeError`, so a
  catch narrowed to it passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #527.
- `SA-0153` (#527): `_diff` recorded a bare `CalledProcessError`, which drops
  git's stderr.
  **Bucket 2**, the record contract's stated reason. **Landed:** a review
  commit on #527.
- `SA-0153` (#527): the end review finds its batch by the latest id.
  **Bucket 3**, correctness. **Open:** item b-615466.
- `SA-0154` (#528): nothing asserted `StackReview` is frozen, and a cell
  removed by its volume's name passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #528.
- `SA-0154` (#528): a second query restated `_BATCH_LAYERS` and needed an
  unguarded lookup, and a helper was a byte copy of another.
  **Bucket 2**, one source. **Open:** item b-50a704. **Landed:** a review
  commit on #528.
- `SA-0157` (#529): the error fallback read the join row as the top layer's
  own lens row.
  **Bucket 3**, correctness. **Landed:** a review commit on #529.
- `SA-0157` (#529): `cli.py` restated a query and a root path, and a
  docstring miscounted the cells the review opens.
  **Bucket 2**, one source. **Open:** item b-50a704. **Landed:** a review
  commit on #529.
- `SA-0159` (#530): the `baseline_names` comment claimed a row per gate
  result and a false cause for a `None` read.
  **Bucket 1**, `prose`. **Open:** item b-43061c. **Landed:** a review commit
  on #530.

## 2026-09-27, `SA-0178` to `SA-0156` (the spec loop's run 19, #539 to #553)

- `SA-0178` (#539): a test restated `_tests_result` from `test_session.py`.
  **Bucket 2**, one source. **Landed:** a review commit on #539.
- `SA-0178` (#539): `probe_findings`'s docstring kept REVIEW's order for a
  function any caller now uses.
  **Bucket 3**, contract. **Landed:** a review commit on #539.
- `SA-0179` (#540): `filed` was typed `str` beside the `Severity` type the
  module already imports.
  **Bucket 2**, one source. **Landed:** a review commit on #540.
- `SA-0179` (#540): a schema comment gave a reason that did not follow.
  **Bucket 3**, contract. **Landed:** a review commit on #540.
- `SA-0180` (#541): the pool assertion left out `task_key`, so a blank-layer
  probe survived.
  **Bucket 1**, `witness`. **Landed:** a review commit on #541.
- `SA-0180` (#541): `_qualify_range` took a prebuilt diff and anchored
  findings, not the base and head the spec's seam named. No witness sees a
  helper's shape.
  **Bucket 3**, contract. **Landed:** a review commit on #541.
- `SA-0180` (#541): `probe_key` was restated twice, and a docstring gave the
  spec's scope as its reason.
  **Bucket 2**, one source. **Landed:** a review commit on #541.
- `SA-0147` (#542): the fixture recorded in-cell rows after the copies,
  against the spec's arrangement, so a read after the last copy survived.
  Nothing drove an unanchored in-cell adequacy finding either.
  **Bucket 1**, `witness`. **Landed:** a review commit on #542.
- `SA-0147` (#542): two docstrings misstated what `qualify` reads and groups.
  **Bucket 3**, contract. **Landed:** a review commit on #542.
- `SA-0148` (#543): the `started` comment still said a spec starts once a
  night, and a witness docstring called an abort a miss.
  **Bucket 2**, `CONTEXT.md`'s vocabulary. **Landed:** a review commit on
  #543.
- `SA-0149` (#544): a spec review that raised left its spec out of `missed`,
  so the dependents of a raised spec still ran.
  **Bucket 3**, correctness. **Landed:** a review commit on #544.
- `SA-0149` (#544): four witness gaps. Cost was asserted on two rows, one row
  errored on its first element, a string was iterated per character, and
  padding went unasserted.
  **Bucket 1**, `witness`. **Landed:** a review commit on #544.
- `SA-0149` (#544): the read restated `Severity`'s members as a tuple literal.
  **Bucket 2**, one source. **Landed:** a review commit on #544.
- `SA-0149` (#544): an em dash in a docstring passed `prose`, hidden by a code
  span wrapped across a line break.
  **Bucket 1**, `prose`. **Open:** item b-ec607a. **Landed:** a review commit.
- `SA-0155` (#545): four witness gaps. The breaker tripped before a raising
  mint, a turn count survived, two blocks went unpinned, and the fold
  compared rows through the same `_apply`. The spec's stripped block was also
  kept padded.
  **Bucket 1**, `witness`. **Landed:** a review commit on #545.
- `SA-0155` (#545): `block` and `block_sha256` were repeated at eleven `_error`
  calls.
  **Bucket 2**, one source. **Landed:** a review commit on #545.
- `SA-0168` (#546): `tasks_by_spec`'s docstring called a minting call
  "unstacked", against the **Stacked branch** entry.
  **Bucket 2**, `CONTEXT.md`'s vocabulary. **Landed:** a review commit on
  #546.
- `SA-0168` (#546): the pushed-sha set was restated by a lookup and a
  conditional add.
  **Bucket 2**, one source. **Landed:** a review commit on #546.
- `SA-0181` (#549): three witness blockers and four concerns. The prefix was
  compared to its own constant, a capability default survived, and seven
  mutants in all survived.
  **Bucket 1**, `witness`. **Landed:** a review commit on #549.
- `SA-0181` (#549): three comments cited §5.5 for a §5.1 rule or misnamed who
  reads the shell prefix.
  **Bucket 3**, contract. **Landed:** a review commit on #549.
- `SA-0169` (#550): the cell-marked test the spec's notes asked for was never
  written, and no gate or lens noticed.
  **Bucket 1**, a size floor. **Open:** item b-20043f. **Landed:** a review
  commit on #550.
- `SA-0169` (#550): a comment called the self-check "the root-left check".
  **Bucket 2**, `CONTEXT.md`'s vocabulary. **Landed:** a review commit on
  #550.
- `SA-0175` (#551): the criterion 4 witness never asserted the `{ceilings}`
  block, and its removal survived.
  **Bucket 1**, `witness`. **Landed:** a review commit on #551.
- `SA-0175` (#551): `_validate` restated `rebut._validate`, and test setup was
  repeated across three witnesses.
  **Bucket 2**, one source. **Landed:** a review commit on #551.
- `SA-0175` (#551): two comments gave false reasons, one of them REBUT's
  `HEAD` reason copied into a spec review.
  **Bucket 3**, contract. **Landed:** a review commit on #551.
- `SA-0156` (#553): the mint witness never asserted a run's repo, so a
  hardcoded repo id passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #553.
- `SA-0156` (#553): the spec session's account lines sit in a `cli.py`
  constant, not in core's prompts.
  **Bucket 2**, one source. **Open:** item b-146869.

## 2026-09-28, `SA-0182` to `SA-0164` (the spec loop's run 20, #559 to #566)

- `SA-0182` (#559): `spec_text` and `spec_texts` restated `Ledger.record_key`'s
  query.
  **Bucket 2**, one source. **Landed:** a review commit on #559.
- `SA-0182` (#559): the origins comment did not parse.
  **Bucket 3**, contract. **Landed:** a review commit on #559.
- `SA-0182` (#559): the next row is numbered by count, so a fold of a trimmed
  fact list collides on the key.
  **No bucket**, it names a rule the spec set. **Open:** item b-013138.
- `SA-0184` (#560): criterion 3's witness never checked that a cut names its
  bound, so a message naming neither bound survived.
  **Bucket 1**, `witness`. **Landed:** a review commit on #560.
- `SA-0184` (#560): the wall's rate lost its measured source and the floor
  lost its reason.
  **Bucket 2**, measured beats reasoned. **Landed:** a review commit on #560.
- `SA-0184` (#560): the library's hour and the `max_turns` default are each
  spelled in two places.
  **Bucket 2**, one source. **Open:** item b-30bbd7.
- `SA-0150` (#561): criterion 2's witness drove the bad bases through the
  helper, so a `run_task` that swallowed the read error survived.
  **Bucket 1**, `witness`. **Landed:** a review commit on #561.
- `SA-0150` (#561): criterion 1's witness never read two of the event's
  ceilings, so the caller's values survived.
  **Bucket 1**, `witness`. **Landed:** a review commit on #561.
- `SA-0150` (#561): an unparseable first text raised out of `run_task`
  instead of refusing.
  **Bucket 3**, correctness. **Landed:** a review commit on #561.
- `SA-0150` (#561): `_CEILING_FIELDS` restated `events.Ceiling`, and a trimmed
  docstring lost why the event is emitted in `run_task`.
  **Bucket 2**, one source. **Landed:** a review commit on #561.
- `SA-0186` (#562): the resolver let any dead newest task unstack a child over
  an older pushed row. REBUT argued it from the spec and the lens withdrew.
  **No bucket**, a rebuttal from a spec contradiction wins. **Landed:** a
  review commit on #562, on the operator's rule. **Open:** item b-ab4b33.
- `SA-0186` (#562): criterion 2's witness never read its own line's text or
  step.
  **Bucket 1**, `witness`. **Landed:** a review commit on #562.
- `SA-0186` (#562): two comments cited `DESIGN.md` §4.2.1 for rules it does not
  state, and a docstring described only one path.
  **Bucket 3**, contract. **Landed:** a review commit on #562.
- `SA-0186` (#562): the scheduler's comment and §4.2.1 no longer match the
  resolver.
  **Bucket 2**, the design documents. **Open:** item b-710086.
- `SA-0176` (#563): the writer prompt named one gate where two block, and left
  out `risk: elevated`.
  **Bucket 3**, contract. **Landed:** a review commit on #563. The review
  prompt keeps the same wording. **Open:** item b-5ec5c5.
- `SA-0176` (#563): three docstrings said more than the code does.
  **Bucket 3**, contract. **Landed:** a review commit on #563.
- `SA-0185` (#564): the witnesses read the rate as a substring, missed
  "changed tokens", took a field name for an estimate, and let a later
  sentence count in tokens.
  **Bucket 1**, `witness`. **Landed:** a review commit on #564.
- `SA-0160` (#565): the re-ask witness checked its prompt by prefix and
  suffix, so a re-ask that dropped the error survived.
  **Bucket 1**, `witness`. **Landed:** a review commit on #565. The review's
  own re-ask witness has the same hole. **Open:** item b-64e40c.
- `SA-0160` (#565): a repair split a sentence to pass `prose` and left a false
  comment on the writer's timeout.
  **Bucket 1**, `prose`. **Landed:** a review commit on #565.
  **Open:** item b-ad1285.
- `SA-0160` (#565): the tests copied their setup and did not table their
  rows, as the spec asked.
  **Bucket 2**, one source. **Landed:** a review commit on #565, on the
  operator's call.
- `SA-0160` (#565): an unannotated helper hid a type mismatch from `types`.
  **Bucket 1**, `types`. **Landed:** one helper pattern, on the operator's
  call. **Open:** item b-713e90.
- `SA-0164` (#566): four witnesses left the writer's layer, a no-writer route,
  the tagged text and `--repo` unasserted.
  **Bucket 1**, `witness`. **Landed:** a review commit on #566.
- `SA-0164` (#566): the review prompt said the queued file changed, and three
  docstrings called a `witness` concern lone.
  **Bucket 3**, contract. **Landed:** a review commit on #566.
- `SA-0164` (#566): the tests restated the rig and doubles the file already
  holds.
  **Bucket 2**, one source. **Landed:** a review commit on #566, on the
  operator's call.
- `SA-0164` (#566): the `revise` type, the budget sum and a phase name are each
  restated.
  **Bucket 2**, one source. **Open:** item b-74e564.

## 2026-09-29, `SA-0187` to `SA-0192` (the spec loop's run 21, #574 to #581)

- `SA-0187` (#574): criterion 2's witness passed a renderer keyed on
  `preserves`, since its one listing criterion was also its one `preserves`
  one.
  **Bucket 1**, `witness`. **Landed:** a review commit on #574.
- `SA-0187` (#574): `tests/test_context.py` read a new constant at import, so
  the file failed to collect at base and `revert` checked no witness.
  **Bucket 1**, `revert`. **Open:** item b-cf832a.
- `SA-0187` (#574): the implement prompt forbade running only the wrong
  versions a spec's notes list, not those under each witness.
  **Bucket 2**, the implementer's standing text. **Landed:** step 5's edit to
  `implement.md`, on the operator's call.
- `SA-0187` (#574): a docstring named a file nothing writes, and the new
  prompt listed its sections out of order.
  **Bucket 3**, contract. **Landed:** a review commit on #574.
- `SA-0190` (#576): criterion 4's witness read a container name that outlives
  teardown, so a session asked after it survived.
  **Bucket 1**, `witness`. **Landed:** a review commit on #576.
- `SA-0190` (#576): criterion 2's witness checked five fields of the blocker,
  not the whole of it.
  **Bucket 1**, `witness`. **Landed:** a review commit on #576.
- `SA-0190` (#576): a leftover alias restated a parameter, and a comment
  cited the wrong criterion's witness.
  **Bucket 2**, one source. **Landed:** a review commit on #576.
- `SA-0190` (#576): wrong-version summaries say "mutant", and wrong versions
  run under the criterion-probe helper's name.
  **Bucket 2**, `CONTEXT.md`'s vocabulary. **Open:** item b-84d4f8.
- `SA-0188` (#577): a quote check that folded case passed both witnesses.
  **Bucket 1**, `witness`. **Landed:** a review commit on #577.
- `SA-0188` (#577): two more docstrings described a two-valued verdict, and a
  comment gave the host the critic's verb.
  **Bucket 3**, contract. **Landed:** a review commit on #577.
- `SA-0188` (#577): a test copied two helpers the file defines, and a
  constant's name said the opposite of its value.
  **Bucket 2**, one source. **Landed:** a review commit on #577.
- `SA-0188` (#577): `DESIGN.md` §4.1 and §5.6 still gave the verdict two
  values.
  **Bucket 2**, the design record. **Landed:** step 5's hand edit.
- `SA-0189` (#579): the fourth-lens witness caught a default `expect` only by
  `TypeError`, never by an assertion.
  **Bucket 1**, `witness`. **Landed:** a review commit on #579.
- `SA-0189` (#579): no witness pinned `expect` as positional.
  **Bucket 1**, `witness`. **Landed:** a review commit on #579.
- `SA-0189` (#579): one check used two constants, new prose said bare "run"
  and "pass", and a docstring restated a signature.
  **Bucket 2**, one source. **Landed:** a review commit on #579.
- `SA-0189` (#579): a fixture declares no recorded lens set, so a truncated
  recorded run still calibrates.
  **No bucket**, it names a field that does not exist. **Open:** item
  b-6d43da.
- `SA-0191` (#580): criterion 3's witness read only the remit, so a worktree
  `CLAUDE.md` instruction elsewhere passed the suite.
  **Bucket 1**, `witness`. **Landed:** a review commit on #580.
- `SA-0191` (#580): no test drove a conventions finding through `run_review`,
  so one filed under another lens survived.
  **Bucket 1**, `witness`. **Landed:** a review commit on #580.
- `SA-0191` (#580): two comments still counted three lenses and seven turns,
  far from any hunk.
  **Bucket 3**, the conventions lens. **Landed:** a review commit on #580.
  The lens asks of each hunk only, which item b-78ccc7 tracks.
- `SA-0191` (#580): `DESIGN.md` §5.3, §5.5.1 and the roadmap still counted
  three lenses.
  **Bucket 2**, the design record. **Landed:** step 5's hand edit.
- `SA-0192` (#581): criterion 2's witness expected the constant it tested, so
  any wording passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #581. Item
  b-5b1f8a asks a gate to refuse the pattern.
- `SA-0192` (#581): the lens withdrew a real `preserves` probe blocker as
  outside the diff.
  **Bucket 1**, `witness`. **Landed:** a review commit on #581. Item b-cd5fd2
  keeps REBUT from arguing such a blocker away.
- `SA-0192` (#581): the block said no `CLAUDE.md` stood while serving a blank
  one.
  **Bucket 3**, contract. **Landed:** a review commit on #581, on the
  operator's call.
- `SA-0192` (#581): the three other prompts hand over "a constant or helper",
  where the conventions remit says "a type, constant or helper".
  **Bucket 3**, the conventions lens. **Open:** item b-78ccc7.

## 2026-09-29, `SA-0193` to `SA-0195` (the spec loop's run 22, #596 to #600)

- `SA-0193` (#596): a guard matching the host's text anywhere in a claim
  passed both witnesses, where the spec says the claim starts with it.
  **Bucket 1**, `witness`. **Landed:** a review commit on #596. Step 1b had
  named it as a note.
- `SA-0193` (#596): a test docstring gave the lens the implementer's
  argument.
  **Bucket 3**, the conventions lens. **Landed:** a review commit on #596.
- `SA-0194` (#598): the `preserves` witness anchored through a shared
  parameter, so it stayed green with the renamed name dropped. The host filed
  it, and the lens withdrew it after REBUT.
  **Bucket 1**, `witness`. **Landed:** a review commit on #598. Item b-cd5fd2
  closes the withdrawal once #596 merges.
- `SA-0194` (#598): a renamed path adds its file extension to the diff's
  tokens, so a line naming another `.py` file anchors.
  **Bucket 3**, the correctness lens. **Open:** item b-2dd65f.
- `SA-0195` (#600): a new test helper restated the bullet parser beside it.
  **Bucket 3**, the conventions lens. **Landed:** a review commit on #600.
  REVIEW ran main's conventions prompt, not the branch's (b-66d1c3).
- `SA-0195` (#600): a test docstring kept the wording the change removed.
  **Bucket 3**, the conventions lens. **Landed:** a review commit on #600.
- `SA-0195` (#600): two declared mutants died on a `ValueError`, not an
  assertion.
  **Bucket 1**, `witness`. **Landed:** a review commit on #600.

## 2026-09-30, `SA-0196`, `SA-0161`, `SA-0173` and `SA-0165` (the spec loop's run 23, #608 to #622)

- `SA-0196` (#608): a walk following only `depends_on[0]` at either loop
  passed, because each ancestor had a second route.
  **Bucket 1**, `witness`. **Landed:** a review commit on #608.
- `SA-0196` (#608): dropping the not-a-list check passed, since a dict
  iterates to a string key the entry check rejects.
  **Bucket 1**, `witness`. **Landed:** a review commit on #608.
- `SA-0196` (#608): a `findings.json` that is not UTF-8 raised rather than
  printing the none-recorded line.
  **Bucket 3**, adequacy. **Landed:** a review commit on #608.
- `SA-0196` (#608): a comment called `EXHAUSTED` a halt, SKILL.md named a
  report it never defines, and a test imported `json` under an alias.
  **Bucket 2**, `CONTEXT.md`'s vocabulary. **Landed:** a review commit on #608.
- `SA-0196` (#608): `record` and `jev --kind cell` anchor staleness
  differently, and a null lens name prints `None`.
  **Bucket 3**, contract. **Open:** item b-a09d30.
- `SA-0161` (#610): the reset session's charge, the prompt's budget line and
  an errored attempt's subtype were each unasserted.
  **Bucket 1**, `witness`. **Landed:** a review commit on #610.
- `SA-0161` (#610): `_read_head` turned a mirror read's `GitError` into an
  absent file, so a broken read pooled a finding as a stale probe.
  **Bucket 2**, `error` is not `fail`. **Landed:** a review commit on #610.
  **Open:** item b-00534f, for the same copy in `qualify.py`.
- `SA-0161` (#610): four messages said bare "writer", one "errored", one
  "exhausted" and one "checkout".
  **Bucket 1**, `terms`, whose table holds none of them. **Landed:** a review
  commit on #610.
- `SA-0161` (#610): a docstring said `_diff` reads no `.git/config`, a test
  bound a variable only to delete it, and a test's name said the opposite of
  its assertions.
  **Bucket 3**, contract. **Landed:** a review commit on #610.
- `SA-0161` (#610): the attempt charge is a third inline copy, and two
  modules diff one layer under different pins.
  **Bucket 2**, one source. **Open:** item b-979dbe.
- `SA-0173` (#618): a build holding `writer_usd` in the task loop only when
  `follow_ups` is given passed the writer-share witness.
  **Bucket 1**, `witness`. **Landed:** a review commit on #618.
- `SA-0173` (#618): a docstring named a spec never minted where the witness
  mints it, and a comment narrated which mutant fails which assertion.
  **Bucket 2**, `CLAUDE.md`'s comment rule. **Landed:** a review commit on
  #618.
- `SA-0165` (#622): the follow-up witness never asserted the writer's
  session, its cell's `gates_dir` or its container.
  **Bucket 1**, `witness`. **Landed:** a review commit on #622.
- `SA-0165` (#622): group `A` was pooled whole before the raise, so two
  pooling cuts passed both rounds.
  **Bucket 1**, `witness`. **Landed:** a review commit on #622.
- `SA-0165` (#622): two docstrings said a raise pools what the walk never
  reached, which holds only after `qualify` returns.
  **Bucket 3**, contract. **Landed:** a review commit on #622.

## 2026-10-01, `SA-0162` and `SA-0151` (the spec loop's run 24, #626 and #628)

Both cells ended `EXHAUSTED` in REVIEW and were adopted by hand. The in-cell
critic's own blockers are not listed here. Each line below is a seat finding
the critic did not raise.

- `SA-0162` (#626): criterion 6's order carried no `touches`, so checking
  every spec of the order passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #626.
- `SA-0162` (#626): `_stack_open_prs` copied `_print_scan_gaps`' two note
  lines instead of calling it.
  **Bucket 3**, conventions. **Landed:** a review commit on #626.
- `SA-0162` (#626): comments called a spec review's route a "verdict", the
  critic's word at REBUT.
  **Bucket 1**, `terms` has no rule for it. **Open.**
- `SA-0162` (#626): the `run_stack_batch` docstring said the end review waits
  for `DRAINED`, and three comments still named `run_batch`.
  **Bucket 3**, contract. **Landed:** a review commit on #626.
- `SA-0162` (#626): the tests rebuilt `AdvancingClock` as `_MutableClock`.
  **Bucket 3**, conventions. **Landed:** a review commit on #626.
- `SA-0162` (#626): a refused revised spec of the order gets no task state.
  **Bucket 3**, contract. **Open:** b-3590be.
- `SA-0151` (#628): criterion 3's witness never read the batch id `finish`
  received.
  **Bucket 1**, `witness`. **Landed:** a review commit on #628.
- `SA-0151` (#628): dropping the path pattern's end anchor passed criterion
  2, a build that writes outside `.saffron/specs/`.
  **Bucket 1**, `witness`. **Landed:** a review commit on #628.
- `SA-0151` (#628): two test docstrings cited `SA-0171`, which no spec is.
  **Bucket 1**, no gate reads cited spec ids. **Open.**
- `SA-0151` (#628): `finish.py` restated the ledger's path pattern, more
  loosely, and `cli.py`'s git runner, unchecked.
  **Bucket 3**, conventions. **Landed:** a review commit on #628.
- `SA-0151` (#628): `_stack_finish`'s docstring said every raise is
  swallowed. It catches two types.
  **Bucket 3**, contract. **Landed:** a review commit on #628.
- `SA-0151` (#628): `commit_finish` drops parse failures, and it writes
  through a symlink a cell committed.
  **Bucket 3**, correctness. **Open:** b-3d2aa1 and b-8d654b.
- `SA-0162` and `SA-0151`: the batch id read three ways, and the layer query
  and git runner restated.
  **Bucket 3**, conventions. **Open:** b-115f9b.
- `SA-0174` (#630): criterion 1's witness put no finding on another batch's
  follow-up, so reading every batch's follow-ups passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #630.
- `SA-0174` (#630): the comment over `FINDINGS_NAME` named the end review and
  `SA-0151` as its writer, and two docstrings left out a case they cover.
  **Bucket 3**, contract. **Landed:** a review commit on #630.

## 2026-10-02, `SA-0177` and `SA-0167` (the spec loop's run 25, #636 and #638)

- `SA-0177` (#636): the last step and the third fold read `head_sha` alone,
  though the claim is the row's whole write.
  **Bucket 1**, `witness`. **Landed:** a review commit on #636.
- `SA-0177` (#636): the witness carried nine bare `# 1.` to `# 9.` comments
  that named no why and pointed at the spec's step numbers.
  **Bucket 3**, conventions. **Landed:** a review commit on #636.
- `SA-0177` (#636): the `_apply` comment said the row "files" under the batch,
  where the diff uses "filed under" for the task key.
  **Bucket 3**, conventions. **Landed:** a review commit on #636.
- `SA-0167` (#638): a comment REBUT left said `SA-0170` reads the pushed line
  by its spelling. `SA-0170` matches `finish.PUSHED`.
  **Bucket 3**, contract. **Landed:** a review commit on #638.
- `SA-0167` (#638): the prefix comment named every line of `publish_finish`,
  though its second line starts with neither prefix.
  **Bucket 3**, contract. **Landed:** a review commit on #638.
- `SA-0167` (#638): the plural helper `_pull` read as "pull request" in a
  module about pull requests.
  **Bucket 3**, conventions. **Landed:** a review commit on #638.
- `SA-0167` (#638): the publish-stopped loop gave `KeyError` an empty label
  and asserted its line in a separate branch.
  **Bucket 3**, conventions. **Landed:** a review commit on #638.
- `SA-0167` (#638): an existing finishing branch drops the worktree removal's
  error, so a leftover worktree goes unreported.
  **Bucket 3**, correctness. **Open:** b-7430c1.

## 2026-10-03, `SA-0170`, `SA-0183` and `SA-0152` (the spec loop's run 26, #647, #648 and #650)

- `SA-0170` (#647): the repo-bound runner's witness ran with `--repo` equal
  to the process's own directory, so a runner using `Path.cwd()` passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #647.
- `SA-0170` (#647): only exit 1 was driven as a refused link, so a check of
  `returncode == 1` passed and would read gh-stack's exit 9 as linked.
  **Bucket 1**, `witness`. **Landed:** a review commit on #647.
- `SA-0170` (#647): the exit-127 case asserted its lines but not its `gh`
  call, which the spec's notes require of every case.
  **Bucket 3**, adequacy. **Landed:** a review commit on #647.
- `SA-0170` (#647): `_finish_gh`'s docstring gave a reason for `GH_REPO`
  that names no fact, where the measured exit 4 is the reason.
  **Bucket 3**, conventions. **Landed:** a review commit on #647.
- `SA-0170` (#647): no test drives a commit raise other than `GitError` or
  `ValueError`, so widening the `except` to `Exception` passes.
  **Bucket 1**, `witness`. **Open:** b-cc8099.
- `SA-0170` (#647): `GhRunner` is defined three times, word for word.
  **Bucket 3**, conventions. **Open:** b-81e109.
- `SA-0152` (#650): a layer's section left out its state and position, though
  the criterion asks for every field of the layer.
  **Bucket 3**, correctness. **Landed:** a review commit on #650.
- `SA-0152` (#650): REBUT moved `TE-4` to the position equal to its index, so
  a renderer numbering layers by index passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #650.
- `SA-0152` (#650): the order entries were asserted one by one, so a
  reversed order passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #650.
- `SA-0152` (#650): no assertion read the batch id or a layer's spec id, so
  a renderer dropping either passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #650.
- `SA-0152` (#650): the order and the outcomes were bare text inside `<ul>`,
  which a browser runs together into one line.
  **Bucket 3**, correctness. **Landed:** a review commit on #650.
- `SA-0152` (#650): the view restated the end-review lens names, the header
  count and a wrong item number, where `end_review.py` and `index.py` hold
  them.
  **Bucket 3**, conventions. **Landed:** a review commit on #650.
- `SA-0152` (#650): the page prints a per-lens term, `not_reached`, for a
  layer whose Spec lens reviewed.
  **Bucket 3**, conventions. **Open:** b-466005.

## 2026-10-03, `SA-0197`, `SA-0198` and `SA-0199` (the spec loop's run 27, #659, #662 and #670)

- `SA-0197` (#659): the refusal witness never read the exit code, so a
  stderr refusal exiting 1 passed for argparse's usage exit.
  **Bucket 1**, `witness`. **Landed:** a review commit on #659.
- `SA-0197` (#659): only a missing batch tree was driven, so `exists()` in
  place of `is_dir()` passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #659.
- `SA-0197` (#659): the directory present at the start held no log, so a
  filter skipped for a log holding lines at the start passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #659.
- `SA-0197` (#659): two docstrings claimed a shared fixture and an offset for
  late joiners that the code does not have.
  **Bucket 3**, conventions. **Landed:** a review commit on #659.
- `SA-0197` (#659): `CLAUDE.md` and `DESIGN.md` still describe `saffron watch`
  as following one spec's log.
  **Bucket 3**, conventions. **Open:** b-348114.
- `SA-0198` (#662): no ledger held nine to nineteen settled tasks, so the
  count boundary could move anywhere in that range.
  **Bucket 1**, `witness`. **Landed:** a review commit on #662.
- `SA-0198` (#662): the tie-break's kill rested on SQLite scanning tied rows
  by ascending rowid.
  **Bucket 1**, `witness`. **Landed:** a review commit on #662.
- `SA-0198` (#662): the test spelled the seven settled names twice, against
  its own docstring.
  **Bucket 3**, conventions. **Landed:** a review commit on #662.
- `SA-0198` (#662): the header key is spelled by hand at each page writer.
  **Bucket 3**, conventions. **Open:** b-2944c9.
- `SA-0198` (#662): `SETTLED_STATES` has no vocabulary test or ontology class.
  **Bucket 1**, a vocabulary test. **Open:** b-b2fffe.
- `SA-0199` (#670): the `ORPHANED` row was checked on three fields, so a row
  that changed its attempts, note or link passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #670.
- `SA-0199` (#670): stored rows were compared on state and three fields, so
  a rewrite that lost attempts or concerns passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #670.
- `SA-0199` (#670): the notes' no-change call on repo `r` was dropped, so a
  write whenever the repo has rows passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #670.
- `SA-0199` (#670): the empty-directory check passed a directory that did not
  exist, so a lock taken in an existing one passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #670.
- `SA-0199` (#670): every failing write raised `OSError`, so either catch in
  `run_task` narrowed to `OSError` passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #670.
- `SA-0199` (#670): the raising `orphan_rows` stub raised `OSError`, so the
  scan's catch narrowed to it passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #670.
- `SA-0199` (#670): no criterion pinned the `ORPHANED` write's header or its
  printed line on failure, though the spec body asks for both.
  **Bucket 1**, `witness`. **Landed:** a review commit on #670.
- `SA-0199` (#670): a comment cited `DESIGN.md` §6 for a rule §6 does not
  state.
  **Bucket 3**, conventions. **Landed:** a review commit on #670.
- `SA-0199` (#670): a new test factory splatted a dict into `QueueLine`,
  where the typed `line()` already exists.
  **Bucket 3**, conventions. **Landed:** a review commit on #670.
- `SA-0199` (#670): a comment named a repeated repair the case does not
  drive, and an inner `_rows` shadowed the module's.
  **Bucket 3**, conventions. **Landed:** a review commit on #670.
- `SA-0199` (#670): `DESIGN.md:1277` calls the end-of-task line a verdict,
  which `CONTEXT.md` avoids.
  **Bucket 3**, conventions. **Open:** b-348114.

## 2026-10-05, `SA-0200` to `SA-0204` (the spec loop's run 28, #673 to #678)

- `SA-0201` (#673): criterion 3's witness never read the task row, so a
  mutant that split the ledger state from the outcome survived.
  **Bucket 1**, `witness`. **Landed:** a review commit on #673.
- `SA-0201` (#673): `_is_layer`'s docstring said `RATE_LIMITED` and
  `PROVIDER_UNREACHABLE` return before it runs. `record_layer` calls it for
  every outcome.
  **Bucket 3**, conventions. **Landed:** a review commit on #673.
- `SA-0201` (#673): the comment on the started set named no state.
  **Bucket 3**, conventions. **Landed:** a review commit on #673.
- `SA-0200` (#674): the witness never checked that a missing measured id is
  named, so two probes survived.
  **Bucket 1**, `witness`. **Landed:** a review commit on #674.
- `SA-0202` (#675): a re-prompt without `EXTRACTION_PROMPT` passed the
  re-prompt witness.
  **Bucket 1**, `witness`. **Landed:** a review commit on #675.
- `SA-0202` (#675): no test drove `_cell`'s escaping of the wrong-version
  line.
  **Bucket 1**, `witness`. **Landed:** a review commit on #675.
- `SA-0202` (#675): `run_wrong_versions` restates `run_lens`'s re-prompt line
  for line.
  **Bucket 3**, conventions. **Open:** b-708c8a.
- `SA-0203` (#676): a REBUT session the SDK cut at the cap never marked the
  cap refused, so the task halted at `REBUTTING`. `SA-0204`'s parent-branch
  spec review found it.
  **Bucket 3**, correctness. **Landed:** a review commit on #676.
- `SA-0203` (#676): no witness drove the cap's `remaining <= 0` boundary.
  **Bucket 1**, `witness`. **Landed:** a review commit on #676.
- `SA-0203` (#676): the `Budget` docstring's rewrite lost why its field is
  typed, and stated history that is false.
  **Bucket 3**, conventions. **Landed:** a review commit on #676.
- `SA-0203` (#676): the notes turn's budget check still prints a stopping
  line before a REBUT that runs.
  **Bucket 3**, correctness. **Open:** b-444bed.
- `SA-0204` (#678): criterion 2's witness never read the row's `pushed_sha`, so
  a package that wrote none passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #678.
- `SA-0204` (#678): five citations named `SA-0210`, which does not exist.
  **Bucket 3**, conventions. **Landed:** a review commit on #678.
- `SA-0203` and `SA-0204` (#676, #678): three sentences in forbidden files
  still say only `READY_FOR_REVIEW` is packaged.
  **Bucket 3**, conventions. **Open:** b-edcab7.

## 2026-10-05, `SA-0205` to `SA-0208` (stage 2's stack batches 13 and 14, #687, #689, #696 and #697)

The end review raised nothing on any of the four layers. Every line here is a
seat finding the in-cell critic and the end review both passed.

- `SA-0208` (#687): only two of six phases held more than one closed attempt,
  so a phase-specific first or last pick read the right peak elsewhere.
  **Bucket 1**, `witness`. **Landed:** a review commit on #687.
- `SA-0208` (#687): the phase table's docstring justified a call-time read by
  a test's monkeypatch.
  **Bucket 3**, conventions. **Landed:** a review commit on #687.
- `SA-0205` (#689): the batch witness drove single model names, so either
  `run_stack_batch` site could keep the first of a joined value.
  **Bucket 1**, `witness`. **Landed:** a review commit on #689.
- `SA-0205` (#689): the runner witness sent no name near `<synthetic>` that
  must be kept, so a wider skip passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #689.
- `SA-0205` (#689): comments and test labels used bare "run" for one turn,
  copied from the spec's own prose.
  **Bucket 3**, conventions. **Landed:** a review commit on #689. The spec
  side is filed with the stage's backlog.
- `SA-0205` (#689): a comment said every field falls back to `None` with no
  attempt, though three fall back to `"error"`, 0 and 0.0.
  **Bucket 3**, conventions. **Landed:** a review commit on #689.
- `SA-0206` (#696): the floor witness priced no `thinking` or `tool_use`
  event, the kinds that carry most counts, so dropping both passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #696.
- `SA-0206` (#696): a comment said a result's usage was priced by the caller.
  No caller prices it, and its counts are cumulative over the turn.
  **Bucket 3**, conventions. **Landed:** a review commit on #696.
- `SA-0206` (#696): a test docstring said a ledger without the new column
  keeps recording turns. Its `close_attempt` raises on the missing column.
  **Bucket 3**, conventions. **Landed:** a review commit on #696.
- `SA-0207` (#697): every undeclared baseline result had no tool, so a filter
  on `result.tool` passed for the declared-gate filter.
  **Bucket 1**, `witness`. **Landed:** a review commit on #697.

## 2026-10-07 — `SA-0220` to `SA-0224` (spec loop run 30, stack #722 to #735)

- `SA-0220` (#722): two comments cited `DESIGN.md` §5.6 and §3 for the tier
  and the head count, which §4.1 defines.
  **Bucket 3**, conventions. **Landed:** a review commit on #722.
- `SA-0220` (#722): a moved schema comment lost its null meaning and the
  measured SQLite reason it sits below the last column.
  **Bucket 3**, conventions. **Landed:** a review commit on #722.
- `SA-0221` (#724): no test pinned `CellSpec.declared_risk`'s null default,
  so a `standard` default passed every witness.
  **Bucket 1**, `witness`. **Landed:** a review commit on #724.
- `SA-0222` (#731): the fold witness left `updated_at` out of its columns, so
  a `task_state` fact timed at the run's start passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #731.
- `SA-0222` (#731): every fixture attempt held a null `model`,
  `terminal_reason` and floor, so dropping any of them passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #731.
- `SA-0222` (#731): `migrated` and `refused` were compared sorted, so a
  reversed source order passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #731. Open:
  b-20043f, since #733 repeated it.
- `SA-0222` (#731): no held fact differed in `batch_key` alone, so a compare
  of kind, time and payload passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #731.
- `SA-0222` (#731): an exhausted package's state was derived from `pr_url`,
  so its fact claimed `READY_FOR_REVIEW`.
  **Bucket 3**, correctness. **Landed:** a review commit on #731, by the
  operator's choice.
- `SA-0222` (#731): the module docstring named a `task_policy` fact no spec
  writes, and cited the record design's sections as bare numbers.
  **Bucket 3**, conventions. **Landed:** a review commit on #731.
- `SA-0223` (#733): the fold witness never read the `gate_results` or
  `failures` rows it rebuilt, so a null summary or duration passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #733.
- `SA-0223` (#733): `migrated` and `refused` were compared sorted again, one
  layer after #731's seats found the same hole.
  **Bucket 1**, `witness`. **Open:** b-20043f.
- `SA-0223` (#733): the doubled-attempt refusal was checked for its phase
  only, so a reason with no attempt number passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #733.
- `SA-0223` (#733): three docstrings claimed what the code lacks, among them
  a null message that `identity` would raise on.
  **Bucket 3**, conventions. **Landed:** a review commit on #733.
- `SA-0223` (#733): eleven comments cited the spec's "problem N" numbering,
  which means nothing once the spec retires.
  **Bucket 2**, `CLAUDE.md`. **Landed:** a review commit on #733.
- `SA-0223` (#733): the spec named five test helpers absent at its base.
  **No bucket**. **Open:** b-cd41ac.
- `SA-0224` (#735): the command witness filtered its output by prefix, so a
  stray line passed "nothing else".
  **Bucket 1**, `witness`. **Landed:** a review commit on #735.
- `SA-0224` (#735): no origin held another writer's prefix, so refusing every
  held key passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #735.
- `SA-0224` (#735): `_migrate`'s docstring sent a declined push to exit 2,
  while the code reports it per task and exits 1.
  **Bucket 3**, conventions. **Landed:** a review commit on #735.
- `SA-0223` and `SA-0224` (#733, #735): both landed near twice their measured
  estimates and over the size ceiling, and `size` only advised at `standard`.
  **Bucket 1**, `size`. **Open:** b-fbd181. The operator kept both.
- Run 30: `terms` failed on `main` for a docstring the gate began reading,
  and no check ran it over the tree.
  **Bucket 1**, `terms`. **Landed:** #720. **Open:** b-1e106d.

## 2026-10-08 — `SA-0226`, `SA-0225`, `SA-0228` (spec loop run 31, #745, #746, #747)

- `SA-0226` (#745): the witness compared `spec_findings` rows and never the
  `spec_finding` facts, so facts left raw passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #745. **Open:**
  b-20043f.
- `SA-0226` (#745): an annotation-only import loaded the cell runtime and the
  phases into every ledger reader.
  **Bucket 3**, conventions. **Landed:** a review commit on #745.
- `SA-0226` (#745): two comments used bare "round", which `CONTEXT.md` avoids.
  **Bucket 1**, `terms`, whose table lacks the word. **Landed:** a review
  commit on #745.
- `SA-0225` (#746): both line-count witnesses drove added-only and never
  removed-only, so a removed guard needing added passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #746. **Open:**
  b-20043f.
- `SA-0225` (#746): the rename re-keyed `prose`'s docstring hit, and the cell
  joined two lines to slip under it.
  **Bucket 1**, `prose`. **Landed:** a review commit on #746. **Open:**
  b-8acb05.
- `SA-0225` (#746): a comment named the wrong function, a second "Minted"
  sat outside a stack batch, and a comment contradicted its list.
  **Bucket 3**, conventions. **Landed:** a review commit on #746.
- `SA-0228` (#747): every fixture row lacked turns, cost and wall time on the
  same attempts, so a cell reading another column's count passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #747. **Open:**
  b-20043f.
- `SA-0228` (#747): a float sum read back through `repr` passed, since every
  fixture sum had an exact `repr`.
  **Bucket 1**, `witness`. **Landed:** a review commit on #747.
- `SA-0228` (#747): the fixture comment gave a reason for its costs that
  measured false as worded.
  **Bucket 3**, conventions. **Landed:** a review commit on #747.

## 2026-10-09, `SA-0227` to `SA-0255` (spec loop run 32, stack #777 to #790)

- `SA-0230` (#777): the budget-cap witness set both fields, so an `and` for
  the `or`, or either clause deleted, passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #777.
- `SA-0230` (#777): two comments kept claims the diff made false, and a third
  said "now".
  **Bucket 3**, conventions. **Landed:** a review commit on #777.
- `SA-0231` (#778): dropping the verdict-error fallback after the cut line
  passed every witness.
  **Bucket 1**, `witness`. **Landed:** a review commit on #778.
- `SA-0231` (#778): the helper docstring the spec named stayed false, and the
  cut-short predicate was spelled twice.
  **Bucket 3**, conventions. **Landed:** a review commit on #778.
- `SA-0232` (#779): the retry witness never read the retried volume, the
  print's order, the kept lost+found or the full message.
  **Bucket 1**, `witness`. **Landed:** a review commit on #779.
- `SA-0232` (#779): a seed that timed out after printing the fetch marker was
  retried.
  **Bucket 3**, the correctness lens. **Landed:** a review commit on #779.
- `SA-0232` (#779): four docstrings and comments went stale, cited a test
  double as the reason, or said "attempts" for seed runs.
  **Bucket 3**, conventions. **Landed:** a review commit on #779.
- `SA-0227` (#781): the seed-id witness never ordered two numbers of
  different widths, and its oracle slugged with the code under test.
  **Bucket 1**, `witness`. **Landed:** a review commit on #781.
- `SA-0227` (#781): `open_attempt`'s docstring omitted two callers, and two
  texts named a command absent at that head.
  **Bucket 3**, conventions. **Landed:** a review commit on #781.
- `SA-0229` (#782): the draft review's sentence was asserted through the
  constant the code sends, so a rewrite passed.
  **Bucket 1**, `witness`. **Landed:** a review commit on #782.
- `SA-0229` (#782): the help text inverted `DESIGN.md` §3.4, and the cell
  hoisted literals the spec said to leave inline.
  **Bucket 3**, conventions. **Landed:** a review commit on #782.
- `SA-0234` (#783): the `GATE_ERROR` on a `CellRuntimeError` from `review`
  had no witness.
  **Bucket 1**, `witness`. **Landed:** a review commit on #783.
- `SA-0234` (#783): four comments misstated which raises miss, and a
  docstring said "retries".
  **Bucket 3**, conventions. **Landed:** a review commit on #783.
- `SA-0234` (#783): a PACKAGE raise after `READY_FOR_REVIEW` is offered
  again, so the whole cell is paid twice. The operator kept it.
  **No bucket**. **Open:** b-883f74.
- `SA-0237` (#784): a witness docstring claimed the host-driven seed reads a
  real seed's environment, and two texts pinned a fact to the base.
  **Bucket 3**, conventions. **Landed:** a review commit on #784.
- `SA-0238` (#785): two helper docstrings miscounted the seeded paths, and a
  witness docstring said "still".
  **Bucket 3**, conventions. **Landed:** a review commit on #785.
- `SA-0239` (#786): a docstring said "the checkout", which Worktree avoids,
  and `terms` passed it.
  **Bucket 1**, `terms`, whose table lacks the phrase. **Landed:** a review
  commit on #786. **Open:** b-4b386f.
- `SA-0239` (#786): the module docstring and the refusal misstated what
  refuses the write.
  **Bucket 3**, conventions. **Landed:** a review commit on #786.
- `SA-0240` (#787): the aborted leg's head added no advisory failure over
  base, and the size leg never read its code.
  **Bucket 1**, `witness`. **Landed:** a review commit on #787.
- `SA-0240` (#787): the body called every advisory gate advisory "at this
  risk tier", the spec's own words. The operator approved new ones.
  **Bucket 3**, conventions. **Landed:** a review commit on #787.
- `SA-0246` (#788): the crash witness accepted any pending state, and no case
  put a column in both mappings.
  **Bucket 1**, `witness`. **Landed:** a review commit on #788.
- `SA-0246` (#788): a comment cited the wrong item, and another stated an
  unmeasured `gh` failure as fact.
  **Bucket 3**, conventions. **Landed:** a review commit on #788.
- `SA-0255` (#790): the hook's files pattern missed the gate's own wrapper,
  and nothing pinned it.
  **Bucket 1**, `witness`. **Landed:** two review commits on #790.
- `SA-0255` (#790): the hook's preamble ran three lines with a semicolon,
  and no gate reads a YAML comment.
  **Bucket 1**, `prose`. **Landed:** a review commit on #790. **Open:**
  b-7f105f.
- `SA-0255` (#790): the test module copied a sibling's `revert` reason that
  is false here.
  **Bucket 3**, conventions. **Landed:** a review commit on #790. **Open:**
  b-a99c76.
- `SA-0233` (#780): the never-entered mutator's raise was swallowed, so its
  witness could not fail.
  **Bucket 1**, `witness`. **Landed:** a review commit on #780.
- `SA-0233` (#780): two docstrings overclaimed what `expressed` and
  `refusal` cover.
  **Bucket 3**, conventions. **Landed:** a review commit on #780.
- `SA-0233` (#780): the new `refusal` key reused `CONTEXT.md`'s Refusal for a
  per-edit decision.
  **Bucket 1**, `terms`. **Landed:** the operator's `CONTEXT.md` sentence
  on #780.
