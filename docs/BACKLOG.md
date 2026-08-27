# Backlog — what v0.5 left, and why each thing matters

Written at the close of v0.5 (`DESIGN.md` rev 14). Every item here is a gap a
live run exposed or a decision deliberately deferred — none is speculation about
what might be nice. Each says what "done" looks like, so it can be picked up
cold.

Ordered by what would hurt most on the first unattended night.

**Where the evidence lives.** `DESIGN.md` Appendices I–L narrate what building
and running v0.5 found. The per-task briefs and implementation reports were
written under `.superpowers/`, which is gitignored and does **not** survive a
merge — anything from them worth keeping was moved into the appendices or into
`docs/superpowers/plans/2026-08-19-v0.5-findings.md` before this was written.

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

**Status:** open. Found by `SA-0011`, implemented by hand on
`joel/sa-0011-witnesses`; the two lines that unbreak it are in that branch, the
fakes themselves are not fixed.

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
an unrelated suite three tasks later. Roughly twenty lines. While there: drop
`tests/test_package.py` from `SA-0011`'s `touches`, where it is declared only
because of this.

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

## What is *not* here, deliberately

DIAGNOSE and `SCOPE_REVIEW`, the scheduler's conflict sets and stacking, `saffron
gc`, multi-repo, the merge train, and the `secrets`/`revert` gates. All are
v1+ by `DESIGN.md` §9's own build order, and none of them is blocked by anything
above. `size` left this list on 2026-08-25: it is built and unwired, which is
item 17. §4.2's own argument applies: at a two-deep queue they arbitrate contention
that never arrives.
