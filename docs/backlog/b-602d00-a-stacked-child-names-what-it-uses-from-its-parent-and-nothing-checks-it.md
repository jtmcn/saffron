---
id: b-602d00
title: A stacked child names what it uses from its parent, and nothing checks those names before its cell starts
status: done
tier: 2
filed: 2026-09-21
closed: 2026-09-25
specs: [SA-0134, SA-0135, SA-0136]
prs: [507, 510, 514]
commits: []
cites: [§4.2]
related: [59, b-e1afbb]
---

## Problem

Filed 2026-09-21 from a comparison of Saffron with the superpowers
plan format.

**A child relies on names its parent must produce.** A stacked child's tree
base is its parent's branch head (§4.2, `CONTEXT.md` "Tree base"). The child's
criteria and notes name functions, fields and paths the parent adds. If the
parent built them under other names, the child's cell finds out after its
first turn is paid for.

**Today the check is prose.** `create-saffron-spec` pre-flight check 4 asks
the writer to name what the child keys by. The writer then checks that the
parent produces it. A reviewer does that by reading. Nothing does it at the
tree base the cell uses.

**The superpowers plan format makes it a field.** Each task declares what it
consumes from earlier tasks. It also declares what it produces for later
ones, with exact signatures.

## Done looks like

A spec can declare the names it consumes from its `depends_on[0]`. Before a
stacked child's cell starts, the host resolves each name at the child's tree
base. A missing name refuses the task with a reason and no model call, as
gate 0 refuses in §4.2.

## Record

- 2026-09-21: filed. Principle 17 applies: refuse before you spend.
- 2026-09-25: in the spec loop's run 16, `SA-0134` reached
  `READY_FOR_REVIEW` as #507 at $3.59 of $20. `SA-0135` followed as #510 at
  $9.12 of $27, and `SA-0136` as #514 at $7.80 of $36. A stacked child's
  consumed names now resolve at its tree base before the cell starts. All
  three retire to `done/`.
