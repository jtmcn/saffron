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
