# Spec chain feedback, 2026-10-11

## b-ca3bc6, per-task networks, split into `SA-0260`, `SA-0261` and `SA-0262`

The operator asked what parallel cells need. A survey found every cell shares
one network, one critic network, one proxy and fixed subnets. b-ca3bc6 was
the item. Its first writer stopped at step 1 on size and named a three-way
split. Naming came first, then a subnet pool, then the gate and reverify
networks. The delegate's own two-way cut priced its parent at 755 lines
against a 600-line limit.

### Measured before any draft

Two spikes on apple/container 1.3.0, both by the delegate on the host.

- A second `network create` on a held /24 exits 1 with "overlaps an existing
  network". A /25 inside it is refused the same way. The next /24 succeeds.
  So the create can be the claim, with no lock file.
- Network names of 31 and 61 characters are accepted.

### Cost

| Step | `SA-0260` | `SA-0261` | `SA-0262` |
|---|---|---|---|
| Split, one writer | 3.5 min | | |
| Draft | 12.5 min | 20.1 min | 23.9 min |
| Review 1 | 3.9 min | 6.8 min | 5.7 min |
| Revise 1 | 1.3 min | 2.0 min | 2.6 min |
| Review 2 | 4.0 min | 6.6 min | 5.7 min |
| Revise 2 | 0.7 min | 0.5 min | 9.7 min |

The three drafts ran in parallel, and so did each review and revision round.
No spec had a third review.

### Rounds

| Spec | Round 1 | Round 2 |
|---|---|---|
| `SA-0260` | 0 blockers, 3 concerns, 4 notes | 1 blocker, 1 concern, 3 notes |
| `SA-0261` | 0 blockers, 6 concerns, 5 notes | 1 blocker, 2 concerns, 2 notes |
| `SA-0262` | 0 blockers, 3 concerns, 3 notes | 0 blockers, 4 concerns, 4 notes |

### Each finding by class

- **A wrong version the witness passes, hidden by a fake's default.** Both
  round 2 blockers. `_stub_the_runtime` lists no holder unless a test passes
  one, so a `cell_up` sweeping every `saffron-` network passed `SA-0260`'s
  witness. `SA-0261`'s witness always passed `subnet=`, so a defaulted
  `subnet` passed it. Pre-flight 1 asks for the members of each set. It does
  not ask what each fake returns by default, which is where both hid.
- **A claim over a set whose witness drives one member.** Round 1 on all
  three. The Gate-only sweep sat outside `SA-0260`'s claim. `SA-0261`'s
  per-leg probes had no criterion. A fresh claim model let a hardcoded
  second /24 pass.
- **A test the change turns red that the spec never names.** Round 1 on
  `SA-0261` and `SA-0262`, and round 2's notes on `SA-0262`. One read a
  constant by string, which `ty` cannot see. Pre-flight 6 lists enumerators
  only.
- **A mutant across a split.** `SA-0262` keyed a mutant on text `SA-0261`
  would write. Round 1 asked `SA-0261` to dictate its spelling. Round 2 found
  that dictating a literal is barred (`docs/agents/issue-tracker.md:83-99`).
  Both mutants were dropped. No check covers a child's mutant on its parent's
  new code.
- **A size estimate counted twice.** Round 2 on `SA-0262`. The measured
  prototype already held the cell-marked file, and the notes counted it again
  by hand. The cell-marked file left the spec, and the delegate writes it on
  the pull request.
- **A behaviour invisible under the default dialect.** Round 2 on `SA-0262`.
  `_admit` refuses only under podman, and tests force apple. It became its own
  criterion, with a witness that selects podman.
- **A claim about the tree that does not hold.** Round 2 on `SA-0261`.
  `podman network ls` prints no subnet column (item 108), so the walk cannot
  name a holder there.
- **A gap between two specs of a chain.** Round 1 on `SA-0260`. After it
  merges, a network teardown leaves behind blocks later tasks until the pool
  lands. The operator runs the three as one stack batch.

### What the delegate did by hand

- Placed `SA-0260` at priority 3, to match its item and its children.
- Moved `_admit` before the walk from `SA-0261` to `SA-0262`, since
  `SA-0261` sat 4 tokens over the size line. Then moved the subnet's no-default
  check the same way.
- Took the cell-marked two-task test out of `SA-0262`, to be written by hand
  on its pull request.
- Left `DESIGN.md` §5.1 and `:680` for an edit after `SA-0262` lands.

### The next checks

1. **Pre-flight 1 reads each fake's defaults.** For a witness over a fake,
   name what the fake returns when the test passes nothing. Then name a wrong
   build that the default hides. Both round 2 blockers were this shape.
2. **A split's children declare no mutant on a parent's new code.** The text
   does not exist at the child's draft, and dictating it is barred.
3. **A measured estimate lists what the prototype held.** Then nothing it
   held is counted again by hand.
