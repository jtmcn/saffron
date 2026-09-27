---
name: setup-saffron
description: "Onboard a target repo onto Saffron: write its `.saffron/` policy, gates, Dockerfile and spec queue, then check them. Run from this checkout with the target's path."
disable-model-invocation: true
---

# Set up Saffron in a target repo

Onboarding writes one `.saffron/` directory in the target and touches zero lines of `saffron/` (§2.1, F11).
The target is the path the user passed. Ask for it when none was given.
Everything else about the target comes from exploring it.

This is a prompt-driven skill. Explore, present what you found, confirm with the user, then write.
Start a timer when you begin. N8 says onboarding takes an afternoon, and the elapsed time is part of the report.

## 1. Explore

Read the target. Assume nothing it does not show you:

- `git -C <target> status` and `git remote -v`. The tree must be clean, because step 5's `committed` check reads it. PACKAGE opens a GitHub pull request, so note a remote that is not GitHub.
- An existing `.saffron/`. When one exists, this run edits it and keeps the owner's declarations.
- The languages, and for each one its formatter, linter, type checker and test runner. Read the config files and the CI workflow, since CI names the commands the owner already trusts.
- How the test runner lists test names and takes a subset of them. `revert` needs the subset, `census` and `criteria` need the list.
- Anything that opens a socket in tests, such as a database or a fixture server. A cell reaches one host, `api.anthropic.com`, so a service the suite needs is baked into the image.
- Numerical libraries that size a thread pool from the CPU count. `thread_env` caps them (§5.1).
- `CLAUDE.md` and `AGENTS.md` at the target's root.

**Done when** you can name a command for each gate role in §5.4's table, or say why the target has no analogue.

## 2. Present findings and ask

Summarise what is present and what is missing. Then take the sections in order, one answer each.
Lead each section with your recommendation, so the user can accept it in a word.

**A. Gate roles.** Propose `format`, `lint`, `types`, `tests` and `no-network`, each mapped to the command step 1 found.
Omit a role with no analogue, since core never needs one it was not given. Every declared gate is blocking unless the user says otherwise.

**B. The domain gate.** Ask the owner one question, from §5.4: *what is expensive to fake here?*
A migration round-trip, a schema check, an invariant only this codebase states. Propose one when the code suggests it. Accept "none yet".

**C. `elevate_on`.** This is most of what onboarding means, so ask even when you have a guess. Offer the guess as the recommendation.
The question is §5.6's: *where in here does a plausible-looking wrong change hurt most?*

**D. `protected` and `integrity`.** Propose these from what step 1 found, without a question per list:

- `protected`: files no task edits, such as a lockfile or a design record the owner names.
- `integrity.test_paths`: where the tests live.
- `integrity.suppressions`: each language's skip, expected-failure and ignore-comment tokens. A token the list omits is a hole `integrity` cannot see.
- `integrity.gate_config`: every file that changes what a gate measures. That includes each tool's config, a `conftest.py` or its analogue, and `**/.gitignore`. Saffron's own `.saffron/policy.yaml` shows the reasoning behind each entry.

**E. `thread_env`.** Only when step 1 found a thread pool to cap. Skip the section otherwise.

## 3. Confirm

Show the user a draft of `.saffron/policy.yaml`, one line per gate naming the command it wraps, the Dockerfile, and the `CLAUDE.md` block.
Let them edit before you write.

## 4. Write

Write into the target, following [GATES.md](GATES.md) for every gate and the Dockerfile:

- `.saffron/policy.yaml`, with a one-line comment only where a choice needs its reason.
- `.saffron/gates/<name>` for each declared gate, executable. The file name is the gate name, with no extension.
- `.saffron/Dockerfile`, `FROM saffron/cell-base:python`.
- `.saffron/specs/.gitkeep`. The queue starts empty.
- A `## Saffron` block in `CLAUDE.md`, created when the target has none. A cell's agent reads it (§8). Name the command behind each gate, so the agent runs the same ones. Update an existing block in place.

Onboarding needs no edit to `saffron/`. When a gate or a declaration seems to need one, stop and report it. That is §9's finding, the boundary failing, and worth more than a finished onboarding.

## 5. Check

Run the check from this checkout:

```
uv run .claude/skills/setup-saffron/check.py <target>
```

It loads the policy with Saffron's loader and runs every gate on the host through Saffron's own runner. Then it runs `tests` on one collected name and reads the tree for leftovers. Each `PROBLEM` line names a gate and what Saffron would do with it.
A gate that reports `fail` is fine at this point, since the baseline subtracts failures already on the base.
A tool missing on the host is an `error` here and says nothing about the image.
Gates never see Saffron's own virtualenv. Put the target's tool directory first on `PATH`, as `PATH=<target>/.venv/bin:$PATH`, or read past it.

Then build the image, which runs every tool at build time:

```
<runtime> build -t saffron/cell:<target-dir-name> -f <target>/.saffron/Dockerfile <target>
```

**Done when** the check exits `0` and the image builds. A problem you cannot fix goes to the user, named.

## 6. Report

Tell the user the elapsed time, each gate and the command it wraps, the domain gate or its absence, and every problem left open.
Leave the target's changes uncommitted, unless the user asks you to commit them.
Name the next step: a spec in `.saffron/specs/`, written with the `create-saffron-spec` skill, then `saffron cell <spec> --repo <target>`.
