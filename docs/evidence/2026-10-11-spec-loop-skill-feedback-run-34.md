# Feedback on run-saffron-spec-loop (run 34, 2026-10-10)

Run 34 took the five queued specs. The operator chose one `--stack` batch at
$280, with no deadline. The batch spent $83.90. The five cells spent $69.54
against $133 of spec budgets. Four cells ended `READY_FOR_REVIEW`. `SA-0259`
halted at `REVIEWING` when a lens failed, and the operator had its branch
opened by hand. The stack is #811 to #822. #809 stands alone on `main`.

## What happened, in order

1. **The first start never reached a cell.** The worktree guard refused a
   chained `umask` and `sed` write of the token file. `uv run --env-file` then
   failed on the missing file, and the batch exited 2 before any spend.
2. **The watch attached to a finished task.** `mcp__cell-watch__watch` ran
   before `SA-0259` wrote its log. It followed `SA-0249` from run 33, even with
   `spec` set. It then sent a hand-over from `SA-0249` to `SA-0259`. Under the
   skill's rule that hand-over would have recorded a spec outside the order.
3. **One lens error halted a green task.** `SA-0259`'s gates passed on attempt
   1. The adequacy lens returned malformed JSON twice. The cell left the task
   at `REVIEWING` with its branch pushed and no PR. The host's own criterion
   probes had filed two blockers under that lens, both `survived`. The log
   said only that the lens produced nothing, and no REBUT ran on them.
4. **The batch ended `INCOMPLETE`.** That task stayed in flight, so the batch
   exited 2 after a full night's work.
5. **The seats found a blocker the critic missed on four of five layers.** The
   exception was `SA-0253`, where the critic and the Spec seat were both clean.
6. **Two spec texts were wrong, and the cells copied them.** `SA-0258`'s
   HOST-HARDENING sentence and `SA-0254`'s "layer" wording were the specs' own
   verbatim text. The operator chose to depart from both in review.
7. **The restack ran by hand again.** Each layer's fixes waited for the layer
   above to package. The delegate then rebased four layers. `git rerere`
   replayed a whole resolved file into the cell's own commit. A range-diff
   caught it.
8. **Jev scored one round against the wrong diff.** `--base saffron/SA-0245`
   resolved to a stale local branch from 2026-10-09. The merge base fell on an
   older `main`. The delegate moved the round aside and scored it again.
9. **The end review found one new defect.** Four of its five findings were
   already fixed or decided on the branches.
10. **No follow-up became a spec.** One draft had invalid YAML, one writer
    session hit an API error, and two hit a proxy 503.

## Run 33's items, checked

1. **Judge a criterion probe against the whole `tests` gate (b-c9a913)**: not
   absorbed. No probe this run was killed only by a test outside its witness.
2. **A check that each witness drives every part of its claim (b-20043f)**:
   not absorbed. It was the seats' most common blocker again, on four layers.
3. **An end review over the reviewed heads (b-8a0c9a, b-27bacc)**: not
   absorbed. The end review read the packaged heads, and four of its five
   findings were already fixed. The writer produced no spec.
4. **A batch that takes the loop's order (b-910cef, b-fab381)**: not needed.
   The snapshot and the batch agreed on all five specs.
5. **A driver that stacks a stack batch's chain (b-f10412)**: not absorbed.
   The delegate rebased three layers by hand and hit the `rerere` trap.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The lines in `.saffron/rejections.md` dated 2026-10-11 are the
evidence.

1. **A lens that fails ends its task in a decided state (b-032c3e,
   b-f7a591).** A phase change. The task should re-run the lens or end
   `READY_FOR_REVIEW` with the lens marked missing. The host's probe blockers
   must still reach REBUT. Today it leaves the task in flight and the batch
   `INCOMPLETE`. Constraining lens output to the schema (b-4e0868) removes the
   cause. b-032c3e sits at tier 3, and this run argues for tier 1.
2. **A check that each witness drives every part of its claim (b-20043f).**
   A lens change, carried over from run 33. Four witness blockers came from
   asserting only part of a claim. Examples are a name the prompt already
   held, a default disposition, an empty list, and an exact division.
3. **A spec review that checks prescribed text against `CONTEXT.md`.** A gate
   or lens on the spec. Two specs dictated wording that broke a definition or
   a measured fact, and the cells copied it faithfully.
4. **An end review over the reviewed heads (b-8a0c9a, b-27bacc).** A phase
   change, carried over from run 33.
5. **A driver that stacks and restacks the chain (b-f10412).** A skill change,
   ranked last. It should run with `rerere` off and resolve every base
   against `origin`, for `jev` too.

## The loop's own gaps

- **Seats stay.** The critic missed a blocker on four of five layers.
- **The watch must start after the first `ceilings:` line.** Before that, it
  follows the newest finished task in silence.
- **A plugin wake-up waits for the turn to end.** Three of them queued behind
  a long restack and arrived together. A Monitor needs a re-arm every 30
  minutes, so neither one alone covers a night.
- **The `check` blocker on `SA-0253` was a false alarm.** It compared the spec
  with `SA-0245`, a shape about twice its size. The cell spent $8.40 of $14.
