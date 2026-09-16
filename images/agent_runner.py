"""The agent, running inside the cell (DESIGN.md §5.1).

**This is the only file in Saffron permitted to touch Agent SDK types.** The
host reads Saffron's own event schema off stdout and never the SDK's, so an SDK
change stops here instead of reaching the orchestrator — the same seam
discipline `saffron/cell/runtime.py` keeps for the container runtime.

Transport: one JSON request on stdin, one JSON event per line on stdout,
flushed as it goes. Exits non-zero if no result event was ever produced — an
absent result must never read as a clean one.
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

# A tool input carries whole file bodies; the commit is the record of what was
# written, so the stream carries only enough to see what the agent is doing.
_MAX_STR = 200

# The result's usage is cumulative over the whole query() call; an assistant
# message's own usage is that one step's. output_tokens is not carried per
# step: the SDK's own cost-tracking docs say it is not accurate there, and
# only the total is in scope for it (spec's Out of scope).
_RESULT_USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)
_STEP_USAGE_KEYS = (
    "input_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)

# One unit of work can be delivered as several assistant messages sharing a
# message_id, each reporting the same usage. Module state on purpose: one
# runner process is one run_agent call, so this outlives nothing it shouldn't.
_seen_assistant_message_ids: set[str] = set()


def _usage_counts(usage: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    """Read named counts out of an SDK `usage` mapping, or null them.

    Never `or None` / `or 0`: a reported 0 must survive, and a key the SDK
    stops sending must read as absent rather than silently zero.
    """
    if not isinstance(usage, dict):
        return dict.fromkeys(keys)
    return {key: usage.get(key) for key in keys}


def _emit(event: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def _clip(value: Any) -> Any:
    if isinstance(value, str) and len(value) > _MAX_STR:
        return value[:_MAX_STR] + f"…(+{len(value) - _MAX_STR} chars)"
    if isinstance(value, dict):
        return {k: _clip(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clip(v) for v in value]
    return value


def _block_event(block: Any) -> dict[str, Any]:
    """One content block, by the attributes it carries rather than its class.

    Duck-typed on purpose: an SDK that adds a block type produces a passthrough
    here, never a crash inside a cell the host cannot see into.
    """
    if isinstance(block, dict):
        return {"type": "passthrough", "kind": str(block.get("type", "dict"))}
    if hasattr(block, "text"):
        return {"type": "text", "text": block.text}
    if hasattr(block, "thinking"):
        return {"type": "thinking", "chars": len(block.thinking)}
    if hasattr(block, "name") and hasattr(block, "input"):
        return {
            "type": "tool_use",
            "id": getattr(block, "id", None),
            "name": block.name,
            "input": _clip(block.input),
        }
    if hasattr(block, "tool_use_id"):
        return {
            "type": "tool_result",
            "tool_use_id": block.tool_use_id,
            "is_error": bool(getattr(block, "is_error", False)),
        }
    return {"type": "passthrough", "kind": type(block).__name__}


def events(message: Any) -> list[dict[str, Any]]:
    """Saffron events for one SDK message. Never raises on an unknown shape."""
    # Before the result branch, which also keys on `session_id`: a rate limit
    # event carries one and no `num_turns`. This is the provider's own ceiling,
    # the only one the cell is subject to rather than merely reporting (§5.1) —
    # as a passthrough it reaches the host as four failed repair attempts.
    if (info := getattr(message, "rate_limit_info", None)) is not None:
        return [
            {
                "type": "rate_limit",
                "status": getattr(info, "status", None),
                "utilization": getattr(info, "utilization", None),
                "resets_at": getattr(info, "resets_at", None),
            }
        ]
    # Result first: it also carries `subtype`, which every system message has.
    if hasattr(message, "num_turns") and hasattr(message, "session_id"):
        event = {
            "type": "result",
            "subtype": getattr(message, "subtype", "unknown"),
            "num_turns": getattr(message, "num_turns", 0),
            "total_cost_usd": getattr(message, "total_cost_usd", None) or 0.0,
            "session_id": getattr(message, "session_id", None),
            "terminal_reason": getattr(message, "terminal_reason", None),
            "is_error": bool(getattr(message, "is_error", False)),
        }
        event.update(_usage_counts(getattr(message, "usage", None), _RESULT_USAGE_KEYS))
        return [event]
    if hasattr(message, "content"):
        content = message.content
        blocks = content if isinstance(content, list) else []
        if hasattr(message, "model"):  # assistant
            evts = [_block_event(block) for block in blocks]
            usage = getattr(message, "usage", None)
            message_id = getattr(message, "message_id", None)
            unseen = message_id is None or message_id not in _seen_assistant_message_ids
            if isinstance(usage, dict) and evts and unseen:
                evts[0].update(_usage_counts(usage, _STEP_USAGE_KEYS))
                if message_id is not None:
                    _seen_assistant_message_ids.add(message_id)
            return evts
        # A user message is the host's own prompt echoed back, or tool results.
        # Its text is never the agent's, so it must not reach `text` events —
        # the host reads those for the <output> block (§5.3).
        results = [b for b in blocks if hasattr(b, "tool_use_id")]
        return [_block_event(b) for b in results] or [
            {"type": "passthrough", "kind": type(message).__name__}
        ]
    if hasattr(message, "subtype"):
        return [
            {
                "type": "system",
                "subtype": message.subtype,
                "data": _clip(getattr(message, "data", {})),
            }
        ]
    return [{"type": "passthrough", "kind": type(message).__name__}]


async def _run(request: dict[str, Any]) -> int:
    from claude_agent_sdk import ClaudeAgentOptions, query

    options = dict(request.get("options") or {})
    if request.get("resume"):
        options["resume"] = request["resume"]

    saw_result = False
    async for message in query(
        prompt=request["prompt"], options=ClaudeAgentOptions(**options)
    ):
        for event in events(message):
            _emit(event)
            saw_result = saw_result or event["type"] == "result"
    return 0 if saw_result else 1


def main() -> int:
    try:
        request = json.load(sys.stdin)
        return asyncio.run(_run(request))
    except Exception as exc:  # noqa: BLE001 — a crash in here must still be an event
        _emit({"type": "error", "error": f"{type(exc).__name__}: {exc}"})
        return 1


if __name__ == "__main__":
    sys.exit(main())
