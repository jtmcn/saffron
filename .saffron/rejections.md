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
