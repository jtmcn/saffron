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
  rewrites a bare `\r` to `\n` *before any gate runs* — so the line arrived
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

---

## What is *not* here, deliberately

DIAGNOSE and `SCOPE_REVIEW`, the scheduler's conflict sets and stacking, `saffron
gc`, multi-repo, the merge train, and the `size`/`secrets`/`revert` gates. All are
v1+ by `DESIGN.md` §9's own build order, and none of them is blocked by anything
above. §4.2's own argument applies: at a two-deep queue they arbitrate contention
that never arrives.
