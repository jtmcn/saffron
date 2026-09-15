---
id: 1
title: '`integrity` needs splitting, not rewriting — and half of it may not be a core gate'
status: done
tier: null
closed: 2026-08-22
by_hand: true
specs: [SA-0004]
prs: [6]
commits: [596f96f]
cites: [§2.1, §5.4]
related: [2, 9]
---

## Problem

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

## Done looks like

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

## Record

**Status:** **done**, by hand, in PR #6 (merge `596f96f`) — not by the factory
patch this item was written about. That patch was reviewed and **rejected**, and
stayed in the batch tree; what shipped keeps its §2.1 split and its suppression
detection and replaces the rest. Nothing below needs picking up. Read it for
what the shipped gate is answering and why, not as work outstanding.

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
