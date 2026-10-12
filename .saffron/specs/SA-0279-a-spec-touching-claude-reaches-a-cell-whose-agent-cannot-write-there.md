---
id: SA-0279
title: A spec whose `touches` reach `.claude/` is not refused, so its cell turns on the agent routing around a write its file tools refuse
type: bug
priority: 2
depends_on: [SA-0280, SA-0282, SA-0283, SA-0267, SA-0268, SA-0269]
estimated_lines: 150
estimate_measured: true
touches:
  - saffron/scheduler.py
  - tests/test_scheduler.py
  - tests/test_cli.py
  - tests/test_task.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/intake.py
  - saffron/cli.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/agents/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/cell/**
  - tests/test_queued_specs.py
  - tests/test_refusal_count.py
  - tests/test_context.py
  - tests/test_session.py
budget_usd: 22
max_attempts: 3
max_turns: 110
acceptance:
  - claim: >-
      The queue scan refuses a spec whose `touches` holds an entry with
      `.claude` as one of its `/`-separated components, under the existing
      `protected_touch` kind, with no `protected` list given. The witness
      drives each spelling in its own spec beside "src/**". Those are a
      literal file ".claude/skills/run-saffron-spec-loop/driver.py", a glob
      ".claude/agents/*.md", ".claude/**", "./.claude/settings.json",
      "**/.claude/**", the nested "sub/.claude/skills/x.md" and the whole
      entry ".claude". A spec touching ".claude/skills/x/SKILL.md" that also
      forbids ".claude/**" is refused too. Each reason names its entry in
      single quotes, names backlog item b-e471bd and says the work lands by
      hand. The near misses ".claudeignore", ".claude-plugin/plugin.json",
      "docs/claude/notes.md", ".claud?/x.md", "**/*.py" and "**" are each
      admitted as a candidate.
    witness: tests/test_scheduler.py::test_a_touches_entry_under_claude_is_refused_in_every_spelling
    wrong_versions:
      - A check of the entry's first component alone, so "./.claude/settings.json", "**/.claude/**" and "sub/.claude/skills/x.md" are admitted.
      - A prefix match on ".claude", so ".claudeignore" and ".claude-plugin/plugin.json" are refused.
      - A substring match on ".claude", so the near misses holding it are refused.
      - A path under ".claude/" matched against each entry as a glob, so "**" and "**/*.py" are refused.
      - The check made only when the `protected` list is not empty, so a repo protecting nothing admits every such spec.
      - The `protected` loop's `forbidden` exemption copied, so a spec that also forbids ".claude/**" is admitted.
      - The check returned under a refusal kind of its own, which `RefusalKind` and §4.2.1's count do not name.
      - A reason that never names the entry, or never says the work lands by hand.
  - claim: >-
      `saffron cell` refuses a spec touching ".claude/skills/x/SKILL.md"
      beside "src/**" before any cell starts, with `policy.yaml` at the base
      protecting nothing. It exits 1 and writes no task row. Its one line
      starts with the spec id, names the entry in single quotes and says the
      work lands by hand.
    witness: tests/test_cli.py::test_a_spec_touching_claude_refuses_before_the_cell_starts
    wrong_versions:
      - The check added to the queue scan's `_refuse` alone, so `saffron cell` starts the cell.
      - The check made only when the `protected` list is not empty.
  - claim: >-
      `run_task` refuses a stack batch's recorded spec text whose `touches`
      add ".claude/x.md" to "src/**" and "tests/**", before any cell
      starts. The `Refused` reason names the entry in single quotes and says
      the work lands by hand. The printed line is the spec id, `refused` and
      that reason. The task records no attempt.
    witness: tests/test_task.py::test_gate_zero_refuses_a_recorded_spec_text_touching_claude
    wrong_versions:
      - The check added to the queue scan and to `saffron cell` alone, so a recorded spec text reaches its cell.
  - claim: >-
      A spec whose `touches` name a literal `protected` path is still refused
      with today's reason, naming the path, the protected list and
      `forbidden`.
    witness: tests/test_scheduler.py::test_a_touches_entry_matching_a_protected_literal_path_is_refused
    preserves: true
---

## Context

Backlog item **b-e471bd**, filed from the spec loop's run 16. It cites
`DESIGN.md` §5.3 and §4.2. The operator chose its second exit: refuse
the spec before any cell, with a reason and no model call. Every line
number below was read at `cad84298`.

**The cell agent's file tools refuse `.claude/`.** IMPLEMENT passes
`permission_mode="dontAsk"` and an empty `setting_sources`
(`saffron/phases/implement.py:164-167`). Nothing grants a path under
`.claude/`. `docs/evidence/2026-10-10-agent-unwritable-paths.md`
measured the refusal at the pinned SDK. It keys on an exact path
component at any depth, so `sub/.claude/` is refused as well. A file
named `.claude` is refused too. `.claudeignore` and `claude/x.md` were
written. Core already spells that set as `UNWRITABLE_DIR_NAMES`
(`saffron/agents/context.py:104-106`).

**`SA-0259` only routes around it.** IMPLEMENT's prompt names each such
`touches` entry and the python3 write through Bash
(`saffron/agents/context.py:131-156`). So a cell finishes only when its
agent takes that route. `SA-0129`'s cell did not and ended
`NOT_IMPLEMENTED`.

**The protected-touch refusal is the one before every cell.**
`protected_touch_refusal(touches, protected, forbidden)` returns a reason
or `None` (`saffron/scheduler.py:365-434`). It decides only a literal
`protected` entry, and returns nothing for an empty list. Three callers
reach it before a cell. The queue scan's `_refuse` returns its reason
under the `protected_touch` kind (`saffron/scheduler.py:737-742`).
The attended run prints `{spec.id:<10} refused  {collision}` and returns
1 (`saffron/cli.py:533-536`). A stack batch's recorded spec text is
refused with it as well (`saffron/task.py:415-420`). That check runs
before any cell (`saffron/task.py:465`). `RefusalKind` lists eight kinds
(`saffron/scheduler.py:152-161`). `tests/test_refusal_count.py` holds
that count to §4.2.1.

**Only the three parents touch `.claude/` in the queue.** At `04d54884`
the specs in `.saffron/specs/` that name a `.claude` component are
`SA-0280`, `SA-0282` and `SA-0283`. Seven retired ones do:
`SA-0092`, `SA-0112`, `SA-0114`, `SA-0115`, `SA-0116`, `SA-0129` and
`SA-0196`. The scan never refuses a spec in `done/`.

**One test runs the retired corpus through the scan.**
`test_no_real_spec_is_refused_on_its_own_acceptance_criteria`
(`tests/test_scheduler.py:3083`) promotes every retired spec to the top
level, then scans them all.
It allows one refusal that is not `depends_on`, `SA-0063`'s, and asserts
every other names `depends_on` (`tests/test_scheduler.py:3107-3109`).
The scan checks `protected_touch_refusal` before any other refusal
(`saffron/scheduler.py:737-742`). So under this change those seven
retired specs are refused on `.claude/` instead, and that test fails. On
the base this spec requires, `SA-0280`, `SA-0282` and `SA-0283` are
retired as well, which makes ten.

## Problem

**This spec waits for three parents.** It runs only once `SA-0280`,
`SA-0282` and `SA-0283` are merged and retired to `done/` on its base. That
means a later batch,
not the same `--stack` night. Each of the three touches files under
`.claude/`, so this refusal would refuse it.

Make `protected_touch_refusal` refuse any `touches` entry holding
`.claude` as a `/`-separated component. Do it whatever `protected` and
`forbidden` hold. Keep its signature, so all three callers get it with no
edit. The queue scan returns the reason under `protected_touch`, which
needs no new kind.

The reason names the entry in single quotes, as the protected reason
does. It names backlog item b-e471bd and says the work lands by hand.
Leave the reason for a protected path exactly as it is.

Rewrite the function's docstring to say it refuses both. Add a sentence
there saying the `protected_touch` kind now also covers a path no
`policy.yaml` declares. Update the module docstring's paragraph on the
seventh refusal (`saffron/scheduler.py:15-17`) the same way. Write the
three new tests the criteria name. Each sits beside the protected-touch
tests in its file.

Then edit `test_no_real_spec_is_refused_on_its_own_acceptance_criteria`.
Name the retired specs that touch `.claude/` as its refusals on
`.claude/`, by exact list, as it names `SA-0063`. There are ten: the
seven above, then `SA-0280`, `SA-0282` and `SA-0283`. Write the list as
literal ids, never computed by the rule under test. Keep its other
assertions, and keep every remaining refusal on `depends_on`.

The queue smoke test promotes `SA-0280`, `SA-0282` and `SA-0283` from its
measured set at your base. Move each one it lists as a candidate to its
refusals, at scan position. Rewrite its top docstring paragraph in place to
say why.

## Out of scope

- **The other four directory names** in `UNWRITABLE_DIR_NAMES`, and the
  measured file names. The operator chose `.claude/` alone. The prompt
  route still covers the rest.
- **An entry led by a wildcard**, such as `**`, `**/*.py` or
  `.c*/**`. It holds no `.claude` component, so it is admitted. Its cell
  meets the file tools' refusal and `SA-0259`'s route as today.
- **The prompt route.** `unwritable_touches_section` still names a
  `.claude` entry. After this change no such spec reaches a cell.
- **Granting writes under `.claude/`.** That was the item's first exit,
  not taken.
- **`DESIGN.md` §4.2.1.** It is edited by hand with this spec.
- **Two texts that describe the protected half alone.** One is the
  comment on a spec whose own `touches` collide with `policy.yaml`'s
  protected list (`saffron/cli.py:514-518`). The other is the docstring
  of `test_no_protected_declared_changes_nothing`. Both stay as they are.

## Notes for the agent

**Every criterion but the last is new code**, so each declares a witness
and no mutant, and `witness` will report `skip`. The refusing branch does
not exist at base. The last criterion is `preserves`, and its test exists
at base.

**At base each new witness fails in its body.** None imports a name the
change adds. The scan admits every spec, `saffron cell` reaches its stub,
and `run_task` reaches its stub.

**Why `.claude` is spelled in core** (§2.1). Core invokes declared gates,
never tools, and knows nothing about a target repo's tools. `.claude/` is
neither. It is the path the agent runtime in every cell refuses, the
runtime `images/agent_runner.py` drives. Core already names it in a
measured set (`saffron/agents/context.py:104-106`). No declaration names
"the cell agent's config directory", so the reason says `.claude/`. Spell
it as a literal, or read it from that set. Do not refuse the set's other
names.

**The scan witness** writes one spec per spelling with `_write_spec`,
each beside "src/**". It writes the touches unquoted, and YAML reads a
leading `*` as an alias. So pass "**/.claude/**", "**/*.py" and "**"
wrapped in single quotes. Call `build_queue` with no `protected`. Map
each refusal back to its spec by reading the refused file with
`load_spec`. Assert each refused reason holds its entry's `repr`, as the
protected tests do.

**The `saffron cell` witness** copies
`test_a_spec_whose_touches_are_protected_refuses_before_the_cell_starts`
in `tests/test_cli.py`. Use `_local_origin_with_policy` with
`"protected: []\n"`, so a check gated on a non-empty list fails it.

**The `run_task` witness** uses `tests/test_task.py`'s
`_recorded_ledger`, `_handed_spec`, `_new_task`, `_record` and
`_rev_text`. Record `_rev_text(touches=...)` with the `.claude` entry
added to its defaults. That fixture's own policy protects a literal
path, so this witness cannot catch a check gated on a non-empty list. The
other two do.

**Once this lands, a core change a test binds to a `.claude/` file needs
a by-hand edit.** No cell can make it. `SA-0280`, `SA-0282` and
`SA-0283` touch files under `.claude/skills/setup-saffron/`, and tests
bind those to core models. So all three land first, which is why they
lead `depends_on`. The other three ids there are queued specs whose
`touches` overlap this one's.

**Your base has the three parents in `done/`.** `SA-0280`, `SA-0282`
and `SA-0283` are merged and retired there. This spec runs in a later
batch than theirs. Were any still queued at your base,
`tests/test_queued_specs.py` would fail on it. That test calls
`protected_touch_refusal` on every queued spec
(`tests/test_queued_specs.py:96-115`). It also fails on any spec added
later that touches `.claude/`. Do not edit it.

**The retired-corpus list is pinned for that base.** It names the ten
retired specs that touch `.claude/` there. Retiring another such spec
later extends the list, in the commit that retires it.

**The `protected_touch` kind is reused on purpose.** It now covers a
path no `policy.yaml` declares. A new kind would change §4.2.1's count
of eight for no reader. Nothing reads `Refusal.kind` once the scan builds
it (`saffron/scheduler.py:1008-1009`).

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** A prototype measured 470 tokens with `size_gate`'s counter,
against the `bug` ceiling of 1300. It held the refusing branch, a
two-line docstring addition, the three new witnesses and the retired
corpus test's edit with seven ids. The whole suite passed on it. It did
not hold the docstring rewrites or the three further ids.
`estimated_lines` is that count over four, plus a margin for those.
