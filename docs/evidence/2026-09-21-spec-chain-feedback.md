# Spec chain feedback, 2026-09-21

The first runs of the `create-saffron-spec` skill. Each section is one spec.
Durations and token counts come from the agents' own completion reports.

## SA-0118, item 103

Branch `joel/spec-diff-attribute-pins`. Item 89's remainder was folded in at
the start and cut after the first review.

### Rounds and cost

| Step | Who | Time | Tokens |
|---|---|---|---|
| Probes before the brief | delegate | about 20 min | not counted |
| Draft | `spec-writer` | 16.2 min | 170k |
| Operator decisions and pre-flight | delegate | about 15 min | not counted |
| First review | `spec-reviewer` | 6.9 min | 102k |
| Revision | delegate, by hand | about 15 min | not counted |
| Second review | `spec-reviewer` | 7.4 min | 117k |

Both revisions were made by hand. A writer revision costs 12 to 22 minutes,
and each finding here was a note edit or a criterion swap.

### Before the first review

The delegate probed the mechanism on both gits before writing the brief. The
brief then carried a measured arm, and the writer asked no design question
about it. The writer returned four questions. Two were settled by running the
writer's own probes on git 2.39.5, which the writer could not run.

- **Ceilings below history.** Pre-flight 7 caught it. `driver.py check` refused
  6 dollars and 40 turns against SA-0101, the only same-shape row at the time.
- **A criterion with no failing witness.** The writer kept `changed_files` in
  scope under a `preserves` guard. Neither vector moves its listing, so the
  delegate cut it. Pre-flight 1 would have raised it, and the writer raised it
  first.

### First review: no blocker, four concerns

| Finding | Class | Check that should have caught it |
|---|---|---|
| The object-format half of criterion 3 is not driven on the cell's git | A witness drives one member of a set | Pre-flight 1. The delegate measured that 2.39.5 ignores the key and did not carry that to the witness. |
| Four existing pin witnesses go vacuous, since the fresh dir never reads `.git/config` | A change breaking a live check or test | Pre-flight 6. No check covers it. `enumerators` only reads directory listings. |
| A second test seam raises on any `workdir` but `/work` | A name the spec leans on | Pre-flight 3. The brief named one seam and not the other. |
| Budget margin under the largest review and REBUT row | Size or ceilings | Pre-flight 7. `driver.py check` passed it, since it reports a concern only below the row. |

The second finding pushed the estimate to about 205 lines. That is inside the
100-line margin, so item 89's remainder was cut to its own spec.

### Second review: no blocker, one concern

| Finding | Class | Check that should have caught it |
|---|---|---|
| The estimate is about 190 of 300 and `size` blocks at `elevated` | Size or ceilings | Pre-flight 7. Raised again after the cut, answered with a note. |
| The global config file sat inside the repo, so `add -A` commits it | An arrangement argued rather than run | Pre-flight 10 |
| The export path's replace-ref witness passes without its pin | A change breaking a live check or test | Pre-flight 6. Same gap as the first review's second finding. |
| A pin spelled in the script makes its mutant's `find` match twice | A witness drives one member of a set | Pre-flight 1 |

### What the next run should change

1. **Pre-flight 6 needs a check for rerouted reads.** When a change moves a
   read to a new source, grep every witness that plants state in the old one.
   Both reviews found this class, and no command looks for it.
2. **Probes isolate `XDG_CONFIG_HOME` as well as `HOME`.** With `HOME` moved,
   `git config --global` wrote the operator's own `~/.config/git/config`. It
   left an `init.templateDir` there and skewed the next probe on the host.
3. **A second worktree cannot be committed from this session.** The isolation
   guard refuses git outside the session's own worktree, and a subagent sent
   there inherits the refusal. Parallel chains need the operator to commit.

## SA-0120, item b-2750d5's second half

Branch `joel/specs-diff-pins-and-probe-rules`, which also carries SA-0118 and
SA-0119 for one pull request. It depends on SA-0119.

### Rounds and cost

| Step | Who | Time | Tokens |
|---|---|---|---|
| Draft, with a prototype of the change | `spec-writer` | 21.0 min | 216k |
| Two by-hand records and pre-flight | delegate | about 10 min | not counted |
| First review | `spec-reviewer` | 9.4 min | 154k |
| Revision | delegate, by hand | about 15 min | not counted |
| Second review | `spec-reviewer` | 6.4 min | 100k |
| Revision | delegate, by hand | about 10 min | not counted |

The prototype counted 351 changed lines against the `feature` ceiling of 600,
so there was no split. It reused `witness_gate` unchanged.

### First review: no blocker, six concerns

| Finding | Class | Check that should have caught it |
|---|---|---|
| A mutator raise and a `tests` gate `error` share one status | Two criteria disagreeing on one input | Pre-flight 2 |
| REBUT's "the tests stayed green" overstates one witness | A change breaking a live check or test | Pre-flight 6 |
| The adequacy drop rate counts host-filed findings | A change breaking a live check or test | Pre-flight 6 |
| Lens-scoring fixtures would credit adequacy | A change breaking a live check or test | Pre-flight 6 |
| A function the parent spec names in no criterion | A name the spec leans on that the base lacks | Pre-flight 3 |
| Two wrong implementations the witness setup allowed | An arrangement argued rather than run | Pre-flight 10 |

Three of the six are the class both earlier specs' reviews also found: a
reader downstream of the change that nobody listed.

### Second review: no blocker, two concerns

| Finding | Class | Check that should have caught it |
|---|---|---|
| The anchoring survivor sat on a hunk line, so a blind reader passed | An arrangement argued rather than run | Pre-flight 10 |
| A `run_tests` raise was invisible to a `mutate` wrapper | Two criteria disagreeing on one input | Pre-flight 2 |

### What the next run should change

1. **Pre-flight 6 lists every reader of what the change writes.** It found
   three readers here and two witnesses on SA-0118. A command that lists the
   readers of a file or field the change writes would catch this class.
2. **A child spec names only what the parent's criteria promise.** Anything
   else the parent's cell may not build.

## SA-0121, SA-0122 and b-ce93aa

Branch `joel/specs-probe-children-and-89`, stacked on the branch above. Three
writers drafted in one checkout at once. Each wrote only its own spec and
record, and the delegate wrote the shared smoke-test paragraph after all three
returned.

### Rounds and cost

| Step | Who | Time | Tokens |
|---|---|---|---|
| SA-0121 draft, with a prototype | `spec-writer` | 23.3 min | 153k |
| SA-0122 draft, with a prototype | `spec-writer` | 12.3 min | 153k |
| b-ce93aa, a by-hand test in place of a spec | `spec-writer` | 16.3 min | 92k |
| SA-0121 first and second review | `spec-reviewer` | 3.5 and 3.8 min | 81k and 68k |
| SA-0122 first and second review | `spec-reviewer` | 3.9 and 4.2 min | 85k and 88k |

### b-ce93aa was not a spec

The writer was told to settle that first. A cell-marked witness is never
collected by the `tests` gate, so it fails `criteria`. A spec with no criteria
passes every gate while its test never runs. So the test landed by hand, and
the writer ran it in a real cell against three mutants of the probe cell's
`env`.

### First reviews: one blocker each

| Finding | Class | Check that should have caught it |
|---|---|---|
| SA-0121 removed a flag that SA-0097's witness relies on | A change breaking a live check or test | Pre-flight 6, extended to earlier specs' witnesses |
| SA-0122's witnesses passed a helper that swaps two values | A witness drives one member of a set | Pre-flight 1 |

These were the day's first blockers. Both sat in the class every earlier
review had found.

### Second reviews: no blocker

| Finding | Class | Check that should have caught it |
|---|---|---|
| SA-0121's fix claimed a guard that no test provides | A claim about the tree that stopped being true | Pre-flight 5, applied to the delegate's own fix |
| SA-0122's fix could flip the verdict and reopen the swap | An arrangement argued rather than run | Pre-flight 10 |

Both second-round findings came from the delegate's by-hand fixes to the first
round. A hand fix is a claim like any other, and it went to a reader untested.

### What the next run should change

1. **Search earlier specs' witnesses before removing a line.** SA-0121's
   blocker was a line SA-0097 placed on purpose. A command that lists every
   done spec whose witness or mutant touches the change's files would find it.
2. **Run a by-hand fix before handing it back.** Both second-round findings
   were fixes argued at the keyboard.
