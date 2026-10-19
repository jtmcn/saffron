---
id: b-3a79a0
title: The loop's driver orders and guards a stack by `depends_on`, not by the stack base a batch built
status: open
tier: 2
filed: 2026-10-17
by_hand: true
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-cab612, b-f73cd0]
---

## Problem

Found in the spec loop's run 43.

`SA-0294` ran as an attended cell and opened #898. The `--stack` batch then
took that open pull request as its stack base. Its log printed `stacked on
saffron/SA-0294 @ 477a34887ebd`, and `SA-0284`'s branch holds #898's commit.
Neither spec names the other in `depends_on`.

The driver reads only `depends_on`. So `driver.py stack` ordered #899 below
#898, the reverse of the branches. Linking that order would base #898 on
`saffron/SA-0284` and put #898's diff inside #899's. The delegate linked the
stack by hand with `gh stack link 898 899`.

The same blindness let a push through. The delegate pushed #898's review
commits while `SA-0284`'s cell ran on #898's packaged head. The skill says
to hold them until the batch drains. Nothing refused the push. The delegate
reverted the remote within a minute, while `SA-0284` was still in IMPLEMENT.

## Done looks like

`driver.py stack` orders layers by the base each branch was cut from, which
the batch records. `driver.py` refuses, or warns on, a push to a branch that
a running batch's stack sits on. Each has a test.

## Record

- 2026-10-17: filed from the spec loop's run 43.
- 2026-10-19: recurred in the spec loop's run 44. `driver.py stack` ordered #914 below #913 and left out #915 and #912. `driver.py size` measured `SA-0287` from the wrong base and read 0 tokens, where the diff is +118/-6. The delegate measured it and linked all eleven layers by hand, as stack #916.
