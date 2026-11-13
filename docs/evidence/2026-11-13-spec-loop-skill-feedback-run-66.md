# Feedback on run-saffron-spec-loop (run 66, 2026-11-13)

Run 66 kept the goal of runs 55 to 65: implement every backlog item. It
queued the two specs the chain wrote on 2026-11-12.

| Spec | PR | Outcome | Spend of budget |
|---|---|---|---|
| `SA-0380` | #1178 | `READY_FOR_REVIEW` | $52.16 of $52 |
| `SA-0381` | none | refused at its citation check | $0 of $30 |
| `SA-0382` | #1179 | `READY_FOR_REVIEW`, a follow-up | $6.15 of $24 |
| `SA-0383` | #1180 | `READY_FOR_REVIEW`, a follow-up | $7.11 of $12 |

Batch 84 ran at `--budget 210` with `--stack --defer-end-review`. It spent
$52.16. Finish 84's end review spent $2.53, and its two follow-up cells
$13.26. The finish committed no finishing layer.

## What the run found

1. **The weekly limit stopped `SA-0380` overnight.** The provider named a
   reset thirteen hours off. The batch trusts six hours at most, so it
   restarted the cell nine times, an hour apart, each rejected at $0. Filed
   as b-45783e.
2. **`SA-0380` moved a line `SA-0381` cites.** The batch refused `SA-0381`
   with `1 citation(s) do not resolve`. `driver.py check` had passed it at
   `origin/main`. This is b-b664d1's third hit.
3. **The end review caught a restated helper.** Its standards lens saw that
   `ready_task` checked a pool cut by hand, beside `review_state`'s own
   `cut`. `SA-0382` fixed it as a follow-up.
4. **Neither follow-up was pooled.** `SA-0380` declares no `depends_on`, so
   b-4a9207's pooling did not arise.
5. **The token and key files vanished again.** `jev.env` was gone from the
   scratchpad when the first score ran. It was rebuilt from `~/.secrets`.
6. **The follow-ups got one seat each.** Each diff was under 100 lines, so
   one seat held both remits. Both came back ready with one note.

## What the reviews found

- **#1178:** 1 Spec blocker, the pool-cut match's two ends. One concern, an
  interrupt never driven. Four notes were fixed, and three were kept.
- **#1179:** 1 note, a line-number citation in a docstring. Kept.
- **#1180:** 1 note, a CLAUDE.md pin outside `test_citations.py`. Kept,
  since the spec forbade that file.

`.saffron/rejections.md` holds four lines for this run.

## Run 65's items, checked

- [ ] **A follow-up writer never copies its origin's `depends_on`:** open.
  `SA-0381` is queued and did not run.
- [ ] **A lens reads for a helper the diff restates:** open, with progress.
  Finish 84's standards lens found one, and `SA-0382` fixed it.
- [ ] **REVIEW drives every input a criterion names:** open. #1178's
  blocker and concern were both inputs the witness never drove.
- [ ] **`driver.py rebase` sees local review commits:** open. Run 66 had
  no layer above a held commit.
- [ ] **`census` reads a renamed parametrize id as a rename:** open, on
  b-f30189.

## Summary: what Saffron should absorb next

1. **`driver.py check` runs `cite` at the base each layer will cut from.**
   A skill-tool change, on b-b664d1. It cost `SA-0381` its cell.
2. **REVIEW drives every input a criterion names.** A lens change. Six
   blockers in three runs were inputs the witness never drove.
3. **A follow-up writer never copies its origin's `depends_on`.** A phase
   change, on b-4a9207, and `SA-0381` is its spec.
4. **A reset past six hours waits six hours.** A batch change, on b-45783e.
5. **`census` reads a renamed parametrize id as a rename.** A gate change,
   on b-f30189.

This PR changes no skill text.

## Next run

`SA-0381` waits for a spec PR that refreshes its citations against `main`
once this stack merges. Run 67 runs it.
