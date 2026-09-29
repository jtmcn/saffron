---
id: b-12ffc3
title: A cell's session transcript is deleted with its state volume, so no record shows what the agent saw
status: open
filed: 2026-09-28
specs: []
prs: []
commits: []
cites: [§4.1, §5.3]
related: [170, b-36d318]
---

## Problem

§4.1 puts transcripts in the batch tree. §5.3 calls the attempt transcript what you read when a PR looks strange.
Neither holds. The cell's Claude Code session lives in `/agent-state`, the state volume.
`cell_down` removes that volume (`saffron/cell/session.py`) and nothing copies it out first.

`events.jsonl` is the only record left, and `images/agent_runner.py` sends it a thin copy:

- A `tool_result` keeps its id and `is_error`, and no content. No `Read` body, `Bash` output or test failure survives.
- `_clip` cuts every tool input string to 200 characters. That cut the commands of 1573 of 8092 `Bash` calls.
- The prompts the agent received are dropped, including the gate failures a repair turn is shown.
- Per-step model, stop reason and `output_tokens` are dropped.

Measured 2026-09-28 over all 128 logs under `~/.saffron/batches/`, 163663 `Agent` events:

| Loss | Count | Characters |
|---|---|---|
| `tool_result` with no content | 18969 | not recorded |
| `_clip` on tool inputs and system data | 5103 fields | 3.69M (`Edit` 2.58M, `Bash` 596K, `Write` 446K) |
| `BOUND_CHARS` on the host | 44 events | 75K, all plan `<output>` text |

The commit keeps what `Edit` and `Write` wrote, as `_MAX_STR`'s comment says.
The tool results and the cut `Bash` commands have no other record.
So a strange PR can show what the agent did, but not what it read before doing it.

Thinking is not a loss. All 10534 thinking blocks carried zero characters, so the raw session would hold only a signature.

## Done looks like

- Before `cell_down` removes the state volume, the host copies the session transcripts out of it.
- They land in the task's batch tree directory, extracted and hashed when copied, like any control artifact.
- The task's events name where each transcript lies and its hash.
- A test starts a cell the way production does, runs one turn, tears the cell down, and finds the transcript on the host.
- `events.jsonl` keeps its bounds. It stays the stream `saffron watch` renders, and the transcript is the full record.

## Record

- 2026-09-28: filed from a by-hand look at where cell conversations are kept.
