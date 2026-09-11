# PROBE — SessionStart skill-install check (Claude Code on the web)

Session started from branch `claude/skills-loading-cloud-lhfm8g`, which adds
`.claude/hooks/session-start.sh`. Recorded from this session's own point of view.

## 1. Skills as they appear in MY available-skills listing

Both present. Verbatim entries:

```
- gh-stack: Manages stacked PRs and splits multi-part work into reviewable branches with gh-stack. Use for stack creation, viewing, edits, push, submit, sync, rebase, merge, or checkout; when asked to split or isolate work for review; whenever a user mentions a stack, branch layers, dependent PRs, or gh stack; or when a stack is checked out.
```

```
- superpowers:requesting-code-review: Use when completing tasks, implementing major features, or before merging to verify work meets requirements
```

The full set of `superpowers:*` entries in my listing, verbatim:

```
- superpowers:brainstorming: You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation.
- superpowers:dispatching-parallel-agents: Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
- superpowers:executing-plans: Use when you have a written implementation plan to execute in a separate session with review checkpoints
- superpowers:finishing-a-development-branch: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work
- superpowers:receiving-code-review: Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative agreement or blind implementation
- superpowers:requesting-code-review: Use when completing tasks, implementing major features, or before merging to verify work meets requirements
- superpowers:subagent-driven-development: Use when executing implementation plans with independent tasks in the current session
- superpowers:systematic-debugging: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
- superpowers:test-driven-development: Use when implementing any feature or bugfix, before writing implementation code
- superpowers:using-git-worktrees: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via native tools or git worktree fallback
- superpowers:using-superpowers: Use when starting any conversation - establishes how to find and use skills, requiring skill invocation before ANY response including clarifying questions
- superpowers:verification-before-completion: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always
- superpowers:writing-plans: Use when you have a spec or requirements for a multi-step task, before touching code
- superpowers:writing-skills: Use when creating new skills, editing existing skills, or verifying skills work before deployment
```

Also present in the same listing, from the same install:

```
- session-start-hook: Creating and developing startup hooks for Claude Code on the web. Use when the user wants to set up a repository for Claude Code on the web, create a SessionStart hook to ensure their project can run tests and linters during web sessions.
```

## 2. `claude plugin list`

```
Installed plugins:

  > superpowers@superpowers-dev
    Version: 6.3.0
    Scope: user
    Status: √ enabled
```

Exit code: 0

## 3. `ls ~/.claude/skills/` and `ls ~/.claude/plugins/cache/`

```
--- ls ~/.claude/skills/ ---
gh-stack
session-start-hook
synced
--- ls ~/.claude/plugins/cache/ ---
superpowers-dev
```

## 4. `$CLAUDE_CODE_REMOTE` as seen by a shell

```
CLAUDE_CODE_REMOTE=[true]
```

## 5. Invoking the Skill tool with skill name `gh-stack`

Succeeded. First line of the tool result:

```
Launching skill: gh-stack
```

The skill body then loaded, beginning:

```
Base directory for this skill: /root/.claude/skills/gh-stack
```

## Verdict

It worked. Both skills installed by the SessionStart hook are visible in this
session's own available-skills listing before any action was taken, and
`gh-stack` invokes successfully through the Skill tool.
