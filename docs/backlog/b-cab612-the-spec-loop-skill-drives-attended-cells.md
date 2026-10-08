---
id: b-cab612
title: "The spec loop's skill drives one attended cell per spec, while the operator made `saffron batch` its default"
status: open
tier: 1
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§4.4]
related: [b-e0e1cf, b-792ab2]
---

## Problem

The operator asked during the spec loop's run 30: "Run the remaining using
batch. It should be the default now." The skill's step 2 still starts one
`saffron cell` per spec, and its driver models that.

- `next` names one spec and waits on its parent's review commits.
- A batch task gets no `record` call, so `stack` saw one reviewable pull
  request until the delegate ran `record` for each by hand.
- `saffron batch --stack` refused the chain's second spec. Its parent was an
  open pull request outside the order (b-e0e1cf), so the run used a plain
  batch.
- A plain batch cuts each child at its parent's packaged head. Review commits
  then come after the whole chain, and the delegate rebased four layers by
  hand.

## Done looks like

Step 2 starts one batch over the snapshot's order. The driver records each
task the batch decided. Review commits on a lower layer restack the layers
above with one command.

## Record

- 2026-10-07: filed from the spec loop's run 30, at the operator's request.
