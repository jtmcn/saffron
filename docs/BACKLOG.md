# Backlog — what v0.5 left, and why each thing matters

Written at the close of v0.5 (`DESIGN.md` rev 14). Every item here is a gap a
live run exposed or a decision deliberately deferred — none is speculation about
what might be nice. Each says what "done" looks like, so it can be picked up
cold.

**Numbered in filing order, not priority order.** The numbers are an API — ten
comments under `saffron/` cite them (`BACKLOG item 33`, `backlog item 41`), so
an item is appended and never renumbered, exactly as `DESIGN.md`'s sections
are. The header line here used to claim the file was ordered by what would hurt
most on the first unattended night; it never was, and as items were appended it
drifted further. **The order to work in is the index below.**

**Where the evidence lives.** `DESIGN.md` Appendices I–L narrate what building
and running v0.5 found. The per-task briefs and implementation reports were
written under `.superpowers/`, which is gitignored and does **not** survive a
merge — anything from them worth keeping was moved into the appendices or into
`docs/superpowers/plans/2026-08-19-v0.5-findings.md` before this was written.

---

## Priority — the order to work in

Settled 2026-09-04. The sort is toward **v1's success criterion**: *a full night
runs while you sleep, and you merge at least half of what it produces before the
coffee's cold* (§9). That target is what makes the tiers below mean anything,
and it is the one thing to re-argue if the order looks wrong — the disagreement
will be with the target, not with the sort.

**Re-sorted 2026-09-07, toward the criterion's second half.** Every spec pull
request of the preceding week needed a human review round after packaging, and
the two worst diffs (#154, #160) drew the cleanest critic verdicts. So within
tier 1 the items that decide whether a `READY_FOR_REVIEW` is *sound* now come
before the ones that make a night *honest* about itself, and most of the latter
are cheaper by hand than through a cell. The argument, the exit criterion, and
which items go through a cell are in
`docs/superpowers/plans/2026-09-07-trusting-the-queue.md`.

### Tier 0 — the milestone gate

**58 is done** (merge `57b676c`, 2026-09-05), and with it **16** and half of
**44**. `saffron batch` exists and the machine below can start.

What replaced it as the gate was not an item: **run a night.** One has now run
against an empty queue (`DRAINED`, 2026-09-05) — the plumbing works. What is
still unmeasured is a night that *runs* something: no cell has started under a
batch, so the budget gate, the breaker and packaging are code with tests and no
evidence. That is the gate now, and it is one cheap spec away.

### Tier 1 — breaks at 03:00 with nobody watching

Soundness first: **79**, **69**, **93**, **94**, **80** (with **83**, **85**, **84**, **82**,
**81** from tier 3, which are why 69's gate cannot yet be declared against
safely), then the remainder of **71**. Honesty second:
**73**, **70**, **45**, **51** (with **49**/**50**, which its fix closes),
**47**, **46**, **40**, **26**, **7**, and the remainder of **78**.

Closed since the 2026-09-04 sort, and left in place because their numbers are
cited: **74** is done (`SA-0063`, `SA-0064`); **88** is closed on a negative
result (2026-09-08 — the gate summary was not the confound); **71** is
two-thirds done and **78** is done in code — each item's own `Status` line says
what is left.
(**59** is done — `SA-0052`, PR #118.)

**93 and 94 sit with them** because they decide whether their numbers can be
read at all: 93 is the metric's unknown resolution, and 94 is that 2 of the
baseline's 8 verified vacuities rest on a cell baseline nobody can inspect.
The corpus has a baseline (`3/12`, 2026-09-09), and the adequacy prompt changed
between the only two passes there have ever been — so nobody knows the metric's
resolution, and two passes disagree by 1 of 12. Until that is measured, a prompt
change read off a single pass is the mistake item 88 left on the harness this
corpus replaced.

**79 and 69 are first** because they are the only items here about the
factory's ability to tell whether its own work is sound. Nine tests shipped in
one session naming behaviour they did not guard, every one of them past the lens
built to catch exactly that; and REVIEW filed no blocker on the one diff that
destroyed a worktree.

**79 is 69's sibling and no longer the only one of its kind.** 69 is the lens
failing at a question only running can answer; 79 is the same lens answering it
in two runs of three and not the third — measured, so the item's own "a question
no lens owns" is retired in place. Both bear on the same thing: whether a
`0 blockers` line means the diff is sound or means nobody looked.

**88 was directly under 79** rather than filed behind it, and is answered
(2026-09-08) without moving the number. The harness still reads three times
harsher than production on the same diff and the leading suspect explains none
of it, so its absolute numbers steer nothing — and 79's exit criterion is
written against an absolute. Track C can start on the harness's *differences*
between two prompts; it cannot be declared met on them.

Each fails in the dark or destroys work no one is awake to rescue. **45** loses
a run's commits nightly; **51** switches the anti-theater gate off for one
printed line; **47** feeds part 3 a column of zeros; **46** is the only account
of a night nobody watched; **40** merges a diff over a ceiling it passed;
**26** cannot tell an empty night from a missing directory; **7** leaves §8's
flywheel inert exactly where it was meant to compound.

### Tier 2 — the morning after

Operator visibility parts 2 and 3 — `SA-0032`–`SA-0039`, with the plan's Task 6
rewritten onto **42** — then Task 11's by-hand documents (**36**, **37**,
**38**), plus **43**, **48**, **52**, **60**, **66**, **67**, ~~**72**~~.

**72 is done** (2026-09-07, by hand), taken ahead of Track A by operator
decision because it was the one item whose defect was a guard that could not
fire. Its number stays listed because item numbers are cited from `saffron/`.

### Tier 3 — real, not urgent

**22**, **23**, **31**, **19**, **20**, **53**, **54**, **14** + **55**,
**56**, **57**, **61**, **62**, **63**, **64**, **69**, **75**, **76**, **77**,
**81**, **82**, **83**, **84**, **85**, **86**, **87**, **89**, **90**, **92**.
(**65** and **68** are done; **80** moved to tier 1 when its evidence arrived.
**91** is done — the spike record landed. **92** was appended un-indexed, which
is the same defect as filing one nowhere at all. **94** was filed here and moved
to tier 1 the same day, when a host run turned it into a correctness item.)

**76 sits here rather than in tier 1** because `structure`, where the hole was
found, is closed: it refuses every ignore source and states its own file set.
What is left is the same change for ruff, which is a measurement rather than a
risk — not, as an earlier draft of this note said, that `.gitignore` in
`integrity.gate_config` already routes the edit to a person. That is the
*tracked* half only: a `.gitignore` naming itself reaches no diff at all.

**What this ordering costs, stated plainly:** tiers 2 and 3 hold 28 of the 39
open items, including every ontology item and every operator-visibility spec
there is already a full plan for. That is the deliberate consequence of ranking
by the milestone rather than by what is nearest to hand.

---

## 1. `integrity` needs splitting, not rewriting — and half of it may not be a core gate

**Status:** **done**, by hand, in PR #6 (merge `596f96f`) — not by the factory
patch this item was written about. That patch was reviewed and **rejected**, and
stayed in the batch tree; what shipped keeps its §2.1 split and its suppression
detection and replaces the rest. Nothing below needs picking up. Read it for
what the shipped gate is answering and why, not as work outstanding.

`SA-0004` produced a 371-line `integrity` gate that passed every gate and its own
31 tests, and adversarial review rejected it (Appendix K). The three Criticals
collapse into **two defects**, and they want different treatment.

### Defect A — a positioning bug. Fix it.

`\ No newline at end of file` is handled only *inside* a hunk, while git emits it
after one. So any diff touching a file without a trailing newline returns
`error`, which §5.4 turns into an aborted attempt the agent is never told about.
The branch exists; it is in the wrong place and untested.

### Defect B — the central heuristic is the wrong shape. Replace it.

"An existing test was removed" is inferred from **net line count**. Delete the
failing test, write a comment longer than the test, and the gate is green — the
exact evasion it exists to stop. The same comparison fails a legitimate
`parametrize` consolidation, so the only repair is padding the file, which
teaches the gaming. Wrong in both directions on one comparison is not a check.

**And the obvious replacement may not be possible in a core gate.** "What is a
test" beyond a path glob is language knowledge, and §2.1 keeps that out of core.
A better-shaped answer already exists in the contract: §5.4 requires the `tests`
gate to accept a **test-subset argument**, so the repo can already enumerate its
tests. If it reported the *collected test names*, comparing the set at `base_sha`
against the set at head answers the question **exactly** — no false positive on a
consolidation, no evasion by padding, and it catches a test silenced by renaming
out of collection, which the rejected gate blesses (verified in review).

The cost is that this half stops being diff-only, so it needs the `revert`-shaped
exception §2.1 already sanctions: *core invokes declared gates, never tools*.

**This is a design decision and belongs in `DESIGN.md` before any code.** §5.4's
`integrity` paragraph currently describes a single diff-reading gate; if test
removal moves to set comparison, that paragraph and the gate-role table change,
and the contract gains a requirement on what `tests` reports.

### What to keep

The review was explicit about what is good, and it is most of the file: the §2.1
split (not one language token in a code path), `error` vs `fail` not blurred,
count-driven hunk consumption with a fixture containing diff-shaped content,
line numbers derived from the `@@` header, and **suppression detection that is
correct** — added lines only, with the context-line and removed-line cases both
tested and right. The `gate_config` check is right too.

### Done looks like

- Suppression and gate-config checks surviving as a diff-reading core gate,
  with defect A fixed and §5.4's "unless `touches` explicitly includes it"
  exemption honoured — the rejected gate omitted it and so failed its own PR
  with sixteen violations.
- Test removal answered by comparing collected test sets, with `DESIGN.md`
  updated first to say so.
- Both wired into `run_one_cell`'s suite beside `scope`.
- A `-diff` gitattribute renders a text file as `Binary files ... differ`; that
  hides content but not paths, so `scope` is safe and this gate must treat such
  a section as unreadable rather than as no change (see item 2).

### Why it is first

Principle 49: a verification an agent can run itself is one it will have already
passed, so the core gates are the only gates that can ever fire.

Note the justification in §5.4 — that a hard-gate *repair loop* trains toward
test destruction — is not the reason this matters here, because the repair loop
has never fired (item 9). The reason is simpler and stronger: **`integrity` reads
the diff and does not care why the diff looks that way.** An agent that runs its
own tests, finds one hard to fix, and deletes it before ever committing produces
exactly the same diff as one that deleted it under repair. The gaming pressure
moved earlier in the process, not away — which makes this the only place that
deletion is visible at all.

**Done, 2026-08-22.** Split, and three of this item's own claims were wrong —
measured, not re-reasoned (`docs/evidence/2026-08-22-integrity-rejected-gate-measured.md`,
Appendix M). The batch tree holds a **post-rebuttal** patch, one fix past the one
Appendix K reviewed. Defect A was already fixed in it: all four positions git
emits `\ No newline at end of file` parse cleanly, so there was nothing to move
and nothing to test. The removal check was run adjacency, not net line count, so
the `parametrize` false positive was already gone — while the evasion was
*cheaper* than this item says, taking one adjacent added line of any content
rather than a comment longer than the test. And a defect nothing had recorded:
the suppression scan substring-matches every added line in every file, so
`d1141d0` — this repository's own merge of PR #5 — fails `integrity` on two
docstrings that quote `@pytest.mark.skip` while explaining that a critic's claim
quotes it.

What shipped: `integrity` keeps the two checks a diff can answer — added
suppressions, and gate-config edits — and treats a `Binary files ... differ`
section as unreadable rather than unchanged. Test removal became `census`, a set
comparison of collected test names, which also catches a test renamed out of
collection: the case every diff-shaped version blessed. **It needed no §2.1
exception.** This item assumed core would have to invoke the `tests` gate the way
`revert` does; it does not, because the baseline and head suites already run
`tests`, so the names needed reporting rather than fetching. The contract gained
one optional field, `collected`, and core subtracts two lists it already holds.

**The `touches` exemption binds `gate_config` alone.** The first design exempted
suppressions too, and review killed it: `scope` already requires every changed
file to be inside `touches`, so a per-file exemption fires on every file of any
diff that can reach green. Measured — a failing test silenced with
`@pytest.mark.skip`, its file named in `touches`, went green on `scope`,
`integrity`, `census` and `tests`. A file-level key cannot exempt a line-level
check without nullifying it. The cost of not exempting suppressions is that prose
quoting a token fails; that is accepted, because a `fail` reaches the repair loop
naming file, line and token, while a gate that never fires reports nothing.

**The cost is measured, not estimated — and re-measured whenever this paragraph
changes.** Against this branch's own diff (`d1141d0..HEAD`) with the real
`.saffron/policy.yaml`, `integrity` reports **71** failures across **11** files —
69 `added-suppression` plus 2 `gate-config-changed` — where
`d1141d0` itself produced 2. Almost all of it is this work's own prose about the
tokens the policy declares: 23 in the plan, 17 in `tests/test_integrity.py`, 7 in
`DESIGN.md`, 6 in the spec, 5 in the policy file, the rest in this file and the
evidence files. **The count is self-referential** — prose quoting a token is
counted, so the first two recordings of it went stale in the commit that made
them, by quoting the tokens they were counting. Describe them, never reproduce
them. A task whose `touches` names those paths is exempt, so this bites only a
task editing a prose file it did not declare. If it starts biting, the relief is a `prose_paths`
key in `integrity` — paths whose *added lines* are not scanned, distinct from
`touches`, which exempts the whole file — not a weaker token list.

**Three defects found by executing the work rather than reading it**, each closed:

- **One byte hid a suppression.** Git splits diff lines only on `\n`; Python's
  `str.splitlines()` splits on nine more characters. Git emits them raw inside a
  `+` line, so one added line shattered into fragments and a fragment beginning
  with a space was filed as a *context* line, which the suppression scan skips.
  Measured end to end: `import os\x0c  # noqa: F401` parses as valid Python,
  `ruff` honours the `noqa`, and `integrity` returned `pass`. The repo's lint gate
  obeyed a suppression the anti-gaming gate could not see.
- **The same line lived in `scope`.** `scope_gate` read the diff with
  `splitlines()` too, so the same injection reached it. Fixed with `integrity`
  rather than left one file away.
- **The evasion also lived one layer up, at the capture boundary.** `runtime._call`
  captured with `subprocess.run(text=True)`, whose universal-newline translation
  rewrites a bare `\r` to `\n` *before any gate executes* — so the line arrived
  already shattered and no parser fix could undo it. It now captures bytes and
  decodes explicitly. That also removed a latent crash: the old text mode decoded
  with the **host locale** under `errors="strict"`, so a non-UTF-8 byte from a
  cell could raise `UnicodeDecodeError` out of `_call`.

Still open, deliberately: a task that *legitimately* removes a test cannot pass,
since no exemption binds `census`. The upgrade path is a spec field, left unbuilt
until a task needs it. A genuine binary fixture inside `touches` trips
`integrity`'s unreadable-section rule — and the same rule is a **deterministic
route out of a red run**: committing a `.gitattributes` carrying `*.py -diff`
renders every Python file as `Binary files ... differ`, so a file inside `touches`
turns `integrity` into `error`, which `aborted_gates` reports as `GATE_ERROR` —
infrastructure, charged to nobody. An agent facing a failing run can reach that
on purpose. The vector is new to this split; the pre-split gate had no binary
handling at all. Closing it is a `--numstat` cross-check (a file git reports
non-zero added lines for cannot legitimately be unreadable), which is a design
change and not this branch's. And `exec_stream`, `LocalExecutor` and
`package.py` still capture with `text=True` — harmless today, since none of them
reads a diff that a gate judges, but they are the remaining siblings of the
boundary this work fixed. All carry `ponytail:` comments or a line here.

## 2. The agent can disable a core gate from inside the cell

**Status:** **done**, in `cf0dee8` (*fix(cell): a gate the agent could
reconfigure from inside the cell*). `DIFF_FLAGS` at `saffron/cell/worktree.py:131`
pins `--src-prefix=a/`, `--dst-prefix=b/` and `--no-ext-diff`, and both
`export_patch` and `changed_files` diff through it.

`worktree.export_patch` runs bare `git diff`, inheriting worktree config the
agent can write. One `git config diff.srcPrefix x/` and a diff deleting the
entire test suite reads as `pass`, because path matching no longer recognises
anything.

**Done looks like:** `export_patch` pins `--src-prefix=a/ --dst-prefix=b/
--no-ext-diff`, and any core gate reading a diff refuses a prefix it does not
recognise rather than silently passing. A test that sets the hostile config and
asserts the gate does not report `pass`.

**Done, 2026-08-20.** `worktree.DIFF_FLAGS` pins prefixes, `--no-ext-diff`,
`--no-textconv` and `--no-renames` on every diff the host reads, and `_git` adds
`-c core.quotePath=false`; a command-line flag beats repo-local `.git/config`,
measured on git 2.50 (including config reached through `include.path`).
`scope_gate` is handed that diff and reports `error` — infrastructure, charged to
nobody — when the headers are not `a/ b/`. Two things the review's account got
slightly wrong, both measured: `--name-only`, which is what `scope` actually
consumed, was never bent by `diff.srcPrefix` (the `pass` was the rejected
`integrity` gate's, which parses hunks); and `diff.external` and a textconv
driver are the sharper knobs — either can empty a diff entirely. Still open: a
`-diff` attribute renders a text file as `Binary files ... differ`, which hides
*content* but never a path, so `scope` is unaffected and the future `integrity`
gate must treat such a section as unreadable rather than as no change.

**And `size` inherits it, 2026-08-25.** Measured on `SA-0002`'s gate: a block
with no `@@` contributes 0, so `*.py -diff` in `.gitattributes` makes a
2000-line rewrite count as 1 and pass — at `elevated`, the one tier where
`size` blocks. It carries a `ponytail:` comment naming the ceiling rather than
a fix, because the honest response is `error` only when the unreadable file is
inside `touches`, as `integrity` already does, and `size_gate` is handed
neither `touches` nor a `--numstat` cross-check. **The wiring spec has both and
should close it**, which makes that spec's second reason to exist.

**Closed at the tier that blocks; corrected 2026-08-25 (#27).** `size_gate` is
handed `touches` and returns `error` when an unreadable block names a declared
path (`_unreadable_declared_path`, `saffron/gates/core/size.py:101`) — reusing
`scope.matches`, so "declared" means one thing in every gate. The paragraph
above stood as outstanding work after the work had shipped, which is the shape
#26 found on item 17: a stamp read as a plan.

**Two residuals, and the first was nearly lost to the correction above.** The
guard is `if unreadable is not None and blocking` (`size.py:162`), so at
`standard` an unreadable declared path still counts as zero lines silently.
That is the right scope — the original complaint was about `elevated`, the one
tier where `size` blocks — but it is a narrower closure than "closed", and an
advisory gate that under-reports is still a gate reporting something false.
The `--numstat` cross-check remains an upgrade path in the docstring rather
than shipped code.

## 3. `findings` and `attempts` have no tables

**Status:** **done**, in `229c4b2` (*feat(ledger): an attempt had no identity,
so every one of them shared the task's*). Both tables exist — `attempts` at
`saffron/ledger.py:54`, `findings` at `:98`.

`DESIGN.md` §4.1 declares both. Neither exists, so:

- REVIEW's findings and REBUT's verdicts and rebuttals live in `rebuttal.json`
  in the batch tree. §4.1 is explicit that `verdict`, `adjudication` and
  `rebuttal` are three distinct columns that must not collapse — they are three
  distinct JSON keys instead, which is the right shape in the wrong place.
- every attempt's gate results share one `attempt_id`, so "which attempt produced
  this failure?" has no join to stand on — the question §5.4's no-progress rule
  and §8's flywheel both assume is answerable.
- `tasks.spent_usd_est` does not exist, so a run ends with no persisted record of
  what it cost. Fine while an operator is watching; not fine for §4.2's budget
  gate.

`SA-0003` produced an `attempts` implementation, unreviewed, in the batch tree —
its patch no longer applies (see item 9).

**Done looks like:** both tables, the drop-rate-per-lens query answerable in SQL,
and cost on the task row.

**Done, 2026-08-23.** All three, by hand; `SA-0003`'s stale patch was not
reopened, and two review rounds followed. What is worth carrying forward, in the
order it was learned:

**The column had no `REFERENCES`, and that is what made the convention
possible.** `gate_results.attempt_id` was a bare `INTEGER`, so holding a
`task_id` in it was not a shortcut the schema tolerated — it was one the schema
could not see. It points at `attempts(attempt_id)` now, and the old convention
is unrepresentable rather than merely discouraged — though that took two more
commits than the schema line, and this paragraph claimed it a round early
(below). Two existing ledger tests asserted it directly and had to change;
`SA-0003`'s "every existing test still passes unchanged" was written before it
was clear that two of them encoded the defect.

**Attempts are opened by wrapping the agent callable, not at the call sites.**
`record_attempts` sits inside `stop_on_rejected`, so a turn the provider walled
records its cost before the rate limit is raised. The consequence is the reason
for the shape: the lens sessions inside `review.run_review` and the rebuttal and
verdict turns inside `rebut.run_rebut` all get rows without either phase
learning what a ledger is — they still take an `agent` and nothing else. A
turn that fails is still recorded; one that raises something neither layer
expects leaves its row open, which is an honest reading of what happened.

**`phase` is the state the task is in, and `spent_usd_est` is derived.**
`open_attempt` reads `tasks.state` rather than taking a phase, because the
caller already sets it at every phase boundary and tracking it twice is how the
two drift. `set_task_state` rolls the spend up from `attempts` in the same
statement, so the figure cannot disagree with the rows it is made of and no
terminal path can forget it — there are seven of them. The equality between
`tasks.spent_usd_est` and `CellOutcome.spent_usd` is asserted, because it is
what proves no spending turn is missing a row.

**`SA-0003` deferred `spent_usd_est` on a question that was already answered.**
It said the sum depends on "whether a resumed session reports per-turn or
whole-session cost, which is not yet known". `session.py` had since measured it
— $0.00396 fresh, $0.00199 on resume of the same `session_id`, so summing is
correct and cumulative would never fall. The deferral outlived its reason.

**Review found the migration, and the obvious repair is illegal.** A ledger
written before `attempts` existed holds a *task_id* in `gate_results.attempt_id`
— and a new attempt's id starts at 1 in that same integer namespace, so task 1's
v0.5 results reattach to whichever attempt draws id 1. Reproduced on a copy of
this machine's own `~/.saffron/ledger.db`, which is exactly such a ledger.
Nulling the legacy values out is not available: the `CHECK` that keeps exactly
one of `attempt_id` and `run_id` set rejects a row with neither, on `UPDATE` as
much as on insert. What shipped was the backfill the old schema comment promised
— one attempt row per legacy value, carrying that value as its own id, so the
ids stay taken and nothing is lost or moved. Measured on that copy: five
backfilled, zero dangling, every task still holding its own results.

**And the backfill protected the data without delivering the constraint.** A
second review round found the paragraph above true only of a ledger created from
scratch: `CREATE TABLE IF NOT EXISTS` is a no-op on an existing `gate_results`,
and SQLite has no `ADD CONSTRAINT`, so on an upgraded ledger the column still
read `attempt_id INTEGER` and a dangling `attempt_id` inserted silently. The
test that was supposed to prove otherwise passed because its fixture builds a
fresh file — the same shape of gap as the one this item exists to end, one level
up: a check that reads as enforcement and is a convention. What ships now is
SQLite's documented 12-step rebuild, after the backfill so every copied row
already has an attempt to point at, `foreign_keys` off across it because
`failures` references `gate_results`, which does not exist between the DROP and
the RENAME.

Dangling rows are copied in rather than refused. SQLite checks a reference when
a row is written, not when it is rebuilt, so a `PRAGMA foreign_key_check` gate
here is theatre: the rebuild has already committed by the time it runs, and the
next open takes the early-return path and lets the row through anyway. The
constraint governs what can be recorded from here on, which is what made the
collision possible. Measured on the copy again: 49 gate results, 12 failures,
5 tasks and 5 runs identical across the migration, a dangling write rejected.
The rewrite happens on first open, so the ledger is worth copying aside before
the next run.

**Two more from that round, both in what the ledger is told.** `task_spend`
selected `tasks.spent_usd_est`, which only `set_task_state` refreshes — correct
only when a state change happened to precede it, which today's one caller
arranges and a read from inside the repair loop would not. It sums `attempts`
now; the column stays, because it is what `queue_lines` reports without a join.
And the rebuttal write was lossy twice: `run_verdict` rejects a verdict set that
is not exactly its own blockers, but nothing validates the *rebuttal* turn's
numbering, so two entries for blocker 1 and none for blocker 2 left blocker 2
reading as unanswered against an artifact that says otherwise. Validated at the
write now. `Rebuttal.action` was dropped outright, which made a claimed fix and
an argument indistinguishable in `findings.rebuttal` — the distinction §4.6's
critic-ROI query is the whole reason for the column.

Two smaller ones from the same review. `open_attempt` against a task that does
not exist selected nothing and still returned `lastrowid` — an id that exists,
belongs to another attempt, and satisfies the foreign key; silent
misattribution, which is the failure this item exists to end. And `RATE_LIMITED`
was the one exit where the ledger and `CellOutcome` disagreed: the raise comes
from outside the turn, so it lands past the `spent +=`. The outcome reads the
attempts back now, which also closes the older gap where a window closing inside
`plan_checkpoint` lost the whole tally with its frame.

Still open, by choice: `findings.adjudication` has no producer — it is the
operator's, and the morning queue (§6) is where it comes from. `attempts.model`
is declared and never written: the runner's `result` event does not carry it and
only assistant messages do, so recording it means changing the event schema.
`batches` and `decisions` remain the two tables of the ten with nothing to put
in them.

## 4. Three of five supervisor bounds are missing

**Status:** **done**. All five bounds are present. Idle and completion landed
in `293f558` (*feat(cell): the two bounds that make silence mean something*) as
`runtime.IDLE_TIMEOUT_S` (300s) and `runtime.COMPLETION_TIMEOUT_S` (10s), and
`Completed.bound` names which of the three ended a read loop rather than
collapsing them into one flag. The wall clock is no longer the unoverridden
3600s this item was written about: `session.py:1115` passes `TURN_TIMEOUT_S`
(900s), and idle catches a stall five minutes in either way.

§4.3 wants turns, spend, idle, completion and wall clock. v0.5 has turns, spend
(host-side, per task) and a wall clock on `exec_stream`. **Idle and completion do
not exist**, and the wall clock defaults to 3600s that `run_one_cell` never
overrides — so an "attended" operator can watch nothing happen for an hour.

§4.3 is emphatic that splitting idle from completion matters: silence *before* an
agent claims to be done is a stall, silence *after* is a lingering child process,
and collapsing them makes a finished agent burn the full idle timeout and then
read as a failure.

**Done looks like:** all five, and a default wall clock an operator would
actually sit through.

**Done, 2026-08-20.** All five. `exec_stream` reads through a queue fed by a
reader thread, so every wait carries a deadline: `idle_s` (300s) before the
payload signals done, `completion_s` (10s) after it, and `timeout_s` for a turn
that keeps producing and never stops. `session.TURN_TIMEOUT_S` is 900s and is
bound onto the agent callable once, so plan, implement, repair, review and
rebuttal all carry it rather than inheriting the library's hour.

The split is load-bearing and is what the returned value now records.
`Completed.bound` names which bound fired; an idle or wall-clock expiry kills
and reports 124, a **completion window close reports 0 and is a success** — the
runner emitted its result and only a child was holding stdout open. `run_agent`
propagates it as `AttemptResult.bound` and its failure message names the bound
instead of saying "timed out" for all three. The done signal comes from
`run_agent` returning true out of `on_line`, not from the runtime parsing
events: the container seam does not know Saffron's schema.

Threads over `selectors`, measured against the alternative rather than
preferred: readiness on the fd is not a line, so a half-written one still
blocks `readline` and the fix is reimplementing line splitting over `os.read`.

**Amended 2026-08-21: one of the five was not bounding, and a bound firing
kills less than it looks like.** Two defects in the above, both measured.

The completion window was recomputed as `now + completion_s` at the top of
every loop iteration, and the `signalled` branch short-circuits the wall clock
— so every line a child wrote pushed the deadline out again and nothing else
applied. A child writing steadily after the result event held `exec_stream`
open forever: an unbounded wait, inside the function whose five bounds exist so
that no wait is unbounded. The window is now fixed once, when the result event
lands, and a chatty child cannot move it.

And the kill does not reach the cell. Measured against a real `container` — a
detached container, a long `container exec`, `proc.kill()` on the host side,
then a look at `/proc` from inside — the process is still there. Killing the
exec client kills the client. So an idle or wall kill left the agent running in
the cell while the driver went on to measure `commits_ahead`, run the whole
gate suite and resume the session, all in that same container, with an
abandoned agent still able to edit `/work` and commit underneath every one of
them. `runtime.reap_cell` now kills everything but PID 1 on those two bounds —
never on the completion window, which is a turn that finished. Measured again
after: the abandoned process is gone, `sleep infinity` survives, and the cell
still takes the next exec.

## 5. PACKAGE, and the fact that patches perish

**Status:** **done** — PACKAGE shipped as sub-project A (`cc986bf` onward,
`saffron/phases/package.py`), and `DESIGN.md` §5.7 is its specification. Patches
no longer perish: a green run rebases onto the remote default branch, re-runs the
full suite when the base moved, pushes a branch and opens a draft pull request.
Item 11 is this build's own follow-up list and item 16 is what its policy fix
left.

There is no PR, no push, no index. A green run leaves `patch.diff` and
`patch.json` in the batch tree and nothing tells you they are there — finding one
requires knowing the layout by heart.

Worse, they decay: `SA-0003`'s patch no longer applies, because three hours of
commits moved `session.py` underneath it. A verified-green change has a shelf
life measured against the branch it was cut from.

**Done looks like:** §5.7's PACKAGE — rebase onto current `main`, re-run the full
suite on the merged result, push with `--force-with-lease` pinned to the checked
SHA, open the PR with the body §5.7 describes — and §6's index. Until then a
patch older than its base is a patch nobody can use.

**Done, 2026-08-22** (PR #5). All of it, and the re-run is conditional: if the
fetched default-branch head still equals `base_sha` the packaged tree is
byte-identical to the one the suite already ran on, so re-verification is
*provably* redundant and the body says it was skipped and why. Otherwise the
suite re-runs in a gate-only cell — never host-side, because the applied tree
carries `.saffron/gates/*` exactly as the patch left them (§2). The base having
moved also invalidates the old baseline, so that cell runs the suite twice and
subtracts, which is §4.4 steps 2-3 applied to one commit.

Three things the build measured rather than reasoned, all now in §5.7. A
conflicting `git apply --3way` exits 1 **and still writes the file**, markers
staged — "apply failed" and "nothing happened" are different states. A degraded
apply exits **0**: preimage blob absent, context matching, and git falls back to
direct application, so conflict detection silently becomes a context match. And
`git commit` in a `--mirror` clone with no identity does not abort — it
auto-detects from the OS and attributes machine-written commits to the operator,
so `commit_squash` passes `-c user.email=saffron@localhost` on the command line.

`repos.origin` now holds the real remote; since v0 it held the mirror's *source*,
a local path, so nothing downstream knew where a pull request would go (§4.1).

## 6. The critic's lenses overlap, and the third does not exist

**Status:** **done** — `SA-0043`, PR #105 (`80a7a3e`). The third lens exists
as `saffron/agents/prompts/review-adequacy.md`, wired at `phases/review.py:39`.
The remit question this item raised was settled separately by #34, and
`review.py:41` records the reasoning: the third lens is adequacy, not blast
radius.

Measured on the critic's first live run (Appendix L): **both lenses filed the
same `touches` finding.** §5.5's no-voting rule rests on lenses being disjoint by
construction — *"the schema critic will never independently corroborate the
correctness critic's timezone finding"* — so an overlap is a prompt defect, not a
duplicate to deduplicate. Principle 51: two lenses reaching one finding is a fact
about the prompts, and it reads as corroboration, which is what makes it
dangerous.

Lens 3 (blast radius) is not built because no risk tier is wired into
`run_one_cell`. It is the lens that would have caught item 2 — the review found
the `srcPrefix` escape and the critic did not, because it lives in `session.py`
rather than in the diff.

**Done looks like:** remits that do not overlap, a risk tier on the task, and the
third lens at `elevated`.

**Amended 2026-08-25 by `SA-0002`, and the amendment changes what lens 3 should
be.** The overlap did not recur: correctness filed the counting blocker,
contract filed a `tool` concern, disjoint by construction on a second live diff.
One run is not proof the prompts are fixed, but it is evidence the remits hold.

The sharper finding is what *both* lenses missed. A later review of the same
97-line diff found two mediums neither lens raised. One was a `-diff`
gitattribute zeroing the count — the escape route item 2 leaves open, arriving
in a new gate. The other was that the multi-file header reset had **no test**:
deleting the line left all sixteen tests passing while a two-file diff
overcounted by two lines per file. That second one is the same class as the
blocker correctness *did* catch — a header-collision bug in `_changed_lines` —
found one level up, in whether the suite would notice a regression.

So the gap the third lens should close is not blast radius. **No lens asks
whether the tests would catch the code being wrong**, and a critic that reads
the diff without mutating it cannot: the implementer's own tests passed, the
gates were green, and the line was invisible to every one of them.

**Corrected 2026-08-25 by #33: the line is not uncovered, and the word mattered.**
Measured twice independently — `saffron/gates/core/size.py` reports **100%
statement and 100% branch coverage** from its own tests, and the reset line is
executed by every one of them. The defect is an *executed line whose effect
nothing observes*, which is the one class coverage cannot report by
construction. The wrong word had a cost: it made diff-scoped coverage look like
a cheap answer to this remit, and #33 was written to price an option that was
never available. See `docs/evidence/2026-08-25-mutation-testing-vs-a-lens.md`.

**And `DESIGN.md` §5.5 says the opposite of this item, which is #34's to
settle.** `DESIGN.md:782`: *"lens #3 in a naive design would be 'test quality' —
but the `revert` gate now answers that mechanically and for free."* Neither
document cites the other. The displacement is also incomplete (reasoned, not
measured): `revert` stashes the source hunks and requires the new tests to fail,
but `SA-0002` landed source and tests together, so stashing the source fails all
sixteen and `revert` reports green without ever asking whether the reset line
specifically is tested. `revert` asks whether the new tests test *anything*;
this remit asks whether they test *each thing*.
§5.5's disjointness argument still holds — this is a third remit, not a second
opinion on the first two.

**Half done, 2026-09-02, by #34 — the remit half, not the risk-tier half.**
This item's own "done looks like" named two things: remits that do not
overlap, and the third lens at `elevated`. Only the first shipped. The third
lens is `adequacy` (`saffron/agents/prompts/review-adequacy.md`), a prompted
critic with no mutation tool and no coverage gate — both were priced again
against this item's own evidence and both lost again, for the reasons already
recorded above. It reads the diff and asks whether the tests in it would
actually notice the code being wrong: an assertion on a value the exercised
code never reads, a test that constructs the value it then asserts, a
structural check over source text a rename defeats, a witness whose setup is
the only input the new code is correct for. Holding no tool that can run
anything, it cannot mutate a line and watch a test fail the way a person
would — so every finding names the edit that would keep the suite green
instead, checkable in one command by whoever can run one. The correctness
lens's own `Evidence` bullet — the one BACKLOG item 6 first flagged as
misfiled test-adequacy language sitting under a data-semantics remit — moved
into this lens rather than being copied, and all three prompts now name all
three boundaries in their `Not yours` lists.

**The risk-tier half is deliberately still open, not silently dropped.**
Nothing in v0.5 or since carries a risk tier that could gate this lens the way
this item originally specified, and building one was out of scope for #34:
measured against this repo's own specs, 28 of 34 declare `elevated`, so
gating on tier would exclude six specs while costing an edit to the
supervisor — which #34 could not touch — for a saving of one lens session
($0.76–$0.91 on the two specs it was priced against). The lens runs at every
tier instead, and REVIEW is not gated on the host budget ceiling, so this
does not fail a task for money. Closing this item for real still means
wiring a risk tier into `run_one_cell` and deciding whether `adequacy` is the
lens that tier gates or whether, having shipped ungated, it stays that way.

**And `DESIGN.md` §5.5 still says the opposite of the shipped code — #34 did
not settle it after all.** The spec put `DESIGN.md` and `CONTEXT.md` in
`forbidden`, so the cell structurally could not touch either; the sentence
above assigning that half to #34 stands unanswered rather than resolved, and
this paragraph exists so the trail is not lost with the work. §5.5 still lists
lens #3 as blast radius at `elevated` (`:889`, `:893`), still asserts `revert`
displaces a test-quality lens (`:903`), and §5.6 still says the tier *adds*
the third lens (`:915`); §7's cost table still prices `Review × 2 lenses`
(`:1124`) and the roadmap still files the third lens under v2 (`:1217`).

`CONTEXT.md` is worse than stale, because it is a runtime input rather than a
record: §5's `Lens` entry names the three remits as correctness, contract and
blast radius, and `context.SECTIONS_BY_PHASE["REVIEW"]` injects §5 verbatim
into every lens's system prompt under a heading reading *"These terms have
exactly one meaning here."* The adequacy lens is therefore handed a vocabulary
block that does not contain its own lens and does contain one that will never
file anything, and §3's *"Elevated adds the third lens"* is now false at every
tier. No gate compares either document against `review.LENSES`, so both are
invisible to the suite.

**Retiring blast radius leaves its remit owned by nobody, at three seats.** All
three prompts still name "the blast-radius lens" in their `Not yours` lists, so
callers-and-downstream findings are actively routed away from every lens that
could file one — worse than uncovered, because each lens is told someone else
has it. Left deliberately (`DESIGN.md` §5.5.1): releasing the remit by editing
three `Not yours` lists scatters it across three lenses, which is the overlap
this item was opened about. Reviving it is a new decision with its own
evidence, and it wants the same risk tier the half above is waiting on.

## 7. `CLAUDE.md` no longer reaches the agent, so the flywheel's middle bucket is inert

`setting_sources: []` was set because a target repo's `.claude/` was configuring
the agent working on it — measured, a planted subagent and skill both loaded out
of `/work` (Appendix J). The fix is right and it has a cost: the repo's
`CLAUDE.md` stops loading too, and that is §2.1's named learning surface and
**bucket 2 of §8's entire flywheel.**

**Done looks like:** `CLAUDE.md` injected host-side from the mirror, the way
`CONTEXT.md` already is — which is the better shape anyway, since a file under
`/work` is rewritable mid-attempt.

## 8. N1 rests on seven guessed ports

**Status:** **done**, in `8e6838a` (*feat(preflight): a host process the
operator has accepted, named and reported*). `PROBED_PORTS` is gone.
`listening_sockets` parses `lsof -nP -iTCP`, `host_probe_ports` raises rather
than covering nothing when the enumeration fails, and `probed_ports` drops a
port only when *every* listener on it is a tolerated process.

`preflight.PROBED_PORTS` is `5432, 5433, 3306, 6379, 8000, 8080, 27017`. The
probe raises rather than passing when it cannot run, which is right — but "no
host service answered on seven ports I thought of" and "no host service is
reachable" are different claims, and the code and `DESIGN.md` both currently make
the second.

This was not hypothetical: the host service that *was* exposed sat on 8000 and
was caught, while four more on 8001+ would have been invisible.

**Done looks like:** enumerate the host's actual wildcard-bound listeners and
probe those.

**Done, 2026-08-20.** `preflight.host_listening_ports()` parses `lsof -nP -iTCP
-sTCP:LISTEN` and probes every listener not bound to loopback — a superset of
wildcard, because a service bound to the LAN address is reachable from a cell
too. Enumeration that cannot run raises; only lsof's own listing counts as
having run, so a listing with nothing but loopback rows is the real empty and a
silent lsof is not. Measured consequence on the machine v0.5 ran on: four macOS
services answer from inside a cell (ARD 3283, Control Centre 5000/7000, rapportd
49152), none of them in the old seven, so `preflight` now fails there until they
are turned off. That is the probe working.

**Amended 2026-08-21: one of the four is now tolerated, by name.** Three of
those services were turned off; `rapportd` remains, holding `*:49152` whatever
Continuity's settings say, and AirDrop going back on will reopen the two ports
it closed. So the probe was refusing to start a cell, permanently, for a daemon
the operator has accepted. `SAFFRON_ALLOW_HOST_PROCESS=rapportd` tolerates it
for that invocation: empty by default, matched by the COMMAND `lsof` reports
rather than by port (rapportd's ports are dynamic — 49152, 60215, 60216 all
seen), and a port drops out only when every listener on it is tolerated. The
preflight line names what was tolerated on every run, because an exception that
goes quiet is the hazard the probe exists for. Enumeration that cannot run
still raises. **This is an accepted risk, not a fix** — an agent in a cell can
reach that socket, and `DESIGN.md` Appendix G says so and says what it costs.
Renamed with it: `host_listening_ports()` → `host_probe_ports()`, which now
returns the ports probed *and* the listeners tolerated.

**Also 2026-08-21.** The probe enumerated a second time inside
`probe_host_bindings`, so the port list the operator was shown at the top of
preflight was not necessarily the one checked; it now takes that list as an
argument. It also connected serially at 1.5s per address-port pair, which puts
roughly a hundred listeners over the 300s cap — preflight failing for having
too much to check, and reporting it as a probe that did not run. The connects
go through a thread pool now; the timeout stays generous.

## 9. Unverified against a live model

**Status:** **partly met, and the standing claim in it is now false.** Two of
the three "expensive" paths this item was waiting on have since fired in
production, both recorded elsewhere in this file rather than here:

- **A critic confirming a plausible-but-wrong finding** — item 42, measured on
  `SA-0040` 2026-09-01. The critic wrote `confirmed: The implementer offered no
  argument and made no visible change` about a finding that was false, and the
  operator inherited a pull request body asserting it.
- **`GATE ⇄ REPAIR` firing at all** — item 45, measured on `SA-0031`: six
  commits, 39 new gate failures and an `EXHAUSTED` terminal. The bullet below
  claiming it "did not fire, for the fourth time" describes 2026-08-25 and has
  not held since.

**Still unmet:** a rebuttal that claims a fix and does neither — §4.3's doneness
rule at the point an agent has the strongest incentive to lie. That one still
needs a task chosen to fail rather than a fifth hope.

Everything here is built and unit-tested and has never met a real session. On
this project's evidence that is exactly where the next defect is.

- **GATE ⇄ REPAIR has never fired.** Three live tasks, three greens on attempt
  one, because a capable agent with `Bash` runs every gate it can reach before
  committing (principle 49). Repair's real domain is only the core gates.
- **A critic confirming** rather than withdrawing. The one live REBUT saw a
  blatantly false blocker withdrawn; a plausible-but-wrong finding is untested,
  and that is the kind that costs mornings.
- **A rebuttal that fixes and commits**, with `head_moved` true.
- **The gate re-run after a rebuttal**, and `EXHAUSTED` when it is red.
- **A rebuttal that claims a fix and does neither** — §4.3's doneness rule at the
  point an agent has the strongest incentive to claim it is done.

**Half met, 2026-08-25**, by `SA-0002` — the first task to run the whole
pipeline, spec to pull request (#15), $2.38 against an $8 budget, green on
attempt one.

**Two of the five fired, and the pair that fired is the pair that matters
most.** The correctness lens filed a true blocker: `_changed_lines` dropped any
hunk line *starting with* `---`/`+++`, so a SQL `-- comment` or a YAML `---`
undercounted the diff. The implementer fixed it, committed, `head_moved` true;
the gates re-ran clean on the new head; the lens withdrew its own finding on
the evidence. That is REVIEW ⇄ REBUT closing the loop against a real defect
rather than a planted one, which is what Appendix L could not show.

**Three are still open** and they are the expensive three: `EXHAUSTED` when the
post-rebuttal re-run is red, a rebuttal that claims a fix and does neither, and
a critic *confirming* a plausible-but-wrong finding. All three are failure
paths, and a green run cannot exercise them — which is the argument for a task
chosen to fail rather than for waiting.

**GATE ⇄ REPAIR did not fire, for the fourth time.** Four live tasks, four
greens on attempt one. This is no longer an accident to be waited out: an agent
with `Bash` runs every gate it can reach before committing, so the bullet above
is the standing behaviour and not a sampling artifact. Repair's domain is the
core gates the agent cannot run — `scope`, `committed`, `census` — and testing
it means a task that trips one of those, not a fifth hope.

**And the run measured two things nothing had.** The agent's `uv run pytest`
took four `403`s from the proxy and cost three turns (item 10, closed). And
five tests in this repo's own suite failed inside a cell while passing on the
host, so the baseline every gate result is subtracted from was carrying five
failures for reasons unrelated to any task (closed by PR #16). Both were
invisible to every unit test and to three prior live runs; both cost money on
the first task that reached PACKAGE.

## 10. Small, measured, cheap

**Status:** **done bar one bullet.** Three of the four carry their own dated
closures below. The open one is `implement.md` doing double duty — it still
emits a plan block when told to implement, and `session.py:391` still always
sends `PLAN_PROMPT` first, so it stays harmless and stays untidy.

- `rebut.py` numbers blockers from 0 in the prompt. **Done, 2026-08-21:**
  numbered from 1 in both places they are produced. Not cosmetic —
  `run_verdict` requires the verdict set to match the blockers exactly, so a
  critic answering "1." for the first of one blocker failed the check, and
  the phase discarded both lens sessions, both rebuttal turns and every
  verdict session over the numbering.
- `implement.md` is non-deterministic on the first turn — 2 of 3 live sessions
  emitted a plan block when told to implement. Harmless today because
  `session.py` always sends `PLAN_PROMPT` first, but the template is doing double
  duty.
- `uv run` inside a cell rebuilds and reinstalls the project on every invocation,
  and would fail outright if it ever needed the network — the proxy allows one
  host. Agents work around it with `python -m`, at the cost of a turn.
  **Done, 2026-08-24.** It does need the network, and the cost is three turns,
  not one: `SA-0002`'s implementer took four `403`s from the proxy on
  `pypi.org` before reaching `python3 -m pytest`. `UV_NO_SYNC=1` in
  `.saffron/Dockerfile` runs it out of the venv the image already baked. The
  general form is an onboarding requirement rather than a Saffron fix, and
  §5.1 now carries it: a repo's image pins its runner to the baked
  environment, because the workaround leaves the run green and bills the
  difference to the task.
- `image_exists` was deleted as dead; if PACKAGE wants a stale-image check it
  comes back.

---

## 11. What PACKAGE left, and the one design question it raised

**Status:** **done**, 2026-08-23 — all six, plus the design decision the
first one asked for, in `DESIGN.md` rev 16. The full account is in this item's
own body below. **One accepted risk stands and is not closed by it:** the
credential refusal keeps a secret off the remote, not off the host, and §5.4's
`secrets` gate is still v1's to build.

Written at the close of sub-project A (PR #5). Every item was found by review or
by measurement during that build; none is speculation. The first is a design
decision, the rest are small.

### The base a task is cut from is the working copy's `HEAD`, not the default branch

`cli.py` sets `base_sha` from `git rev-parse HEAD` in the repo you invoked it in.
Run from a feature branch, `base_sha` is that branch's tip, so the fetched
default-branch head never equals it: re-verification fires on **every** package,
starting two containers and running two full suites, and the "provably redundant
skip" is only reachable from a checkout sitting exactly on an up-to-date default
branch. Worse, the patch is cut against a tree the default branch has never seen,
so `--3way` merges onto a base missing every commit the feature branch carries,
and a task touching a file the branch also touched conflicts — a `MERGE_FAILED`
that is an artifact of where the operator was standing.

**This is a design question, not a defect.** §5.7 is silent on where `base_sha`
comes from, and the scheduler (§4.2) will need an answer before it can start
tasks unattended. **Done looks like:** §5.7 saying whether a task's base is the
invoking checkout's `HEAD` or the remote's default branch, and the code agreeing.

### `github_slug` fails quiet on anything that is not a two-segment GitHub URL

Measured: `/Users/joel/Code/saffron` returns `Code/saffron`, and a GitLab-style
`group/owner/repo` returns `owner/repo` — the leading segment is dropped rather
than refused. Harmless for `github.com`, which is always two segments, but a
local-path origin is exactly what `session.py` falls back to, and a wrong slug
reaches `gh` as a repo that does not exist. **Done looks like:** a URL that is not
a recognisable forge remote raises rather than guessing.

### A pushed branch whose `gh pr create` failed is recorded nowhere but stdout

`_finish` runs after `open_draft_pr`, so a `gh` that is missing, unauthenticated,
or refused leaves the branch pushed and the ledger still reading
`READY_FOR_REVIEW` with no `branch` and no `pushed_sha`. A re-run self-heals — the
lease matches the branch it pushed — but the operator has to know that. **Done
looks like:** branch and pushed sha recorded before the pull request is opened,
and only the URL after.

### `reverify`'s cell does not get the repo's `thread_env`

The in-cell suite runs under `cell_env(proxy_ip, policy.thread_env)`; the
re-verification cell gets `env={}`. Empty for Saffron, so it changes nothing
today — but the two suites being subtracted are run under different environments
by construction, which is a suite-drift vector for the second repo onboarded
(§9's v2 is where that bites).

### Three test gaps, each one assertion

The pipe-escaping test covers only `_new_failures`, not the two tables added for
findings and disagreements — and a `|` is likelier in a model-authored `claim`
than in a gate message. `test_an_unanchored_finding_still_appears` checks the
claim renders but never that the row is marked `no`, which is the half that makes
drop rate visible (§5.5). And no test exercises `attempts`, `new_failures`,
`reviews` or `rebut_result` on `CellOutcome`'s success path.

### §5.7 says "rebase" and means `git apply --3way`

Step 1 says *rebase onto current `main`*; the v1 subsection describes applying one
squashed patch. Both are true — step 1 is the intent, the subsection is the
mechanism — but the document never says so, and a reader meeting them in order
will think one contradicts the other. One sentence, no renumbering.

### And one accepted risk, restated so it does not go quiet

The credential refusal keeps a secret off the *remote*, not off the *host*:
`patch.diff` and `pr_body.md` still sit in the batch tree with it in them.
`_CREDENTIAL_SHAPES` is a partial list under a `ponytail:` comment naming that
ceiling, and the real answer is §5.4's `secrets` gate, which is still v1's to
build.

**Done, 2026-08-23.** All six, and the design decision the first one asked for
is written down: `DESIGN.md` rev 16 — §5.1 for the fetch, §5.4 for the gate
source, §5.7 for the base, Appendix N for what building it found. A task's base
is now the head of the remote's default branch as of task start, so both ends of
the comparison read one source and the redundant-suite skip is reachable by
construction rather than from a checkout that happened to be standing in the
right place. Two things this item got wrong, both measured rather than
re-reasoned:

**`github_slug` was wrong on three of five real inputs, not on GitLab alone.** A
one-segment URL — `https://example.com/repo` — takes the **host** as the owner,
which this item does not name and which is the case where a wrong slug looks most
plausible. And the first fix was itself wrong, caught in review: a pattern
matching `github.com` after any of `^ @ / .` let `/Users/joel/go/src/github.com/owner/repo`
through, and twelve fixtures had by then been moved to a path shape that
satisfied it. Appendix N carries the 14-case table the shipped pattern is
measured against.

**The ledger defect is one column, not two.** `branch` was already written at
insert time by `create_task`, from `spec.branch`; only `pushed_sha` was missing,
written solely by `set_task_package` after `open_draft_pr`. What ships records
the pushed sha before the pull request is opened and the URL after.

`reverify` takes `dict(policy.thread_env)` rather than `cell_env(...)`: the
obvious route would have put `CLAUDE_CODE_OAUTH_TOKEN` into a gate-only cell with
no proxy and no egress. The three test gaps are closed, and §5.7 now says in one
sentence that step 1's "rebase" is the intent and `git apply --3way` the
mechanism. The accepted credential risk above is unchanged and still §5.4's
`secrets` gate to close.

---

## 12. `census` trusts the gate runner, and the gate runner is in the cell

**Status:** **done**, 2026-08-23 — both halves. The full account is in this
item's own body below, which was written as the fix landed; this line exists so
a scan of the file's status markers sees it.

Promised by the split's spec (part 2.3) and not written until the fix wave.
`census`'s subtraction is exact about the two lists it is handed, and both lists
are produced inside the untrusted cell — by `/work/.saffron/gates/tests.py` and a
second pytest process. CLAUDE.md's founding line is that every control that
matters lives outside the cell; this one does not. Two routes, both measured:

- **A `conftest.py` that lies to `--collect-only`.** A
  `pytest_collection_modifyitems` that drops a test only when
  `config.option.collectonly` is false makes enumeration report a name the run
  never executes. `census` passes because the name is still collected; `tests`
  passes because the test never ran. The removal is invisible to both.
- **Uncommitted edits are invisible to every diff-reading gate and fully
  effective on every gate result.** `worktree.export_patch` and
  `worktree.changed_files` both diff `base_sha..HEAD`, while `CellExecutor` execs
  gates against `/work` — the worktree. So **any** uncommitted change is absent
  from `scope`, from `integrity` and from the packaged patch, while being live
  for the suite. The spec names `/work/.saffron/gates/tests.py`, and the
  `.saffron/**` `gate_config` pattern closes only the committed case — but the
  hole is wider than one file: an uncommitted edit to any source file changes
  what the suite is measuring, and the reviewer reads a patch that does not
  contain it.

Neither route argues for the diff-shaped removal check this branch rejected: that
one was evadable by a single adjacent added line and needed no `conftest.py` at
all. The honest statement of what shipped is that **`census` buys exactness
against an honest suite, not integrity against a hostile one.**

**Done looks like:** a decision on the gate-runner trust boundary, which §5.4's
`no-network` gate and the gate contract both currently assume is cooperative. The
two candidate halves are independent: (a) gates run from a host-supplied copy of
`.saffron/gates/` rather than the one in `/work`, so an in-cell edit — committed
or not — cannot reach the runner; (b) the host refuses a dirty worktree at gate
time, or diffs `base_sha..worktree` so that an uncommitted edit is at least
*visible* to `scope` and `integrity`. Neither is v0.5's to build, and this item
exists so the choice is made deliberately rather than inherited.

**Done, 2026-08-23.** Both halves, which this item leaves as alternatives.
`.saffron/gates/` is exported from the mirror at `base_sha` and mounted read-only
at `/gates`, and the runner execs from there; a new core gate, `committed`, fails
the attempt when `git status` is not clean at gate time, one failure per path.
`DESIGN.md` rev 16 states the invariant both serve — anything that changes what
the suite measures must appear in the patch a human reads — and restates the
residual unchanged: a committed `conftest.py` still defeats `census`, and
`**/conftest.py` in this repo's `gate_config` routes that edit to a person rather
than failing it.

Two things this item does not contain, both worth more than the routes it names:

**Pinning the gates closes a baseline drift nothing had recorded, and that is the
stronger reason for doing it.** The baseline suite runs in the same cell and the
same worktree as head, before the agent starts, so the baseline ran the base
tree's gates and head ran whatever gates were in `/work` by then — a task editing
its own `tests` gate changed what the two subtracted sides mean. Suite drift by
construction, the same shape item 11 flags for `reverify`'s missing `thread_env`.

**`reverify` was a second copy of the same seam.** Its own cell, its own
`prepare_worktree`, its own `gate_executables(WORKTREE_MOUNT)`. Changing only
`session.py` would have left the two suites `reverify` subtracts coming from
different executables, and a required `gates_dir` would have broken PACKAGE at
runtime — invisible to `make check`, because the tests covering that path are
cell-marked and excluded by default. Found by review, not by running.

The dirty-tree half needed no new control flow: `committed` is a gate, so a dirty
tree gets the repair turn the loop already gives every `fail`, and a second
identical look ends the attempt on the no-progress rule.

---

## 13. Gate executables come from `base_sha`; the policy declaring them still comes from the working copy

**Status:** **done**, in `1b670c3` (*fix(session): the policy declaring a
run's gates came from the working copy*). `session.py:800` reads
`load_policy(gates_dir)` — the same export the gate executables resolve
against.

The same asymmetry item 11 raised for a task's base, in a second place, left
half-closed by the fix that closed the first. `session.py` calls
`load_policy(repo)` — reading and validating `.saffron/policy.yaml` and the
gate executables in the operator's working copy — then resolves
`gate_executables(Path("/gates"))` against `export_gates`'s archive of
`base_sha`, the remote's default-branch head. Before this branch those were
the same tree; now they can diverge on any branch that touches `.saffron/`.

Two concrete consequences. An operator on a branch that adds a gate role gets
a `PREFLIGHT_FAILED` whose watch line reads *"the toolchain is broken, not the
code"* — a wrong diagnosis for a policy/export mismatch, not an infrastructure
failure. And `policy_sha` in the ledger names the working-copy policy rather
than the one that actually governed the exported gates, so the ledger's record
of what ran is not the record of what was declared.

A repo adding its *first* gate lands somewhere else again, and worse. There is
no `.saffron/gates` at `base_sha` at all, so `export_gates` raises on the
unmatched pathspec at `session.py:572` — after the image build, the host probe
and the proxy — and the run exits 2 as infrastructure rather than reaching
`PREFLIGHT_FAILED`. `export_gates_for`'s guard covers the opposite case,
`gates: {}`, where the policy declares nothing to export.

This is the ordinary workflow, not an edge case: writing or renaming a gate
means being on a branch that adds it, and running `saffron cell` from that
branch is how you would test it. The run reaches `PREFLIGHT_FAILED` before the
agent starts, so it costs nothing but the wrong diagnosis. Until it is closed,
the workaround is to land the gate on the default branch first — `base_sha` is
the remote's head, so the export sees a gate only once it is pushed there.

**Done looks like:** `load_policy` reading from the same export
`gate_executables` already resolves against, rather than from `repo`.
`export_gates` already archives a subtree with `git archive <sha> .saffron`;
loading policy from that archive — `git archive <sha> .saffron` plus
`load_policy` pointed at the export instead of the working copy — is the shape
of the fix, not a new mechanism.

**Done, 2026-08-24.** The shape held: the pathspec widened from
`.saffron/gates` to `.saffron`, and `_drive_cell` reads its policy back out of
that export. Three things the item did not say.

**The fix deleted a function rather than adding one.** `export_gates_for`'s
`gates: {}` guard existed *only* because the narrow pathspec made `git archive`
fail on a repo with no `gates/` — widening it removes the guard's reason, and
`export_gates` already cleared its own dest, which is the half of that guard
worth keeping (its staleness test moved onto `export_gates` with it). Renamed
with it: `export_gates` → `export_saffron_dir`, because a function that now
carries the policy the run is judged under cannot be named for the subdirectory
it used to copy.

**The export moved out of the try block, not just above `load_policy`.** It ran
after the image build, the host probe and the proxy; it now runs before all
three and before the ledger has a task row — so a `base_sha` carrying no
`.saffron` at all costs nothing and leaves no run behind. That case is still an
exit 2: a repo whose default branch is not onboarded cannot start a cell, which
is what pinning the policy to `base_sha` means and is stated in §5.4.

**`/gates` now also holds `specs/` and the `Dockerfile`** — everything under
`.saffron/`, because one archive is one pathspec. They are read-only and the
cell already has all of it at `/work`, so this leaks nothing; it is noted
because a mount named `/gates` holding specs is otherwise a surprise.

---

## 14. `committed` fails on build artifacts a repo does not gitignore

**Decided 2026-09-04, and the item's own open measurement is now taken.**
`.gitignore` is the declaration. It already exists, `git status --porcelain`
already honours it, and stating that as an onboarding requirement is the whole
fix. **Tier 3.**

This item asked to be tested before it was closed: *"if none of
`format`/`lint`/`types`/`tests` writes either file then this item is right by
accident and should say so for the right reason."* Measured — all five declared
gates run against a clean tree, `git status --porcelain` diffed before and
after: **zero untracked artifacts.** `.mypy_cache` is moot, because the
typechecker is `ty` and it wrote no cache. `.coverage` came from a hand-run
during #33, not from a declared gate. So this repo is right by accident,
confirmed, and it stays right until a gate that writes an artifact is declared.

**The narrower fallback is explicitly not being built**: `committed` ignoring
untracked paths the baseline call also produced *by directory* would be a
second identity rule sitting beside the baseline subtraction's, and `CLAUDE.md`
warns in as many words against making those match. Item 55 (`dist/`) is the
same family and is one line of `.gitignore`.

`dirty_paths` is read after the declared suite on both calls so that an artifact
a gate writes lands on baseline and head alike and `subtract_baseline` cancels it
(§5.4). The cancellation is by identity — `(gate, file, code, message)` — so it
only reaches artifacts whose **paths** match on both sides.

A head-only path has nothing to cancel against. The task adds `src/newmod.py`; the
head `tests` gate compiles it and leaves `src/__pycache__/newmod.cpython-312.pyc`,
which the baseline never had. `committed` fails, the repair turn says *changed but
not committed — fix these and commit*, the agent commits the artifact, and `scope`
then fails it as a path outside `touches`. The attempts burn out and the run ends
`EXHAUSTED` on a diff that was green. `.coverage.<host>.<pid>.<rand>` and
`.mypy_cache/<module>.meta.json` are the same shape.

Saffron's own `.gitignore` covers all three, which is why nothing here caught it;
an onboarded repo whose ignores are looser is not covered.

**That sentence is false, measured 2026-08-25 (#30). It covers one of three.**
`git check-ignore` against the shapes this item names: `__pycache__/*.pyc` is
ignored; `.coverage`, `.coverage.<host>.<pid>.<rand>` and
`.mypy_cache/<module>.meta.json` are **not**. The whole file is nine lines and
has no coverage entry and no mypy entry. Found by accident — a `coverage` run
during #33 left a `.coverage` that `git status` reported as untracked, which is
the opening move of the sequence above.

So the reason this has never fired here is not that the declaration is complete.
It is that no declared gate has yet written one of the two unignored artifacts —
**untested, and worth testing before this item is closed**, since if none of
`format`/`lint`/`types`/`tests` writes either file then this item is right by
accident and should say so for the right reason.

The consequence for the decision: this item argues the repo-declaration route is
free for Saffron and costly only at repo two. It is not free here, and under an
unattended night the failure is silent, arrives at the worst hour, and presents
as a task that could not pass its gates rather than as a misconfigured repo.
`session.py:674` carries a `ponytail:` comment resting on the same assumption.

Adding two lines to `.gitignore` closes this repo's instance and leaves the
question — whose declaration is this? — exactly where it was. Worth doing; not a
resolution.

**Done looks like:** the repo declaring its build output, since which paths are
artifacts is language knowledge §2.1 keeps out of core — `.gitignore` is already
that declaration and `git status --porcelain` already honours it, so onboarding
documentation stating the requirement may be the whole fix. If it is not, the
narrower mechanism is `committed` ignoring untracked paths that the baseline call
also produced *by directory* rather than by path — which is a second identity rule
sitting next to the subtraction's, and CLAUDE.md warns against making those match.

---

## 15. Two more reads of the working copy, one of them the same defect as item 13

**Status:** **done**, in `2d67d0d` (*fix(package): PACKAGE was verified under
the checkout's policy, not the base's*). `package.py:676` reads
`load_policy(gates_dir)`. **Item 16 is what this fix created** and stays open:
nothing records *which* policy PACKAGE verified under.

Found while closing item 13, measured, not reasoned — and left open because
both sit in PACKAGE rather than in the cell.

**`cli.py` loads the policy for PACKAGE from `repo`.** `package()` then hands
it to `reverify`, which resolves `gate_executables` against gates exported from
`fetch_head` — item 13's asymmetry exactly, one phase later and against a
different sha. A working copy declaring a role `fetch_head` does not carry
makes the re-verification gate error, which raises as infrastructure at the
point the task is otherwise `READY_FOR_REVIEW`. It also feeds
`policy.integrity.test_paths` into the pull request body, so the body describes
the checkout's declaration rather than the one the packaged commit was verified
under. **Done looks like:** `package()` loading its policy from the export it
already makes at `fetch_head`, which means dropping the `policy` parameter
rather than threading a second one.

**Done, 2026-08-24.** `package()` exports `.saffron` at `fetch_head` and reads
its policy from it, unconditionally rather than inside the re-verification
branch — the body's `test_paths` is read on every path, so a policy loaded only
when the base moved would have been half a fix. The `policy` parameter is gone
and `cli` no longer reads `.saffron/policy.yaml` at all, which took the refusal
read with it: it existed to keep an invalid checkout policy from costing a run,
and the checkout's policy is now read nowhere on the cell path. One measured
consequence for onboarding: a repo whose default branch carries no
`.saffron/policy.yaml` cannot package, the same way it cannot start a cell.

**The cell image is built from the working copy's `.saffron/Dockerfile`**
(`image.build_cell_image(repo)`) while the gates, the policy and the base tree
all come from `base_sha`. This one may be correct as it stands — the image is
the toolchain, not the judgment, and an operator testing a new Dockerfile wants
the branch's — but it is now the only member of the family that reads the
checkout, and nothing says which way it is meant to go. **Done looks like:**
§5.1 saying so either way.

**Done, 2026-08-24: deliberate, and §5.1 says so.** The image stays the
checkout's. The drift is real and now named rather than implied — this repo's
own Dockerfile `COPY`s `pyproject.toml` and `uv.lock` out of the build context,
so a branch that touches the lock bakes those dependencies into an image
running `base_sha`'s code. It is accepted because the image is the toolchain
and not the judgment. **The scheduler reopens it**: unattended there is no
checkout for the phrase to mean anything, and the answer there is a build
context exported from `base_sha` like every other input. That is v1+ work and
is not filed as an item here, because §4.2 has to exist before it can be
written.

---

## 16. No record says which policy PACKAGE verified under

**Status: done** — `SA-0046`, PR #116, merge `57b676c`. `tasks.policy_sha` is
written at cell start from the export at `base_sha` and rewritten at PACKAGE
only when re-verification ran under a different declaration. The record stands
across a gate that errors out of `reverify`, on purpose: the row says what
re-verification ran *under*, not what it concluded.

One thing the column does not do, worth knowing before a reader trusts it: it
holds the *last* declaration a task ran under, not both. After PACKAGE rewrites
it, the base-time value is gone, so "what did this task's cell gates run under"
is no longer answerable from it. §4.1's invalidation reader compares against
in-flight tasks, before PACKAGE, so that reader is unaffected.

**Decided 2026-09-04: a `policy_sha` column on `tasks`, built with item 58
rather than before it.** Written at cell start and rewritten at PACKAGE when it
differs, which gives the per-task lineage this item says is the part that makes
it an item.

The pairing this item asks for is now answerable: §4.1's invalidation rule has
no reader until batches exist, and a batch is precisely the window in which a
policy moves under an in-flight task. With the column, invalidation is a
comparison rather than a document's claim. **Tier 0**, folded into item 58.

Found reviewing item 15's fix, which created the gap by closing a worse one.
`policy_sha` on the `repos` row is written once, at cell start, from the export
at `base_sha`. When the default branch has moved, PACKAGE re-verifies under
`fetch_head`'s policy instead — a *different* declaration, correctly so — and
nothing records that: not the ledger, not the pull request body, not a watch
line. The body says the gates were re-run on the packaged commit "because the
base moved" without naming what they were re-run under.

This is item 13's own complaint one phase later — *the ledger's record of what
ran is not the record of what was declared* — and the sha is already in hand at
the call site, discarded as `policy, _`.

**Done looks like:** a per-task record, which is the part that makes this an
item rather than a one-line fix. `repos.policy_sha` is per repo and written
before the task exists, so there is nowhere to put a second declaration without
deciding where a task's own policy lineage lives. §4.1's invalidation rule
(*change a repo's gate declarations mid-batch and its in-flight tasks are
invalidated*) is the same question from the other end and should be answered
with it.

---

---

## 17. `size` exists and nothing calls it

**Status:** **done** — `SA-0005` (`2f7c6d9`). `size_gate` is called at
`session.py:1017`, advisory unless the effective risk tier is elevated
(`session.py:950`).

`SA-0002` built the gate (#15) and its spec put the consumer out of scope, on
the correct reasoning that the risk tier has none until v1. So the module is
present, unit-tested, adversarially reviewed — and unreachable: `session.py`'s
`_suite` builds its core-gate list from `scope`, `integrity`, `committed` and
`census`, and `size` is not in it.

**This is a spec-writing lesson before it is a task.** A spec whose output has
no consumer produces a module, not a capability, and the gate loop cannot be
handed one without a change it does not have: every `fail` today means repair,
while §5.6 makes `size` **advisory at `standard` and blocking only at
`elevated`**. There is no advisory result the repair loop honours.

**Corrected 2026-08-25, writing `SA-0005`:** the sentence here said
`policy.elevate_on` "does not exist either", and it does — `Policy.elevate_on`
(`saffron/repos/policy.py:51`), parsed, validated, tested, and already carrying
three patterns in this repo's own `.saffron/policy.yaml`. So does
`GateDeclaration.blocking` (`:29`), which is the advisory switch for *declared*
gates. Both have **no reader anywhere downstream**. That makes this task
smaller than the item claimed and its failure mode worse: a declaration a repo
can set, that validates, and that changes nothing is indistinguishable from one
that works until someone checks.

**Done looks like:** an advisory status the repair loop does not act on,
`policy.elevate_on` matched against the diff, `risk` reaching `run_one_cell`,
and `size` in `_suite`. Two things it must carry, both found reviewing #15:

- **Call it host-side, never declare it.** `size` leaves `tool` unset, which is
  right for a gate that executes nothing — and `runner.run_gate` turns a
  declared gate's `pass`/`fail` with no `tool` into `error`. Declaring it in a
  `policy.yaml` errors every task.
- **Close the binary hole with what this spec has.** A block git renders as
  `Binary files ... differ` has no `@@`, so it counts 0 and a `-diff`
  gitattribute zeroes the gate on a rewrite of any size — at `elevated`, the one
  tier where it blocks. It carries a `ponytail:` comment rather than a fix
  because the honest response is `error` only when the unreadable file is inside
  `touches`, and `size_gate` is handed neither `touches` nor a `--numstat`
  cross-check. This spec is handed both.

The same wiring is what item 6's third lens needs, and the two should be built
together or in that order.

**Done, 2026-08-25**, across three specs rather than one — which is the part
worth carrying forward. `SA-0005` (#21) wired the tier and the advisory set,
`SA-0007` (#23) closed the two call sites `SA-0005`'s `touches` could not reach,
and `SA-0006` (#24) closed the binary hole. All four clauses of *done looks
like* hold: `effective_risk(spec.risk, changed, policy.elevate_on)` matches the
diff per attempt (`session.py:663`), `cli.py:176` passes `risk=spec.risk` into
`CellSpec`, `advisory_gates` plus `_blocking` give the repair loop a status it
does not act on, and `size` is in `_suite` (`session.py:691`).

**The advisory switch is two rules, not one, and they are not the same rule.**
`size` is advisory unless the tier is elevated; a declared gate the repo marked
`blocking: false` is advisory at *every* tier, because that is what the
declaration means rather than a tier-dependent switch. They sit in adjacent
lines and reading them as one is the mistake available here.

**And `size` still needs `blocking` even though it is host-side.** Refusing an
unreadable diff ends the attempt through `aborted_gates`, which no advisory
filter downstream can soften — so a gate that stops nothing at this tier must
not spend that refusal. That is why the fix `SA-0006` shipped is a `blocking`
argument and not an `error` return.

**What this item taught, beyond the gate.** Item 18 files the general pattern —
a declaration that parses, validates, and changes nothing. This is the instance
that produced it, and the sequence is the evidence: `SA-0005` could not close
its own gap because its `touches` did not reach `cli.py` and `package.py`, so a
second spec existed only to finish the first. A spec whose acceptance criteria
reach outside its own `touches` is unsatisfiable by construction.

---

## 18. A spec's ceilings were declarations with no reader, and turn exhaustion is total loss

**Status:** **done**, 2026-08-25 — the item's own closure paragraph is below.

Found by running `SA-0005`, which is the only way it could have been found: it
is invisible to every unit test and to four green live runs.

**Two of three ceilings did nothing.** `cli.py` built `CellSpec` with
`budget_usd=args.budget` and `max_attempts=args.max_attempts`, whose argparse
defaults made *not given* and *given the default* the same value — so a spec's
own `budget_usd` and `max_attempts` were parsed, validated, and discarded.
`max_turns` was not on `Spec` at all: hardcoded 60, unsettable, unprintable.
This is the third declaration-with-no-reader in two days, after
`Policy.elevate_on` and `GateDeclaration.blocking` (item 17). **The pattern is
worth more than any of the three instances**: a field that parses and validates
and changes nothing is indistinguishable from one that works, and the repo has
now produced four of them.

**And the ceiling that fired was the one nobody could see.** `SA-0005` died at
turn 61 with $5.34 of a declared $12 spent — stopped by the bound its author
could not raise, holding more than half the budget it *could* declare.

**Turn exhaustion discards everything.** An idle or wall kill leaves commits
behind (item 4). `error_max_turns` fires with the worktree full, the cell is
torn down, and the run exports nothing: 61 turns of correct work, $7.50, zero
commits. `implement.md` said *"Commit your work"* — singular, at the end.

**Closed, 2026-08-25.** The flags default to `None` and stay overrides, the
spec governs otherwise, `max_turns` joins `Spec`, all three print with their
source on the way in, and a turn ceiling names itself in the failure instead of
reading as `exited 1`. `implement.md` asks for a commit per coherent step and
says why, with the measurement.

**And a fifth, found the same day by `SA-0005` (#21).** `cli.py` never passed
`risk=spec.risk` into `CellSpec`, and `package.py` never passed the effective
tier or the advisory set to the PR body or the queue line — a value computed,
carried out on `CellOutcome`, and read by nobody. `SA-0007` closes it.

**What made it worth more than a sixth instance: the tests.** Every test of the
new behaviour called the renderer directly with hand-supplied values, so the
suite was green about a function that works and silent about whether anything
calls it. That is the shape all five share — the declaration end is tested, the
reading end does not exist, and no test spans the two. **A test that constructs
the argument it then asserts on cannot detect a caller that never passes it.**

**And the spec is what made it unfixable in place.** `SA-0005`'s `touches` did
not include `cli.py` or `package.py`, so the implementer could not have closed
the gap without failing `scope`, and one of the three findings was dropped as
unanchorable for the same reason — it named a file the diff could not contain.
Both lenses confirmed the blocker after the rebuttal, the first recorded
disagreement this pipeline has produced (item 9), and the adjudication is on
#21: **the fault was the spec's, not the implementer's.** A spec whose
acceptance criteria reach outside its own `touches` is unsatisfiable by
construction, and nothing in intake checks for it.

**And `SA-0016`'s criterion-path refusal, built to catch exactly this at
intake, does not fire on `SA-0005` — measured, not reasoned about:**

```
uv run python -c "
from pathlib import Path
from saffron.intake import load_spec
from saffron.scheduler import _unmatched_criterion_path
spec, _ = load_spec(Path('.saffron/specs/SA-0005-size-wiring.md'))
print(_unmatched_criterion_path(spec), len(spec.acceptance_criteria))"
None 7
```

Seven criteria parse in full — `SA-0014` already fixed the truncation that
would explain a `None` here — and still none of them trips the refusal,
because none of the seven names a path at all, backticked or bare. They name
behaviour: "the PR body header and the queue line report" the effective tier,
"`size` runs in `_suite`". The paths that behaviour lives in are `cli.py` and
`package.py`, exactly the ones this item already names as outside `touches`.
A refusal keyed on path tokens cannot see a criterion that reaches outside
`touches` by naming behaviour instead of a file, and no widening of the token
rule changes that: resolving "the queue line" to a file is a symbol index,
which is language-aware, and core knows nothing about languages (§2.1) — the
check cannot live in the scan. `SA-0018` closes the gap from the other side
instead: a door at the plan checkpoint an IMPLEMENT attempt can propose scope
through, reaching `SCOPE_REVIEW` with the paths and the root cause, so a spec
shaped like `SA-0005` stops there instead of at a fourth exhausted attempt.

**Still open, deliberately:** `error_max_turns` is not resumable. A bound that
resumes is not a bound, and committing per step removes most of the loss — if a
run exhausts turns *with* its commits landing, that is the evidence for
reopening this, and the honest shape then is a repair-loop state rather than a
retry.

---

## 19. `GateDeclaration.when` is parsed and read by nothing

**Status:** open. Found while declaring Saffron's own `shacl` gate (PR #46).

`repos/policy.py` accepts `when: "**/*.ttl"` on a gate declaration and stores it;
`run_suite` runs every declared gate in declaration order and consults it nowhere.
The only reader in the tree is an assertion in `tests/test_policy.py` that the
field parses. `DESIGN.md` §5.4 illustrates the contract with a conditional gate
and §10 calls repo-defined gates "conditional on touched paths", so a reader
following the design writes a clause the loader accepts and nothing honours —
backlog item 17's shape (`size` built and nothing calling it), one layer out.

Saffron's own `shacl` gate is declared **without** `when` for exactly this reason:
a control that reads as present and is not is Appendix I's founding defect, and
validation is milliseconds so conditionality buys nothing here. That dodges the
trap and leaves it armed for the second repo, which is why this is written down.

**Done looks like** one of: `run_suite` filters on `when` against the diff's
changed paths and a test proves a non-matching gate does not run; or `load_policy`
rejects `when` outright until something reads it, and §5.4's illustration drops
it. §5.4 now says the field is unread — that note comes out with the fix.

## 20. No cell-marked test exercises the `shacl` gate

**Status:** open. Same PR.

`tests/test_saffron_gates.py` runs the gate through a bare `subprocess.run` that
inherits pytest's environment, so it finds `pyshacl` in Saffron's own venv.
Through the real `LocalExecutor` it reports `error: pyshacl not on PATH`, because
`_gate_env` strips that venv — which is correct and is what `tests` already does,
since gates target the cell. The in-cell evidence is one line in
`.saffron/Dockerfile` asserting `pyshacl --version` at build time.

That is the same class of gap Appendix I is about: every mechanism reported green
and the thing under test was somewhere else. It is thinner here — the build-time
assertion is real, and `python3` and the `pyshacl` console script both resolve to
`/opt/venv` — but nothing proves the gate produces a contract-shaped result from
inside a cell.

**Done looks like** a `@pytest.mark.cell` test that starts a cell the way
production does and runs `shacl` through `CellExecutor`, asserting `pass` and a
`tool` obtained in the cell rather than on the host.

---

## 21. Two `SimpleNamespace` fakes stand in for `Spec` and drift silently

**Status:** **done**, driven from `SA-0012`
(`.saffron/specs/done/SA-0012-spec-doubles.md`) in PR #49 (`f31550c`). Both call sites
now build a real `Spec` through `parse_spec`. Found by `SA-0011`. Review of that
diff found the defect had moved rather than died — value drift where this was
shape drift — which is item 24. Read what follows for why the fakes cost what
they did, not as work outstanding.

`tests/test_package.py:679` and `:783` build a `Spec` out of `SimpleNamespace`,
carrying whatever attributes `package()` happened to read when they were written.
They are not typed, so nothing checks them against the model, and they do not
fail when `Spec` gains a field — they fail later, when some renderer finally
*reads* that field, in tests that are nominally about something else entirely.

That is exactly how it went. `SA-0011` added `Spec.acceptance` and nothing
noticed for three tasks; the moment `pr_body._criteria` read it, fourteen
PACKAGE tests died on `AttributeError: 'types.SimpleNamespace' object has no
attribute 'acceptance'` — none of them about acceptance criteria, all of them
about pushes, conflicts and queue lines.

**The trap is the `touches` interaction, and it is what makes this worth an
item.** A spec's `touches` is written by reasoning about which files the change
*should* need, and nobody knows these fakes exist until the code runs. So the
cell hits a wall with no way over it: editing `tests/test_package.py` fails
`scope`, and leaving it fails `tests`. Both burn the attempt, on every attempt,
until the budget is gone — and the agent cannot widen its own `touches`, which
is the point of `touches`. `SA-0011` only got past it because a human was
watching and amended the spec. An unattended night would have spent the whole
budget on it.

The blast radius is small and was measured, not assumed: these two are the only
structural `Spec` doubles in the repo. `tests/test_session.py:86` builds a real
`CellSpec`, `tests/test_report.py` goes through `parse_spec`, and
`saffron/replay.py:51` uses a real `Spec` from `load_spec`. `CellSpec` is never
`asdict`-ed or serialised, so a pydantic model inside the dataclass costs
nothing.

Tempting and wrong: `getattr(spec, "acceptance", [])` in `pr_body`. It makes a
missing field indistinguishable from an empty one, which is §5.4's `tool` defect
in a third costume — and it puts a default in production code to accommodate a
test fake.

**Done looks like** both call sites building a real `Spec` (via `parse_spec` on
a string literal, as `tests/test_report.py` already does), so the next field
`Spec` gains is a type error at construction rather than an `AttributeError` in
an unrelated suite three tasks later. Roughly twenty lines.

**One thing it left.** `SA-0011`'s `touches` still names `tests/test_package.py`
(`.saffron/specs/done/SA-0011-criteria-have-witnesses.md:24`), declared only because
of these fakes. `SA-0012` and `SA-0013` both put it out of scope, and
`.saffron/**` is `forbidden` in every spec — no cell can do it. It wants a
human edit.

---

## 22. Core gate names are not reserved, and `pr_body` is now a second consumer of that hole

**Status:** open. Found by review of `SA-0011`.

`GateName` at `saffron/repos/policy.py:53` accepts any string matching
`^[A-Za-z0-9_-]+$`, so nothing stops a repo declaring `gates: {criteria: {...}}`.
Three consequences, all verified against the running code:

`saffron/phases/package.py:402`'s `reverify` runs only
`policy.gate_executables(...)` (`:468-469`) — no core gates. On a rebase
(`verified_on = "packaged"` at `:638`) the `gates` handed to `render_pr_body`
(`:673`) therefore contain no core `criteria` result, so a repo-declared gate
named `criteria` reporting `pass` is the one `pr_body._criteria` selects
(`saffron/report/pr_body.py:140`) and it ticks every box it never earned. This
is the defect `2c3b231` ("a repo-declared gate named criteria ticked every
box") fixed on the session path — `_suite` appends the host-constructed result
last, so it cannot be shadowed there — and it is still open on the reverify
path, which never runs `_suite` at all.

`_suite` also builds `advisory_gates` straight from `policy.gates`
(`saffron/cell/session.py:672-674`), so `gates: {criteria: {blocking: false}}`
makes the *core* `criteria` gate advisory — same hole for `census`. And
`suite_drift` keys both suites by bare gate name (`saffron/gates/baseline.py:84`),
so the same collision family reaches `scope`, `census` and `committed` there
too.

**Done looks like** a `frozenset` of core gate names and one `field_validator`
on `Policy.gates` in `saffron/repos/policy.py` rejecting them, which closes all
three call sites at once and gives the ontology's `CoreGateShape` an enforced
counterpart in code.

---

## 23. A witness already green at `base_sha` makes a spec unsatisfiable, and nothing says so

**Status:** open. Found by review of `SA-0011`.

`saffron/gates/core/criteria.py` reports `witness-green-at-base` (`:100`) for a
non-`preserves` witness that already passed at base. It is blocking, and no
repair turn can fix it: the agent's only routes are renaming or deleting the
pre-existing test, and `census` and `integrity` both block those. So an
operator authoring error — naming a witness that already passes — burns
`max_attempts × budget_usd` with nothing to show, the same corpse `DESIGN.md:379`
records for item 18 (`SA-0005`, $5.34, dead at turn 61).

It cannot be caught at intake, because it needs the suite. But the baseline
suite already holds the answer: after `baseline = _suite([])`
(`saffron/cell/session.py:724`), any non-`preserves` witness appearing in the
baseline's `collected` union is a spec that cannot pass, before a single repair
attempt is spent finding that out the expensive way.

**Done looks like** one `watch()` line there naming those witnesses, turning
four dead attempts into a legible operator message on the first unattended
night.

---

## 24. The fixture item 21 built drifts in value, not shape

**Status:** **done** — `SA-0013` (PR #51), 2026-08-28. Found by review of
`SA-0012` (PR #49); the spec it was written into is
`.saffron/specs/done/SA-0013-fixture-values-are-witnessed.md`.

Item 21's fix replaced the two `SimpleNamespace` fakes with `_spec()`, which
builds a real `Spec` by putting a string literal through `parse_spec`. Nothing
asserts that the values handed to `_spec()` survive the trip. Measured, not
reasoned: break the `## Acceptance criteria` header so `_CRITERIA_SECTION`
misses, or corrupt the `touches` line to yield `["ZZZf.txt"]`, and the whole
module still reports **97 passed**. `["f.txt"]` and `["it works"]` appear in
`tests/test_package.py` only as arguments to the helper, and no assertion
mentions either.

So the `packageable` fixture that feeds most of PACKAGE's tests can start
handing `package()` a spec with no criteria and a scope matching nothing, and
every test stays green while exercising less than its name claims. `parse_spec`
changing its criteria regex is enough to trigger it, and that regex has no test
tying it to this fixture. It is item 21's own thesis — a fixture whose contents
nothing checks — one level down.

**Done looks like** one new test beside the existing one, asserting
`spec.touches` and `spec.acceptance_criteria` against what `_spec()` was called
with: two assertions, red under either mutation above. New rather than an
extension of `test_the_package_fixtures_build_a_real_spec`, which is green at
base and would fail `criteria`'s `witness-green-at-base` — item 23, met in the
wild while authoring the spec.

---

## 25. A spec's own diff can be too large for its own repair loop

**Status:** **done** — the resplit landed. `SA-0014` (PR #56), `SA-0015`
(#59), `SA-0016` (#60) and `SA-0017` (#64) are all `MERGED`, so the too-wide
`SA-0009` was recut into four pieces that each fit inside one repair loop.
The "still open" paragraph at the end of the body is now **item 56**: nothing
weighs a spec's own shape against its `type`'s size ceiling before a cell
starts. That is a separate control from the recut, and the recut did not build
it.

Resplit as `SA-0014`–`SA-0017`. Found by running `SA-0009` (task 11).

`SA-0009` was §4.2.1's read-only half — discovery, the re-queue filter, the
six refusals, `saffron queue` — as one spec. It never converged: two `IMPLEMENTING`
attempts landed 990 changed lines across seven files, `size` reported `fail` in
every gate result after, at the 600-line `feature` ceiling
(`gate_result_id` 113/124/135), and
two `REPAIRING` attempts each burned a full `max_turns=100` trying to cut the
diff down without ever getting `committed` clean again — $31.60 against an $18
budget, terminal state `EXHAUSTED`, zero lines merged.

**The size was foreseeable before a single turn ran.** The diffstat splits
cleanly along the spec's own acceptance criteria: `tests/test_scheduler.py`
alone was 433 of the 990 lines, because it was carrying tests for two
unrelated mechanisms — the `spec_sha` re-queue filter and the five refusals —
each demanding its own fixture per the spec text. A spec whose acceptance
criteria describe more than one mechanism is a spec whose diff is the sum of
both, and nothing checked the sum against the ceiling before the cell started.

**Done looks like** the same work recut so each piece fits inside one repair
loop: `SA-0014` (intake's parser fix and directory discovery), `SA-0015`
(the ledger reads and the re-queue filter), `SA-0016` (the four refusals that
need `touches`, criteria, or GitHub state), `SA-0017` (`saffron queue`'s CLI
wiring) — chained by `depends_on`, ~150–420 lines apiece by the same diffstat.
`SA-0009` itself is left as written: its `spec_sha` is pinned to the
`EXHAUSTED` task above, and editing it would only mint a fresh `spec_sha` for
a monolith nothing intends to run again.

**Split out as item 56:** nothing yet checks a spec's own shape — how many
acceptance criteria, how many files in `touches` — against its `type`'s size
ceiling before a cell starts. That would have caught this one for the price of
a `gh`-free scan, the same argument item 18 made for turn ceilings.

---

## 26. Discovery cannot tell an empty night from a missing directory

`discover_specs` (`saffron/intake.py`, landing with `SA-0014` in PR #56) returns
`(specs, failures)` and reaches the filesystem through `directory.glob("*.md")`.
`Path.glob` yields nothing for a directory that does not exist and nothing for a
path that is a file, so all three of these are the same value:

```
discover_specs(Path("/nope/nothing"))   -> ([], [])
discover_specs(Path("saffron/intake.py")) -> ([], [])
discover_specs(<an empty directory>)    -> ([], [])
```

Measured at `30bd85c`. The spec's second acceptance criterion asks only that a
*malformed spec* not raise past discovery, so this is not a violation of it —
the scan does what it was asked. It is the distinction this repo enforces
everywhere else that is missing: `error` ≠ `fail`, and a gate that never ran
must not read like one that ran and passed. A scan that never saw a directory
must not read like a night with no work in it.

It matters at the seam, not here. `SA-0017` resolves `base_sha` and exports
`.saffron/specs/` from a repo; `SA-0015` builds the queue from what discovery
returns. An export that silently produced nothing — wrong `base_sha`, a repo
that never had `.saffron/`, a path assembled with the wrong join — reaches the
scheduler as a quiet empty queue, and the first unattended night ends having
done nothing with no record saying why. That is the failure mode this backlog
is ordered by.

**Done looks like** `discover_specs` raising `SpecError` when `directory` is not
an existing directory, with a test for the missing path and the not-a-directory
path. The caller owns the export, so a directory that is not there is an
infrastructure fault (exit `2`), not an empty scan — the same call
`PREFLIGHT_FAILED` makes. An existing but empty directory stays `([], [])`,
which is a true statement about a repo with no specs.

---

## 27. `SA-0018` built a door it could not document, and the prompt then contradicted it

**Status:** **done** — `SA-0021`, by hand on the host, 2026-08-30.

`SA-0018` added a second producer of `SCOPE_REVIEW`: an IMPLEMENT attempt whose
declared `touches` cannot satisfy its criteria proposes a set instead of grinding
to a ceiling. The code shipped and works. The documents that define what the words
mean did not move, because **`DESIGN.md` and `CONTEXT.md` were both in `SA-0018`'s
own `forbidden` list** — so the spec that created the affordance was structurally
unable to describe it.

The result was a prompt that contradicted itself. `CONTEXT.md` §3 is injected into
the IMPLEMENT system prompt (`SECTIONS_BY_PHASE['IMPLEMENT']` is `(1, 2, 3, 4, 10)`),
and its **Touches** entry read "proposed by DIAGNOSE and ratified by the operator on
bug specs". So the same assembled prompt offered the implementer the door and told
it, more specifically, that the door was DIAGNOSE's on bug specs. The specific
sentence wins that argument.

**This is the situation `SA-0018` exists to give an exit from, one spec later and
one level up.** Its `touches` could not reach the files its own feature made wrong;
by the feature's own logic the correct move was a scope proposal naming `DESIGN.md`
and `CONTEXT.md`. It was found by review instead. Note that a *proposal* naming
those paths would have been recorded — `validate_scope_proposal` checks only that a
path escapes `touches`, not that it escapes the deny lists — so the door was open;
nothing pointed the implementer at it.

Closed by `SA-0021`, by hand on the host (see item 28), 2026-08-30: §3.3 draws
`SCOPE_REVIEW` from IMPLEMENTING, §5.3.1 states the door's three rules, §5.2 no
longer claims the contract as DIAGNOSE's alone, and `CONTEXT.md`'s **Touches**
entry names both proposers. The witness reads the *assembled* prompt rather than
`CONTEXT.md`'s text, because reasoning about which sentences reach the model is
what failed here.

---

## 28. A spec whose `touches` are protected paths dies at the plan checkpoint with no exit

**Status:** **done** — `SA-0023`, 2026-08-31.

`SA-0021` — the spec that closes item 27 — declared `DESIGN.md` and `CONTEXT.md`
in `touches`, which is the only honest declaration it could make. Run as a cell on
2026-08-30 (ledger task 18) it ended `PLAN_REJECTED` in 2m44s having spent $0.82:

```
PLAN: rejected, $0.82 spent — DESIGN.md is a protected path
```

`.saffron/policy.yaml` lists `DESIGN.md`, `CONTEXT.md`, `.saffron/**` and `uv.lock`
under `protected:`, and `validate_plan` (`saffron/agents/artifacts.py`) rejects any
plan naming a protected path — checked after `touches` and `forbidden`, with no
exemption for a path the spec itself declares. The protection is right: those two
documents are authoritative, and a cell rewriting the definition of its own
constraints is exactly what a global deny list is for. What is missing is an exit.

The scope-proposal door does not cover this. That door is for "the declared
`touches` cannot satisfy the criteria"; here they can — it is policy, not scope,
that bars them. So the implementer correctly wrote a plan, and the plan was
correctly rejected, and the task is terminal at a state that means "your spec needs
work" when the spec is as good as it can be. Every future attempt spends the same
$0.82 to reach the same wall. This is item 18's shape — a declaration with no
reader — inverted: a rejection with no route.

**Done looks like** a plan naming a protected path inside the spec's own declared
`touches` ending at `SCOPE_REVIEW` rather than `PLAN_REJECTED`, carrying the
protected paths as the proposal and the rejection reason as the root cause, so the
work reaches the operator as a one-click "do this by hand" rather than as a dead
task. A plan naming a protected path *outside* `touches` stays a rejection: that is
an agent reaching for something it was never given, which is the case the check was
written for. Until then, a docs spec over protected paths must be run by hand and
say so in its own notes.

**One tension to meet deliberately rather than at implementation time.** Such a
proposal names only paths *inside* the declared `touches`, which is precisely what
`validate_scope_proposal` refuses — "every proposed path is already inside touches".
Generated host-side it would bypass that validator, and `SCOPE_REVIEW` would then
carry two meanings: a scope to ratify, and "this one is yours to do by hand".
`CONTEXT.md` defines **Ratify** as what the operator does to a *proposed `touches`
set*, so the second meaning needs either a different state or a deliberate widening
of that definition — not a quiet reuse.

**Closed differently from this item's own "Done looks like."** Not a second
`SCOPE_REVIEW` producer — the tension two paragraphs up is why: that state already
means "ratify a proposed `touches` set", and this collision is not one. Instead,
`SA-0023` added a refusal beside `SA-0016`'s: `scheduler.protected_touch_refusal`
compares a spec's declared `touches` against `policy.yaml`'s `protected` list with
the same glob matcher every other `touches` comparison uses, deciding only literal
`protected` entries — an entry that is itself a glob (`.saffron/**`) is left to
`validate_plan`'s own rejection, unmoved, still the backstop. Read at both places
this repo's specs actually run: the scan (`build_queue`'s new `protected`
parameter) and the attended single-spec run (`cli._run_cell`, before a cell
exists), both from the same `base_sha` export `build_queue`'s specs already come
from — never the working copy (items 13 and 15). What it cost to learn: one task,
$0.82, and a spec that had to be run by hand with nothing on the way in saying so.

---

## 29. Nothing recorded that a task merged, measured against this repo's own ledger

**Status:** **done**, 2026-08-30, driven from `SA-0019` (PR #70) — the
item's own closure paragraph is below.

`SA-0019`. `set_task_state` is the only writer of `tasks.state`, and PACKAGE's
last word is always `READY_FOR_REVIEW` — nothing asked GitHub what happened
after, though §3.3 draws arrows onward to `MERGED`/`REJECTED`/
`CHANGES_REQUESTED`/`APPROVED`, and a dead batch scan leaves `ORPHANED`.

**Measured, 2026-08-30:** `select task_id,spec_id,state,pr_url from tasks
where pr_url is not null` against this machine's ledger returned six rows,
every one `READY_FOR_REVIEW`. Cross-referenced against this repo's own
`git log --all --oneline --merges`:

| spec | pull request | ledger said | `gh` says |
|---|---|---|---|
| `SA-0013`..`SA-0017` | #51, #56, #59, #60, #64 | `READY_FOR_REVIEW` | `MERGED` |
| `SA-0018` | #65 | `READY_FOR_REVIEW` | still open |

Five of six were wrong, with no mechanism that could make them right.

**A corpse was never stamped either**, per §4.2.1's own premise: "in flight"
and "dead" are synonyms only inside a batch scan, which v0.5 has none of —
the only candidate caller is `saffron queue`, run at will, mid-phase
included. A first attempt (`EXHAUSTED` at $12.12) stamped every in-flight
row unconditionally and was correctly blocked: `ORPHANED` is in
`scheduler.REQUEUE_STATES`, so a live row stamped that way is handed back
out as resumable — a second cell on the same branch.

**Done, 2026-08-30.** `saffron/reconcile.py`'s `reconcile()` — a writer
inverting `scheduler._open_prs`'s best-effort shape (an untrustworthy `gh`
answer counts as "could not be asked", never "not merged"; `MERGED` is never
asked again) — wired into a new `saffron reconcile --repo .` and into
`saffron queue` before it scans. Neither asserts §4.2.1's batch-scan premise,
so neither stamps `ORPHANED`; the supervisor still does, on the path it
already owned (`cell/session.py`, §4.5). **What has no writer is the scan's
half** — the corpse a hard kill or a power cut leaves behind, which is the
case §4.2.1 is actually about, and it waits for a caller that can assert the
premise. Tested against this repo's own six rows above, plus the CLI witness
that `IMPLEMENTING` survives `queue`/`reconcile`.

**One live-task path is left open deliberately, and `SA-0020` must close it
before a scan gets teeth.** The in-flight guard protects a first run for a
structural reason — `pr_url` is NULL until PACKAGE's last write, so there is
nothing to ask about. A *resumed* task escapes it. `_drive_cell` writes
`READY_FOR_REVIEW` and calls `finish_run` before `cli._run_cell` invokes
PACKAGE, so while PACKAGE runs the row reads `READY_FOR_REVIEW` and still
carries the **previous** attempt's `pr_url`, whose `reviewDecision` is the
`CHANGES_REQUESTED` that requeued it. Reconciling inside that window writes a
`REQUEUE_STATES` value onto a task whose cell is alive — the same double
-execution shape the first attempt was blocked for, arriving by the other
column. Harmless in v0.5: no scan starts a cell, and PACKAGE's
`set_task_package` overwrites the row moments later. **Done looks like** the
state being stamped out of `PR_PENDING_STATES` before PACKAGE is called
(`cli.py` owns that ordering), not a wider guard inside `reconcile` — the row
is genuinely `READY_FOR_REVIEW` in that window, so no state test can tell it
from a finished one. Note `runs.status = 'RUNNING'` is a liveness signal the
ledger already carries and no forbidden file owns; it does not close *this*
window, because `finish_run` precedes PACKAGE.

---

## 30. A protected document's one-line definition of a gate drifts the moment the gate changes, and the fix is always by hand

`SA-0024` widened `scope_gate` (`saffron/gates/core/scope.py`) to also fail a
changed file matching a spec's `forbidden` list or the repo's `protected` list,
not only a file outside `touches`. `CONTEXT.md` §3 still defines the gate in
one line: *"The check that changed files are a subset of `touches`."* That
sentence is now false — it describes half the gate — and nothing in this
spec's `touches` can fix it: `CONTEXT.md` is `protected`, so no plan naming it
can be validated (item 28's `SA-0023` refusal), and it is in this spec's own
`forbidden` list besides. The correction is a by-hand follow-up, the same
shape item 27 (`SA-0018`/`SA-0021`) and item 28 (`SA-0023`) already
established for a protected document a spec cannot reach.

**This is the second instance of that drift, not the first.** Item 27 is the
first: `SA-0018` added a second producer of `SCOPE_REVIEW` and could not update
`CONTEXT.md`'s **Touches** entry to say so, because `DESIGN.md` and
`CONTEXT.md` were both in `SA-0018`'s own `forbidden` list — the same
structural reason this item exists. `SA-0021` closed that one, by hand, one
spec later. The pattern both instances share: a spec that changes what a core
mechanism does can never be the spec that updates the one document defining it
in prose, because that document is `protected` by the same policy the spec's
own change makes more precise. A third instance should not need a third
backlog item before it is treated as a rule of the process rather than a
one-off gap: **any spec that changes core gate or phase behaviour should name,
in its own notes, the `CONTEXT.md`/`DESIGN.md` sentence its change makes
stale**, so the by-hand follow-up has a known list rather than a fresh reading
of both documents each time.

**Status:** **done** — by hand on the host, 2026-08-31, in `SA-0024`'s own
pull request.

**And the enumeration is what the item was actually for.** `CONTEXT.md` §3 was
the sentence this item named, and it was the *least* load-bearing of the six.
`DESIGN.md` — authoritative for what the system does, and cited by section
number from specs — carried four more, one of which stated the shipped
behaviour's exact opposite:

- §3.1's frontmatter example: `forbidden: # denied at the plan checkpoint, not
  against the diff`
- §3.1's paragraph *"**`forbidden` and `protected` bind the plan, not the
  diff** … No gate reads either against a diff."*
- §3.1's next paragraph, describing the gap as *"Stated rather than fixed"*
  after `SA-0024` fixed it
- §5.4's gate table row: `| scope | core | yes | changed files ⊆ touches |`
- §5.2's writeback rule, which item 31 covers separately

The second of those already carried a scar — *"the wording here said otherwise
until `SA-0011` leaned on it"* — so a spec that read it would have leaned on
wording false in the opposite direction. The by-hand list this item asks specs
to carry was written into `SA-0024` and still named only one of six documents,
which is the argument for making it a check rather than a request: **the spec
that proposed the rule did not follow it.** A plan-checkpoint or gate-0 check
that a spec changing a core gate names the `DESIGN.md`/`CONTEXT.md` sentences
its change makes stale is the shape; it is not written.

## 31. `SA-0024` made `touches` unable to rescue the ratification writeback, in a repo whose spec directory is `protected`

§5.2 requires the task's own spec path to be added to the ratified `touches`
when a scope proposal is recorded, *"or that first commit fails the `scope`
gate on every ratified task"* — the writeback commits to `.saffron/specs/…`,
which DIAGNOSE would never propose. `saffron/cell/session.py` implements it,
and its comment names the measurement.

`SA-0024` made the deny lists independent of `touches`, which is the whole
point of the change: widening `touches` must not clear a denied path. But
this repo's `.saffron/policy.yaml` lists `.saffron/**` under `protected`, so
the host-authored writeback commit is now exactly such a path. A ratified task
would report `[scope] .saffron/specs/SA-XXXX-….md protected` — a blocking
failure the agent cannot repair, because reverting it destroys the
ratification the operator just granted.

**Latent, not live.** Nothing in `saffron/` performs the writeback yet:
`SCOPE_REVIEW` writes `scope_proposal.json` and stops for a human, and
`base_sha` is the remote default-branch head, so a writeback merged by hand is
already behind the base a cell diffs against. The mechanism is designed,
documented and half-built, which is why this is an item rather than a note.

**Done looks like** the recorded spec path exempted from the deny lists in the
same place it joins `touches` — one exemption, host-added, never the model's —
with a test that a ratified task's first commit passes `scope` in a repo whose
spec directory is `protected`. Found by the review of `SA-0024`, not by a run.

## 32. The dependency gate asked whether a parent shipped and answered from a record of cell runs

**Status:** **done**, 2026-08-31, by hand on the host — `_retired_ids` at
`saffron/scheduler.py:464`, read at `:757`. The account is in this item's own
body below; this line exists so a scan of the file's status markers sees it.

**Done, 2026-08-31**, by hand on the host — `_retired_ids` in
`saffron/scheduler.py`, admitting a `depends_on` whose parent sits in
`.saffron/specs/done/`.

`SA-0020` narrowed the dependency refusal to admit a parent recorded `MERGED`,
which is right for a parent a cell ran. **Only a cell writes a task.** So a
spec a human implemented looks exactly like a spec nobody has run, and its
dependents stayed refused however plainly the parent's code sat in `main`. The
gate asked "is the parent's work in the default branch" and answered from a
record of cell runs; in a repo where humans and cells both commit, those are
two questions.

Measured the same day it shipped: `SA-0020` was implemented by hand, so
`SA-0022` was refused with *"no task in the ledger says it merged"* — true,
and not what the operator needed to know. The queue was empty and its one
refusal was wrong about the only work left.

Retirement to `specs/done/` already meant exactly the missing fact — that
directory's README opens *"Specs whose work is in `main`"* — and stating it
there costs nothing and writes no false row into the audit trail, which is the
one thing the ledger may not contain. Ids are read from frontmatter rather
than filenames, and a retired spec that no longer parses is not credited: the
refusal stands, the only direction that cannot admit a child whose parent is
absent.

**What this does not do:** stacking (§4.2, `SA-0022`). A retired parent is
admitted for the same reason a merged one is — the child is cut from the
default branch and the parent's commits are already in it. A parent that is
merely `READY_FOR_REVIEW` is still refused, which is §4.2's own rule minus the
half v0.5 cannot honour.

## 33. Stacking's other half needs two bases, and the two now disagree on purpose

**Status:** **done** — all three specs merged: `SA-0022` (PR #81),
`SA-0025` (#82) and `SA-0026` (#84). `CellSpec.stacked_on` is distinct from
`base_sha`, PACKAGE resolves a real parent, and `CONTEXT.md` carries the **Tree
base** entry the split needed.

`SA-0020`'s first attempt (ledger task 20, `EXHAUSTED` at $14.43 against a $16
budget, 2026-08-30) found that a stacked task — one whose parent is still only
`READY_FOR_REVIEW`, item 32's remaining half — needs `worktree.prepare_worktree`
to check out the parent's own unmerged branch head, ahead of `base_sha`, while
the exported patch was still computed as `export_patch(container, base_sha)`
and so captured the parent's entire diff plus the child's own. It could not fix
that: `saffron/phases/**` was forbidden to it, and the `touches` insufficiency
only surfaced after the plan checkpoint, past §5.3.1's one door out.

This split the remaining work in two. This item is the half with no production
trigger: `CellSpec.stacked_on`, distinct from `base_sha`, and
`worktree.prepare_worktree`'s matching parameter, so a worktree can be built on
a base other than the run's pin and a patch can be exported against that same
base rather than against `base_sha` — proven with a real two-commit parent
branch and a real child commit on top, not a value a test constructs and then
reads back. `cli.py` sets `stacked_on=None` explicitly at the one place a
`CellSpec` is built, so `depends_on` is not consulted on that path at all and
no real task stacks yet. `SA-0025` resolves a real parent onto the field, wires
it into `_drive_cell`, teaches PACKAGE to target the parent's branch, and
widens the dependency gate to admit a `READY_FOR_REVIEW` parent.

**The disagreement this creates is real the moment `SA-0025` wires it up, and
it is worth deciding now rather than at the hour nobody is watching.** A
stacked worktree's tree is the parent's unmerged commits plus the child's own —
code the gate executables and the policy declaring them, both exported from
`base_sha` (item 13), have never seen. Two ways that can go wrong: a gate role
the parent's own commits added exists in the tree but not in the exported
`.saffron/gates/`, so `run_suite` never invokes it — a silent gap, not a
`skip` that names itself; and a gate that would judge the parent's own change
differently under the parent's own policy update instead judges it under the
policy that predates that update.

**Decision: `base_sha` wins — the gates and the policy declaring them stay
resolved from it, stacked task or not.** Two reasons, not one. First, this
spec's own out-of-scope line is explicit that it does not redefine what
`base_sha` means; moving the gate source to `stacked_on` for some tasks and not
others *is* that redefinition, one call site at a time, and item 13 already
spent a whole item settling gates-from-`base_sha` as the run's pin — a second,
task-local exception to it is a third thing to keep in step with the first two
rather than one settled fact. Second, `base_sha` is the one value every task in
a run shares; a gate source that moved with `stacked_on` would mean two
sibling tasks stacked on two different parents run under two different gate
suites inside the same run — a suite-drift vector already named once, for
`reverify`'s missing `thread_env` (item 11), and the common case here rather
than the exception.

**What this defers, by name, for `SA-0025` to inherit rather than rediscover.**
A parent that adds or changes a gate role stays invisible to a child stacked on
it until the parent lands on the default branch and `base_sha` itself moves
past it — the same shape item 13 already accepted for an operator's own
branch, now also true of a dependent task's parent. Closing that without
moving what `base_sha` pins means exporting a second, `stacked_on`-sourced gate
set for a stacked task alone and running both suites, which is unbuilt and is
not this item's to build: the requirement here was that the disagreement be
recorded, not resolved.

**`package.py`'s own read of the base, which looks correct and is not.**
`saffron/phases/package.py:526` is `json.loads(patch.json)["base_sha"]`, and it
feeds `assert_base_objects`, the `git apply --3way`, `needs_reverification`
and the pull request body's provenance. `SA-0022` records `tree_base` beside
`base_sha` precisely so that read *can* be made correct — for a stacked child
the patch is relative to `tree_base`, and applying it to `base_sha` puts
parent-relative hunks on a tree without the parent's commits: `MERGE_FAILED`
at best, an apply that looks right at worst. It is the likeliest place
`SA-0025` gets this wrong, because a one-word read that is correct today
raises no question. `SA-0025` also owes `CONTEXT.md` an entry for the second
base: `tree_base` is a new noun and it is already in a durable artifact.

**Re-verification is the second caller, and it is not covered above.**
`saffron/phases/package.py` calls `prepare_worktree` a second time, building
its baseline and head worktrees from the current default-branch head. For a
stacked child that is the wrong baseline outright — the parent's commits are
not in it — which is a different failure from the gate-source disagreement
this item decides. `saffron/phases/**` is forbidden to `SA-0022`, so recording
it here is the only action available; `SA-0025` owns the file and the fix.

**Decided and implemented, 2026-08-31 (`SA-0025`).** `package()` now takes an
optional `parent_branch`. Unset — every caller today — nothing above changes:
`target_branch`/`target_head` resolve to `default`/`fetch_head` exactly as
before, and reading `tree_base` instead of `base_sha` for the patch's preimage
check is a no-op, because `SA-0022` already writes the two equal for an
unstacked task. Set, and the parent's own commits are not yet an ancestor of
`fetch_head`, PACKAGE opens against the parent's current head instead —
fetched fresh, so a parent that merged, force-updated or was deleted between
the child's start and its push is caught (named as `ParentGone`, one message
for "gone", a different one for "moved to a commit the mirror cannot reach")
before a pull request opens against a branch that is not there. A parent
already merged into `fetch_head` falls back to the ordinary target rather than
re-fetching a branch that is routinely deleted the moment its own PR lands.

This also answers the re-verification baseline question left open above:
**the fresh baseline is whichever tree the child is ultimately packaged
against** — the parent's current head when stacked and the merged-fallback
has not fired, `fetch_head` otherwise — never `fetch_head` unconditionally.
`needs_reverification` and `reverify`'s `new_base_sha` both read that one
value (`target_head`) now, closing the gap the paragraph above named: a
stacked child's baseline used to omit the parent's own commits entirely. The
disagreement decided above — the gates and the policy declaring them staying
pinned to `fetch_head`'s export regardless of stacking — is unchanged; only
the baseline commit `reverify` diffs against moved.

**Left unrecognised, by design: a squash-merged parent.** The ancestor check
above is `git merge-base --is-ancestor tree_base fetch_head`, mirror-local.
GitHub's squash-merge writes a new commit object onto the default branch that
shares no history with the parent branch's own commits, so a squash-merged
parent whose branch was then deleted — the ordinary shape once a PR lands —
reads as "gone without merging" rather than "merged": `ParentGone` fires and
the task ends `MERGE_FAILED` for a change that, in fact, already shipped.
Recognising a squash merge needs GitHub's own merge record (the PR's `merged`
flag and `merge_commit_sha`), not anything the mirror holds, and building that
is not this item's to do. The failure mode this leaves is a false negative
that costs a task, never a pull request opened against a branch that is not
there and never a silent double-apply of the parent's hunks — the two shapes
this item exists to rule out.

**Two more shapes accepted rather than solved, and one debt reassigned.**

- *A parent force-pushed to a history that no longer contains `tree_base`.*
  Distinct from the two `ParentGone` names: the fetch succeeds and the head is
  reachable, so nothing above fires, and the child's patch three-way-rebases
  onto a divergent parent. In the bad cases that conflicts and ends
  `MERGE_FAILED`; in the benign-looking ones it can resurrect content the
  force-push removed. A `merge-base --is-ancestor tree_base parent_head` check
  would name it, and `SA-0026` — which is what first produces a real parent to
  force-push — cannot make it: `saffron/phases/**` is forbidden there. It needs
  a spec of its own, after stacking is live and the shape can be measured.
- *A pruned mirror inverts a gone parent's classification.*
  `assert_base_objects(mirror, tree_base)` has to precede the fetch — it is
  checking for objects the fetch would otherwise supply — so a parent deleted
  without merging, in a mirror since gc'd, raises `PackageError` and exits 2
  before the `ParentGone` path can make it this task's own `MERGE_FAILED`.
  Latent and gc-dependent; the ordering is right and the classification is not.
- *`CONTEXT.md` still owes `tree_base` an entry.* This item asked `SA-0025` for
  it, and `SA-0025` forbids itself `CONTEXT.md` — correctly, since its
  documentation half is by hand. `SA-0026` carries the sentences, and carries
  this one with them: `tree_base` is a noun in a durable artifact and the
  glossary does not have it.

**Decided and implemented, 2026-08-31 (`SA-0026`).** The producer is real now.
`cli._resolve_stacked_on` reads `Ledger.tasks_by_spec_id(repo_id,
depends_on[0])` — every task row this repo has ever run for that one parent
spec id, across every `spec_sha` it has carried, the same "merging is
permanent" reach `merged_anywhere` already takes, because this attended path
never reads the parent's spec file and so has no current sha to filter rows
to. Among those rows, the newest one still in `scheduler.
DEPENDENCY_WAITING_STATES` (`READY_FOR_REVIEW`, `APPROVED`, `MERGE_TRAIN`) is
"the parent's task" — the same waiting-outranks-dead precedence
`_dependency_refusal` already gave the gate's own refusal text. Not the same
row, though: the gate reads only the parent's current `spec_sha`, so a parent
whose spec text moved after its pull request opened has a waiting row here and
none there. The branch is real either way; the gate decides whether the
dependent runs, and the resolver only decides what it is cut from. Its `pushed_sha` becomes `CellSpec.stacked_on`, its `branch`
becomes `package()`'s `parent_branch`, and both are `None` together —
never one without the other — the moment either is missing, empty, or not a
resolved sha: a merged or retired parent (no waiting row at all) yields an
ordinary unstacked cell rather than a `CellSpec.__post_init__` `ValueError`.
K=1: only `depends_on[0]` is ever a stacking candidate. The dependency gate
(`scheduler._dependency_refusal`) now returns `None` — admits — for the three
waiting states instead of refusing them with the sentence this item's own
neighbours quoted; that sentence is gone, not left beside a gate that no
longer says it.

The two shapes named above are exactly as open as they were; shipping the
producer did not close either. Force-push detection is still unbuilt —
`saffron/phases/**` stays forbidden here, so the `merge-base --is-ancestor
tree_base parent_head` check the first bullet names is recorded again, not
added, now that a real stacked parent exists for one to force-push onto.
`CONTEXT.md`'s `tree_base` entry is still owed by hand — this spec forbids
itself that file too, for the same reason `SA-0025` did.

**A canary fired that this spec had no file to retire, and the deny list is
what made that a defect.** `SA-0025` planted `tests/test_package.py::
test_the_operators_reachable_packaging_path_is_unstacked`, asserting the
literal string `parent_branch` does not appear anywhere in `saffron/cli.py`
— true the day it was written, and false the moment a producer exists, by
the test's own docstring ("the one caller reaching `package()` in production
must not pass a parent"). `SA-0026` is that producer, and `tests/test_package.py`
is not among its `touches`, so the cell could satisfy the guard's letter or
fail the `scope` gate and nothing else. It spelled the keyword by
concatenation (`{"parent" + "_branch": ...}`), said so in a comment, and
recorded it here — the right handling of a box a spec put it in, and both
review lenses still flagged the result, correctly: a green guard that proves
only the absence of one spelling misleads whoever next reads it.

Retired by hand at review, 2026-08-31. The text search is deleted rather than
rewritten — it asserted a property of `cli.py` from `tests/test_package.py`,
and a source grep is satisfiable by any caller willing to spell the keyword
differently. Both halves are asserted on the call now, in `tests/test_cli.py`:
`test_a_stacked_worktree_passes_its_parents_branch_to_package` for a stacked
run, and `test_an_unstacked_worktree_passes_no_parent_branch_to_package` for
the converse. `cli.py` spells the keyword.

**The rule this is the second instance of.** A spec that turns on a
capability must own the tests that assert the capability is off, or its
`touches` hands the agent a choice between a false green and a `scope`
refusal. `SA-0022` missed `saffron/cli.py`; this one missed
`tests/test_package.py`. Both were caught in review rather than by the gate
that could have caught them — an inertness guard names the spec that will
retire it, and nothing checks that the named spec can reach the file. At
three instances the rule is wider than tests: `SA-0026` could reach neither
`saffron/cell/session.py`'s nor `saffron/phases/package.py`'s comments saying
stacking was off, both corrected by hand at review. **A spec that turns on a
capability must be able to reach every artifact that says the capability is
off** — the guard, the comment, and the design sentence alike.

**The ledger's recorded sha is not the branch, and nothing put the branch in
the mirror.** Found in review, not by a gate, and it would have killed the
first real stacked run. `_resolve_stacked_on` originally returned the parent
task's `pushed_sha`; two separate problems with that:

- *Nothing fetches it.* `ensure_mirror` fetches `+refs/*:refs/*` from the
  operator's **local checkout** with `--prune`, so a parent branch they do not
  happen to have checked out is deleted from the mirror; `fetch_default_branch`
  fetches only the default branch; and the cell's own seed (`worktree.py`)
  fetches the mirror's default refspec. Measured: this repository's mirror had
  already pruned `refs/heads/saffron/SA-0025` while that pull request was open,
  and its `refs/heads/saffron/*` set is exactly the operator's local branches.
  `git checkout -b <branch> <parent_sha>` in the seed is then
  `fatal: unable to read tree`, exit 2, naming neither the parent nor why.
  `fetch_default_branch`'s own comment made this argument one branch over.
- *It is a commit behind.* `pushed_sha` is written once, by PACKAGE. Every
  review fix an operator commits by hand moves the branch past it. Measured on
  this pull request: task 26's `pushed_sha` was `ab23523` while
  `saffron/SA-0026`'s head was `5ab674e` — a child would have been cut from a
  tree containing the concatenation dodge the review had already removed.

Both are one fix: the ledger says **which branch**, `fetch_parent_branch`
(`SA-0025`, one branch over from where it was already used) says **which
commit**. `ParentGone` there is an unstacked cell and a printed line, not a
failure — a deleted parent branch has either merged or been abandoned, and
neither is worth killing an attended run over.

**The overlap refusal shadowed the widened gate completely.** `_refuse` checks
a candidate's `touches` against every open pull request's changed files
*before* it reaches the dependency check. A parent at `READY_FOR_REVIEW` has an
open pull request by definition, and almost every spec here touches
`docs/BACKLOG.md` — so nearly every stacked child was refused on its own
parent's pull request and never reached the admission this item exists to
build. `SA-0025`'s pull request changed `docs/BACKLOG.md`, which is in
`SA-0026`'s `touches`: this very pair would have been refused. Fixed at review
by exempting `depends_on[0]`'s branch, and only that one — a child cut from
its parent's tree already contains the parent's changes, which is what
stacking is; any other task's pull request over the same file is still the
collision the check exists for.

**The by-hand half, done at review rather than owed.** `DESIGN.md` and
`CONTEXT.md` are `forbidden` to every spec in this sequence, deliberately, so
an operator corrects them: §4.2's dependency-gate rule and §4.2.1's `depends_on`
paragraph (which said every other parent state is still refused), §5.7 (which
described one base, and now carries the two-bases paragraph and the
fetch-never-remember rule), §9's v2 list (which still deferred stacking), and
`CONTEXT.md`'s new **Tree base** entry. §3.1's frontmatter example needed no
edit: `depends_on: [TE-0139] # satisfied at READY_FOR_REVIEW` was the design's
stated intent all along, and is true for the first time.

---

## 34. A turn ceiling that fires with zero commits was total loss, and item 18's prompt was not enough

**Status:** **done** — `SA-0028` (PR #87), 2026-09-01. The item's own
closure paragraph is below.

**Closed by `SA-0028`, 2026-09-01.** Item 18 closed `SA-0005`'s turn-ceiling gap
by making `max_turns` a real, per-spec, printed ceiling and asking
`implement.md` for a commit per coherent step, "with the measurement." That was
necessary and it was not sufficient: `SA-0025`, ledger task 24, hit the same
shape it was written about and died the same way.

**Measured, once, and it cost a whole task.** `SA-0025` ran `NOT_IMPLEMENTED`
at $14.61 — the first zero-commit run of the eight logged at the time. Its two
attempt rows:

| n | turns | cost | subtype | terminal_reason |
|---|---|---|---|---|
| 1 | 36 | $2.93 | `success` | `completed` |
| 2 | 141 | $11.68 | `error_max_turns` | `max_turns` |

The plan was accepted and was good. The implement turn ran to its ceiling
trimming the diff to fit `size`, committed nothing, and `teardown: no commits,
nothing to export` threw all of it away — with $5.39 of the budget still
unspent. **The turn ceiling bound, not the dollars**, which is the fact a
prompt cannot answer: `implement.md` already said "commit your work," and the
agent still ran to 141 turns without doing it. Telling an agent to behave
differently is not a control; it did not become one the second time either.

**The control is structural, at the one boundary the host already owns.**
`session.py` already reads `terminal_reason` off the closed turn and
`commits_ahead` off the worktree — the two facts together are unambiguous: a
turn that ended with `terminal_reason == "max_turns"` and zero commits was cut
off, not finished. When both hold, and only then, the host now spends one more
turn — resumed on the same `session_id`, so the agent keeps the context it
already paid for — whose only instruction is to commit what already exists.
Bounded at `SALVAGE_MAX_TURNS` (five, against `intake`'s default ceiling of
sixty — the spec that measured this set its own to 120), and clamped to the
spec's own `max_turns` so it can never exceed the turn it salvages: a salvage
that could itself run to 140 turns is the defect
this item closes, one level down. The budget ceiling is checked before the
salvage turn is spent, never after — a task with no room left ends exactly as
it did before this existed, and the watch line says the budget stopped it
rather than silently skipping the turn. A turn that finished on its own with
nothing gets no salvage: the agent decided it was done, and §4.3's "doneness is
measured, never reported" does not become "measured, then argued with."

**What this does not cover, on purpose.** It is one turn at one boundary
(IMPLEMENT only — not the REPAIR loop's own turns, which already checkpoint
dirty work on a bound firing, item 4). Two neighbouring branches lose an
uncommitted tree exactly as before, and both are decisions rather than
oversights. A run *over budget* when the ceiling fires takes no host checkpoint:
committing there would push a task with no money left into GATE and spend the
suite it cannot pay for, and `EXHAUSTED` is the outcome it earned. A run ended
by some *other* bound — idle, wall-clock, a crash — takes none either: the
salvage turn is spent on one measured pair of facts, and widening the free
checkpoint to every abnormal ending is a separate argument from the one this
item makes, on a path whose retry is already warranted. Neither is free of
cost, and both are worth revisiting with a measurement rather than a guess. It
also does not raise `max_turns` or spend
the leftover budget on more implementation (the failed run did not need more
turns; it needed to have committed at turn 20), and it does not steer a turn
while it is running — the host cannot inject an instruction mid-turn, only
resume at the boundary it already owns.

**The decision this item also records: a dirty, uncommitted `/work` at
teardown is still never packaged, even after this exists.** The tempting
second half — when the salvage turn also produces nothing, export the working
tree's diff anyway, on the theory that *some* record beats none — was
considered and rejected. Control artifacts are extracted and hashed the moment
they are produced and never re-read from `/work`; a file left in the workspace
is a claim, not a record. A working-tree diff that reached `patch.diff` would
be packaged as though it had passed gates it never faced, and `committed`
exists precisely to refuse that at GATE. If a diagnostic dump of the dirty tree
turns out to be worth having for triage, it needs its own name, its own place
PACKAGE never reads, and its own spec — not a quiet exception carved into the
one artifact the operator trusts.

**What review added after the cell, and what it left open.** Three holes the
gates could not see: the host checkpoint fired only when the salvage turn was
*cut off*, so a salvage that returned cleanly having committed nothing — a
commit hook rejecting it is the likely shape — lost the work it was spent to
save; the crashed-turn watch line keyed on `is_error`, one of the four things
`run_agent`'s own failure predicate ORs, so a turn that crashed after emitting
a clean result still read as "finished and produced nothing"; and the salvage
turn inherited the implement turn's cost as `_reconcile_cost`'s fallback,
which bills a five-turn `git commit` at a 120-turn turn's price and can book
`EXHAUSTED` on a task the salvage just rescued.

**What the second review round found, all four in the same shape.** The cost
scaling was applied in one direction only: the salvage turn was correctly given
a scaled-down fallback, and then its own small figure was carried forward as
`last_cost`, becoming the crash fallback for the *next* turn — which runs on the
full ceiling. That reopens §4.1's budget-that-stops-counting one hop downstream
of where the scaling closed it, so `last_cost` now keeps the implement turn's
figure across the salvage. `commit_dirty` raises rather than returns when a hook
rejects the commit, so a host checkpoint on a tree the repo's own `prek` hooks
refuse converted an earned `NOT_IMPLEMENTED` into an infrastructure abort,
charged to nobody: the salvage path now catches `CellRuntimeError`, says so on
the watch line, and lets the `commits_ahead` re-measure decide. The same shape
is still live in the repair loop's own checkpoint, where the tree is not known
dirty and so is less likely to fire — it needs its own spec. And
`cut_off_at_turn_ceiling` read `terminal_reason` alone where `run_agent` keys on
`subtype`; the ledger row carried both, and a result event arriving without the
one field would have skipped the salvage in silence, which is indistinguishable
from a control that ran and found nothing.

**Owed to an operator, by design.** `DESIGN.md` and `CONTEXT.md` are `forbidden`
to `SA-0028`, and three edits are outstanding: §5.3's account of IMPLEMENT
describes one checkpoint and there are now two; §4.3's "doneness is measured,
never reported" gains the qualification this item argues for (a turn cut off is
not a turn that reported doneness), and its own table still says IMPLEMENT is
measured `base..HEAD` when the code has measured from the plan turn's head since
item 18; and `CONTEXT.md` grants bare-caps status to phases plus the plan
checkpoint by name, which `SALVAGE:` now needs too — it is a turn at a boundary,
deliberately not a phase, the same entry the plan checkpoint carries.

---

## 35. An inertness guard names its own successor, and nothing checked the successor could reach it

**Status:** **done** — `SA-0027`, 2026-09-01.

`SA-0022`, `SA-0025` and `SA-0026` each shipped a capability inert on purpose,
asserting it with a test that the capability is off and a comment naming which
spec will flip it. Nothing checked the named spec's `touches` could reach the
file carrying that comment, and `SA-0026`'s own review is the corpse, twice:
`tests/test_package.py`'s guard (planted by `SA-0025`) asserted the literal
string `parent_branch` never appears in `saffron/cli.py`, but that file was
not in `SA-0026`'s `touches`, so its agent could neither edit the guard nor
run the gates against it — it spelled the keyword
`{"parent" + "_branch": ...}` to dodge the match instead, said so in a
comment, and logged the box it was in as this file's item 33; and
`saffron/cell/session.py` and `saffron/phases/package.py` each carried a
comment saying stacking was off, both `forbidden` to `SA-0026`. Both review
lenses flagged the first, both files were corrected by hand for the same
reason: the file was never one the spec retiring it could reach. A `git grep`
against the mirror at `base_sha` costs no export, no working tree and no
network; what it prevents is a full cell paying for a choice between a false
green and a `scope` refusal on work the spec was right to do.

**Done looks like, and is:** the convention, stated in code
(`mirror.py`'s `retirement_markers` docstring, not only here) — a comment or
docstring carrying `saffron:retired-by <SPEC-ID>` declares that its file
asserts something that spec is expected to falsify.
`mirror.retirement_markers(mirror, sha)` reads every marker out of a bare
mirror with `git grep -n -z`, no export or checkout, answering `[]` rather
than raising on a repository with none (`git grep` exits 1 on no match —
`error` ≠ `fail`). `scheduler.retirement_refusal(spec, markers)` is a pure
refusal in `protected_touch_refusal`'s own shape (item 28), read with
`scope.matches` — the same function `scope`, `integrity`, `size` and item
16's criterion-path refusal already share: a marker this spec's `touches`
cannot reach refuses, naming the file and the declared `touches`; one inside
the spec's own `forbidden` refuses too, worded differently, since "may not
touch it at all" and "touches doesn't reach it" are different operator
fixes. Empty `touches` skips the second check outright — item 16's own bug
guard, since an empty list is a bug awaiting DIAGNOSE, not a spec that failed
to declare — but not `forbidden`, which a bug spec can carry regardless.
Wired into both pre-cell paths item 28's refusal reaches: `build_queue`
(gate 0) and `cli._run_cell`, best-effort against the mirror the way
`_protected_paths_at` already is. A marker naming a spec id nothing in the
directory (or `specs/done/`) declares gets its own line in `build_queue`'s
refusals — item 24's `done/` rule, applied to this class of dangling
reference.

**What this still cannot see.** Reachability, not intent: a marker naming an
id that exists is not flagged even if that spec is long `MERGED` or
`REJECTED`. It garbage-collects nothing — a guard's own removal deletes its
marker by construction, but one left behind some other way still reads as
live. And it is opt-in: a heuristic over every `SA-NNNN` mention would refuse
most of this repository, which cites spec ids as attribution far more than as
a claim about the future — a capability shipped inert *without* a marker is
as invisible to this refusal as it was before.

**What review added after the cell.** Two holes the gates could not see, both
the same shape: `git grep` cannot tell a line that *writes* a marker from a
line that *is* one. A spec must quote the marker it arms in its own
acceptance criteria, so every such spec read back as carrying a marker at its
own path and refused itself — naming its `forbidden` list, which was not the
cause. `.saffron/specs` is now excluded from the grep: a spec is where a
marker is discussed, never where one lives. `tests/**` deliberately is *not*
excluded, because `SA-0025`'s own inertness guard lived in a test file — so
`tests/test_mirror.py` spells the string by concatenation instead, having
otherwise shipped four dangling markers into this repository and four
permanent refusals into every `saffron queue`. And a third limitation for the
list above: the empty-`touches` guard means a bug spec is checked against
markers only *before* DIAGNOSE populates its `touches`, never after — the
same pre-cell-only hole item 28's sibling refusal has.

**What the second review round found, and three more blind spots it named.**
The item shipped carrying a stray diff3 conflict marker — one line, naming an
in-cell commit that exists in no history here — through two review commits. In
a file the project treats as a primary record, that is the workspace-claim
failure in documentation form. And a dangling-marker line asserted more than
the scan had read: `known_ids` is built from the spec files that *parsed*, so a
marker naming an id declared only by an unparseable file was called a dangling
reference. It now says how many files did not parse, the way
`_dependency_refusal` already qualifies the identical case.

Three things this refusal still cannot see, all named rather than fixed:

- **A marker whose id the regex cannot parse is dropped in silence.**
  `saffron:retired-by SA_0027`, a stray colon after the keyword, or a marker
  inside a binary file all *match the grep* and then vanish — the false green
  this item exists to end, one layer down. Fixing it is a decision and not a
  one-liner: this repository writes the literal keyword in a regex, in three
  scheduler f-strings, in two test writers and in this paragraph, and every one
  of those would become a "malformed marker" line on every `saffron queue`. The
  permissive id parse is kept deliberately for the same reason — trailing
  garbage (`SA-0031-extra`) resolves to its prefix and so reaches an operator
  as either a named refusal or a dangling line, where a stricter pattern would
  return it to silence. Visible-and-possibly-misattributed beats invisible.
- **Only `.saffron/specs` is excluded, so a document that writes a real id
  arms a real marker.** This file, `CLAUDE.md` and `DESIGN.md` escape today
  only by writing a placeholder rather than a concrete id. Excluding `docs/**`
  was considered and rejected: `docs/` is a target repo's convention, not
  Saffron's, and core knows nothing about a repo's layout (§2.1). `.saffron/`
  is excluded precisely because it *is* Saffron's own path.
- **The repo-wide `protected` list is not consulted.** `retirement_refusal`
  reads `spec.forbidden` but not `policy.yaml`'s `protected`, which `_refuse`
  already holds. A marker in a protected path, named by a spec whose `touches`
  glob covers it, is admitted here and dies at the plan checkpoint instead —
  the same corpse this refusal exists to prevent, one list over.

---

## 36. The event schema wants its own `DESIGN.md` §4 subsection, and nothing can write one

`saffron/events.py` fixes the kinds, the `kind` discriminator and the
timestamp representation, and `DESIGN.md` carries no event schema at all.
`DESIGN.md` is `protected`, so no cell can add one.

The count is now **ten**: `Ceilings` was added by hand with `saffron/task.py`,
so a §4.x written against "nine" would be stale before it landed. Stated as a
count that moves, rather than a number to correct again.

Done looks like: a new §4.x naming the kinds, the wire discriminator and
`events.jsonl`'s one-file-per-task, no-rotation ceiling — by hand, after
`SA-0040`, when the shape has stopped moving.

## 37. `events.Terminal` and `CONTEXT.md`'s "terminal state" are two different things

`CONTEXT.md` reserves **terminal state** for the states that reach the operator.
`events.Terminal` means the five ways an IMPLEMENT turn ends having committed
nothing. Two of the five map onto a terminal state, which makes the collision
easy to miss rather than hard.

Renaming was deferred because `SA-0029`'s criteria and `SA-0030`/`SA-0040` all
cite `Terminal`. An earlier draft of this item said the name was `DESIGN.md`
§4.1's; it is not — see item 36. Found reviewing PR #91.

Done looks like: `TurnEnded` across the three specs, or a `CONTEXT.md` entry
saying the two terms are deliberately distinct. Protected either way, so by
hand, and worth settling before `SA-0040` and `SA-0038` render the word.

## 38. `events.Phase` splits `GATE ⇄ REPAIR`, and `CONTEXT.md` does not

`CONTEXT.md` names six phases, counting `GATE ⇄ REPAIR` as one; `events.Phase`
lists seven, because a gate attempt and a repair turn print different lines.
The split is probably right and is currently held by a comment and a test.

Done looks like: `CONTEXT.md` saying whether it is sanctioned, and the `Literal`
following. Protected, so by hand. Second divergence — see item 37.

## 39. `types` is a blocking gate that can never fail

**Status:** **done**, by hand, on `joel/ty-typechecking`. The gate executes
`ty` (pinned exactly in `pyproject.toml`), `[tool.pyright]` is gone, a prek hook
carries it into `make check` and CI, and `.saffron/Dockerfile` asserts
`ty --version`. `policy.yaml` is unchanged, as this item predicted. Two things
it did **not** predict, both measured:

**ty, not pyright, and the reason is the cell.** The `pyright` PyPI package is a
Node wrapper that downloads a runtime on first use. `cell-base.python` has no
node, and the proxy allows one host — so the download takes a 403, the same
failure the Dockerfile's `UV_NO_SYNC` note already records for `uv run`. ty is a
single binary from ruff's vendor. It is also the better surface for the agent in
the loop: 0.09s against 1.97s on this tree, 23 KB of `concise` output against
pyright's 127 KB of JSON, and no duplicates (13% of pyright's 206 diagnostics
were exact repeats). Deduped, the two agree on the same production defects.

**"neither touches `saffron/`" was wrong**, and usefully so — turning the gate on
found 11 real defects in it: five `int(cursor.lastrowid)` where sqlite types the
value `int | None`, a `list[str] | None` iterated in `criteria`, two
`list[X] = ()` defaults in `pr_body`, and `fields()` on an untyped `_KINDS`.

**The mutation this item was written about is caught by nothing, and that is not
a ty limitation.** Measured against the shipped gate:

| mutation | `types` | `test_the_enumerations_are_pinned` |
|---|---|---|
| `ceiling: Ceiling` widened to `ceiling: str` | pass | pass |
| `Terminal` dropped from the `Event` union | **fail** | pass |
| a member removed from `Ceiling` | **fail** | **fail** |
| a member added to `Ceiling` | pass | **fail** |

Widening a type cannot error in any checker unless some code exercises the wider
value, and none does; pyright behaves identically. So this item's reading of
`test_the_enumerations_are_pinned` as a "substitute" is backwards — it is the
only control over a member quietly *added* or renamed, and it stays. The row the
gate uniquely covers is the dropped union member.

Caught in review, and the sharpest finding of the branch: the first version set
`[tool.ty.environment] python = ".venv"`. A cell worktree is a fresh
`git init`/fetch/checkout and `.venv` is gitignored, so it is never present —
and a configured environment ty cannot resolve is a hard failure, exit 2 with
nothing on stdout, which this gate correctly calls `error`. `error` aborts the
attempt and is charged to nobody (§5.4), so a blocking `types` gate would have
aborted every attempt against this repo. Item 39 would have been closed by
replacing a gate that could never fail with one that could never run. Reproduced
against a clean clone before fixing; the fix is that ty resolves the environment
from its own executable, so `/opt/venv/bin/ty` finds `/opt/venv`. The test that
should have caught it now exists — none of the others paired the repo's own
config with a tree shaped like a cell's.

The parser is `concise` and reconciles against ty's own `Found N diagnostics`
trailer, so a diagnostic it cannot key (one carrying no line, a message shape
that moved) is `error` rather than a smaller repair target than the real one.
Exit codes beyond 0 and 1 are `error` for the same reason. ty's only JSON output
is its `gitlab` format, which is a schema name and not a destination; a flag
naming a forge this repo does not use would read as an integration it is not.

`# ty: ignore` joins `integrity.suppressions`. ty honours it, and before this
branch that did not matter because nothing enforced types; a blocking gate with
a suppression syntax the anti-gaming gate cannot see is the hole that gate
exists to close.

One standing cost, recorded rather than fixed: `docs/evidence/scripts/` is in
scope, so every future evidence script — a verbatim record of something already
executed — must type-check or a blocking gate goes red. Three existing ones
needed an `assert spec and spec.loader`.

Also fixed in passing: the gate's implementation was first written as
`.saffron/gates/types.py`, which sits on `sys.path[0]` and shadows the stdlib
`types` every `import json` reaches through. It crashed under one interpreter
and survived under another, writing nothing to stdout — a gate that did not run,
reported as nothing at all. Renamed `typecheck.py`, with a test asserting no
gate script shadows a stdlib module name.

`.saffron/gates/types` emits `skip` unconditionally, `policy.yaml` declares it
`blocking: true`, and `pyproject.toml` carries a configured `[tool.pyright]`
block that nothing runs — pyright is not a dependency, a hook, or installed.
`policy.yaml`'s own note on `shacl`, five lines below, states the principle this
breaks: *a control that reads as present and is not is the founding defect of
Appendix I.*

Measured while reviewing PR #91: mutations replacing `Ceiling` and
`TerminalReason` with bare `str`, and removing `Terminal` from the `Event`
union, all left the suite green. `saffron/events.py` is a module whose whole
value is type safety, and `tests/test_events.py` now hand-rolls
`test_the_enumerations_are_pinned` as a substitute.

Done looks like: pyright as a dev dependency and `.saffron/gates/types`
executing it — the gate is already declared and already blocking, so nothing in
`policy.yaml` changes. Or, if that is not wanted, the gate stops claiming to
block. Either is a repo-side change and neither touches `saffron/`.


## 40. A host-side fix round can undo a gate the cell passed

`SA-0029` (PR #91) left its cell at 548 changed lines, inside the 600 a
`feature` gets. Two host-side review rounds took it to **863**. The `size` gate
runs inside the cell, against the cell's own diff; nothing re-runs it after the
operator commits review fixes to the branch, so the branch merges failing a
blocking gate it passed on the way out.

Most of the growth is tests, and that is the second half of the finding:
`_changed_lines` counts the whole diff, so a spec whose acceptance criteria
demand thorough tests is charged for satisfying them. `SA-0029` has fourteen
criteria, and both reviews of it added tests precisely because criteria were
being held up by comments. Cutting those to reach 600 would trade a real
control for a number.

Done looks like: the loop running `size` (at minimum) against the branch before
it is marked ready, and a decision on whether the ceiling should count test
lines at all — §5.4 sets one number for a diff whose test half is mandated
elsewhere. Recorded rather than fixed here: PR #91 is over the ceiling and is
being merged over it deliberately, with this item as the record.


## 41. `NO_PROXY=""` denies a cell its own loopback, so a test that stands up a local server fails at baseline forever

**Status:** **done**, by hand, on `joel/cell-loopback-not-proxied`. `proxy_env`
returns `NO_PROXY: "127.0.0.1,localhost"`, and a driven test asserts the probe
reaches a server started beside it while the upstream stays proxied. The
alternative this item offered — marking the failing test `cell` — was **not**
taken: it passes on the host, and excluding it would have hidden the defect
rather than fixed it. One correction to the reasoning below, from review: the
open question is not whether `--internal` makes these variables inert.
`DESIGN.md` §5.1 records that an `--internal` network still routes to the host
gateway, which is why `assert_host_is_unreachable` exists. What makes the
change safe is narrower and measured — `10.88.0.1` matches neither `NO_PROXY`
entry, so nothing the gateway exposes becomes reachable.

`saffron/cell/proxy.py:proxy_env` returned `{"HTTPS_PROXY": url, "HTTP_PROXY":
url, "NO_PROXY": ""}`. Empty means *nothing* bypasses squid — `127.0.0.1`
included. `test_the_probe_script_itself_answers_a_401` binds an `HTTPServer` on
loopback and probes it
with `preflight._UPSTREAM_PROBE`, which uses `urllib` and so honours the proxy
variables. The container's request to itself is routed out to squid, which
allowlists only the upstream, and is denied.

Measured on `SA-0040`, 2026-09-01. In-cell baseline: `1 failed, 1094 passed`.
Same commit on the host: `1 passed`. That run's teardown printed ten of these,
one per suite execution across baseline, two gate attempts and the
post-rebuttal run:

```
teardown: proxy DENIED … TCP_DENIED/403 3367 GET http://127.0.0.1:37283/v1/models
```

Three costs, in increasing order of seriousness:

- **Every cell run starts with a red `tests` gate.** Baseline subtraction
  absorbs it correctly, which is exactly why it has gone unnoticed since the
  proxy was wired.
- **It misleads the critic.** `SA-0040`'s correctness lens opened its blocker
  with "the `tests` gate reports 1 failure in this run", reasoned to the
  nearest new test, and raised a blocker against the golden fixture's digest.
  The digest was fine — mutating it fails the assertion — but the rebuttal
  turn's artifact was itself lost to a JSON parse error, so the pull request
  shipped a `confirmed` disagreement founded on this line. One environment
  papercut cost a lens finding, a rebuttal, and an operator adjudication.
- **It trains the operator to skim the denials.** `teardown: proxy DENIED` is
  the channel that would show a cell trying to reach something it should not.
  Ten lines per run that are one repo test talking to itself is noise in the
  one place noise is most expensive.

Done looks like a decision, not a patch. `NO_PROXY=""` is the correct isolation
posture for anything off-box and must not be widened to hosts. The open
question is whether loopback *inside the container* — which is the cell
itself, and reaches nothing the cell does not already have — belongs behind
the boundary at all. If it does, the alternative is that `saffron`'s own suite
cannot contain a test that binds a socket, and `test_the_probe_script_itself
_answers_a_401` should carry the `cell` marker and say so.


## 42. A rebuttal lost to a trailing comma is recorded as a confirmed disagreement

`phases/rebut.py:207` discards a rebuttal artifact that is not the schema and
returns `RebuttalTurn(error=...)`. That is deliberate, and the comment says
why: the plan checkpoint re-prompts once (`cell/session.py:404`) because a
rejected plan costs an attempt that has not happened yet, whereas *"this
attempt is already made, and HEAD already says what it did."*

`SA-0040` (PR #93) is the case where the second half of that sentence does not
hold. Measured 2026-09-01:

```
REBUT: 0 rebuttal(s), HEAD moved, not the schema: Illegal trailing comma
       before end of object: line 6 column 1116 (char 1186)
```

The turn cost $2.59, edited the branch, and conceded one of the two blockers —
`describe`'s `Baseline` branch was rewritten and a test added, and the critic's
re-read correctly marked that one `withdrawn`. Its *arguments* were what the
trailing comma destroyed. On the other blocker the critic then wrote
`confirmed: The implementer offered no argument and made no visible change`,
and that finding was false: the fixture digest it doubted is captured, not
typed, and mutating it fails the assertion at `tests/test_events.py:798`.
Nothing needed to change, and there was no surviving argument to say so.

So the operator inherits a pull request body asserting a confirmed
disagreement, founded on a lens finding that was itself founded on the
unrelated red baseline in item 41. "HEAD already says what it did" is true only
for a reader who re-reads the diff against every finding; the generated body
says the opposite, and the body is what gets read.

`SA-0034` (plan Task 6) is the natural home for the *recording* half — it is
already a bug spec about a rebuttal outcome that is not written down — but its
`forbidden` list excludes `saffron/report/**`, and no spec in part 3 touches
`pr_body.py` either. The visible half has no home in that plan yet.

Done looks like the artifact's *shape* failure not being silently equivalent to
the agent having no answer. Cheapest honest fix is not a re-prompt: it is that a
`RebuttalTurn` carrying `error` renders in the pull request body as
**"the rebuttal was unreadable"** rather than as an implementer who declined to
argue, and that `HEAD moved` — already recorded in `rebuttal.json` — is shown
next to it. Whether a malformed rebuttal is also worth one re-prompt is a
separate question from whether the record should imply an answer that was never
read.

## 43. Two of `cell/session.py`'s events never fit a kind, and `emit` is not the whole output seam

`SA-0030` migrated all 47 `watch(...)` call sites in `cell/session.py` to
`emit(<Event>)`, against `events.FAMILIES`. Two did not, by design —
`events.FINDINGS[0]` names them: the task's own terminal announcement
(`f"{outcome}: ${spent:.2f} spent, session {session_id}"`) and the rate-limit
rejection line. Neither `Terminal` (scoped to the five zero-commit IMPLEMENT
endings) nor `Budget` (a ceiling/value/limit triple) fits an arbitrary outcome
word and a session id without a tenth kind, which this spec's own out-of-scope
section forbids. Both stay direct `print()` calls in `_drive_cell`, which means
`events.jsonl` never carries them — `read_log` plus `describe` reproduces every
other printed line in order, but not these two. A future report reading
"what did this task's own log say happened" has to fall back to the ledger's
`tasks.state` for the outcome word, which is already there and already typed;
the gap is real but has a working substitute, which is presumably why `SA-0029`
scoped a tenth kind out from the start.

**The second half of that gap has no substitute and was not disclosed until
review found it: `emit` is no longer the supervisor's total output seam.**
Those two `print()` calls go to process stdout whatever the caller passed.
A caller supplying its own `emit` — which is exactly what `SA-0042` is
specified to do from `cli.py`, and what any batch or headless consumer would
do — still gets two lines it cannot redirect, and the one it most wants is the
task's own terminal announcement. Measured on `saffron/SA-0030`: driving
`run_one_cell(..., emit=seen.append)` without the test harness's
`session.print` double leaks `READY_FOR_REVIEW: $0.40 spent, session sess-1`
to stdout; at base, `watch=` captured 100% of output. Note the harness hides
this — `tests/test_session.py` patches `session.print` with `raising=False`,
so the double silently no-ops if those calls ever move. Done looks like the
tenth kind `SA-0029` scoped out, or an `emit`-shaped sink for lines no kind
carries; not a third `print`.

**Closed by `SA-0041`, 2026-09-02.** `phases/implement.py`, `phases/review.py`
and `phases/rebut.py` were `forbidden` to `SA-0030` and called a plain
`watch(str)` with a line they had already fully formatted — `agent: `,
`agent: (raw) `, `REVIEW: ` or `REBUT: ` were the only four prefixes those
three files ever handed it. `session._phase_watch` recovered the event those
strings were always going to be by matching on that prefix and slicing it
off, which was correct only because no other prefix reached it. `SA-0041`
migrated those three files to construct `Agent`/`PhaseStart` events directly
and call `describe()` themselves — `implement.run_agent` gained a required
`spec_id` and now emits `Agent(event=<dict>)` at the point the cell's own
dict is still available, instead of flattening it to prose first — which is
what let `_phase_watch` itself, both constructions, be deleted outright.
`SA-0031`'s plan to migrate `cli.py`/`phases/package.py` in the same spec is
what died at 141 turns; `SA-0042` carries that half forward on its own, since
`package()` runs outside `run_one_cell` and never received the supervisor's
`emit` in the first place.

**The first half closed by `SA-0042`, 2026-09-02; the second half is still
open and this spec moved against it.** `cli.py` now builds one `emit` fan-out
— print plus a task-scoped `EventLog`, the same shape `session._default_emit`
already used — and hands the identical object to both `run_one_cell` and
`package()`, so PACKAGE's events finally reach `events.jsonl` too. **Seven** of
`package.py`'s eight `watch(str)` call sites and `cli._resolve_stacked_on`'s
two are now `emit(<Event>)`, against existing kinds and with no message change.

The eighth did not migrate, and it is the mirror image of
`events.FINDINGS[0]` above: `reverify`'s `"re-verify: {label} suite at {sha}"`
is `events.FINDINGS[1]`'s own named exception — no `PhaseStart` label fits a
lower-case, hyphenated step without widening `LineLabel`, which needs the
forbidden `events.py` — so it stays a direct, unconditional `print()`.

That leaves the second half of this item worse, not better, and review is what
said so. `session.py`'s two `print`s are untouched (forbidden here), and
`package.py` now adds a **third** — precisely the shape the done condition
above rules out. It is also a small regression in kind: before, a caller could
pass `package(watch=…)` and capture or silence the `re-verify:` line, and no
caller can redirect it now. Done is unchanged: the tenth kind, or an
`emit`-shaped sink for lines no kind carries. Three prints, not two.

**A tenth kind now exists, and it is not this one.** `saffron/task.py` added
`events.Ceilings` for the per-task ceilings line, so "the tenth kind
`SA-0029` scoped out" is no longer an unbuilt thing and this item's done
condition must not be read as met. The three prints above are a *terminal
announcement*, a *rate-limit rejection* and `reverify`'s `re-verify:` step;
`Ceilings` carries none of them, and none of the ten kinds does. Done is
unchanged: an eleventh kind for the two `session.py` lines and a `LineLabel`
that fits a lower-case step, or an `emit`-shaped sink for lines no kind
carries. What did change is the precedent — `events.py` is no longer a file
nothing may add to, and the cost of adding a kind is now measured: the
dataclass, the union, `_KINDS`, one `describe` branch, one `FAMILIES` row,
two counts in `tests/test_events.py` and one render case.

Two stale docstrings for whoever takes that on, both in `session.py` and so
both unrepairable here. `_default_emit`'s says `cli.py` "never passes `emit`",
and `run_one_cell`'s says the default "lives here, not in `cli.py` (forbidden
to this spec)". `cli.py` is no longer forbidden, is the only production caller
of `run_one_cell`, and now builds exactly that fan-out — so the `emit is None`
branch is reached from tests alone.

## 44. A single turn can overshoot the budget ceiling, because the check runs before it

**Status: done** — `SA-0050`, PR #121, merge `57b676c`. `run_batch` computes
`budget_usd - ledger.batch_spend(batch_id)` before each candidate, reading
spend back out of the ledger rather than trusting a tally kept in the loop —
which is what survives a caller cut mid-night.

The wording this item settled needed one correction after review, and
`DESIGN.md` §3 and `CONTEXT.md` now carry it: the batch bound is *also*
best-effort, because it admits a task on that task's **declared** ceiling. A
night can end at most one task's overshoot above budget. Bounded by one
overshoot rather than unbounded is the real distinction, and it is the whole
value of checking between tasks.

**Decided 2026-09-04: option two, plus the ceiling that is actually
enforceable.** `budget_usd` is a best-effort bound and says so where it is
declared. The enforceable ceiling is **per batch, checked between tasks** —
folded into item 58.

Option one is rejected for the reason this item states about itself: a turn's
cost is not knowable until it ends, so charging a worst-case estimate means
*guessing* the bound. That is the defect item 56 argues against for size
predicates, and here it is worse — a guess that refuses a legitimate turn costs
more than a 6.5% overshoot.

The reframe is what §9's v1 target buys. Unattended, one task running $1.17
over is not the exposure; a night spending unboundedly is. Between tasks
nothing is mid-flight, which is exactly why a bound is enforceable there and
cannot be inside a turn. **Tier 0**, with item 58.

`_over_budget` gates a turn on what has been spent *so far*. It cannot bound
what the turn about to run will cost, and a turn's cost is not knowable until
it ends.

Measured on `SA-0031`, 2026-09-01. Admitted under an $18.00 budget with roughly
$6 spent, its IMPLEMENT turn ran to the 140-turn ceiling and cost **$13.18 on
its own**, ending the run at **$19.17 — 6.5% over a ceiling it never checked
against.** The ledger row records `budget_usd 18.0, spent_usd_est 19.165`.

The overshoot is bounded only by the turn ceiling and the wall clock, which are
the same two bounds that let the turn get long in the first place. A task with
`max_turns` raised — the obvious response to a turn that ran out of turns — has
a proportionally larger overshoot available to it.

Done looks like a decision about which of two honest options to take, not a
patch: charge the ceiling *before* a turn against a worst-case estimate and
refuse a turn that could exceed it, or accept that `budget_usd` is a
best-effort bound and say so where it is declared. What it should not stay is a
number the system reports as a ceiling and enforces as a suggestion.

## 45. An `EXHAUSTED` run that made commits pushes no branch, so its work survives only as a patch

`SA-0028` closed the door where an implement turn dies on its ceiling with
*nothing* committed. This is the door beside it: commits exist, gates are red,
the budget or the attempts are gone, and PACKAGE never runs — so nothing is
pushed and there is no pull request.

Measured on `SA-0031`: six commits, 39 new gate failures, `$19.17` spent, and a
ledger row reading `branch saffron/SA-0031, pushed_sha NULL, pr_url NULL`. The
only survivor is `teardown`'s `patch.diff`. It is real work — it applies
cleanly to `saffron/SA-0030` and leaves 15 failures, so it was roughly 85%
finished — and nothing in the system will ever look at it again.

The cost is not the disk space. It is that the operator's only route back to
$19.17 of work is to know the batch tree exists, find the patch, and apply it by
hand — none of which any output tells them.

Done looks like pushing the branch on any terminal state that made commits,
recording `pushed_sha`, and saying so on the way out. A pull request is a
separate question — red gates should not open one — but a branch nobody can
reach is not a decision, it is a leak. The split design
(`docs/superpowers/specs/2026-09-01-splitting-a-too-wide-spec-design.md`) needs
this independently: its mid-flight split hands child 1 the parent's branch, and
there is no branch to hand.


## 46. `events.jsonl` now persists an untrusted cell's raw output verbatim, and nothing bounds or scans it

**Decided 2026-09-04: it is evidence, not an operator's record.** So it takes
a size cap and must come within the `secrets` gate's reach. **Tier 1.**

The deciding argument is §9's v1 criterion. The defining property of the
milestone is that *nobody was watching* — so a log reduced to bounded
renderings would discard the only account of the night it matters most on.
That rules out the cheaper answer.

Two specifics, so the spec does not have to re-derive them:

- **One value on both paths.** Reuse `implement.QUARANTINE_BYTES` (8192) rather
  than minting a second number — the item names "one value, both paths" as the
  open half, and a second constant is how the two drift.
- **`secrets` must reach the batch tree, not only the diff.** §5.4 lists it as
  a v1 gate, so this is written down now to be built into it rather than
  retrofitted after.

`SA-0041` makes `implement.run_agent` emit the parsed cell event under
`Agent.event`, which is the fix that spec exists for — the dict was previously
flattened to prose before the host ever saw it, so `Agent.event` was
permanently `None`.

The side effect, raised by that run's contract lens: **what reaches persistence
changed shape.** Before, only `_describe`'s bounded renderings were written — a
`tool_result` became the fixed string `agent: tool ok`, `text` was truncated at
160 characters and `tool_use` at 120. Now the raw dict is written verbatim to
`~/.saffron/batches/v0/<id>/events.jsonl`, and for `text`, `tool_use` and
`tool_result` that dict can carry full file contents, whole command outputs, or
anything else an untrusted cell chose to put on stdout.

Two things follow, neither addressed anywhere:

- **Volume is unbounded on the path that matters.** `SA-0041` bounded the raw
  quarantined line at capture (`implement.QUARANTINE_BYTES`, 8192) after review
  measured 5 MB of stdout writing 5 MB of log. That closes the accidental case
  only: the same payload wrapped in nine bytes of JSON takes the `Agent.event`
  path and still writes 5 MB, because bounding it needs `saffron/events.py`,
  which that spec forbids. One value, both paths, is still the open decision.
- **The `secrets` gate never sees it.** That gate reads the diff. A batch tree
  artifact is not a diff, so a credential a cell printed to stdout is persisted
  host-side and scanned by nothing. §5.4 lists `secrets` as a v1 gate, so this
  is a gap that widens rather than one that exists today — which is the reason
  to record it now rather than after it is built.

Neither the golden fixture nor the unit tests can see this: both exercise small
synthetic dicts, so the change is invisible to the suite by construction.

Done looks like a decision about what the log is for. If it is an operator's
record of a night, the rendered line is sufficient and `Agent.event` should be
bounded the way the display already is. If it is evidence, it needs a size cap
and to be in the `secrets` gate's reach. `SA-0041` could not make that choice —
`saffron/events.py` is `forbidden` to it — and made the reachability fix it was
asked for, which is correct.


## 47. Every gate attempt in `events.jsonl` claims zero commits and zero spend, and part 3 is built to read it

`cell/session.py` emits an `Attempt` for each GATE and REBUT decision with
`commits=0, spent_usd_est=0.0` — four call sites — and the rebuttal-time gate
events additionally hardcode `attempt=1`, which is wrong whenever the repair
loop has already reached attempt N.

None of it is visible. `describe`'s `Attempt` branches return on `aborted`,
`drift`, `new_failures`+`decision`, or `new_failures` before ever reaching the
fallthrough that renders `commits` and `spent_usd_est`, so the terminal is
correct, the golden fixture is indifferent, and no test can see the fields at
all. The defect is entirely in what the log *keeps*.

Two consequences, both for a reader rather than an operator:

- **`0` cannot be told from "not computed".** `events.py` sets the opposite
  convention two dataclasses away, in as many words: *"`None`, never `0`: a
  skipped or errored gate had no count computed."* `Attempt.commits: int`
  cannot express it, so a consumer reads a real zero and a missing measurement
  identically.
- **Summing `spent_usd_est` across rows is wrong twice over** — the gate rows
  contribute nothing, and the IMPLEMENT row is *cumulative*, not incremental.
  Measured on `SA-0041`, 2026-09-02: it emitted `IMPLEMENT: 6 commit(s), $11.31
  spent`, and the ledger's attempts for that task read $2.457 and $8.856. The
  line is the running total, so two IMPLEMENT rows in one run double-count.

This is filed now because of who reads it next. `SA-0035`–`SA-0039` build §6's
pages from exactly this data, and a page that sums a column of zeros and one
running total will render a confident wrong number rather than fail. `SA-0034`
is the neighbouring case for the ledger; this is the same question for the log.

Done looks like `commits` and `spent_usd_est` being `int | None` and
`float | None` on `Attempt`, set only where they were measured, and the
rebuttal path carrying the attempt number it actually ran at. That needs
`saffron/events.py`, which `SA-0041` and `SA-0042` both forbid — so it is
either a spec of its own or the first thing part 3's first spec does.

## 48. §4.2.1's count of the refusal gate drifts every time one is added, and has twice

`SA-0023` added `protected_touch_refusal` (`saffron/scheduler.py`), so
`DESIGN.md:383` — *"The refusal gate refuses six things, and the fifth is the
only one with a corpse behind it"* — undercounts by one, and the enumeration
that follows it does not mention the new one at all.

The drift was designed in rather than overlooked: `DESIGN.md` is `protected`,
so `SA-0023` could not touch it, and the module docstring is honest about the
gap ("beyond §4.2.1's own six"). What makes it worth an item rather than a
shrug is the circularity underneath. **The only spec that could repair a
sentence in `DESIGN.md` is one whose `touches` names `DESIGN.md` — and that is
now exactly what this refusal refuses.** `SA-0021` was the last such spec and
it was run by hand for this reason; after `SA-0023` it does not even reach a
cell. Every future correction to the two authoritative documents is a
by-hand correction, permanently.

That is the right trade — a cell rewriting the definition of its own
constraints is what a global deny list is for — but it means the documents
drift by default and nothing schedules the catch-up. §4.2.1's count is the
first instance.

**Status: the count is correct and the item stays open, which is the whole
argument.** Two corrections have now landed by hand. The six→seven one came
with `SA-0023`; it was already wrong again by the time that was written,
because `SA-0027` had added an eighth. `DESIGN.md:383` now reads *"The refusal
gate refuses eight things"* and names both, and `scheduler.py`'s docstring says
§4.2.1 counts them.

**Twice in one release, each time caught by a person who happened to be
looking, is the finding.** Neither correction was scheduled; both were noticed
while reading for something else, and between them the authoritative document
said the wrong number for the whole of that window. A ninth refusal will drift
exactly the same way. **Done looks like** a check that `DESIGN.md`'s stated
count matches what `_refuse` applies — it fails the moment the ninth lands,
which no sweep does. Whether that check is cheap is unmeasured: it needs the
refusals enumerable by something other than reading `_refuse`, and no registry
exists. Item 30 reached the same practice from `SA-0024`'s side of the same
wall; this is the third instance, which item 30 itself said should not need a
third item to become a rule.

---

## 49. `revert` only checks *new* tests — a changed-body-same-name test has no coverage

**Decided 2026-09-04, with items 50 and 51: the `tests` role reports what
became of each name it was handed.** One §5.4 contract addition, not three
fixes. It closes 50 and 51 outright and narrows this one; what is left here is
the changed-body-same-name case, which needs the repo-declared hunk-to-node-id
mapping this item already describes. **Tier 1** with 51, since that is what
forces the contract.

Its subset is `collected(head) - collected(base)`, `census`'s own route. That
catches a new test that tests nothing; it cannot catch an *existing* test
rewritten under the same node id, which needs a hunk-to-node-id mapping —
language knowledge §2.1 keeps out of core. **Done looks like** a repo-declared
role reporting that mapping, so core can compute a second, disjoint subset
through the machinery already built; unbuilt because no runner reports it
yet. `criteria`'s witnesses and the third critic lens (§5.5.1) both narrow
this, so a changed-body test with no declared witness is the only true gap.

---

## 50. `revert` produces no evidence for the spec shape it was built for

**Decided 2026-09-04: closed by the contract change item 49 now records.** A
`tests` role that reports the disposition of every name it was handed turns a
collection error into the `fail` `revert` is waiting for, which is exactly what
this item asks for. **Tier 1** with 51.

Its canonical case is a spec that lands a module *and* its tests together: the
revert removes the module, the new tests fail to import, and that is the gate's
success condition rather than a problem. This repo's `tests` gate cannot report
it as one. A collection error prints no line its regex or its `FAILED ` fallback
can key on, so it reports `error`; `revert` will not read an untrustworthy run
as a pass, so it reports **`skip`** — honest, non-blocking, and no evidence in
either direction. The gate therefore bites hardest on a diff that adds tests for
source that already existed, and says nothing at all about one that adds both.

**Done looks like** the `tests` role reporting a collection error inside the
contract it already fills — `failures` keyed on the node ids it was asked to run
and could not collect — which turns the case into the `fail` `revert` is waiting
for. A contract question, not core's: §5.4 already obliges the role to accept a
subset, and this obliges it to say what became of one. Until then the ceiling
lives in `revert.py`'s comment and one test, and nowhere an operator reads.

---

## 51. A cell can buy `revert` a `skip` for one printed line

**Decided 2026-09-04: the §5.4 contract change, and this item is why it is
Tier 1.** A cell switches the anti-theater gate off for an attempt with one
printed line, needing no `conftest.py`, so the `gate_config` routing that
exists for this class never fires. That is a control reading as present while
not applying — Appendix I's founding defect — and the item is explicit that no
name filter closes it, because telling a real node id from an invented one is
language knowledge §2.1 keeps out of core. **Contract or nothing.**

The cost is real and is accepted: every onboarded repo's `tests` gate has to
implement the addition, and v2's success criterion is an afternoon-long
onboarding. Under §9's v1 target that cost lands later than this defect does.

`revert` is the only gate that *executes* a name the cell produced, so it is the
only one where a collection line is an argument rather than a string to compare.
Names reading as command-line options are dropped (`_argv_safe`), which closes
the shape that would force a false `pass` — a `--deselect=` line deselecting the
one test the gate is asking about. **It does not close the family.**

Measured against this repo's own gates. A test file registering an `atexit`
handler that prints `zzz::bogus` leaks that line onto `pytest --collect-only`'s
stdout: the handler runs after pytest tears its capture down, so a plain
module-level `print` does *not* leak and this does. The collection still exits
0, and `.saffron/gates/tests.py` calls any line holding `::` a collected name.
The name is new at head, joins the subset, matches no file, the reverted run
exits 4 with no parsed failures, the `tests` gate reports `error`, and `revert`
reads an untrustworthy run as `skip`. **One line in a new test file, and the
anti-theater gate is off for that attempt.** It needs no `conftest.py`, so the
`gate_config` routing in `.saffron/policy.yaml` — which exists for exactly this
class, and says so — never fires.

**No name filter closes it.** A bogus id spells as easily inside the repo's
declared `test_paths` as outside them, and telling a real node id from an
invented one is the language knowledge §2.1 keeps out of core. **Done looks
like** the contract addition item 50 wants for the opposite reason: a `tests`
role that reports what became of each name it was handed, so a name it could not
collect is a fact the gate can read rather than a silence it must interpret.
Until then the dropped names are named in the gate's summary — which makes the
*other* shape visible to an operator, and leaves this one invisible.

---

## 52. `MERGE_TRAIN` is a state the scheduler reads twice and neither authoritative document declares

`DESIGN.md:259` shows a task entering it, `saffron/scheduler.py:67` has it in
`DONE_STATES` and `:91` in `DEPENDENCY_WAITING_STATES`, and §4.2.1 names it twice
— in the queue filter and in the list of parents that admit a dependent. It
appears in **neither** `CONTEXT.md` nor `ontology/saffron.ttl`.

Found by Appendix O's spike (rev 19), while counting what a shape form would need.
It is the fourth defect the modelling exercise has found in these documents, which
is Appendix O's own argument *for* the vocabulary landing on the same page as the
verdict that closed the operational question against it.

**It is not obvious which set it joins, and that is the work.** `CONTEXT.md` §6 is
careful that a state a task *ends in* is a wider set than the states that *reach
you* — `MERGED` ends a task and reaches nobody. `MERGE_TRAIN` is a re-queue arrow
in §3.3 and "done with the spec" to the scheduler, so it is plainly an `EndState`;
whether it is a `TerminalState` needs deciding rather than assuming, and that
decision is exactly the one item this document keeps getting wrong.

Phase A makes the propagation free once decided: `saffron:MERGE_TRAIN a
saffron:EndState` in the vocabulary and `uv run python -m ontology.render` writes
`CONTEXT.md` and the shapes. `TaskShape`'s `endedInState` list is the one hand
edit, and `test_every_terminal_state_is_a_state_a_task_can_end_in` names the file
if it is forgotten.

Two soft copies are worth knowing about and are **not** part of this: `cli.py`'s
exit-code map and `report/index.py`'s `_STATE_RANK` both fall through to a
documented default rather than raising, so an undeclared state degrades there
rather than breaking. That is by design and stays.

**Done looks like** `MERGE_TRAIN` declared once in `ontology/saffron.ttl`, the
derived surfaces regenerated, `TaskShape` updated, and a one-line note in §3.3 or
§6 saying which of the two sets it joined and why.

### Decided 2026-09-08, and the item grew

`MERGE_TRAIN` is an **`EndState`**, not a terminal one — this item's own
"plainly an `EndState`" was right, and it survived an argument that it was not.
The argument was that a task in the merge train has not ended: it becomes
`MERGED` or `MERGE_FAILED`, so it is in flight. That is true and it is not the
rule, because it is equally true of `APPROVED`, which is already an `EndState`.

**What the rule actually is, because `EndState`'s own comment says otherwise.**
The comment reads "a state a task can finish in", which implies the row stops
changing. It does not: `CHANGES_REQUESTED`, `ORPHANED`, `RATE_LIMITED`,
`GATE_ERROR` and `PREFLIGHT_FAILED` all resume *the same row* —
`Candidate.task_id` is set for `REQUEUE_STATES` precisely so "the resumed work
reattaches to the row it was sent back to fix rather than a fresh one"
(`scheduler.py`). Five of `EndState`'s members contradict its definition. The
rule that fits every member is **whether the task is Saffron's to advance**:
`DRAFT` and `QUEUED` because it will be advanced tonight, `DIAGNOSING` through
`REBUTTING` because it is being advanced now; everything else waits on the
operator, on GitHub, on the merge train, or on `gc`. Sharpening that comment is
part of this item now — the wording sent two readers to the wrong answer in one
sitting, which is item **75**'s failure mode in the file that is supposed to be
authoritative.

**The item is no longer one state.** Declaring `MERGE_TRAIN` needs a class to
declare it *into*, and the vocabulary has none: `EndState` and `TerminalState`
model the states a task ends in, and nothing models the eight §4.2.1 names a
task passes through. So:

- `ontology/saffron.ttl` gains **`TaskState`** as a supertype over `EndState`
  and a new **`InFlightState`** — exactly §4.2.1's eight (`DRAFT`, `QUEUED`,
  `DIAGNOSING`, `IMPLEMENTING`, `GATING`, `REPAIRING`, `REVIEWING`,
  `REBUTTING`), every one of them a state where a cell is Saffron's to run.
- `CONTEXT.md` gains **Task state** as its own term enumerating all of them.
  **Terminal state** is untouched, so §6's "everything else is internal" stays
  true as written. Both join `CLOSED_SETS`; no carve-out, for item **72**'s
  reason — a set excluded from the cross-check on a plausible-sounding basis
  cost three pull requests once already.
- A hand-written `TaskState` `Literal` cross-checked in
  `tests/ontology/test_vocabulary_agrees_with_code.py`, following `Severity`
  and `StopReason`. Not generated: nothing under `saffron/` imports a graph
  library and `pyproject.toml` says so.

**`set_task_state` stays untyped.** Neither landed defect was writer-side, and
a type with no measured defect behind it is machinery this repo does not buy.

### The half of this item that was decided wrongly

This item says `cli.py`'s exit-code map and `report/index.py`'s `_STATE_RANK`
"both fall through to a documented default rather than raising, so an
undeclared state degrades there rather than breaking. That is by design and
stays." **Half of that is reopened, and the evidence is this document's own.**

Both of the landed defects were exactly that fall-through: `6938c41` ("a state
that exists only in code is half a state" — `_STATE_RANK` knew neither
`GATE_ERROR` nor `NOT_IMPLEMENTED`, and `saffron cell` exited 0 for every
terminal state) and `a4324f0` ("every abort exits 2, and every state has a
rank" — `EXHAUSTED`, `ORPHANED`, `REVIEWING` and `REBUTTING` fell to
`_ORDINARY` and sorted below elevated-risk green tasks). Two defects, both
reader-side, both in the half declared safe.

`a4324f0` mitigated itself with "nothing calls `queue_lines` in production yet,
which is the only reason this has not been seen". That is now false, and it was
about a different function: `_STATE_RANK` is reached through
`report.sort_key` ← `render_index` ← `append_queue_line`, which
`phases/package.py` calls on every packaged task. **The ranking is live.**

**The two tables are not symmetric, which is what this item missed by treating
them as one.** An unknown state exiting `1` is a true statement — "the task did
not make it" is accurate about a state nobody has classified. An unknown state
ranking as `_ORDINARY` is an active misstatement: it sorts a dead cell below a
green reviewable task on the page the whole system exists to produce. So:

- **`CELL_EXIT` keeps its default**, and the reason is now written down rather
  than assumed.
- **`_STATE_RANK` becomes total** over the row domain, as two explicit sets —
  ranked-by-state and ranked-by-risk — with a test that every state is in
  exactly one. The risk ranking stays a deliberate choice rather than a
  fallback that also absorbs the unclassified.

**The domain is rows, not tasks.** §6 designs the morning index as a table of
rows, and one kind is a skipped repo — `toolbox — SKIPPED`, spec id an em-dash,
ranked 0 because "an entire repo produced nothing, which is the most expensive
thing on the page". So `QueueLine.state` is already wider than `tasks.state`
today, by design. `report/index.py` gets `RowState = TaskState |
Literal["SKIPPED"]` and `_STATE_RANK` is exhaustive over *that*. `SKIPPED`
stays, commented as designed-and-pending until multi-repo — it has no producer
because multi-repo is v2, not because nobody thought about it, and this was
nearly deleted on the second reading.

A refusal is the third row kind §6 and `CONTEXT.md` both describe and nothing
writes: refusals reach stdout, never `index.html`. Filed separately rather than
built here — a `REFUSED` classified before anything writes it is how `SKIPPED`
happened. The exhaustiveness test above is what will force the decision when a
producer does arrive.

### The other four sets

`scheduler.DONE_STATES`, `REQUEUE_STATES`, `DEPENDENCY_WAITING_STATES`,
`DEPENDENCY_DEAD_STATES` and `reconcile.IN_FLIGHT_STATES` are five more
hand-maintained classifications of the same strings, and nothing checks any of
them against anything. Each gets subset-hood against `TaskState`;
`IN_FLIGHT_STATES` gets **equality** with `InFlightState`, because it is meant
to be the whole class; and `DONE_STATES | REQUEUE_STATES` gets a coverage
assertion over every non-in-flight state, because §4.2.1 says the in-flight
states are deliberately on neither list — which makes an *end* state on neither
a silent bug of exactly the kind this item is now about.

Subset-hood alone would have caught neither landed defect. Both were omissions,
and no subset check catches an omission.

### Also falsified by this work

`tests/ontology/test_vocabulary_agrees_with_code.py`'s docstring: "The terminal
states the code names do still fall through to a documented default rather than
a raise, so they are not a closed set on the code side and are not checked
here." That sentence states the precondition this item removes.

**By hand, and its own pull request.** It spans the vocabulary, two generated
surfaces, three modules and their tests, and `ontology.render` has to be run and
its output committed — which a cell cannot prove it did honestly.

**Tier 2 still.** Larger than when it was sorted, and it competes with tier 1's
soundness items. Sequencing it behind them is the backlog's own rule working,
not a reason to shrink the item.

---

## 53. Three closed sets live only in the shapes, where nothing cross-checks them

**Decided 2026-09-04: they are vocabulary. Enumerate all three** in
`CONTEXT.md`, joining `CLOSED_SETS`, `SETS` and `SHAPE_SETS` — three lines and
a regenerate. **Tier 3.**

The item says the reason matters more than the choice, so: the test is **who
has to know the term.** `SpecType` appears in every spec's frontmatter and,
since item 56, selects the size ceiling that can end a run `EXHAUSTED`.
`BlockingLevel` is written by repo authors in `policy.yaml`, which is the exact
surface v2's afternoon-long onboarding is measured against. The rebuttal roles
render into pull request bodies read at review time. None of the three is
internal to the shapes.

§4's precedent for leaving repo-defined gate *names* out does not extend to
these: gate names are open by design, and a set that is closed by `sh:in` and
enforced by a blocking gate is a controlled vocabulary whether or not it is
written down as one.

`SpecType` (`feature`/`bug`/`refactor`), `BlockingLevel`
(`alwaysBlocking`/`blockingWhenElevated`/`advisory`) and the rebuttal roles
(`disputes`/`concedes`, `confirms`/`withdraws`) are closed by `sh:in` in
`ontology/shapes/saffron-shapes.ttl` and enforced by the blocking `shacl` gate.
None is among the generated sets, because `CONTEXT.md` does not enumerate any of
them — so `test_vocabulary_agrees_with_context` cannot see them and
`ontology/render.py` does not write them.

They are therefore in exactly the state the generated sets were in before Phase
A: a closed set with one hand-maintained copy per file, and no check that the
copies agree. The difference is that the second copy has not been written yet,
so nothing has drifted. This is a deferred decision, not a live defect.

**Done looks like** a decision, in writing: either `CONTEXT.md` enumerates them
and they join `CLOSED_SETS`, `SETS` and `SHAPE_SETS` — three lines and a
regenerate — or a stated reason why they are shape-internal and not vocabulary,
of the kind §4 already gives for repo-defined gate names. The reason matters more
than the choice; `test_the_generator_and_the_cross_check_name_the_same_sets`
will hold whichever way it goes.

---

## 54. The drift test rides the `tests` gate, so the ledger cannot say which check failed

`tests/ontology/test_generated_surfaces_are_current.py` is what catches a
vocabulary that moved ahead of its derived surfaces. It is a pytest test, not a
`.saffron/gates/` executable, and that was chosen deliberately: it inherits its
`tool` field by execution (`pytest --version`), which a hand-written gate would
have to obtain itself (§5.4, Appendix H) — the exact hole Appendix H is about.

The cost is paid in the morning queue. An operator sees "some test failed" rather
than a named gate, and the distinction between "the code is wrong" and "the
generated documents are stale" is one the ledger cannot make.

**Done looks like** either a `.saffron/gates/` executable that runs the render and
obtains its own `tool` by executing something real, or a written decision that the
test is enough — with the reason, so the next reader does not re-litigate it. It
becomes worth doing the first night an operator misreads a stale-surface failure
as a code failure.

---

## 55. `dist/` is not gitignored, so a build artifact is one `git add -A` from being committed

`uv build` writes `dist/` and nothing ignores it. It is not present in a clean
tree, so it is invisible until someone runs a build — and `pyproject.toml`'s
`packages = ["saffron"]` is a claim worth checking by building, which is how this
was found.

**Done looks like** one line in `.gitignore`. Filed rather than fixed in passing
because it belongs to no branch in flight; it is a two-minute item for whoever
touches packaging next.

---

## 56. Nothing weighs a spec against its own size ceiling before the money is spent

Split out of item 25, which the `SA-0014`–`SA-0017` recut closed by hand. The
recut fixed one spec; **the check that would have caught it before a cell
started was never built**, and every spec written since has been sized by
whoever wrote it.

`SA-0009` is the measurement. Two `IMPLEMENTING` attempts landed 990 changed
lines across seven files, `size` reported `fail` in every gate result after, at
the 600-line `feature` ceiling (`gate_result_id` 113/124/135), and two
`REPAIRING` attempts
each burned a full `max_turns=100` trying to cut the diff back down without
ever getting `committed` clean again. **$31.60 against an $18 budget,
`EXHAUSTED`, zero lines merged.** The overrun was not bad luck: the diffstat
split cleanly along the spec's own acceptance criteria, and
`tests/test_scheduler.py` alone was 433 of the 990 lines because it was
carrying fixtures for two unrelated mechanisms the spec text asked for
separately.

**Everything the check needs is already parsed and host-side.** `Spec` carries
`type`, `touches` and `acceptance_criteria`; `saffron/gates/core/size.py`
carries `_CEILINGS` (`bug` 300, `feature` 600, `refactor` 1000) and
`_DEFAULT_CEILING`. The scan runs before a container starts and costs no
`gh` call, which is what makes this cheap in the way item 18's turn-ceiling
argument was cheap: the ceiling already exists and is enforced far too late,
against a diff somebody has already paid for.

**The hard part is the predicate, not the plumbing, and it should not be
guessed.** Criteria count times files in `touches` is a number with no
measurement behind it, and a refusal gate that fires on a good spec is worse
than no gate — `saffron queue` refuses before a cell runs, so a false positive
costs a spec that never gets written rather than a diff that never lands.
Twenty specs carry a `MERGED` row in `~/.saffron/ledger.db` with a real
diffstat behind them, each pinned to its own `spec_sha`, so the honest first
move is to fit the predicate against that corpus and see whether it separates
`SA-0009` from the twenty that converged.

**Done looks like** one of: a warning line on `saffron queue` naming a spec
whose shape predicts an over-ceiling diff, fitted against the merged corpus
rather than reasoned; or a written finding that the corpus does not separate
them, which retires the idea. **The refusal gate is the wrong home either
way** — §4.2.1's refusals are all facts (a parent did not merge, a path is
protected), and this is a forecast. A forecast that blocks is the shape item
23 is about.

---

## 57. The vocabulary hook matches within a line, and this file is hard-wrapped

`.pre-commit-config.yaml`'s `retired-vocabulary` hook is `language: pygrep` with
`entry: '(?i)gate[ -]runs?\b'`. pygrep searches **line by line**, and every
prose file in this repo is hard-wrapped at ~78 columns, so a retired two-word
term that happens to straddle a line break is not seen.

**Measured, not reasoned.** Two files, same words:

```
_probe_flat.md     the retired two words, space between, one line  -> Failed  (caught)
_probe_wrapped.md  the same two words, split by a line break       -> Passed  (missed)
```

(Described rather than quoted, for the reason `.saffron/policy.yaml` gives about
its own suppression list: the tokens a check scans for are themselves scanned.)

And it has already happened here. Item 25 has carried *"`size` failed every
gate / run after"* since it was written; the hook ran over that line on every
commit since and passed it, because the wrap put `gate` and `run` on separate
lines. It was found only because a later edit put the same phrase on one line
and the hook rejected *that* — so the control's one catch to date was of a
sentence a person had just written, not of the one that had been sitting in the
file for a week.

**The rate is not marginal.** Across the 52 markdown files the hook covers
(its `exclude` drops `CONTEXT.md`, `CLAUDE.md`, `docs/superpowers/` and
`docs/evidence/`) the mean is **12.6 words per line**, so roughly **one
occurrence in thirteen** of any two-word term falls across a break. 28 lines in
those files already end in the bare word `gate`.

**This is Appendix I's shape in the vocabulary layer** — a control that reads
as present, reports green, and is not applying — which is the argument for
fixing it rather than noting it. It is also why the count matters: one in
thirteen is low enough that the hook looks like it works.

**Done looks like** the check reading the file rather than the line. `pygrep`
cannot: the cheapest honest fix is a small `language: script` hook that
normalises whitespace across line breaks before matching, which also makes the
pattern list somewhere a second retired term can be added. **Not** a
`multiline` pygrep flag alone — `\b` and `[ -]` would still have to grow a
newline case, and the next term added would need the same care, which is the
part that rots.

**One thing to decide with it, and it is not obviously a defect:** `CONTEXT.md`
carries dozens of `_Avoid_` terms and the hook enforces exactly one. That looks
deliberate — most of the others are common English (`run`, `session`, `the
tool`) and a mechanical match would drown in false positives, whereas
`gate[ -]run` is safely distinctive. Worth stating in the config so the next
reader does not take the gap for an oversight and "finish" it.

---

## 58. Nothing runs a batch, and v1 is defined by a night that does

**Status: done** — seven specs, `SA-0045` through `SA-0054`, PRs #115/#116/#117
/#120/#121/#122/#123, merged together as `57b676c`. `saffron batch --repo .
--budget 50 --until 06:30` exists, `saffron/batch.py` owns the loop, the
`batches` table records the night, and `docs/host/dev.saffron.batch.plist` is
the launchd job. Absorbed items **16** and half of **44**, both now closed
above.

**A night has been run, against an empty queue** — `DRAINED`, exit `0`, $0.00,
2026-09-05 (`docs/evidence/2026-09-05-first-batch-drained.md`). That proves
readiness, the mirror fetch, the scan, `reconcile`, the ledger row, the
deadline resolving to tomorrow, and the exit code.

**No cell has started under a batch.** So the budget gate, the breaker,
`--until` firing, packaging, the orphan sweep and what a night costs are all
tested and none is measured. A night with one cheap spec in it is the next
thing worth running, and until it has, this item is done in the sense that the
code exists rather than in the sense that the night works.

What the review round found is worth recording, because it is the argument for
the round: seven tests across the stack named behaviour they did not guard, and
every one read fine. Two migration guards asserted the string `replace` had
just removed; the breaker reset was deletable with the suite green;
`parent_branch=None` would have targeted `main` from every stacked child; both
operator-facing print lines were replaceable with `pass`. And the token probe
was inert — `400` read as valid, so it accepted any string at all (item **66**,
and `docs/evidence/2026-09-05-token-probe-request-shape.md`). None of that was
caught by reading. It was caught by running the mutation, and by one live
measurement.

**Tier 0.** Not found by a run — found by asking what the other 29 items were
being ordered *toward*, 2026-09-04.

`saffron/cli.py` exposes four subcommands: `replay`, `cell`, `queue`,
`reconcile`. There is no `run_batch` anywhere under `saffron/`. `queue` prints
what a batch *would* run and reconciles pull request state; nothing executes
it. §4.4 "Batch orchestration" is design with no implementation, and §9's v1
criterion — *a full night runs while you sleep, and you merge at least half of
what it produces before the coffee's cold* — is therefore not merely unmet but
structurally unreachable.

What runs specs today is `run-saffron-spec-loop`, a Claude Code skill driving
`saffron cell` once per spec with an agent supervising. That is the attended
loop working as intended, and it is **not** the thing v1 names: the skill is
host tooling, not the product, and it needs someone at the keyboard.

**This is why it sits above the whole backlog.** Every open item is a
refinement of a pipeline that cannot yet run unattended, and "what would hurt
most on the first unattended night" cannot be honestly ranked while nothing can
produce one. Two items fold into it rather than standing alone:

- **Item 16** — a task's policy lineage. §4.1's invalidation rule (*change a
  repo's gate declarations mid-batch and its in-flight tasks are invalidated*)
  is a doc claim with no reader until batches exist, and a batch is exactly the
  window where a policy moves under an in-flight task. Building the runner
  against a ledger that cannot say what a task ran under is building it twice.
- **Item 44**'s enforceable half — a per-batch ceiling, checked *between* tasks.
  That is the only place a spend bound is enforceable at all, because nothing is
  mid-flight at that moment; `budget_usd` cannot be, for the reason item 44 now
  records.

**Done looks like** a plan, split into specs by that plan — the shape
`docs/superpowers/plans/2026-08-31-operator-visibility.md` uses. **Not one
spec.** §4.4 spans `cli.py`, a new orchestration module, `scheduler.py` and
`ledger.py`, and item 56 is the measurement of what happens when a spec that
wide reaches a cell: `SA-0009`, $31.60, `EXHAUSTED`, zero lines merged. The
plan itself is written by hand — §4.4 is design, and `DESIGN.md` is
`protected`.

---

## 59. The overlap refusal walks one hop, so a stack deeper than two refuses its own grandchild

**Tier 1.** Measured 2026-09-04, on this repo's own queue, by the first stack
three deep.

**Status:** **done**, by `SA-0053`'s predecessor `SA-0052` (PR #118, merge
`37b2dc2`) — one attempt, $5.03, no blocking findings. The exemption now walks
`depends_on[0]` transitively through the discovered specs, carrying a visited
set seeded with the candidate's own id so a dependency cycle ends the walk
instead of hanging the scan. `build_queue`'s signature is unchanged and the two
live-witness tests were not touched: 239 added lines, 0 removed. Verified after
the merge — the queue that had refused `SA-0049` reports zero refusals.

`saffron/scheduler.py`'s open-pull-request overlap refusal exempts the
candidate's own branch and one parent:

```python
parent_branch = _branch(candidate.spec.depends_on[0]) if candidate.spec.depends_on else None
for pr in open_prs:
    if pr.get("headRefName") in (own_branch, parent_branch):
        continue
```

`depends_on[0]` is the **immediate** parent. A stack is transitive.
`SA-0049` → `SA-0048` → `SA-0046` → `SA-0045`: the exemption covers `SA-0048`
and not `SA-0046`, whose pull request is open and whose changed files include
`saffron/ledger.py`. `SA-0049` touches `saffron/ledger.py`, so it is refused:

```
SA-0049: touches overlaps open pull request #116's changed files:
         saffron/ledger.py, tests/test_ledger.py
```

**The refusal is a false positive, and stacking is why.** A stacked child is
cut from its parent's branch head, so a linear stack's grandparent changes are
already in the child's own base *by construction*. There is nothing to
conflict with — that is the whole point of `SA-0022`, `SA-0025` and `SA-0026`.
The gate is refusing the case the stacking machinery exists to admit, which is
the shape §4.2.1 already had to correct once for the dependency gate.

**Invisible today, and that is the dangerous part.** `saffron cell` never
consults `build_queue` — only `saffron queue` does (`cli.py:531`) — so every
spec in this session's stack was driven successfully while the scan was
refusing one of them. The refusal costs nothing until a batch reads it, and
then it costs a task per night, silently, on exactly the deep queues stacking
was built for.

**Done looks like** the exemption walking the chain rather than one link:
collect every ancestor's branch by following `depends_on[0]` transitively
through the discovered specs, and exempt all of them. The specs are already in
hand at that point — `build_queue` has the whole scanned set — so this needs no
new lookup. A test with a three-deep stack and an open grandparent pull request
is what fails today.

**Not** widening the refusal to ignore all overlaps: the gate is right about
two unrelated tasks touching one file, which is what it was built for. Only the
ancestor case is wrong, and only because the chain is walked one link deep.

---

## 60. A review lens's whole report is discarded on a schema error, and nothing re-prompts

**Tier 2.** Measured 2026-09-04 on `SA-0053`, and the finding it cost was a
real one.

The correctness lens returned a well-argued finding about `saffron/watch.py`
and omitted one field:

```
correctness produced nothing — not the schema: 1 validation error for _Report
findings.0.severity
  Field required [type=missing]
```

`review.py:168` turns that exception straight into `LensReview(..., error=...)`.
The finding is gone — recoverable only by grepping `events.jsonl` by hand,
which is how the text above was retrieved.

**The stop is correct and is not the defect.** `review.py:274` makes an errored
lens a stop at `REVIEWING`: *"A lens that errored **is** a stop"*. So a
vanished lens can never read as a clean review, which is the Appendix I
discipline working exactly as designed. Nothing here argues for softening it.

**The gap is the missing re-prompt.** The plan artifact re-prompts once on a
schema failure — `session.py:451`, *"not the schema, re-prompting once"* — and
a lens does not, though both are a fresh session returning JSON against a
declared shape and both cost roughly the same to ask again. One malformed
enum field ended the attempt at $3.61 with a correct finding thrown away.

**Done looks like** `review.py` re-prompting a lens once on `NotSchema`, the
way `artifacts.py` already does for the plan, with the second failure still
producing the stop it produces today. The re-prompt must carry the validation
error itself: the lens omitted a required field, and being told which one is
most of the fix.

**Not** relaxing the schema to make `severity` optional. The severity is what
`_describe` counts and what decides whether a finding blocks; a report whose
findings have no severity is not a report that can be acted on.

---

## 61. `describe` raises on a payload `read_log` hands back unchecked

**Tier 3.** Found reviewing `SA-0053` (PR #119), and fixed *around* rather than
fixed: `saffron/events.py` was `forbidden` to that spec.

`read_log` type-checks nothing — it is `cls(**obj)` onto a plain dataclass — so
a corrupt or hand-edited line round-trips into `Agent(event='not an object')`
and `describe` raises `AttributeError` on `.get`. Measured:

```
read_log tolerates it: [Agent(timestamp=1.0, spec_id='T1', raw=False, event='x', …)]
describe RAISED: AttributeError 'str' object has no attribute 'get'
```

That is per-line corruption defeating the per-line tolerance `read_log`'s own
docstring promises, and it takes the whole caller down with it. `watch.py`
guards its own call (`_is_malformed`), so the follower is safe; every other
caller of `describe` is not.

**Done looks like** `read_log` refusing to build an event whose field is the
wrong type at all — the drop it already performs for a missing field, extended
to a present one of the wrong shape — so no caller has to guard. The producer
side is already guarded (`implement.py:255` checks `isinstance(event, dict)`),
so nothing hostile reaches this today; a hand-edited log does.

**Not** each caller repeating `watch.py`'s guard. That is the duplication the
guard exists to make unnecessary once, and `describe`'s contract should be
"any `Event`" or it is not the single renderer this repo relies on it being.

---

## 62. A follower re-reads the whole log every poll, so watching a night is O(n²)

**Tier 3.** Measured 2026-09-04 while reviewing `SA-0053` (PR #119), and named
in a `ponytail:` beside the call.

`watch.follow` calls `read_log` once per poll and slices past what it has
already seen. `read_log` has no offset — it reads and parses the entire file —
so following costs O(n²) over a night. Measured: **5.7s for one `read_log`** on
a 37 MB / 160k-line log, past which the default 1s interval falls permanently
behind and pegs a core re-parsing what it already rendered. `events.py`'s own
`ponytail:` names "tens of MB a night" as the ceiling, so this is inside the
range the log is designed for.

**Done looks like** `read_log` taking a byte offset and returning the position
it stopped at, with `follow` holding that between polls. The truncated-final-
line tolerance has to survive it: a partial line at the offset boundary must
leave the offset *before* it, or the next poll resumes mid-object and drops
every line after.

**Not** having the follower parse the file itself. A second parser beside
`read_log` is the same defect as a second renderer beside `describe`, which is
the thing `SA-0053` was written to avoid.

---

## 63. `describe` renders three agent payload fields unclipped, straight to a terminal

**Tier 3.** Found reviewing `SA-0053` (PR #119). Not a regression — the
attended terminal has had this exposure since `SA-0029` — but that PR added a
*second* consumer, which is what makes it worth filing.

`_describe_agent_event` clips `text` at 160 characters and `tool_use` at 120.
Its `error`, `rate_limit` and fallback branches clip nothing and strip nothing.
An `Agent` event carrying `{"type": "error", "error": "\x1b[2J\x1b]0;…\x07" +
"A"*5000}` renders with the escape bytes intact, which reaches the operator's
terminal as a screen clear and a title change. The content is authored inside a
cell, and CLAUDE.md's governing line is that a cell is untrusted.

`saffron watch` makes it worse in one specific way: it can replay a finished
cell's output into a fresh terminal, long after the run, for an operator who
was not watching when it happened.

**Done looks like** the three unclipped branches clipped like the other two,
and C0 control characters other than nothing at all stripped in `describe` —
once, where the single renderer is, not in each caller.

**Not** escaping in `watch.py`. That is a second renderer by another name, and
it would leave the attended terminal — the one that reads this output during a
live run — still exposed.

---

## 64. A re-run appends to the same log, so `watch` shows two nights as one

**Tier 3.** Measured 2026-09-04 while reading `SA-0051`'s second run with the
verb built two specs earlier.

The batch tree keys a task directory by spec id — `~/.saffron/batches/v0/<SPEC-ID>` —
and `EventLog` appends. A spec driven twice therefore writes both runs into one
`events.jsonl`, in order, with nothing between them. `saffron watch SA-0051`
opened on this line:

```
PLAN: rejected, $1.80 spent — plan's own estimate of 650 changed lines exceeds
the feature ceiling of 600
```

which belonged to the *previous* attempt, not the one being watched. The run
being read had been accepted at 300 lines and was in its repair turn.

**Not the same gap as the no-rotation ceiling.** `EventLog`'s own `ponytail:`
names one file per task with no rotation, and that is about size. This is about
*identity*: two runs of one spec are two different nights, and nothing in the
file says where the first ends. An operator diagnosing a re-run reads the
failure of a run that no longer exists and draws a conclusion about the one
that does — which is worse than a file that is merely large.

**It is also how a stale log reads as a live one.** A spec that was driven last
week and is being driven now shows last week's `READY_FOR_REVIEW` and pull
request URL above today's preflight. `--no-follow` on a task that has not
started yet prints the previous run in full and looks current.

**Done looks like** a run boundary in the log that `describe` renders — the
run id is already minted before the first event is written, so a marker
carrying it costs nothing to produce — and `watch` defaulting to the newest
run, with the whole file reachable behind a flag. The cheap half is the marker;
the flag can wait for someone to want it.

**Not** one directory per run. The task directory's name is what `saffron
watch SA-0051` resolves, what `patch.diff` and `plan.json` live beside, and
what the batch index links to; making it run-scoped changes four things to fix
one, and `plan.json` being overwritten by a re-run is the same defect with the
same fix.

---

## 65. The batch's four stop reasons are a closed set that lives only in SQL

**Status: done** — `saffron:BatchStopReason` in the vocabulary, `CONTEXT.md`
regenerated, and `saffron:BatchShape` closing the set with `sh:in`.

Four readers now have to agree, and a test fails on each direction of drift:
the vocabulary, `CONTEXT.md`'s **Batch stop reason** entry (generated, not
hand-copied), `batch.StopReason`, and the `CHECK` on `batches.status` — the
last parsed out of `SCHEMA` rather than restated, because a copy of the four in
a test drifts exactly the way the constraint drifted from the vocabulary. That
is the specific hole this item named: a fifth reason added in SQL alone.

The shape carries one axiom the `CHECK` cannot state. `minCount 0`: a batch
with no stop reason is legal *precisely while it is in flight*, which is the
NULL-means-running distinction §6's morning queue reads. A constraint can say
which strings are legal; it cannot say that absence means something.

Worth recording because it is the confusion the class exists to prevent: the
shape rejects `EXHAUSTED` and `ORPHANED` as stop reasons. They are *task* end
states, they share a column type and a naming style with these four, and
`saffron batch` maps three of the four to exit `0` — so reading one set as the
other misreports a night.

**Tier 3.** Found reviewing `SA-0045` (PR #115), and again reviewing `SA-0049`.

`DRAINED`, `BUDGET`, `UNTIL` and `INFRASTRUCTURE` are a closed set — a `CHECK`
constraint on `batches.status` refuses anything else, and `batch.StopReason` is
a `Literal` of the same four. They appear in neither `ontology/saffron.ttl` nor
`CONTEXT.md`.

Every other closed set in this repo is generated from the vocabulary and
cross-checked by `tests/ontology/test_vocabulary_agrees_with_context.py`, which
is the mechanism CLAUDE.md names as authoritative. This is the sixth, and the
first with no vocabulary entry: nothing stops a fifth reason being added in SQL
alone, and nothing tells a reader of `CONTEXT.md` that the four exist.

Deferring was correct in the layer that found it — `ontology/` and `CONTEXT.md`
were both `forbidden` to `SA-0045` and to every spec above it — but the
deferral has no owner now.

**Done looks like** a `saffron:BatchStopReason` class in the vocabulary with the
four individuals, `uv run python -m ontology.render` re-run, and the closed-set
test naming it alongside the other five. The `CHECK` constraint stays: the
vocabulary is authoritative for the words, and the constraint is what enforces
them at the one place a bad value could be written.

---

## 66. The token probe is measured for a live credential and inferred for a dead one

**Tier 2.** Filed 2026-09-05 alongside the measurement in
`docs/evidence/2026-09-05-token-probe-request-shape.md`.

That measurement established what `/v1/models` answers a *live* subscription
token, and it mattered: without `anthropic-version` the endpoint returns `400`
for any token at all, because it validates the header before the credential —
so the probe's original boolean form (`exc.code not in (401, 403)`) called every
credential valid, including a revoked one. That is fixed.

What is still inferred is the other half. Nothing has observed what a
**revoked** token answers with the header present. `401` is the expectation and
the code treats `401`/`403` as the only INVALID verdicts.

The gap is safe in one direction by construction: any other status is
`UNKNOWN`, which refuses the night while naming the endpoint rather than the
credential. So a wrong guess costs a night that declines to start and says why
— never a night that starts on a dead token. That is why this is Tier 2 rather
than Tier 1.

**Done looks like** the results table in that evidence file having a revoked
column, filled from a real run. The moment to do it is a token rotation, when a
dead token exists anyway: revoke, run
`docs/evidence/scripts/2026-09-05-token-probe-shape.py`, record the status. If
it is not `401`/`403`, add it to the INVALID set and say in the comment that it
was measured.

---

## 67. `--until` does not stop a running cell, and §4.5 says it does

**Tier 2.** Found reviewing `SA-0054` (PR #123).

`run_batch` checks the deadline between candidates, and `run_one_cell` takes no
deadline argument at all — so a cell already running at 06:30 runs to its own
`max_turns` and `max_attempts`. The wall-clock end of a night is therefore the
deadline plus at most one task, which can be hours.

`DESIGN.md` §4.5 states the opposite: *"The supervisor sets [`ORPHANED`] on
kill, on crash, and on `--until`."* Two documents now disagree in writing, and
the code matches the weaker one.

`docs/HOST-HARDENING.md` §4a was amended to describe the real behaviour — a
"start no new task after" bound — so an operator reading the setup guide is not
misled today. That is a patch over the gap, not the gap closed.

**Done looks like** one of two decisions taken deliberately and written down:
either the supervisor gains a deadline and stamps `ORPHANED` when it passes, and
§4.5 stands; or §4.5 is amended to say the bound is between tasks, and the
budget is named as the ceiling that actually holds unattended. The second is
cheaper and defensible — a killed cell mid-REBUT wastes everything it spent —
but it should be a decision, not a drift.

---

## 68. Readiness and the scan each fetch the same mirror, once per night

**Status: done** — `SA-0055`, PR #131, merge `819cbff`. `_resolve_queue` takes
an optional `PinnedBase`; `_batch` hands down the mirror, url and base_sha that
`check_readiness` already established, and `saffron queue` — which runs no
readiness check on purpose — still derives its own.

**The first spec Saffron ran unattended.** `saffron batch` picked it up,
drove the cell, packaged it and opened the pull request: 25 minutes, $6.68
against a $15 budget, `READY_FOR_REVIEW`, `batch: DRAINED`, exit 0. It also
found a third duplicated `real_remote` call this item did not know about.

Two things the review round found afterwards are worth carrying, because both
are about a claim outrunning its evidence rather than about this fix. The
`PinnedBase` docstring said it avoided adjacent same-typed parameters and did
not — measured, `PinnedBase(mirror, base_sha, url)` type-checked cleanly and
put the URL in `base_sha`, now fixed with `kw_only`. And the narrowing at the
call site called "a passing `Readiness` carries all three" a contract, which
`Readiness` does not enforce and nothing asserted; it does now.

**Tier 3.** Found reviewing `SA-0054` (PR #123).

`check_readiness` and `_resolve_queue` both call `ensure_mirror`, `real_remote`
and `fetch_default_branch`, and `saffron batch` calls both — readiness first
(§4.4 step 1), then the scan. §4.2.1's whole argument for hoisting preflight
was that a batch does these once per run rather than once per task; it now does
them twice per run.

`Readiness` already returns `mirror`, `url` and `base_sha` precisely so a caller
need not re-derive them, and `_resolve_queue` recomputes all three anyway.

Harmless at K=1 against one repo — two mirror fetches, seconds apart, the second
a no-op fetch — which is why this is Tier 3 rather than urgent. It stops being
harmless at multi-repo, where it doubles the network cost of starting a night.

**Done looks like** `_resolve_queue` accepting the mirror, url and base_sha a
readiness check already established, rather than deriving its own. Note the
ordering constraint that makes this awkward and worth doing carefully:
readiness must run *first* (a scan that raises before the batch row exists is
what item 58's review fixed), so the seam is readiness handing its results
down, never the scan handing them up.

---

## 69. The adequacy lens reads where only running can answer, and nine tests got through

**Its table is now a scored corpus, 2026-09-09, and that closes nothing here.**
`docs/evidence/2026-09-09-lens-corpus-baseline.md` grades adequacy at **2 of the
10 declared defects it owns**, and separately verifies **8 vacuity probes** whose
named edit left the fixture's suite green — the first numbers this item's
question has ever had. Both are measurements of the gap. The mechanism is still
item **71**'s seam: a `witness` result on a real attempt is what closes this.

**Partly built, not done.** `SA-0056` (PR #135), `SA-0057` (#136) and `SA-0058`
(#139) merged 2026-09-06 and built the whole mechanism: a `mutant` beside a
claim, an applier, the `witness` gate, and the wiring. **It runs on nothing** —
`witness_gate` mutates a host path and a cell's worktree has none, so
`run_suite`'s `tree` parameter is one no production caller can supply. Item
**71** is that seam and `SA-0059` is its fix; this item is not done until a
`witness` result appears on a real attempt.

Two things the chain produced that are worth having anyway: `mutation.py`'s
applier, whose whole-file digest refuses a restore into a tree that moved, and
`run_witness`'s pre-flight probe, which tells "this repo's `tests` gate cannot
be filtered" apart from "the mutant killed its witness" and was not asked for.

**Tier 1.** Measured across one session, 2026-09-05: the batch orchestration
stack and the two pull requests after it.

**Nine tests shipped naming a behaviour they did not guard.** Each passed the
gates, passed three review lenses including the one built for this question,
and passed a human read. Every one was found by running a mutation:

| Where | The mutant that survived |
|---|---|
| `SA-0045`, `SA-0046` | reflow one `SCHEMA` line — both migration guards assert what `replace` removed |
| `SA-0048` | `exc.code not in (401, 403)` -> `not in (999,)`; 89 tests green |
| `SA-0050` | delete the breaker reset; suite green |
| `SA-0054` | `parent_branch=None`; 76/76 green — every stacked child would target `main` |
| `SA-0054` | `print(f"batch: {stop}")` -> `pass`; 76/76 green |
| item 65 | delete `sh:in`; every case decided by `sh:class` instead |
| `SA-0055` | `pinned=derived` invisible to an assertion matching only `ast.Constant` |
| `SA-0055` | delete the `readiness.ok` guard; the narrowing assert raises and exit 2 still holds |

Two of them were written by review agents, and one by the operator's own
session while fixing the others.

**This is not a diligence problem, and "review harder" cannot fix it.** A
vacuous test and a sound one are textually identical: nobody writes a test
intending it not to guard. Vacuity is not a property of the test's text — it is
a property of how the *pair* responds to perturbation, and reading examines one
object while the defect lives in the relation between two. Every row above
required simulating an execution: that `str.replace` removes all occurrences,
that a stub two files away discards `**kwargs`, that no test in 1260 captures
stdout, which SHACL constraint fires first.

`saffron/agents/prompts/review-adequacy.md` states the compromise in its own
words — *"You cannot mutate a line and watch a test fail, which is the ordinary
way a person would answer this question."* The lens was built knowing it was
substituting reading for running. This session is the evidence that the
substitution does not hold: on `SA-0055` the adequacy lens returned **0
findings** while two of seven witnesses were weak.

**This contradicts a standing decision, and the decision was reasonable.**
`docs/evidence/2026-08-25-mutation-testing-vs-a-lens.md` recommended the
prompted lens over a tool, and its arguments still hold about *tools*:
`cosmic-ray` returned 11 survivors of which 10 were one annotation mutated ten
ways, `mutmut` cannot scope below a function and cannot run over a suite that
gates its own tree. But that record's lens evidence was n=5, sonnet, one repo,
and — its own words — "a prompt written after the defect was known". It should
be read alongside this item rather than as settled.

**Done looks like** a mutation check that is *spec-guided rather than
syntactic*, which is the thing the review agents actually did and the thing
neither tool does. Saffron already holds the targets as structured data: each
`acceptance:` entry is a claim plus the witness that guards it. For each
witness, break the property the claim names and require **that named witness**
to fail — a stronger assertion than any tool's "something failed". Cost is one
scoped test run per witness, not a suite run per syntactic mutant, which is
what put mutation testing out of the window in the first place.

Note this is the granularity `revert` (§5.4) is missing rather than a
replacement for it: that gate stashes the whole patch and asks whether the new
tests test *anything*. This asks whether they test *each thing*, which is where
all nine of the above live.

**Two constraints on the design, both learned the hard way here.**

*The mutant must be minimal.* Deleting `sh:class` and `sh:in` together proved
one of them was load-bearing, not which, and shipped a vacuous test anyway. One
claim, one mutant.

*It must not become the only reader.* Everything else the review round found —
an unmeasured request shape on the token probe, a write lock held after a
designed raise, a batch row left open on Ctrl-C, three docstrings claiming more
than their code — was found by reading, and no mutation would have surfaced any
of it. The two answer different questions. Only one of them has a mechanical
answer, and it is currently being guessed at.

---

## 70. A task lost to a provider error leaves the night reporting `DRAINED`, exit 0

**Tier 1.** Measured 2026-09-06, driving `SA-0057` — the first unattended run
in this repo to lose a task to something other than its own code.

The provider erred mid-response during REBUT. The agent exited 1 with no
output, and `run_one_cell` returned an outcome in state `REBUTTING`:

```
agent: API Error: Server error mid-response. The response above may be incomplete.
agent: success in 7 turns, $0.34 (api_error)
REBUT: the rebuttal moved no commit and made no argument
SA-0057    REBUTTING
batch: DRAINED
```

Exit `0`. $3.75 spent, no pull request, and a night an unattended caller
records as clean.

**Why.** `batch.ABORT_STATES` is `GATE_ERROR`, `PREFLIGHT_FAILED`,
`RATE_LIMITED`. `REBUTTING` is in none of them, so the breaker did not count
it — the loop treated it as a state the task *earned*, reset the consecutive
count, and drained. Nothing else looks: `run_batch` reads `outcome.state`
against two sets and neither describes "the task did not finish".

That is the shape this repo keeps finding and keeps having to name again — a
control that reads as success when the work did not happen. Appendix J is the
same shape in a cell, `SA-0048`'s token probe the same shape in preflight, and
this is it in the loop.

**What is *not* broken, and should be said before anyone fixes the wrong
half.** Recovery works, unaided. `REBUTTING` is in
`reconcile.IN_FLIGHT_STATES`, so the next batch scan stamps it `ORPHANED`;
`ORPHANED` is in `scheduler.REQUEUE_STATES`, so it requeues. Measured on the
very next run — `reconcile: task 52 -> ORPHANED`, re-run, `READY_FOR_REVIEW`,
PR #136. The machine healed itself. What it did not do is *say* that it had to,
or that the first attempt's $3.75 bought nothing.

**Done looks like** an in-flight terminal state being visible in how the night
ends. Three parts, and the third is the one to argue about:

- **The stop reason.** `DRAINED` means the queue emptied. A queue that emptied
  with a task left mid-phase is not the same night, and §4.2.1's four reasons
  have no word for it. Either a fifth reason or `INFRASTRUCTURE` — and note a
  fifth touches `saffron:BatchStopReason`, `CONTEXT.md`, `saffron:BatchShape`
  and the `CHECK` on `batches.status`, all of which item 65 made agree.
- **The exit code.** `0` is "the night made it". This one did not.
- **The breaker.** Less clear-cut. Counting every in-flight outcome as an abort
  would fire the breaker on two consecutive provider blips, ending a night that
  would have recovered on its third task. Counting none of them is what
  happened here. The honest answer may be that the breaker is right and only
  the reporting is wrong — resolve this deliberately rather than by editing
  `ABORT_STATES` because it is the nearest set to hand.

**Not** re-running inside the same night. The scan is resolved once, before the
loop, and that is what makes termination structural (`saffron/batch.py`). A
retry inside the loop reintroduces the "does the queue change" question the
`for` was written to avoid.

---

## 71. `witness` is built, wired, and cannot run — the `tree` it needs does not exist in a cell

**Status: done, 2026-09-08.** The third landed: `phases/package.py`'s
re-verification now passes `acceptance=` and a `worktree.source_mutated` bound
to each package cell's own container, on both the baseline and the head suite,
so the two suites have the same shape and `suite_drift` can compare `witness`
across the two call sites. Safe to pass only because item 83 landed first: a
witness whose test does not exist at the rebased base is `unproven` there rather
than an abort.

**Prior status: two of the three below were done, 2026-09-07.** `SA-0060` (PR #148)
gave `witness_gate` the injected mutator; `SA-0061` (#150) and `SA-0062` (#154)
made `session._suite` pass `acceptance=` and a real `worktree.source_mutated`,
and `advisory_gates` now reads `contract.witness_blocking`. Measured on real
attempts: `SA-0063` and `SA-0064` each recorded `witness` as `pass` — *"2 of 2"*
and *"1 of 1 witness(es) died under their own mutant"* — in the ledger's
`gate_results`. **The third is open:** PACKAGE's re-verification
(`phases/package.py`, the `run_suite` call under `re-verify:`) passes neither
`acceptance=` nor `mutate=`, so `witness` is left out of that suite entirely and
`suite_drift` has nothing to compare it against. A by-hand fix: the package
cell's container is already in hand there.

**Tier 1.** Found reviewing `SA-0058` (PR #139), 2026-09-06. Item 69's chain
built the gate over three specs and the headline problem is unchanged: nothing
invokes it.

**The shape defect, which is the real one.** `witness_gate` takes `tree: Path`
and mutates it with host file I/O — `apply_mutant` calls `read_bytes` and
`write_bytes` on a host path. During a cell run there is no such path:
`saffron/cell/worktree.py` says it outright, *"Work happens on the volume, not
a bind mount"*. So `run_suite(..., tree=...)` is not a parameter no caller
supplies **yet**; it is one no production caller can ever supply.

`revert` solved this and the solution is sitting one file over: it takes an
injected `Reverted = Callable[[list[str]], AbstractContextManager[None]]` and
mutates *through* the container. `witness_gate` takes a raw `Path` and does the
writing itself.

`SA-0058`'s spec anticipated exactly this — *"if wiring reveals the gate needs
a different shape, that is a finding to file rather than an edit to make"* —
and the finding was not filed. A review lens raised it as a blocker and
withdrew it on the correct observation that `saffron/cell/**` is `forbidden`,
which answers whether to *edit* and not whether to *record*. This item is the
record that was owed.

**The blocking level is decided in prose and contradicted in effect.**
`contract.witness_blocking` returns `tier == "elevated"`, and its docstring
says *"whichever caller decides what an attempt does with a blocking `witness`
failure reads this"*. No caller does — grep finds only `tests/test_gates.py`.
The caller that would is `session._blocking`, which is `failure.gate not in
advisory_gates`, and `advisory_gates` adds only `size` at non-elevated tiers.
So a `witness` failure is **blocking at `standard`**, the opposite of §5.4.1
and of the function that exists to say so.

**Done looks like** three things, and the first gates the others:

- `witness_gate` taking an injected tree-mutation callable in `revert`'s shape,
  so a cell run can supply it. Needs a spec owning `saffron/gates/core/
  witness.py`.
- `session._suite` passing `tree=` and `acceptance=`, and `advisory_gates`
  gaining `witness` at non-elevated tiers — or `_blocking` consulting
  `witness_blocking`. Needs `saffron/cell/session.py`, which is `elevate_on`.
- PACKAGE's re-verification (`phases/package.py`) supplying the same, or the
  two suites differ in shape and `suite_drift` does not compare across those
  call sites, so nothing would say so.

**Not** a reason to revert `SA-0058`. `run_witness`, the pre-flight probe and
the ordering are sound and are what the fix builds on; what is missing is a
seam only a spec that owns `witness.py` and `session.py` together can cut.

**A note on how three specs produced this.** Each was scoped so its `forbidden`
list kept it honest, and the seam that needed changing was outside all three.
The chain could not have found this before `SA-0058` tried to wire it, which is
an argument for wiring early rather than last — the spec that connects a
mechanism to its caller is the one that discovers the mechanism cannot be
connected.

---

## 72. `witness` and `mutant` exist in code and in no vocabulary, and the guard for that reads the vocabulary

**Status:** **done**, by hand, 2026-09-07. `saffron:witness` is declared at
`blockingWhenElevated` and named by `SizeTierShape`; `mutant` and `witness` are
`CONTEXT.md` §4 entries and deliberately *not* vocabulary terms, because
`test_no_dead_terms` rejects a class no shape reads. The guard now reads
`saffron/gates/core/` off disk and was run against the unfixed tree, where it
names `['witness']` — and declaring the triple then made `test_shapes` name
`['witness']` too, which is `CLAUDE.md`'s promised guard firing for the first
time on the case it was written for.

**Tier 2.** Found reviewing `SA-0056` and again reviewing `SA-0058`, 2026-09-06.

Item 69's chain added a core gate and a term, and neither reached
`ontology/saffron.ttl` or `CONTEXT.md`. Measured:

```
vocabulary declares:  census committed criteria integrity revert scope secrets size
saffron/gates/core/:  census committed criteria integrity revert scope size witness
```

`secrets` is the ordinary direction — specified in the vocabulary, not yet
built. **`witness` is the first core gate in the other direction: built, and in
no vocabulary.** `mutant` is the same for a term: `CONTEXT.md` is authoritative
for meaning and does not contain the word, though `DESIGN.md` §5.4.1 introduces
it in bold as a defined term and a module is named after it.

**The guard cannot fire, and `CLAUDE.md` promises it will.** That file says a
new core gate "needs a blocking level in `saffron:CoreGateBlockingShape` … and
a test names the shape and the file when you forget."
`tests/ontology/test_shapes.py` does exactly that — over
`vocabulary.subjects(rdf:type, saffron:CoreGate)`. A gate absent from the
vocabulary is absent from that set, so the test passes and the promise is false
for precisely the case it exists to catch. `CoreGateShape`'s `sh:in` does not
reject it either, for the same reason.

Beyond the ontology: `session._blocking` treats any gate outside
`advisory_gates` as blocking at every tier, so an unvocabularied core gate
defaults to the strictest level with nothing to catch it — which is half of
item **71**.

**Why nobody did it, and why that is the real finding.** This is the third
occurrence of one shape: *the spec that introduces a term is `forbidden` from
the vocabulary that would define it.*

- item **65** — the four batch stop reasons; `ontology/` forbidden to `SA-0045`
  and to every spec above it
- **`mutant`** — flagged reviewing `SA-0056`, forbidden there and to `SA-0057`
- **`witness`** — forbidden to `SA-0057` and to `SA-0058`

Each `forbidden` list was right: a cell inventing vocabulary while implementing
against it is how a term comes to mean whatever the implementation needed. The
defect is that nothing then owns the entry, and three chains have now ended
with a term the code uses and the glossary does not have.

**A structural detail that decides who can fix it.** `ontology/` is *not* in
`policy.yaml`'s `protected` list, so a cell may edit the vocabulary — but
`CONTEXT.md` is protected, and it is *generated* from the vocabulary by
`ontology.render`. `test_generated_surfaces_are_current` fails if the two
disagree. So the two halves must move together and one of them a cell may not
touch: this is an operator's edit, or a spec that declares `ontology/**` in
`touches` and hands the render to the operator. Worth deciding once rather than
per term.

**Done looks like** `saffron:witness a saffron:CoreGate` with a blocking level
in `saffron:SizeTierShape` — it moves with the tier exactly as `size` does, and
it is the second such gate, so that shape's comment calling `size` "the one
core gate a risk tier moves" needs amending too — a `mutant` entry in
`CONTEXT.md`'s vocabulary, `uv run python -m ontology.render` re-run, and the
closed-set tests green.

**The pattern, decided.** Of the two arms — either the vocabulary stops being
`forbidden` to the spec that introduces a term, or every such spec carries a
follow-up filed when it is written rather than discovered three pull requests
later — the first is structurally unavailable, and that is measured rather than
argued. `ontology/saffron.ttl` is neither `protected` nor in
`integrity.gate_config`, so a cell may edit it; but the change is not complete
until `ontology.render` rewrites `CONTEXT.md`, which *is* `protected`, and
`protected_touch_refusal` runs at intake (`saffron/cli.py:441`). A spec
declaring the regeneration is refused before a cell starts; one omitting it
fails `scope` on an out-of-scope file, or lands a vocabulary its own derived
surfaces contradict and fails `test_generated_surfaces_are_current`. That
test's docstring already said so, and nobody had read it back to this item.

So the second arm: `docs/agents/issue-tracker.md` now requires a spec that
introduces a term to file its vocabulary follow-up, marked **by hand**, in the
same commit as the spec.

**One term left undecided, on purpose.** `notes` — item **74**'s channel,
shipped in `SA-0063`/`SA-0064` — is in no vocabulary either. It is not a gate,
and `DESIGN.md` does not bold it as a defined term the way §5.4.1 bolds
**mutant**, so declaring it here would be the vocabulary-invention the
`forbidden` lists exist to prevent. It is a candidate, not an omission; decide
it when a document defines it.

**Two brittle guards found while closing this**, both the same shape one level
down — a test pinned to the membership it checks. `test_render`'s fixture
asserted `` `revert`, `probe`. `` , naming the last core gate by hand, so
declaring a ninth broke it; it now derives the tail from `render.members`. And
`ontology.render` rewrites a closed set's enumeration but not the prose after
it, so adding `witness` left a 90-character line in a file whose longest was 87
— cosmetic, hand-rewrapped, and worth knowing before the next set grows.

---

## 73. The budget overshoot is one attempt, not one turn, and the design says 6.5%

**Tier 1.** Measured 2026-09-06 driving `SA-0059`
(`docs/evidence/2026-09-06-an-attempt-is-the-overshoot-bound.md`).

A task declaring `budget_usd: 16` spent **$26.75**, inside a night whose budget
was $22. Both ceilings were exceeded, and neither is broken in the way its
documentation implies.

`session._over_budget` is `spent < spec.budget_usd`, evaluated *between*
attempts. Nothing caps an attempt's cumulative cost: `max_budget_usd` caps a
single turn inside the cell and `max_turns` caps the count, so an attempt is
bounded by their product. Measured — an attempt admitted at $12.64 against a
$16 ceiling ran to its 110-turn limit and cost $14.11.

**`DESIGN.md` §3 cites the overshoot as "measured at 6.5% on `SA-0031`".** That
is a *turn's* overshoot and it is a true measurement of the wrong unit. The
overshoot that matters is an attempt's, and here it was 67% of the ceiling.
`CONTEXT.md`'s Task entry and item **44**'s closure inherit the same
understatement — "at most one task's overshoot" is structurally right and reads
as small.

**What is *not* wrong.** The bound holds: `run_batch` checks derived spend
before each candidate, so a night overspends by at most one task's overshoot
rather than one per task. A ten-task night does not drift ten times. The defect
is that three documents describe that bound in a way that makes it sound like a
rounding error.

**Done looks like** a decision between two answers, taken deliberately:

- **Say it accurately.** Amend §3, `CONTEXT.md` and item 44 to name the
  attempt as the unit and this run as the measurement. Cheapest, changes no
  behaviour, and leaves an unattended night able to end ~1.7x a task's ceiling
  over budget.
- **Bound it.** Refuse an attempt whose *remaining* budget is less than some
  fraction of a whole one, rather than merely greater than zero — the ceiling
  becomes a real bound at the cost of ending some tasks earlier than they need
  to end. Note this interacts with `max_attempts`: a task that would have
  passed on attempt 3 is refused into `EXHAUSTED` instead, which spends the
  money and gets nothing.

The first is not a lesser fix. §5.4's whole argument for `budget_usd` being
best-effort is that guessing a bound costs more than the overshoot; the same
argument applies here, and the honest answer may be that only the documentation
is wrong.

**Not** a finding about `SA-0059`'s size. Nine files at `elevated` exhausting
two attempts is a spec too large for one cell, which is separate and is why
`EXHAUSTED` was the honest outcome.

---

## 74. An agent has no channel to record a fact it is forbidden to fix

**Status: done, 2026-09-07** — the first shape below. `SA-0063` (PR #158) built
the channel: a `notes` artifact extracted and hashed at the moment it is
produced, carried on the outcome, rendered by `pr_body.py` under a heading that
names it as the implementer's own and unadjudicated, clipped and neutralized.
`SA-0064` (PR #160) connected the one production call that had not passed it.
The first finding to arrive through it is item **84**, in `SA-0064`'s own
`notes.json`. One caveat worth stating: no pull request body has carried a notes
section *yet* — `SA-0064` packaged under `base_sha` code that predates its own
wiring, so #160's body has none. The first task to run from a base at or after
`bb9fd74` is the measurement. Item **86** holds the rendering-side test gaps.

**Tier 1.** Found reviewing `SA-0061` (PR #150), 2026-09-06, and it is an
instruction this repo has now given twice and cannot be obeyed.

`SA-0058`'s spec said: *"if wiring reveals the gate needs a different shape,
that is a finding to file rather than an edit to make."* Nothing was filed;
that omission is item **71**. `SA-0061`'s spec therefore said it harder — *"and
this time file it, in the pull request body and in `docs/BACKLOG.md`'s
language"* — and wiring falsified four comments in files it could not touch.
One reached the operator, as a review lens's `concern`. Three did not.

**The instruction is unsatisfiable by construction.**
`saffron/report/pr_body.py` assembles a pull request body entirely from the
outcome: title, acceptance criteria, failures, the test diff, the disagreement
table, lens findings, gates, provenance. **There is no agent-authored prose
section anywhere in it.** The only text an agent writes that survives packaging
is a rebuttal — which exists only when a lens raised a blocker — and its commit
subjects, which no one reads as a findings channel.

And `docs/BACKLOG.md` is `protected` in `policy.yaml`, so "in
`docs/BACKLOG.md`'s language" cannot mean writing there either.

So a spec asking an agent to *record* something is asking for a thing the
system does not have, and every `forbidden` list makes that ask more likely:
the tighter the scope, the more an agent sees that it may not fix.

**Why this is Tier 1 rather than a nicety.** Every finding in items 70–73 came
from a review round after the fact. The agent that wired the gate is the one
that knew, at the moment it knew, which comment it had just falsified. That is
the cheapest possible moment to record it and the system throws it away.

**Done looks like** one of:

- **A findings section in the pull request body**, filled from something the
  agent writes — an artifact extracted and hashed at the moment it is produced,
  the way `plan.json` already is (§5.3), never re-read from `/work`.
- **Or a `notes` field on the outcome**, rendered by `pr_body.py` under a
  heading that says these are the agent's own and unadjudicated.

Either way it is untrusted text from a cell and must be rendered as such —
`SA-0044`'s anti-theater reasoning applies: an agent that can write prose into
a pull request body can write prose that sounds like a passing verdict. Clip
it, mark it, and never let it near a status.

**Not** a lens. §5.5's critics already produce findings and are adjudicated;
this is the *implementer* saying "I saw a thing I was told not to touch", which
is a different speaker and a different trust level.

---

## 75. Four comments the `witness` wiring falsified, and no queued spec can reach them

**Tier 3.** Found reviewing `SA-0061` (PR #150), 2026-09-06. Small, mechanical,
and filed rather than fixed because filing is the whole point of item **74**.

`SA-0061` wired `witness` into a cell run and gave it a blocking level that
agrees with `contract.witness_blocking`. Four statements written while that was
*not* true are now false:

- `saffron/gates/contract.py` — *"**Nothing reads it yet, and the thing that
  will currently disagrees.** … a `witness` failure blocks at `standard`
  today."* Both halves. `session._blocking` now reads it.
- `saffron/gates/runner.py` — *"no production caller can supply one until
  `SA-0061` wires a stub"*. `SA-0061` is merged. **Corrected 2026-09-08 (#166)**,
  out of order with the other three: that branch added `package.reverify` as a
  second production caller supplying `mutate`, and leaving a comment known to be
  false in a file the same diff edits is worse than closing a quarter of this
  item early. The other three still want the single pass below.
- `tests/test_witness_gate.py` — *"the reaches half is currently false:
  `witness` is in no `advisory_gates` set, so a failure blocks at every tier"*.
- `tests/test_witness_gate.py` — *"inserting `if failure.gate == "witness":
  return False` into `session._blocking` … fails nothing in the whole suite"*.
  Measured: it now fails `test_a_witness_failure_is_advisory_at_standard_and_
  blocking_when_elevated`.

The last is the one that misleads worst. A reviewer reading it would believe
the reaches half is still open, when `SA-0061` closed it — and that docstring
was written *to record a gap*, which makes it exactly the kind of comment
someone trusts.

**Why it is filed and not fixed.** No queued spec can touch these.
`SA-0062`'s `forbidden` list contains `saffron/gates/**` and its `touches`
does not include `tests/test_witness_gate.py`. A commit message on `SA-0061`
first asserted the opposite — that `SA-0062` "already touches
`saffron/gates/**`" — which is precisely the item-71 failure repeating: a
finding handed to something that cannot act on it is a finding lost. Corrected
there, recorded here.

**Done looks like** one spec owning `saffron/gates/contract.py`,
`saffron/gates/runner.py` and `tests/test_witness_gate.py`, correcting all four
in a pass. It is comment-only, so `type: chore` and a small ceiling; the value
is that the next reader of any of them is not misled about what is built.

**Worth folding in while there:** `run_witness`'s subset probe is now live on
every suite call for any criterion declaring a `mutant` — one extra in-cell
`tests` invocation per `_suite`, baseline and head, to reach a guaranteed
`skip` while the mutator is a stub. Zero cost for this repo today, since no
spec declares one. A target repo that does would pay it, and nothing says so.

---

## 76. A gitignore entry removes a tracked file from `lint` and `format`

Found reviewing the `structure` gate (PR #145), where the same hole was closed.
ast-grep and ruff both walk with a gitignore filter that has no notion of what
git *tracks*: one line in `.gitignore` naming a file that is committed removes it
from the gate's view while it stays in the diff, in the index, and in the merged
result. Measured on `structure` before the fix — `fail` on the planted violation,
one line added, `pass` — and ruff documents the same walk (`--no-respect-gitignore`
exists precisely because of it).

`.gitignore` is in `integrity.gate_config`, which routes an edit to a person on
every gate at once — but that is the *tracked* half only, and a later review round
found the rest. A `.gitignore` naming both a violating tracked file and itself is
never added by `git add -A`: it reaches no diff, no commit, and nothing
`git status --porcelain -uall` reports, so no policy list can ever see it.
Measured on `structure` before its second fix: violation committed, scan `pass`.
Routing is not a substitute for refusing. What is left is per-gate:

- **`lint` and `format`** should stop respecting any ignore source and name their
  own exclusions, as `structure` now does with `--no-ignore vcs` and `--globs`.
  The reason to measure rather than guess: `.venv/` and `.claude/worktrees/` are
  gitignored, and a scan that walks into either is slow and reports third-party
  code. For `structure` that cost was 0.04s against 0.27s and zero new matches;
  ruff's own walk is a separate measurement.
- **`tests`** is a different question — pytest collects through its own config —
  and should be checked rather than assumed to share the defect.

**Done looks like** a test per gate in the shape of
`test_an_ignore_file_outside_the_diff_cannot_hide_a_violation`: a tracked file
that violates, an ignore file naming it, and the gate still reporting `fail`. The
`.git` directory in that fixture is load-bearing — the walker honours a
`.gitignore` only in a tree that looks like a repository, so without one the test
passes against the unfixed gate.

---

## 77. The `tool` invariant is gated for Python, and one gate is written in shell

Found reviewing PR #145. `.saffron/rules/gate-tool-must-be-executed.yml` is
`language: python`, and `.saffron/gates/format` builds its whole contract in `sh`.
Measured: rewriting its `tool="ruff $(ruff --version | awk …)"` to
`tool="ruff 0.16.3"` — the literal §5.4 exists to forbid — leaves `structure`
reporting `pass`. Five of the six gates here are `sh` wrappers that `exec python3`
and so are covered; `format` is the one authored in shell, and a target repo
onboarding these rules may have more.

The Python side of this is now closed as far as a structural rule reaches,
including the contract serialized by hand as a single string — which is exactly
the shape `format` uses, so it is what a new Python gate copies.

**Done looks like** a `language: bash` rule in `.saffron/rules/` with its own
`invalid` snippet for `tool="<literal>"`, and `ruleDirs` already loads it. Cheap;
it is here rather than in #145 because the rule needs its own false-positive
measurement against the five wrappers and `format`'s own `case` arms.

---

## 78. `witness` mutates before `committed` runs, and the spec that built it says the opposite

**Status: done in code, open in `DESIGN.md`, 2026-09-07.** The two fixes on
PR #154 itself (`4b533d5`, `290f070`): `worktree.source_mutated` yields a reason
when the mutant's file is dirty — the shape `revert` uses, landing `witness` on
`skip` — and a failed write restores from `HEAD` before it re-raises, so a
truncation cannot outlive the failure. What is left is the third paragraph of
"done looks like": the `run_suite`-before-`committed` ordering is load-bearing
and written down nowhere. One sentence in §5.4, by hand — a gate that mutates
the tree self-guards against dirtiness, because `committed` runs after it.

Found reviewing PR #154 (`SA-0062`), 2026-09-06. The spec justifies a
`git checkout HEAD` undo with *"the agent's work is committed by the time gates
run — `committed` is what guarantees it"*. Measured: it does not.
`cell/session.py:1008` calls `run_suite`, which holds `witness`;
`committed_gate` is not called until `cell/session.py:1049`. `witness` runs
first, on a tree that may still be dirty, and the host checkpoint is later
still.

So the undo restores to `HEAD` a file the agent may have edited and not
committed. The uncommitted work is destroyed, and `committed` — the one gate
whose job is to notice a dirty tree — then sees a clean one. This is the exact
failure the sibling gate refuses to cause: `gates/core/revert.py:180` skips when
its paths are dirty, because *"no evidence about theater is worth destroying the
agent's uncommitted work and blinding the gate that would have caught it."*
`worktree.source_mutated` performs the identical restore with no such check. The
inconsistency is visible inside the new code: `_read_file` documents that it
reads the working tree, *not* `HEAD`, and the undo then restores `HEAD`.

A second shape in the same function. The write is `> path`, which truncates
before `base64 -d` produces anything, so a non-zero exit raises out of
`__enter__` over a file that is now mutated or empty. `gates/core/witness.py:79`
states the contract that forbids this — *"a raise from `__enter__` must mean
nothing was changed"* — and names this precise case as the one a host mutator
cannot reach: *"a container exec that applies the edit and then loses the
connection is exactly the shape that is not."* It adds that all three
obligations *"bind every implementation"*. Flagged in advance, in a file the
spec was forbidden to edit, and not met.

Both are latent only until a spec declares a mutant, which `SA-0062`'s own
*Out of scope* says is the next one.

**Done looks like** `source_mutated` yielding a reason when the mutant's file is
dirty — the shape `revert` already uses, landing `witness` on `skip` — and a
failed write either restoring from `HEAD` before it re-raises or going through a
temp file inside the cell, so a truncation cannot outlive the failure. Then the
ordering itself: either `committed` moves ahead of `run_suite` in `_suite`, or
`DESIGN.md` records that a gate which mutates must self-guard against dirtiness.
Right now that ordering is load-bearing and written down nowhere, which is how a
spec came to assert its opposite and pass review.

---

## 79. Three lenses read one diff and none asked what a failed write leaves behind

**Track A is delivered, 2026-09-09.** The scored corpus exists and has a kept
baseline: `docs/evidence/2026-09-09-lens-corpus-baseline.md`, eight fixtures,
twelve declared defects, `3/12` graded. The exit criterion in
`docs/superpowers/plans/2026-09-07-trusting-the-queue.md` is rewritten off this
item's one fixture onto that corpus. **This item is not thereby closed**: it asks
whether a lens owns the failure-path question, and a corpus that grades 3 of 12
is a measurement of that gap rather than a closing of it.

**Status: measured 2026-09-07, and the diagnosis below is wrong on one point.**
The known-bad diff this item asks for exists — `docs/evidence/fixtures/SA-0062/`,
scored by `harness/lens_scoring.py` and re-runnable after any lens change. First
pass, three runs, $5.70: `docs/evidence/2026-09-07-lens-scoring-first-pass.md`.

Both defects **are** raised. The truncating write was filed 3/3, by the
**contract** lens, reached through `witness.Mutated`'s own written contract; the
undo-over-uncommitted-work 2/3 by correctness. So *what does the failure path
leave behind* is not a question no lens owns — the run this item was written
from is the one where the correctness lens spent itself on a UTF-8 concern
instead, and a single sample read as a remit gap. What is real is the variance
in *which* defect a run raises and at what grade: run 1 missed the undo, run 3
filed the truncating write as a concern, run 2 filed both as blockers. The fix is
therefore aimed at that spread, not at widening a remit or adding a fourth lens,
neither of which would have changed run 1. The paragraph below proposing the
fourth lens is superseded; everything else in the item stands, including the
`blocker`-for-a-contradicted-criterion suggestion at the end, which is untested.

**Corrected 2026-09-08.** This block first read "run 1 of three would still have
shipped this pull request green", which the pass's own data contradicts: anchored
blockers per run are 1, 2, 1 — run 1's contract lens filed the truncating write
as a blocker at `worktree.py:418` — and §5.5 routes any single anchored blocker
to REBUT. All three runs would have blocked, against zero on the production run
of the same range. The number came from `dirty-restore`'s 2/3, a per-defect score
applied to a per-pull-request claim. The gap it hides is the interesting one and
is now open as item 88: 3/3 here against 0/1 in production is larger than lens
variance explains, and the frozen `gates.txt` reading `no tool reported` on all
14 lines is the leading candidate.

**Still owed by this item:** the independent review itself is not kept beside
the fixture. `recorded-findings.json` holds REVIEW's *production* output, which
is what `calibrate` needs; the independent grading survives only as declared
phrases and severities in `fixture.toml`, sourced from item 78. "With the
independent review beside it" is not yet literally true.

Found 2026-09-06, comparing REVIEW's output on PR #154 against an independent
review of the same `base..head`. REVIEW filed **0 blockers and 3 concerns** and
the task reached `READY_FOR_REVIEW` at $8.70. The independent pass over the same
range found the two defects in item **78**, both of which destroy or poison the
worktree while reporting something else, and graded both critical. Two of
REVIEW's three concerns match findings the independent pass graded *below* those
two. Neither of the two was filed at any severity.

The fact that makes this a remit gap rather than bad luck: **both were findable
by reading.** Each is named in a comment already in the tree —
`gates/core/revert.py:174` states the refusal and its reason,
`gates/core/witness.py:79` names the `__enter__` shape and says the obligation
binds every implementation. Neither needed a mutation run to surface. This is
therefore not item **69**, which is the adequacy lens reaching for an answer only
running can give. Here the answer was in the repository, and no lens was looking
for it.

§5.5's three lenses are correctness & data semantics, contract & schema, and
test adequacy, **disjoint by construction** — which is the property that makes
any single blocker route to REBUT without a vote. The cost of that choice is
that the lenses do not backstop each other, so a question no lens owns is not
covered thinly, it is invisible. *What does the failure path leave behind* is
such a question. It is not correctness of the happy path, not schema, and not
test adequacy.

Worth recording alongside it, because it is cheaper to fix and may be the same
cause: the adequacy concern that *was* filed describes `witness_gate` reporting a
false `pass` where §5.4 requires `error`, which contradicts an acceptance
criterion the same PR body renders as satisfied. §5.5 already holds that a lens
filing everything as `concern` is as much a prompting defect as one that
hallucinates; a finding contradicting a checked criterion is a candidate for
`blocker`, and nothing currently says so.

**Done looks like** PR #154's range kept as a known-bad diff with its two graded
defects and the independent review beside it — the way Appendix L measured the
critic against one — and REVIEW re-run against it after any lens change, scored
on how many of the two it raises. The fix is a remit rather than machinery:
either widened on an existing lens or given to a fourth, and measured against
that diff rather than argued. Cheap to try, and it is the item that decides
whether §9's "merge half of what it produces" is read off a number that means
anything.

---

## 80. The mutant a witness is judged by is withheld from the prompt and left in the worktree

Found writing `SA-0063`, 2026-09-06 — the first spec in this repo to declare a
mutant, so the first for which this is reachable at all.

`agents/context.py:76` hands the implementer each criterion's `witness` and
`claim` and never its `mutant`. That is deliberate and `SA-0056` gives the
reason: *"a cell is untrusted, and a mutant it authored is a mutant chosen to be
killed."* A mutant it can merely *read* is the same defect one step removed —
the test still gets written to kill that exact edit and nothing else.

**But the spec is a file in the worktree the agent is working in.** `.saffron/**`
is `forbidden`, and `forbidden` is the `scope` gate reading a diff: it says what
an agent may not *change*. It says nothing about what an agent may read, and
`cat .saffron/specs/SA-0063-*.md` is one turn.

So the withholding is a prompt-level control standing in front of the
anti-theater mechanism, and this repo's own governing line already settles what
that is worth: prompts and in-agent hooks shape behaviour; they are never the
boundary. The failure it admits is the exact one `witness` exists to refuse —
the gate reports `pass` because the test killed the mutant, over a test written
to kill that mutant and nothing else, and `run_witness`'s pre-flight probe
cannot tell those apart because from outside they are identical.

**Tier 1 as of 2026-09-07 — the evidence arrived.** `SA-0064`'s implementer
reasoned in its notes about a criterion's `mutant` field, which the prompt
withholds and which the host's own copy of that spec no longer contained: it had
read the worktree copy. Item **85** carries the measurement. The paragraph below
is kept as filed, because what it predicted is what happened.

~~Tier 3, and it moves on evidence rather than on argument.~~ No run had yet had
a mutant to read, so the likelihood was unmeasured while the consequence is
tier-1 shaped. `SA-0063` is the first run that could produce the datapoint, and
its `## Notes for the agent` asks the implementer to say so if it reads the file
— an honour system named as one, which is the measurement available before the
fix exists. **A run that shows an agent reading its own spec moves this to tier
1 without further argument.**

**Done looks like** the copy of the spec the cell can reach not carrying
`mutant:` at all. The host already reads its own authoritative copy — preflight
exports `.saffron` from the mirror at `base_sha` — so the two readers are
already distinct and only the worktree copy needs stripping. The alternative is
not placing the spec in the worktree at all, which is cleaner and costs the
agent a file it is otherwise given for context. What this needs is not code so
much as a decision about which copy is authoritative for whom; either shape is
cheap once that is settled.

---

## 81. The guard against a spec refused on its own criteria never sees 31 of 53 specs

**Status: the diagnosis is wrong, the fix landed anyway, 2026-09-08.** The
ordering claim below does not hold and did not hold when this was filed:
`scheduler.py:687` is the criterion-path check and the `depends_on` loop is at
697, so the dependency is decided *after*, not before. Measured by planting
`saffron/nowhere/invented.py` in each spec's first checklist box in turn and
reading what the queue refuses it for — of the **30** specs whose criteria
`_criteria_texts` reads from the markdown checklist, **28 report the
criterion-path refusal**. `SA-0016`, named below as a spec the guard cannot
reach, is among the 28: it is caught. The remaining two are probe-dependent
rather than a second class — `SA-0021` stops on an earlier `depends_on`
refusal, and `SA-0001` is not refused at all because its own
`forbidden: saffron/**` reads the planted token as a citation.

**This paragraph first shipped with the denominator wrong, as 32 of which 4
stopped earlier — caught in review of #166.** 32 is the count of specs carrying
a `depends_on`, which is the very coincidence the next paragraph accuses the
original item of. A corrected measurement that reproduces the error it corrects
is worth recording rather than quietly fixing: the number was reasoned from the
population the item named instead of read off the run.

The "53 specs, 31 preempted, 22 examined" figure appears to have counted specs
that carry a `depends_on` (32 of 54 today) rather than specs whose refusal
preempted the check. That is the number a reader would get by reasoning from
the ordering rather than by running it, which is what `CLAUDE.md`'s rule is
about.

What survives is the weaker complaint, and it is real:
`test_no_real_spec_is_refused_on_its_own_acceptance_criteria` reaches the
property only because of an ordering nothing pins, and it asserts something
weaker — that no refusal is a criterion-path refusal — so it goes silently
blind the day the order changes. So the item's **Done looks like** is
implemented as written:
`test_no_real_spec_names_a_criterion_path_its_touches_do_not_cover` runs
`_unmatched_criterion_path` over every spec `discover_specs` finds, with no
ledger and no refusal ordering in front of it, and refuses to pass on a corpus
it did not actually scan.

**Its first version scanned 49 of the 54, and the wording here said 54.** It
was built on `_real_corpus`, which copies `done/` alone — so the specs still
live at the top of `.saffron/specs` were outside it, which is exactly the set a
fresh defect appears in first. Caught in review of #166 and widened; the mutant
is `saffron/nowhere/invented.py` planted in `SA-0060`, which the retired-only
corpus passes blind. The discovery failures are no longer asserted empty
either: a spec that does not parse cannot be asked this question, and item 82's
validator makes exactly one such spec on the branch stacked above this one.


Found filing `SA-0063`, 2026-09-06. That spec shipped with `/work` in an
acceptance claim; `_unmatched_criterion_path` reads it as a path token, no
`touches` pattern of that spec matches it, and **a spec refused on its own
acceptance criteria never runs.**

`tests/test_scheduler.py::test_no_real_spec_is_refused_on_its_own_acceptance_criteria`
is the test written for exactly that class — its docstring names `SA-0011` and
`SA-0016` as the two it memorialises — and it passed throughout. Measured by
reintroducing the token and running both: the queue smoke test fails, that one
does not. What caught the defect was `test_saffron_queue_smoke_reproduces_this_
repos_measured_queue` asserting an exact refusal *count*, which is luck: it
fires only when the number moves, and it would have said nothing had the same
defect arrived in a spec already being refused for something else.

**The refusal ordering is what blinds it.** A `depends_on` no `MERGED` task
satisfies is decided before `_refuse` reaches the criterion-path check, and the
test supplies no ledger — deliberately, so that "nothing is filtered before
`_refuse` runs and every spec reaches it". Every spec carrying a `depends_on`
therefore refuses on the dependency and stops. Measured over the corpus the
test itself builds (whole `done/` moved to top level): **53 specs, 31 preempted,
22 examined.**

The docstring states the blindness without noticing it: *"a `depends_on` refusal
is the expected shape here, because the corpus is one long dependency chain with
no tasks behind it; a refusal on anything else is the bug."* It is the expected
shape, and it is also the thing that stops the check from ever running. So the
test grows blinder as the corpus grows: every chained spec added is one more it
cannot see.

`SA-0011` declares `depends_on: []` and is examined. `SA-0016` declares
`SA-0015` and is not — one of the two specs the test exists to remember is
outside what it can reach.

**Done looks like** the property asserted directly rather than through the queue:
`_unmatched_criterion_path` over every spec `discover_specs` finds, with no
ledger, no `gh`, and no refusal ordering in front of it. That is what the test's
name already promises, and it is one loop. Keep the queue-shaped test for what
it does cover — the ordering is what makes it blind, not the corpus, so a fixture
that satisfies every dependency would work too and would cost more to maintain
than the property is worth.

---

## 82. A mutant can pin the text a spec dictates or the text an agent writes, never both

**Status: done, 2026-09-08.** The constraint is stated where an author meets it
— `docs/agents/issue-tracker.md`'s conventions, beside the rest of the spec
format — and `intake.py` refuses at parse a mutant whose `find` text appears in
the spec's body **or in its own claim**: a claim is prompt text by the same
route, `context.witnesses_block` handing it to the implementer and
`criteria_section` to the critic.

Measured against this repo's 54 specs: one refusal, `SA-0063`, which is the
spec this item was written about and the exact mutant it describes.

**Read that number with its denominator.** Only **two** of the 54 declare a
mutant at all (`SA-0063` and `SA-0064`), so the check has fired on the only two
chances it has had. "One refusal in 54" invites a false-positive rate this
corpus cannot support. No length threshold was added, and whether one is needed
is *not* measured: the argument for going without is that a `find` must match
exactly once in its file, so a very short one is already an unusable mutant —
and that argument thins as the text gets longer. A rough count over this corpus
finds dozens of backticked identifier-shaped spans quoted verbatim in a spec
body that would each match exactly once in a file that spec's `touches` covers,
so collisions are not obviously rare. If it starts biting, the tree-aware half
belongs beside `saffron/mutation.py`, which is the module that may read the
repo — `intake.py` deliberately cannot, so it cannot tell a `find` naming text
that already exists at base (disclosing nothing, since the implementer can read
the file) from one naming text the spec invents.

**Corrected in review of #167**, along with two defects that review found: the
check compared a mutant against its *own* claim only, while `witnesses_block`
hands the implementer every claim — a sibling claim disclosed just as well and
nothing refused it; and the refusal removed a spec from `_retired_ids`' credit,
so retiring `SA-0063` to `done/` — the documented next step — would have
stranded `SA-0064`, whose parent it is. A disclosed mutant now raises
`DisclosedMutantError`, which carries the parsed spec, and a retirement still
credits a spec refused on policy rather than on shape.

One consequence worth knowing before the check meets a spec someone is waiting
on: an unparseable spec leaves the scanned set, so its dependents refuse with
*"depends_on X is not among the specs in this directory"* — a dangling
reference rather than an unmerged dependency. `SA-0064` reads that way in the
queue today. The cascade is `discover_specs`' designed shape, but the sentence
points at the wrong fact.


Found writing `SA-0064`, 2026-09-07, after `SA-0063` ran both halves of it.

A `Mutant` names exact text and applies only when `find` matches exactly once.
For a spec that builds code which does not exist yet, the operator writing the
mutant cannot know the text the agent will produce. There are two ways out and
each costs something.

**Dictate the literal.** `SA-0063` did: it mandated an exact heading and an
exact constant declaration so the mutants would match, and they did — *"2 of 2
witness(es) died under their own mutant"*, the first real `witness` verdict this
repo has produced. But the spec body **is** prompt text: `build_system_prompt`
passes it as a substituted `{spec}` value, so every literal a spec pins is a
literal the implementer reads. `SA-0063` went further and named them as
mutant-pinned in its own `## Notes for the agent`, which is the same as handing
the mutants over. Its verdict is therefore sound evidence that the *mechanism*
works and no evidence that the *tests* are honest — a test written to kill a
known mutant is the theater the gate exists to refuse.

**Or pin what the code already determines.** `SA-0064` does: a field that
exists, a parameter that exists, a predicate already written, so the natural
spelling is close to forced and no disclosure is needed to make it match. The
verdict then means something. The cost is that this only works where the change
*edits* existing code. A spec creating something new has no such text to name.

So the mechanism measures honestly where a change is an edit, and measures
itself where a change is new — which is a real limit on the answer item **69**
was built to give, and one nobody would find: the reasoning currently lives in
two spec files' `## Notes for the agent` sections and nowhere a spec author
looks.

**Measured after this was written:** the second option does not work either,
and item **83** is why — a mutant that matches at the base commit kills the task
at baseline. So as things stand an author can have an honest mutant or a
runnable spec, and 83 has to land before this item's advice is usable at all.

**Done looks like** the constraint stated where an author meets it —
`docs/agents/issue-tracker.md`'s conventions, beside the rest of the spec
format — rather than a code change. Worth pairing with one cheap validator,
though: `intake.py` could refuse at parse a mutant whose `find` text appears in
the spec body it is declared in. That is one string search beside `Mutant`'s
existing "not empty" check, and it catches exactly the mistake `SA-0063` made,
which no reviewer caught either — both lenses that read that spec's diff missed
it, and it was found only by reading the agent's own reasoning as it worked.

---

## 83. A mutant that matches at the base commit kills the task before it starts

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

---

## 84. `revert` judges a witness whose subject the spec forbids

**Status: done, 2026-09-08 (#166), against `source` rather than the
`touches` this item's *Done looks like* names.** `revert` sets aside a
criterion whose `mutant.file` is not among the source files the diff changed,
and says which in the summary. The divergence is deliberate: `touches` is what
a spec was *permitted* to change, and a spec permitted to change a file it then
left alone leaves the gate equally unable to answer, so `source` — the set
about to be reverted — is what the question is actually made of. `SA-0064`, the
case that filed this, is set aside under either rule.

**One narrowing the first implementation lacked, added in review.** `source`
excludes the repo's declared test paths wholesale, so a subject inside them is
outside `source` for every diff there will ever be: exempting it would have
given any criterion whose `mutant.file` names a test file a standing pass from
the anti-theater gate, bought with one line of frontmatter — `_argv_safe`'s
buyable-`skip` shape from the other side. A test subject says nothing about
whether the witness leans on the source being reverted, so it stays judged.

Received 2026-09-07 through the notes channel item **74** asked for — the first
finding this repo has been handed by an implementer rather than by a lens or a
person. `SA-0063` built the channel, `SA-0064` wired it, and this arrived in
`SA-0064`'s own run, in its own words:

> `revert` ran anyway, found that
> `tests/test_session.py::test_a_protected_path_alone_asks_for_notes` depended
> on none of this diff's own source files … and correctly flagged it as
> theater. … it's a workaround for what reads like a gap in `revert_gate`: it
> has no way to recognize "this witness's mutant is declared against a file
> this spec forbids me from editing" and skip itself accordingly.

`revert_gate` folds every declared acceptance witness into one question — does
this test still pass with the diff's own source reverted — and a spec can make
that question unanswerable. `SA-0064`'s criterion 2 was a deliberate coverage
backfill for a predicate in `saffron/cell/session.py`, a file that spec
`forbids`; only `saffron/phases/package.py` was in `touches`. The new test
therefore depended on none of the diff's source, which is what `revert` calls
theater, and here was the point.

**The workaround shipped.** The test now also drives a real `package.package()`
against a real git remote so that it depends on both, which satisfies the gate
and leaves a test of one boolean predicate standing up a git remote to check it.
That cost is in #160's diff and is the honest reason to fix this rather than
argue it.

The implementer bounds it itself: *"I don't think this generalizes beyond specs
that split a claim's verifier (mutant) from its enforcement site (`touches`) the
way this one does."* Narrow, then — but this is the second gate in two days to
answer `fail`/`error` where the spec's own scope made the question unanswerable,
and item **83** is the first. Same class: a gate that cannot say *unproven*
says something worse.

**Done looks like** `revert` skipping a witness whose subject lies outside the
spec's `touches`, with a summary saying so. "This diff could not have made that
test pass, because the spec did not let it near the code" is unproven, not
theater, and `skip` is the status that already means it.

---

## 85. The host runs one copy of a spec and the cell reads another

**Status: done, 2026-09-08 (#166).** `spec_drift` compares the two copies
the run already holds and reports through `Preflight`. It never refuses: an
operator iterating on a spec is exactly what produced this. Absence is silent —
the first version reported a spec with no copy at base, which is the ordinary
shape of an attended run and the *absence* of the hazard rather than an
instance of it, and it would have printed on nearly every run.

Measured 2026-09-07, on `SA-0064`'s second run.

`saffron cell <path>` loads the spec with `load_spec(args.spec)` — the file the
operator names, on disk, now. The cell's worktree is built from the mirror at
`base_sha`, so it carries whatever `.saffron/specs/` holds on the default
branch. Nothing compares them.

They differed on this run, and it showed. The host's copy had criterion 2's
mutant removed (item **83**, an hour earlier); `main`'s copy still carried it.
The implementer's notes then reasoned about *"Criterion 2's spec-declared mutant
lives in `saffron/cell/session.py`"* — a field `agents/context.py` withholds
from the prompt by construction, and one the host's own copy no longer had. The
agent was working from a contract the host was not judging it against.

This is also the measurement item **80** asked for and it is what moves that
item to tier 1: the prompt-level withholding of `mutant` is defeated by the
worktree copy, and now demonstrably rather than in principle.

**Done looks like** attended mode reporting the difference, or refusing it. Both
copies are already in hand at preflight — `spec_sha` is computed host-side and
`.saffron` is exported from `base_sha` regardless — so the check is a comparison
of two strings the run already holds, not new machinery. Refusing may be too
strong for an operator deliberately iterating on a spec, which is exactly what
produced this; naming it in the preflight line is not.

---

## 86. The notes channel's two rendering-side safety properties are unwitnessed

**Still unwritten, 2026-09-09, and the corpus now says so with a number.** Both
properties are `SA-0063`'s declared defects, and the baseline pass graded
**neither** — every finding that fixture produced anchored in
`saffron/cell/session.py` and `saffron/phases/package.py`, none in
`saffron/report/pr_body.py` or `tests/test_report.py`. So no lens reached them,
which is a measured miss rather than the assumed one. The two assertions are
still owed.

Found reviewing `SA-0064` (#160), 2026-09-07, by mutation rather than by
reading. Both are gaps in what the suite *proves*, not live defects — I
confirmed each behaviour holds today by hand. Both live in
`tests/test_report.py`, which `SA-0063` and `SA-0064` each had outside their
`touches`, so neither run could have closed them.

**Neutralization on the notes path is asserted nowhere.** `_notes` does defang
an `@mention` and a `Fixes #12` — measured: `_notes("ping @maintainer and Fixes
#12")` comes back with zero-width joiners in both. But
`test_notes_cannot_move_a_status_or_a_gate_result` feeds exactly that string in
and then asserts only that the *head* of the body is unchanged. It never looks
inside the notes section, so deleting the `neutralize` call on this path leaves
the suite green. This is the one place a cell's output causes an effect outside
the boundary without executing (`pr_body.neutralize`'s own docstring), and the
notes are a new way into it.

**`SA-0064`'s criterion 4 does not witness its own claim.** It reads *"a task
that recorded nothing packages the body it packages today"* and names
`test_the_pr_body_reports_the_effective_tier_not_the_specs_declared_one` as the
witness, with `preserves: true`. Measured at `0631855`: make `_notes` render
a heading over
empty notes and that test stays green — the only test that turns red is
`test_notes_cannot_move_a_status_or_a_gate_result`, and it catches it
incidentally, through an exact-prefix comparison aimed at something else.

Watch the mutation itself: `        return ""` appears seven times in
`pr_body.py` and only line 390 is `_notes`'s, so a first-occurrence replace
lands in an unrelated function and reports a green suite that means nothing.
It did, on the first attempt at this measurement — the number was right and
the thing measured was not. A
`preserves` witness is a keep-this-green contract rather than a real witness, so
this is defensible as written; the property is nonetheless guarded by accident.

That second half is a spec-authoring fault, not an implementer's, and it
generalises: a `preserves` witness is only as good as the operator's judgement
that the named test would actually notice, and nothing checks that judgement.
`criteria` confirms the test passed at both ends, which it would whether or not
it has anything to do with the claim.

**Done looks like** two assertions in `tests/test_report.py` — that a mention
and an issue-closing reference are defanged *inside* the rendered notes section,
and that empty notes render no heading — plus, separately worth deciding,
whether `preserves` should require the operator to name what would falsify it
the way `mutant` does for the other direction. The first is half an hour; the
second is a design question and probably belongs beside item **82**.

---

## 87. Two prose claims about the core gate set went stale where no guard reaches

Found reviewing item **72**'s own branch (#164), 2026-09-07. Neither is a live
defect — both are sentences that were true when written and are now false, in
the two places item 72's new guard cannot see. That guard compares
`saffron/gates/core/*.py` against `ontology/saffron.ttl`; it reads no prose.

`DESIGN.md` §7's risk table says *"The seven core gates never execute repo
code — most read the diff, but `census` and `criteria` read other gates' results
instead; any core gate that wants to *run* something belongs on the repo side"*.
Nine now, and the second half is the larger error: `revert` and `witness` both
invoke the repo's declared `tests` gate (§5.4.1 calls `witness` *"`revert`'s
exception, not a new one"*), so the row's own rule reads as violated by two of
the gates it governs rather than as the boundary it is. The distinction the row
wants is *invokes a declared gate* versus *knows a tool*, which is §2.1's actual
line.

`saffron/gates/contract.py:113` still carries **"Nothing reads it yet, and the
thing that will currently disagrees."** in `witness_blocking`'s docstring.
`session.py:998` reads it — item **71**'s reconciliation landed and left the
paragraph describing the world before it. This one costs something today: item
72's commit message and `SizeTierShape`'s comment both cite
`contract.witness_blocking` as the authority for `witness`'s blocking level, and
a reader who follows the citation lands on a paragraph saying nothing reads it.

**Done looks like** both sentences corrected by hand — `DESIGN.md` is
`protected` and its §7 table is not generated, so neither is a cell's to touch.
Worth deciding separately whether the `revert`/`witness` distinction deserves a
`CONTEXT.md` §4 line of its own, since three files now state it in three
wordings. Half an hour.

---

## 88. The scoring harness reads a lens three times as harsh as production, and the fixture is a suspect

**Status: the suspect is eliminated and the gap is unchanged, 2026-09-08**
(`docs/evidence/2026-09-08-lens-scoring-second-pass.md`, $4.84). With the tools
back in `gates.txt` and every other input held, anchored blockers per run are
1, 1, 2 against the first pass's 1, 2, 1 — four either way, every run of both
routing to REBUT against production's zero. Naming the tools moved the count by
**zero**. What is left is the two candidates below that the pass does not
narrow, and the item closes on its own fallback: the harness's absolute numbers
steer nothing, its differences over one fixture do. The `tool` column landed
anyway (`gate_results`, 2026-09-08) so the next fixture needs no splice.

Two things the pass found that the item did not predict, both in the plan now:
the per-defect scores *did* move — `dirty-restore` 2/3 → 1/3, `truncating-write`
3/3 → 2/3 seen — on an input change with no mechanism to make either defect
harder to see, so item 79's exit criterion is written on the noisier of the two
numbers; and production's side of the comparison is **n=1**, which no amount of
work on the harness fixes.

**Tier 1**, directly under 79 — it is 79's own measuring instrument, and 79's
exit criterion is written against an absolute this item puts in doubt.
**Found 2026-09-07**, in the first lens-scoring pass
(`docs/evidence/2026-09-07-lens-scoring-first-pass.md`). Over PR #154's exact
range, the harness's three runs filed anchored blockers 1, 2, 1 — every run
would have routed to REBUT (§5.5). The production run over the same range filed
**zero** blockers and three concerns, and reached `READY_FOR_REVIEW`. Same diff,
same three lenses, same prompts.

A harness that reads a lens as much harsher than production cannot score a
prompt change: the number it moves is not the number the night produces. This
is the harness's own version of item 79, and it sits under Track A rather than
Track C.

Three candidates, in the order they are worth eliminating:

**The frozen `gates.txt`.** All 14 lines read `no tool reported`, because
`gate_results` has no `tool` column to rebuild them from. §5.4 makes `tool`
exactly what separates a gate that ran from one that never did, and
`review.gate_summary` exists so "a critic told a gate passed should be able to
see which did". A lens told fourteen gates ran and not one named a tool has
structural reason to distrust them and dig harder — a bias in precisely the
direction observed. Cheapest to test and the leading suspect.

*Corrected and repaired 2026-09-08.* Production named **7 of 14**, not 14: six
of the other seven are host-side core gates that execute nothing and report no
tool there too, and `witness` inherits the `tests` tool but skipped a spec that
declares no mutants — so the gap was 7 against 0. `gate_results` now carries a `tool`
column, but the 14 rows predate it and a nullable column is null for every one —
so the fixture was repaired instead, from the tools in the same run's
`baseline.json`, by `docs/evidence/scripts/2026-09-08-sa0062-gate-tools.py`.

**Budget and turns.** The original had $3.30 and 90 turns; the pass gave $4.00
and 30. No lens came near either ceiling in either, so this is unlikely, but it
is not held constant and the record says so. *Still open after the second pass,
which held it constant with the first rather than matching production — moving
two inputs at once would have made that pass unreadable.*

**Genuine run-to-run variance**, of which the pass has n=3 over one fixture.
*The surviving candidate, and the second pass sharpened it: the harness now has
n=3 twice and production still has n=1. A single production run that filed zero
is not evidence that production files zero reliably, and no work on the harness
can settle that — only running the range through production again would.*

**Done looks like** a `tool` column on `gate_results`, or a fixture whose
`gates.txt` is captured at review time rather than rebuilt from the ledger —
then one more pass, and the blocker count compared against production's zero.
Until that is settled, the harness's absolute numbers steer nothing; only its
*differences* between two prompts over the same fixture do, which is what Track
C actually needs. Worth saying in the plan, because item 79's exit criterion is
written against an absolute. *Done as written, 2026-09-08: the column, the
repaired fixture and the pass. The comparison came back unchanged, so the
closing sentence is the operative one rather than the fallback it was written
as.*

---

## 89. `DIFF_FLAGS` pins less of the diff's shape than its own comment claims

Found building the lens-corpus harness's byte-identity check (2026-09-08),
which had to reproduce `export_patch`'s output on a host it does not control
and, in doing so, needed three flags `saffron/cell/worktree.py` does not set.

`worktree.py:127`'s comment over `DIFF_FLAGS` says it pins "the shape of every
diff the host reads" against config the agent can write inside its own
worktree (§2). The five flags at `worktree.py:131-144` back that for
`diff.srcPrefix`/`dstPrefix`/`noprefix`/`mnemonicPrefix`, `diff.external`,
`diff.textconv` and rename detection — but not for `core.abbrev`,
`diff.context` or `diff.algorithm`, none of which any flag or `-c` override
here touches. An agent that runs `git config diff.context 40` (or
`core.abbrev`, or `diff.algorithm patience`) before its own commits changes
`export_patch`'s bytes with nothing in this module noticing, which is a
narrower guarantee than the comment states.

**Severity is low, and worth saying plainly rather than implying.**
`core.abbrev` and `diff.algorithm` are cosmetic here: nothing host-side parses
an `index` line's hash or cares which algorithm chose a hunk boundary.
`diff.context` has the one real effect — `saffron/agents/findings.py`'s
`parse_diff` puts every line a hunk's declared range covers into
`hunk_lines` (`findings.py:79`), context lines included, and `_is_anchored`
(`findings.py:135`) tries `hunk_lines` first. A wider context widens what a
finding may anchor to. The blast radius is capped two ways: `facts.tokens`,
the second anchoring target, is collected only from `+`/`-` lines
(`_consume_hunk`, `findings.py:102-110`), which no context setting moves; and
the merged commit still comes from git objects, never from the archived
`patch.diff` — nothing about this lets unreviewed code into the tree it did
not already reach some other way. What it can do is nudge a finding onto a
line it would not otherwise have reached, and leave the archived patch a
record of what an agent chose to show rather than what the range actually
contains.

`harness/recovery.py`'s `pinned_diff` is the worked example: reproducing a
recorded patch on an arbitrary host needed `--abbrev=7 --unified=3
--diff-algorithm=myers` on top of `DIFF_FLAGS` and its two `-c` overrides, all
three measured against every one of this repo's own recorded patches rather
than assumed.

**Done looks like** `DIFF_FLAGS` (or `_git`'s `-c` overrides) gaining the same
three pins `pinned_diff` already carries — an explicit `--unified=<n>` matters
most, since it is the one with anchoring consequences; `--abbrev`/
`--diff-algorithm` close the comment's claim rather than a live hazard. Cite
`harness/recovery.py`'s `pinned_diff` for the exact flags and the measurement
behind each.

---

## 90. `_drive_cell` has doubled since it was born and is over half its module

**Tier 3 — real, not urgent.** Nothing here fails at 03:00 and the function is
green. **Found 2026-09-08**, by static analysis and not by a run: this is a
measurement rather than a gap a live run exposed, and it is filed anyway
because the measurement is monotonic and the file it concerns is the one the
rest of the repo moves underneath.

`_drive_cell` (`saffron/cell/session.py:960`) is **1100 lines** — 53% of its
2059-line module, and 3.1x the next-longest function under `saffron/`
(`package`, 358). It has never been shorter:

| date | commit | module | `_drive_cell` |
|---|---|---|---|
| 2026-08-22 | `851836a` | 916 | 513 (born) |
| 2026-08-25 | `3604f31` | 1154 | 678 |
| 2026-08-31 | `0301518` | 1358 | 772 |
| 2026-09-03 | `2b1afda` | 1812 | 1082 |
| 2026-09-08 | `ab8c9d4` | 2059 | 1100 |

Seventeen days, 2.1x, every sample up. `session.py` is also the most-churned
file here — **93 of the 348 commits** touching `saffron/`, 1.8x the next
(`cli.py`, 53).

What makes it worth filing rather than noting: the function inlines the phase
sequence — preflight, `cell_up`, the baseline suite, the plan checkpoint,
IMPLEMENT, salvage, the repair loop, REVIEW, REBUT, teardown — while
`saffron/phases/` exists as the home for exactly that, and `implement.py`,
`review.py` and `rebut.py` are each already extracted. The seam is established
and this is what did not go through it.

Two costs are already on the record. **The distance is being paid in comments:**
`current_tier` and `advisory_gates` are bound at `:1113` and read at `:2016` —
903 lines apart — and the gap needs the seven-line comment at `:1105-1112`
arguing the path between them is unreachable. `ty` passes, but a checker
configured outside this repo reports both as possibly-unbound, which is what a
reader who has not found that comment sees. **And a patch's shelf life is
measured against this file:** item 5 records `SA-0003`'s patch no longer
applying because "three hours of commits moved `session.py` underneath it". The
most-churned file is the one a packaged patch is likeliest to be invalidated by,
and it is 27% of all movement under `saffron/`.

**Done looks like** `_drive_cell` reading as the phase sequence it drives, with
the phases that have no module of their own living beside `implement.py`,
`review.py` and `rebut.py`. Not a line count: the test is whether one phase can
be read without the 900 lines around it, and whether `current_tier`'s binding
and its use fit on one screen. Worth doing by hand rather than through a cell —
it is a pure refactor of the most load-bearing function in the control plane,
the suite guarding it is 1562 tests, and a cell's own diff here would be the
hardest this repo has asked a critic to read.

## 91. The 2026-09-09 mutation spike is evidence that lives nowhere `docs/evidence/` can see

**Done, 2026-09-09** — `docs/evidence/2026-09-09-adequacy-probe-spike.md`. The
`f9f007c4` pair reproduces to the recorded `1250 passed` exactly; the
`f76931df`/`91f56c69` pair is transcribed from the review reproduction, not
re-run, and the file says so.

**Tier 3 — real, not urgent.** Nothing fails; the risk is that a number
outlives the record that justified it.

Four mutations the adequacy lens named in pass 1 were applied at their fixture
heads and the suite run: `pr_body.py:391` at `f76931df` (1502 passed),
`batch.py:72` at `91f56c69` (1292 passed), and two at `f9f007c4` (1250 passed
each). All four stayed green, which is what makes them verified-real vacuities
rather than plausible ones, and they are the whole evidential basis for
`docs/superpowers/specs/2026-09-09-mutation-verified-capability-design.md`.

At the time this item was filed, that record existed only in a session ledger
under a scratch directory — a spec arguing from a measurement nobody can
re-read is the shape item 87 is about, one level out. Two of the four had
already been independently reproduced during review (`f76931df` and
`91f56c69`, both to the exact figure); the `f9f007c4` pair had been reproduced
by nobody.

The fix was small: land the four rows, their commands and outputs where any
exist, under `docs/evidence/`, reproducing the two nobody had re-run. Done, in
the "Done" line above — see `docs/evidence/2026-09-09-adequacy-probe-spike.md`
for the full per-row provenance, including which two remain transcribed from
the review reproduction rather than re-run for that file. It was a
**precondition of the plan** that spec leads to, not of the spec itself —
filed here because a precondition recorded only inside the document that
depends on it is a claim, not a record.

## 92. Three things the corpus's probe path ships knowing, recorded only in scratch

**Tier 3 — real, not urgent.** All three were found by review on the branch that
built the vacuity-probe path, judged not to block it, and written down in that
branch's SDD workspace — which is git-ignored session scratch. Item 91's own
body makes the argument: a thing recorded only inside the document that depends
on it is a claim, not a record. This is that argument applied to itself.

1. **No test drives the real `CellExecutor` path.** Every driver test replaces
   `run_gate`, so the contract is pinned but the exec is not. One fixture has
   since run end to end against a real cell, which is evidence rather than
   coverage; a `-m cell` test is the durable version.
2. **`tests/test_corpus.py` covers two things** — `harness/corpus.py`'s
   predicate and a dated evidence driver — at ~750 lines. A
   `tests/test_lens_corpus_driver.py` split is mechanical.
3. **`TEST_PATHS = ("tests/",)` is this repo's layout, hardcoded in the
   driver.** `check_probe` requires the argument so it cannot be silently
   absent, and the prefixes are normalised, so the guard holds for the eight
   shipped fixtures. But `--fixtures` points wherever it is told, and
   `src/tests/test_x.py` would pass it. `policy.integrity.test_paths` is the
   right source and is globs (`tests/**`) where this compares prefixes, so it
   is a translation rather than a substitution.

Also open and *not* in this list because it is already in the design spec: the
in-cell suite runs 5.5x faster than the same tree on the host, and nobody has
explained it. `probes.json` now records the gate's tool, collected count and
summary per verdict, so the next pass can say whether the suite that answered
was the whole one.

---

## 93. Requiring a probe may have cost the adequacy lens recall, and nothing measured it

**Tier 1 — it bears on whether the corpus's own number means anything.** The
adequacy prompt gained a required `probe` field
(`saffron/agents/prompts/review-adequacy.md`) between pass 1 and the baseline
pass. Adequacy owns **10 of the corpus's 12** declared defects, and it went
**3/10 to 2/10** across that change — both defects in the difference are
adequacy-owned (`SA-0063`'s pair). n=1 each side, so the drop is neither noise
nor a measured regression: it is *confounded*, and
`docs/evidence/2026-09-09-lens-corpus-baseline.md` claims neither reading.

What makes it answerable: pass 1's runs are on disk, but re-scoring them cannot
help — the prompt changes the *runs*, not the predicate that reads them. It needs
a pass under each prompt at the same `--runs`, or a higher `--runs` under the
current one to establish the spread first. The second is cheaper and comes first:
at `--runs 1` over eight fixtures nobody knows this metric's resolution, and two
passes disagreeing by 1 of 12 is all the evidence there is.

Until then, no prompt change should be read off a single corpus pass — the same
instruction item 88 left on the one-fixture harness, now owed by its replacement.

---

## 94. A probe's baseline failures are subtracted and then discarded

**Tier 1 — it bears on whether a `survived` verdict means anything.** Filed as
tier 3 on 2026-09-09 and moved the same day, when the measurement below turned it
from an auditability gap into a correctness one.

**The cell's baseline can be red for reasons the host is not, and nothing records
which.** `SA-0063`'s head (`f76931df`) runs **`1502 passed`** on the host — run
directly, in a detached worktree, 107.31s — where the cell reports `1 failed,
1499 passed, 2 skipped` at the same 1502 collected. So one failure and two skips
exist only in the cell, and the failure's identity is written nowhere: not in
`gates.txt`, which carries the summary line only, and not in `probes.json`, which
keeps only what survives the subtraction. Every `survived` in the corpus is
computed against a baseline of that kind, and the two symptoms sit beside the
unexplained 5.7x in the same place.
`check_probe` holds the baseline `GateResult` to subtract from, and
`probes.json` persists only what survives the subtraction (`failures`). So a
`survived` over a head whose suite was already red cannot be checked by anyone
reading the record.

Measured at the baseline pass: the subtraction cancels that failure and both
probes record `failures: []`, which is correct — no *new* failure. But whether it
is in the very test that would have caught the mutation is undecidable from the
record, and if it is, the cancellation masks a kill. That is **2 of the
baseline's 8 verified vacuities**, and **no re-run can settle those two**: a probe
is authored by the lens per run — `SA-0054`'s re-run named two *different* edits —
so re-running yields different probes rather than an audit of these.

Done looks like: `ProbeResult` carries the baseline's failure identities beside
the new ones, and `probes.json` writes them. Additive, and the value is already
in `check_probe`'s hand — the same shape as the `tool`/`collected`/`summary`
fields, which exist because a verdict that keeps nothing about the suite that
answered it cannot be re-read. **Land it before the next pass, not before pass
3**: item 93 needs a further pass to establish this metric's resolution, and that
pass should not be spent producing more verdicts nobody can audit. Adding the
field cannot retroactively populate a pass already run, so this baseline's two
stay unauditable whatever happens here — the value is entirely forward, which is
the argument for landing it early rather than the argument for deferring it.

Worth pairing with it: the cell's own baseline summary line, and an explanation
for the two cell-only skips. A `survived` over a baseline that skipped the
relevant test is the same defect wearing a different hat.

---

## What is *not* here, deliberately

DIAGNOSE and `SCOPE_REVIEW`, the scheduler's conflict sets and stacking, `saffron
gc`, multi-repo, the merge train, and the `secrets` gate. All are v1+ by
`DESIGN.md` §9's own build order, and none of them is blocked by anything
above. `size` left this list on 2026-08-25: it is built and unwired, which is
item 17. `revert` left it with `SA-0044`: it is built and wired into `_suite`,
which is item 49. §4.2's own argument applies: at a two-deep queue they
arbitrate contention that never arrives.
