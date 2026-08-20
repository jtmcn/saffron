"""Control artifacts: the extraction turn and the plan checkpoint (§5.3).

A control artifact left in the workspace is a claim, not a record. The host
extracts and hashes it the moment it is produced and never reads it from /work
again — a validated plan the implementer then quietly edits is exactly the kind
of failure that leaves no trace in the diff.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re

from pydantic import BaseModel, Field, ValidationError

EXTRACTION_PROMPT = (
    "Emit a single <output> block as the last thing in your response. "
    "Do not change files. Do not run commands. "
    "Do not include text outside the block."
)

_BLOCK = re.compile(r"<output>(.*?)</output>", re.DOTALL)


class PlanRejected(Exception):
    """The plan failed host-side validation. No implementation token is spent."""


class Plan(BaseModel):
    understanding: str
    approach: str
    files_to_change: list[str]
    test_strategy: str
    risks: list[str] = Field(default_factory=list)
    blocking_questions: list[str] = Field(default_factory=list)


def parse_output_block(text: str) -> str:
    match = _BLOCK.search(text)
    if not match:
        raise ValueError("no <output> block in the response")
    return match.group(1).strip()


def hash_artifact(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


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
        raise PlanRejected(f"plan.json is not the schema: {exc}") from exc

    if plan.blocking_questions:
        raise PlanRejected(
            "plan carries a blocking question, which means the spec is "
            f"underspecified: {plan.blocking_questions[0]}"
        )

    for path in plan.files_to_change:
        if not _matches_any(path, touches):
            raise PlanRejected(f"{path} is outside touches")
        if _matches_any(path, forbidden):
            raise PlanRejected(f"{path} is forbidden")
        if _matches_any(path, protected):
            raise PlanRejected(f"{path} is a protected path")

    if spec_type in {"feature", "bug"} and not any(
        "test" in path for path in plan.files_to_change
    ):
        raise PlanRejected(
            f"a {spec_type} plan names no test file — "
            "acceptance criteria that cannot fail are prose"
        )

    return plan
