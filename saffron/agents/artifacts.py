"""Control artifacts: the extraction turn and the plan checkpoint (§5.3).

A control artifact left in the workspace is a claim, not a record. The host
extracts and hashes it the moment it is produced and never reads it from /work
again — a validated plan the implementer then quietly edits is exactly the kind
of failure that leaves no trace in the diff.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath

from pydantic import BaseModel, Field, ValidationError

from saffron.gates.core.scope import matches
from saffron.gates.core.size import _CEILINGS, _DEFAULT_CEILING

EXTRACTION_PROMPT = (
    "Emit a single <output> block as the last thing in your response. "
    "Do not change files. Do not run commands. "
    "Do not include text outside the block."
)

_BLOCK = re.compile(r"<output>(.*?)</output>", re.DOTALL)


class PlanRejected(Exception):
    """The plan failed host-side validation. No *implementation* token is spent
    — but the checkpoint's own turns were, and a shape rejection is final only
    after a second one has run. `plan_checkpoint` sets `spent_usd`."""

    spent_usd: float = 0.0


class PlanNotSchema(PlanRejected):
    """The output was not the schema — a failure of *shape*, not of content.

    The one rejection worth a single bounded re-prompt (§5.3). Every other
    rejection is about what the plan says, and re-asking would be negotiating.
    """


class Plan(BaseModel):
    understanding: str
    approach: str
    files_to_change: list[str]
    test_strategy: str
    risks: list[str] = Field(default_factory=list)
    blocking_questions: list[str] = Field(default_factory=list)
    estimated_lines: int = Field(gt=0)
    """Added + removed, the same count `size_gate` takes off the real diff.
    Required, not defaulted: a ceiling nothing estimates against is not a
    control (§5.3's plan checkpoint spends zero model calls to reject early)."""


def parse_output_block(text: str) -> str:
    # The last block, because that is what EXTRACTION_PROMPT asks for: a draft
    # block followed by the real one would otherwise validate the draft (§5.3).
    blocks = _BLOCK.findall(text)
    if not blocks:
        raise ValueError("no <output> block in the response")
    return blocks[-1].strip()


def hash_artifact(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _matches_any(path: str, patterns: list[str]) -> bool:
    """Same matcher scope_gate uses — a plan that clears this must also clear the gate."""
    return any(matches(path, pattern) for pattern in patterns)


def _names_a_test(path: str) -> bool:
    """What a test runner would collect: pytest's `test_*.py` / `*_test.py`, and
    the same stems for the other ecosystems a target repo might be (`.spec.ts`,
    `Test.java`). Directory names do not count — a plan must name the file."""
    name = PurePosixPath(path).name
    stem = name.split(".")[0]
    return (
        stem.startswith("test_")
        or stem.endswith("_test")
        or stem.endswith("Test")
        or ".test." in name
        or ".spec." in name
    )


def validate_plan(
    raw: str,
    *,
    touches: list[str],
    forbidden: list[str],
    protected: list[str],
    spec_type: str,
) -> Plan:
    """Validate, or raise PlanRejected. Every rule here costs zero model calls."""
    try:
        plan = Plan.model_validate(json.loads(parse_output_block(raw)))
    except (ValueError, ValidationError) as exc:
        raise PlanNotSchema(f"plan.json is not the schema: {exc}") from exc

    if plan.blocking_questions:
        raise PlanRejected(
            "plan carries a blocking question, which means the spec is "
            f"underspecified: {plan.blocking_questions[0]}"
        )

    if not touches:
        raise PlanRejected(
            "the spec declares no touches — a plan cannot be validated "
            "against an empty set"
        )

    for path in plan.files_to_change:
        if not _matches_any(path, touches):
            raise PlanRejected(f"{path} is outside touches")
        if _matches_any(path, forbidden):
            raise PlanRejected(f"{path} is forbidden")
        if _matches_any(path, protected):
            raise PlanRejected(f"{path} is a protected path")

    # The collection convention, not a substring: `"test" in path` is satisfied
    # by `latest_config.py` — and so is `"test" in name`, since "latest" itself
    # contains it. A rule a plan satisfies by accident is not a rule.
    if spec_type in {"feature", "bug"} and not any(
        _names_a_test(path) for path in plan.files_to_change
    ):
        raise PlanRejected(
            f"a {spec_type} plan names no test file — "
            "acceptance criteria that cannot fail are prose"
        )

    ceiling = _CEILINGS.get(spec_type, _DEFAULT_CEILING)
    if plan.estimated_lines > ceiling:
        raise PlanRejected(
            f"plan's own estimate of {plan.estimated_lines} changed lines "
            f"exceeds the {spec_type} ceiling of {ceiling} — the diff `size` "
            "gate will fail on before a single edit is made"
        )

    return plan
