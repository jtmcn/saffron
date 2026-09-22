# Spec chain feedback, 2026-09-21: SA-0119

The second spec of the day's `create-saffron-spec` runs. SA-0118's record sits
on its own branch, in `2026-09-21-spec-chain-feedback.md`. Durations and token
counts come from the agents' completion reports.

## SA-0119, items b-461729 and b-a70ec1

Branch `joel/spec-probe-path-rules`. It was drafted in a second worktree, in
parallel with SA-0118, and moved into the first worktree to be committed.

### Rounds and cost

| Step | Who | Time | Tokens |
|---|---|---|---|
| Draft, with a prototype of the change | `spec-writer` | 23.8 min | 242k |
| Move and pre-flight | delegate | about 10 min | not counted |
| First review | `spec-reviewer` | 6.4 min | 87k |
| Revision | delegate, by hand | about 15 min | not counted |
| Second review | `spec-reviewer` | 5.8 min | 75k |

### The split

The brief allowed four items in one spec, or a split above 200 lines. The
writer prototyped the change and counted instead of estimating. The first two
items measured 209 lines and all four about 307. So the spec holds two items,
and b-e403c1 and b-ce93aa wait as children. b-a70ec1 could not stand alone,
since its witness passes at base and `revert` would block it.

### First review: no blocker, four concerns

| Finding | Class | Check that should have caught it |
|---|---|---|
| Criterion 3 claimed more than its witness compared | A witness drives one member of a set | Pre-flight 1 |
| An empty list and an out-of-tree path answered one input two ways | Two criteria disagreeing on one input | Pre-flight 2 |
| Nothing excluded `fnmatch` in place of `scope.matches` | A witness drives one member of a set | Pre-flight 1. A one-line run settled it. |
| Two protected sentences go incomplete | A design argument the documents do not support | Pre-flight 8 |

Fixing the third finding first put a path token in a claim. The scheduler read
it as a path outside `touches` and refused the spec. The writer had hit the
same refusal with another path.

### Second review: no blocker, two concerns

| Finding | Class | Check that should have caught it |
|---|---|---|
| The wrong implementations were measured only on the writer's prototype | An arrangement argued rather than run | Pre-flight 10. Accepted, since the prototype was the writer's run. |
| Three sentences in touched code still name the removed prefix rule | A claim about the tree that stopped being true | Pre-flight 5, applied to the change's own aftermath |

### What the next run should change

1. **A claim names no path outside `touches`.** Put a concrete path in the
   notes. The scheduler reads every path token in a claim.
2. **Prototype before splitting.** A counted prototype decided this split with
   no review round, where an estimate had allowed four items.
3. **Grep for sentences that describe removed code.** Both reviews found one.
