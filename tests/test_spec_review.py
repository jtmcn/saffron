import copy
import json
from functools import partial

import pytest

from saffron.phases import implement


def _block(obj: object, *, lang: str = "json") -> str:
    return f"```{lang}\n{json.dumps(obj)}\n```"


def _fenced(body: str, *, lang: str = "json") -> str:
    """A fence around raw text, never `json.dumps`, so the criterion-5
    witness can tell the kept block apart from a re-serialized one."""
    return f"```{lang}\n{body}\n```"


def _session(text: str, *, cost: float = 0.5, error=None, resets_at=None):
    from saffron.spec_review import SpecReviewSession

    return SpecReviewSession(text=text, cost_usd=cost, error=error, resets_at=resets_at)


def _attempt(
    *,
    session_id=None,
    cost=0.0,
    num_turns=0,
    status=None,
    resets_at=None,
    structured_output=None,
    text="",
):
    """An `AttemptResult` as `run_agent` would return it. Pre-existing
    shape, never a name this spec adds, so it stays importable at module
    scope for a reverted run."""
    return implement.AttemptResult(
        session_id=session_id,
        subtype="success",
        terminal_reason=None,
        num_turns=num_turns,
        cost_usd_est=cost,
        text=text,
        is_error=False,
        bound="",
        rate_limit_status=status,
        rate_limit_resets_at=resets_at,
        structured_output=structured_output,
    )


_KILLED = object()


class _Agent:
    """Records each call and plays back one scripted outcome per call: an
    `AttemptResult` to return, an exception to raise, or `_KILLED`. The
    killed case builds the no-result-event failure from that call's own
    `last_cost_usd`, the way `run_agent` builds it."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        assert self.script, "unexpected call"
        outcome = self.script.pop(0)
        if outcome is _KILLED:
            killed = implement.AttemptResult(
                session_id=None,
                subtype="error",
                terminal_reason=None,
                num_turns=0,
                cost_usd_est=kwargs.get("last_cost_usd", 0.0),
                text="",
                is_error=True,
                bound="",
                rate_limit_status=None,
                rate_limit_resets_at=None,
                structured_output=None,
            )
            raise implement.AgentFailed("the agent produced no result event", killed)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


# A first-turn text: prose, a fenced block, then an <output> block. The
# session must never read it into `text`, its own extraction turn does.
_J_FINDING = {
    "claim": "c",
    "criterion": 1,
    "file": "f.py",
    "line": 1,
    "severity": "blocker",
    "fixes": "scope",
}
J = (
    "Some prose about the spec.\n\n"
    + _block({"findings": [_J_FINDING]})
    + "\n\n<output>\n"
    + json.dumps({"findings": [_J_FINDING]})
    + "\n</output>\n"
)

# The extraction turn's structured value, keys in the model's own order.
D = {
    "findings": [
        {
            "severity": "blocker",
            "claim": "naïve read",
            "criterion": 1,
            "file": "a.py",
            "line": 3,
            "fixes": "build",
        },
        {
            "severity": "note",
            "claim": "the title runs long",
            "criterion": None,
            "file": None,
            "line": None,
            "fixes": None,
        },
    ]
}

# `D`, with each finding's own keys in reverse order. Validating it still
# gives back `D`'s order, because a model normalizes to its own fields.
V = {"findings": [dict(reversed(list(f.items()))) for f in D["findings"]]}

# A second-turn text: prose, an <output> block, then a fenced json block.
# Each block holds one scope blocker, and each parses on its own.
T = (
    "Some review prose.\n\n"
    "<output>\n"
    + json.dumps({"findings": [_J_FINDING]})
    + "\n</output>\n\n"
    + _block({"findings": [_J_FINDING]})
)

# The host's own serialization of `D`: what a clean extraction turn gives.
F = "```json\n" + json.dumps(D, indent=2, ensure_ascii=False) + "\n```\n"

# `V`, dumped as a plain JSON string rather than validated as a value.
S = json.dumps(V)

# What the criteria 1, 2 and 5 witnesses pass `run_spec_review`. Each helper
# imports this spec's names inside its body, so a reverted run skips no test.
_CONTAINER = "c-1"
_SYSTEM_PROMPT = "sys"
_PROMPT = "p"


def _first_options():
    from saffron.spec_review import (
        SPEC_REVIEW_BUDGET_USD,
        SPEC_REVIEW_MAX_TURNS,
        SPEC_SESSION_TOOLS,
    )

    return implement.agent_options(
        system_prompt=_SYSTEM_PROMPT,
        max_turns=SPEC_REVIEW_MAX_TURNS,
        budget_usd=SPEC_REVIEW_BUDGET_USD,
        tools=SPEC_SESSION_TOOLS,
    )


def _extract_options():
    from saffron.spec_review import SPEC_REVIEW_EXTRACT_BUDGET_USD, SPEC_REVIEW_FORMAT

    return _first_options() | {
        "max_budget_usd": SPEC_REVIEW_EXTRACT_BUDGET_USD,
        "output_format": SPEC_REVIEW_FORMAT,
    }


def _run(double):
    from saffron.spec_review import run_spec_review

    return run_spec_review(
        _CONTAINER, system_prompt=_SYSTEM_PROMPT, prompt=_PROMPT, agent=double
    )


def _first(**overrides):
    return _attempt(
        **{"text": J, "cost": 0.5, "session_id": "s-1", "num_turns": 7} | overrides
    )


def _second(**overrides):
    base = {
        "text": T,
        "cost": 0.25,
        "session_id": "s-2",
        "num_turns": 2,
        "structured_output": V,
    }
    return _attempt(**base | overrides)


def _assert_first_call(double):
    args, kwargs = double.calls[0]
    assert args == (_CONTAINER,)
    assert kwargs == {"prompt": _PROMPT, "options": _first_options()}


def test_a_spec_review_routes_on_the_severities_in_its_last_json_block(monkeypatch):
    from saffron import spec_review as sr

    finding = {"claim": "c", "criterion": 1, "file": "f.py", "line": 1}

    rows = [
        (_session(_block({"findings": []})), "run"),
        (_session(_block({"findings": [{**finding, "severity": "note"}]})), "run"),
        (
            _session(
                _block(
                    {
                        "findings": [
                            {**finding, "severity": "concern", "fixes": "witness"}
                        ]
                    }
                )
            ),
            "run",
        ),
        (
            _session(
                _block(
                    {
                        "findings": [
                            {**finding, "severity": "blocker", "fixes": "scope"},
                            {**finding, "severity": "blocker", "fixes": "build"},
                            {**finding, "severity": "blocker", "fixes": "witness"},
                        ]
                    }
                )
            ),
            "escalate",
        ),
        (
            _session(
                _block(
                    {
                        "findings": [
                            {**finding, "severity": "blocker", "fixes": None},
                            {**finding, "severity": "blocker"},
                        ]
                    }
                )
            ),
            "escalate",
        ),
        (
            _session(
                _block(
                    {"findings": [{**finding, "severity": "note", "evidence": "extra"}]}
                )
            ),
            "run",
        ),
        (_session(_block({"findings": []}), error="boom"), "error"),
        (_session("no fence here at all"), "error"),
        (_session(_block({"findings": []}, lang="text")), "error"),
        (_session("```json\nnot json at all\n```"), "error"),
        (_session(_block([{**finding, "severity": "blocker"}])), "error"),
        (_session(_block({"nope": []})), "error"),
        (_session(_block({"findings": ""})), "error"),
        (_session(_block({"findings": [{**finding, "severity": "Blocker"}]})), "error"),
        (
            _session(_block({"findings": [{**finding, "severity": "critical"}]})),
            "error",
        ),
        (
            _session(
                _block(
                    {
                        "findings": [
                            {**finding, "severity": "blocker", "fixes": "rewrite"}
                        ]
                    }
                )
            ),
            "error",
        ),
        (
            _session(
                _block(
                    {
                        "findings": [
                            {**finding, "severity": "concern", "fixes": "rewrite"}
                        ]
                    }
                )
            ),
            "error",
        ),
        (
            _session(_block({"findings": [{**finding, "severity": "note"}, "nope"]})),
            "error",
        ),
        (
            _session(
                _block(
                    {
                        "findings": [
                            {
                                "severity": "note",
                                "criterion": 1,
                                "file": "f",
                                "line": 1,
                            }
                        ]
                    }
                )
            ),
            "error",
        ),
        (
            _session(
                _block({"findings": [{**finding, "severity": "blocker"}]})
                + "\n"
                + _block({"findings": []})
            ),
            "run",
        ),
        (
            _session(
                _block({"findings": []})
                + "\n"
                + _block({"findings": [{**finding, "severity": "blocker"}]})
            ),
            "escalate",
        ),
        (
            _session(
                _block({"findings": [{**finding, "severity": "blocker"}]}),
                resets_at=1893456000,
            ),
            "wait",
        ),
        (
            _session("no fence here at all", error="boom", resets_at=1893456000),
            "wait",
        ),
    ]

    for session, expected in rows:
        review = sr.read_spec_review(session)
        assert sr.spec_review_route(review) == expected
        assert review.cost_usd == 0.5

    first, second = rows[0][0], rows[1][0]
    assert sr.read_spec_review(first).cost_usd == 0.5
    assert sr.read_spec_review(second).cost_usd == 0.5

    concern_review = sr.read_spec_review(rows[2][0])
    assert concern_review.findings[0].fixes == "witness"

    mid_claim = _session(
        _block(
            {
                "findings": [
                    {
                        **finding,
                        "severity": "note",
                        "claim": "output shows ``` embedded",
                    }
                ]
            }
        )
    )
    assert sr.spec_review_route(sr.read_spec_review(mid_claim)) == "run"

    assert sr.SPEC_REVIEW_TAGS == ("scope", "build", "witness")
    assert isinstance(sr.SPEC_REVIEW_TAGS, tuple)

    monkeypatch.setattr(sr, "SPEC_REVIEW_TAGS", (*sr.SPEC_REVIEW_TAGS, "rewrite"))
    patched = _session(
        _block({"findings": [{**finding, "severity": "blocker", "fixes": "rewrite"}]})
    )
    assert sr.spec_review_route(sr.read_spec_review(patched)) == "escalate"


def test_a_spec_review_carries_its_last_json_block_and_its_hash():
    from saffron.agents.artifacts import hash_artifact
    from saffron.spec_review import read_spec_review

    # Two spaces after the colon, so a block serialised again through
    # `json.dumps` reads differently from the text kept here.
    clean = '{"findings":  []}'
    blocker = (
        '{"findings": [{"severity": "blocker", "claim": "c", '
        '"criterion": 1, "file": "f", "line": 1}]}'
    )

    rows = [
        (_session(_fenced(clean)), clean),
        (_session(_fenced(blocker)), blocker),
        (_session(_fenced(clean), error="boom"), clean),
        (_session(_fenced(clean), resets_at=1893456000), clean),
        (_session(_fenced(blocker) + "\n" + _fenced(clean)), clean),
        (_session(_fenced(clean, lang="text")), None),
        (_session("no fence here at all"), None),
        (_session(_fenced("not json")), "not json"),
        (_session(_fenced(f"\n  {clean}  \n")), clean),
    ]

    for session, expected in rows:
        review = read_spec_review(session)
        assert review.block == expected
        expected_hash = hash_artifact(expected) if expected is not None else None
        assert review.block_sha256 == expected_hash


def test_a_spec_review_session_returns_a_rejected_window_as_a_reset_time():
    from saffron.spec_review import (
        SPEC_REVIEW_BUDGET_USD,
        SPEC_REVIEW_EXTRACT_BUDGET_USD,
        SPEC_REVIEW_MAX_TURNS,
        SPEC_REVIEW_SESSION_USD,
        SPEC_REVIEW_TIMEOUT_S,
        SPEC_SESSION_TOOLS,
        UNREADABLE_RESET,
        SpecReviewSession,
    )

    assert SPEC_REVIEW_MAX_TURNS == 90
    assert SPEC_REVIEW_BUDGET_USD == 6.0
    assert SPEC_REVIEW_EXTRACT_BUDGET_USD == 1.0
    assert SPEC_REVIEW_SESSION_USD == 8.0
    assert SPEC_REVIEW_TIMEOUT_S == 1800.0
    assert UNREADABLE_RESET == 1
    assert sorted(SPEC_SESSION_TOOLS) == ["Bash", "Glob", "Grep", "Read"]

    def _assert_one_call(double):
        assert len(double.calls) == 1
        _assert_first_call(double)
        assert "output_format" not in double.calls[0][1]["options"]

    # Returned, rejected.
    double = _Agent(
        [
            _attempt(
                text=J,
                cost=0.25,
                status="rejected",
                resets_at=1755800000,
                session_id="s-1",
                num_turns=7,
            )
        ]
    )
    result = _run(double)
    _assert_one_call(double)
    assert result == SpecReviewSession(
        text="",
        cost_usd=0.25,
        error=None,
        resets_at=1755800000,
        session_id="s-1",
        num_turns=7,
    )
    assert type(result.resets_at) is int

    # Raised, rejected, a huge but clean reset.
    double = _Agent(
        [
            implement.AgentFailed(
                "api_error",
                _attempt(
                    status="rejected",
                    resets_at=10**20,
                    cost=0.125,
                    session_id="s-1",
                    num_turns=3,
                ),
            )
        ]
    )
    result = _run(double)
    _assert_one_call(double)
    assert result == SpecReviewSession(
        text="",
        cost_usd=0.125,
        error=None,
        resets_at=10**20,
        session_id="s-1",
        num_turns=3,
    )
    assert type(result.resets_at) is int

    # The same, but the reset is unreadable or at or below 0.
    for bad_reset in (None, "soon", True, 1755800000.0, 0, -5):
        double = _Agent(
            [
                implement.AgentFailed(
                    "api_error",
                    _attempt(
                        status="rejected",
                        resets_at=bad_reset,
                        cost=0.125,
                        session_id="s-1",
                        num_turns=3,
                    ),
                )
            ]
        )
        result = _run(double)
        _assert_one_call(double)
        assert result == SpecReviewSession(
            text="",
            cost_usd=0.125,
            error=None,
            resets_at=UNREADABLE_RESET,
            session_id="s-1",
            num_turns=3,
        )
        assert type(result.resets_at) is int

    # Raised, not rejected, with an attempt.
    double = _Agent(
        [
            implement.AgentFailed(
                "idle bound",
                _attempt(text=J, cost=0.0625, session_id="s-1", num_turns=7),
            )
        ]
    )
    result = _run(double)
    _assert_one_call(double)
    assert result == SpecReviewSession(
        text="",
        cost_usd=0.0625,
        error="idle bound",
        resets_at=None,
        session_id="s-1",
        num_turns=7,
    )

    # Raised, with no attempt at all.
    double = _Agent([implement.AgentFailed("no result")])
    result = _run(double)
    _assert_one_call(double)
    assert result == SpecReviewSession(
        text="",
        cost_usd=0.0,
        error="no result",
        resets_at=None,
        session_id=None,
        num_turns=0,
    )

    # Any other exception propagates.
    double = _Agent([RuntimeError("runner died")])
    with pytest.raises(RuntimeError):
        _run(double)
    assert len(double.calls) == 1


def test_a_spec_review_returns_its_tags_from_a_separate_extraction_turn():
    from saffron.spec_review import (
        SPEC_REVIEW_EXTRACT_PROMPT,
        SPEC_REVIEW_FORMAT,
        SpecReviewSession,
        _SpecReviewFindings,
    )

    def _assert_second_call(double, *, last_cost_usd=0.5):
        args, kwargs = double.calls[1]
        assert args == (_CONTAINER,)
        assert kwargs == {
            "prompt": SPEC_REVIEW_EXTRACT_PROMPT,
            "options": _extract_options(),
            "resume": "s-1",
            "last_cost_usd": last_cost_usd,
        }

    # First status none, second returns.
    double = _Agent([_first(), _second()])
    result = _run(double)
    assert len(double.calls) == 2
    _assert_first_call(double)
    _assert_second_call(double)
    assert result == SpecReviewSession(
        text=F,
        cost_usd=0.75,
        error=None,
        resets_at=None,
        session_id="s-2",
        num_turns=9,
    )
    assert "scope" not in result.text

    # First status allowed, reset 9, the same second turn.
    double = _Agent([_first(status="allowed", resets_at=9), _second()])
    result = _run(double)
    assert len(double.calls) == 2
    _assert_second_call(double)
    assert result == SpecReviewSession(
        text=F,
        cost_usd=0.75,
        error=None,
        resets_at=None,
        session_id="s-2",
        num_turns=9,
    )

    # Second returns V with its first finding's `fixes` retagged.
    v_typo = copy.deepcopy(V)
    v_typo["findings"][0]["fixes"] = "typo"
    d_typo = copy.deepcopy(D)
    d_typo["findings"][0]["fixes"] = "typo"
    f_typo = "```json\n" + json.dumps(d_typo, indent=2, ensure_ascii=False) + "\n```\n"
    double = _Agent([_first(), _second(structured_output=v_typo)])
    result = _run(double)
    assert len(double.calls) == 2
    assert result == SpecReviewSession(
        text=f_typo,
        cost_usd=0.75,
        error=None,
        resets_at=None,
        session_id="s-2",
        num_turns=9,
    )
    assert "scope" not in result.text

    # Second returns with no session_id.
    double = _Agent([_first(), _second(session_id=None)])
    result = _run(double)
    assert len(double.calls) == 2
    assert result == SpecReviewSession(
        text=F,
        cost_usd=0.75,
        error=None,
        resets_at=None,
        session_id="s-1",
        num_turns=9,
    )

    # First returns no session_id: no second call.
    double = _Agent([_first(session_id=None)])
    result = _run(double)
    assert len(double.calls) == 1
    _assert_first_call(double)
    assert result == SpecReviewSession(
        text="",
        cost_usd=0.5,
        error="no session to extract from",
        resets_at=None,
        session_id=None,
        num_turns=7,
    )

    # Second returns rejected, reset 9.
    double = _Agent([_first(), _second(status="rejected", resets_at=9)])
    result = _run(double)
    assert len(double.calls) == 2
    _assert_second_call(double)
    assert result == SpecReviewSession(
        text="", cost_usd=0.75, error=None, resets_at=9, session_id="s-2", num_turns=9
    )
    assert type(result.resets_at) is int

    # Second returns rejected, reset -5.
    double = _Agent([_first(), _second(status="rejected", resets_at=-5)])
    result = _run(double)
    assert len(double.calls) == 2
    assert result == SpecReviewSession(
        text="", cost_usd=0.75, error=None, resets_at=1, session_id="s-2", num_turns=9
    )

    # Second raises AgentFailed("api_error"), rejected, reset "soon".
    double = _Agent(
        [
            _first(),
            implement.AgentFailed(
                "api_error",
                _attempt(
                    status="rejected",
                    resets_at="soon",
                    cost=0.25,
                    session_id="s-2",
                    num_turns=2,
                ),
            ),
        ]
    )
    result = _run(double)
    assert len(double.calls) == 2
    _assert_second_call(double)
    assert result == SpecReviewSession(
        text="", cost_usd=0.75, error=None, resets_at=1, session_id="s-2", num_turns=9
    )

    # Second raises AgentFailed("cut") with an attempt.
    double = _Agent(
        [
            _first(),
            implement.AgentFailed(
                "cut", _attempt(cost=0.25, session_id="s-2", num_turns=2)
            ),
        ]
    )
    result = _run(double)
    assert len(double.calls) == 2
    assert result == SpecReviewSession(
        text="",
        cost_usd=0.75,
        error="cut",
        resets_at=None,
        session_id="s-2",
        num_turns=9,
    )

    # Second raises AgentFailed("gone") with no attempt.
    double = _Agent([_first(), implement.AgentFailed("gone")])
    result = _run(double)
    assert len(double.calls) == 2
    assert result == SpecReviewSession(
        text="",
        cost_usd=0.5,
        error="gone",
        resets_at=None,
        session_id="s-1",
        num_turns=7,
    )

    # Second is the killed turn.
    double = _Agent([_first(), _KILLED])
    result = _run(double)
    assert len(double.calls) == 2
    _assert_second_call(double)
    assert result == SpecReviewSession(
        text="",
        cost_usd=1.0,
        error="the agent produced no result event",
        resets_at=None,
        session_id="s-1",
        num_turns=7,
    )

    # First at cost 4.0, second the killed turn: `last_cost_usd` caps at 1.0.
    double = _Agent([_first(cost=4.0), _KILLED])
    result = _run(double)
    assert len(double.calls) == 2
    _assert_second_call(double, last_cost_usd=1.0)
    assert result == SpecReviewSession(
        text="",
        cost_usd=5.0,
        error="the agent produced no result event",
        resets_at=None,
        session_id="s-1",
        num_turns=7,
    )

    # Second raises an exception the module does not know about.
    double = _Agent([_first(), RuntimeError("boom")])
    with pytest.raises(RuntimeError):
        _run(double)
    assert len(double.calls) == 2

    # The schema itself.
    root = _SpecReviewFindings.model_json_schema()
    assert {"type": "json_schema", "schema": root} == SPEC_REVIEW_FORMAT
    assert root["type"] == "object"
    assert root["required"] == ["findings"]
    assert root["additionalProperties"] is False
    items = root["properties"]["findings"]["items"]
    ref = items["$ref"].removeprefix("#/$defs/")
    finding_schema = root["$defs"][ref]
    field_order = ["severity", "claim", "criterion", "file", "line", "fixes"]
    assert list(finding_schema["properties"]) == field_order
    assert finding_schema["required"] == field_order
    assert finding_schema["additionalProperties"] is False
    assert finding_schema["properties"]["severity"]["enum"] == [
        "blocker",
        "concern",
        "note",
    ]
    for name in ("criterion", "file", "line", "fixes"):
        any_of = finding_schema["properties"][name]["anyOf"]
        assert {"type": "null"} in any_of
    fixes_schema = json.dumps(finding_schema["properties"]["fixes"])
    assert "enum" not in fixes_schema
    assert "const" not in fixes_schema


def test_the_spec_review_system_prompt_fills_the_repos_declarations_into_cores_template(
    tmp_path, monkeypatch
):
    import saffron.spec_review as sr
    from saffron.gates.core import size
    from saffron.repos.policy import GateDeclaration, Policy

    template_path = tmp_path / "spec-review.md"
    template_path.write_text(
        "G\n{gates}\nP\n{protected}\nE\n{elevate_on}\nC\n{ceilings}\nT\n{tags}\n"
    )

    policy = Policy(
        gates={
            "tests": GateDeclaration(blocking=True),
            "lint": GateDeclaration(blocking=False),
        },
        protected=["uv.lock", "docs/{a,b}.md"],
        elevate_on=["saffron/ledger.py"],
    )
    monkeypatch.setitem(size._CEILINGS, "feature", 2999)

    expected = (
        "G\n"
        "- `tests`\n"
        "- `lint` (advisory)\n"
        "P\n"
        "- `uv.lock`\n"
        "- `docs/{a,b}.md`\n"
        "E\n"
        "- `saffron/ledger.py`\n"
        "C\n"
        "- `bug`: 1300 changed tokens\n"
        "- `feature`: 2999 changed tokens\n"
        "- `refactor`: 4200 changed tokens\n"
        "- any other type: 4200 changed tokens\n"
        "T\n"
        "- `scope`\n"
        "- `build`\n"
        "- `witness`\n"
    )
    assert sr.spec_review_system_prompt(policy, prompts_dir=tmp_path) == expected
    assert sr.SPEC_REVIEW_PROMPT == "spec-review.md"

    empty_expected = (
        "G\n"
        "none\n"
        "P\n"
        "none\n"
        "E\n"
        "none\n"
        "C\n"
        "- `bug`: 1300 changed tokens\n"
        "- `feature`: 2999 changed tokens\n"
        "- `refactor`: 4200 changed tokens\n"
        "- any other type: 4200 changed tokens\n"
        "T\n"
        "- `scope`\n"
        "- `build`\n"
        "- `witness`\n"
    )
    assert (
        sr.spec_review_system_prompt(Policy(), prompts_dir=tmp_path) == empty_expected
    )

    monkeypatch.setattr(sr, "SPEC_REVIEW_TAGS", ("x", "y"))
    tagged_expected = expected.replace(
        "T\n- `scope`\n- `build`\n- `witness`\n", "T\n- `x`\n- `y`\n"
    )
    assert sr.spec_review_system_prompt(policy, prompts_dir=tmp_path) == tagged_expected

    template_path.write_text("only {tags}\n")
    assert (
        sr.spec_review_system_prompt(policy, prompts_dir=tmp_path)
        == "only - `x`\n- `y`\n"
    )


def test_cores_spec_review_prompts_fill_every_slot_and_name_no_repo_tool():
    from saffron.agents import artifacts, context
    from saffron.repos.policy import GateDeclaration, Policy
    from saffron.spec_review import (
        SPEC_REVIEW_EXTRACT_PROMPT,
        spec_review_system_prompt,
    )

    policy = Policy(
        gates={
            "tests": GateDeclaration(blocking=True),
            "lint": GateDeclaration(blocking=False),
        },
        protected=["uv.lock", "docs/{a,b}.md"],
        elevate_on=["saffron/ledger.py"],
    )
    rendered = spec_review_system_prompt(policy, prompts_dir=context.PROMPTS_DIR)
    for slot in ("{gates}", "{protected}", "{elevate_on}", "{ceilings}", "{tags}"):
        assert slot not in rendered
    for block in (
        "- `tests`",
        "- `lint` (advisory)",
        "- `uv.lock`",
        "- `docs/{a,b}.md`",
        "- `saffron/ledger.py`",
        "- `feature`: 3000 changed tokens",
        "- any other type: 4200 changed tokens",
        "- `scope`",
        "- `build`",
        "- `witness`",
    ):
        assert block in rendered

    assert context.turn_prompt("spec-review-extract") == SPEC_REVIEW_EXTRACT_PROMPT
    for name in (
        "findings",
        "severity",
        "claim",
        "fixes",
        "blocker",
        "concern",
        "note",
        "witness",
    ):
        assert name in SPEC_REVIEW_EXTRACT_PROMPT

    lines = SPEC_REVIEW_EXTRACT_PROMPT.splitlines()
    for line in (
        "Answer now in the required structured format.",
        "Do not change files.",
        "Do not run commands.",
    ):
        assert line in lines

    assert artifacts.EXTRACTION_PROMPT not in SPEC_REVIEW_EXTRACT_PROMPT
    raw_extract = (context.TURNS_DIR / "spec-review-extract.md").read_text()
    assert "{extraction}" not in raw_extract

    raw_review = (context.PROMPTS_DIR / "spec-review.md").read_text()
    flat_review = " ".join(raw_review.split())
    assert (
        "A concern that a criterion's witness cannot be measured carries "
        "`witness`." in flat_review
    )

    flat_extract = " ".join(raw_extract.split())
    assert (
        "Copy each finding's `fixes` exactly as your review gave it, and "
        "decide no tag from the prose." in flat_extract
    )

    forbidden = [
        ".claude",
        "CLAUDE.md",
        "DESIGN.md",
        "CONTEXT.md",
        "driver.py",
        "pytest",
        "uv run",
        "make check",
        "ruff",
        "prek",
        "saffron/",
        "docs/",
        "/opt/",
        "://",
        "the reviewer",
        "<output>",
        "output block",
    ]
    review_lower = raw_review.lower()
    extract_lower = raw_extract.lower()
    for word in forbidden:
        assert word.lower() not in review_lower
        assert word.lower() not in extract_lower


def test_a_spec_review_re_asks_once_when_its_extraction_is_not_the_schema():
    from saffron.spec_review import SPEC_REVIEW_EXTRACT_PROMPT, SpecReviewSession

    # The re-ask: the second turn answers with nothing structured by default.
    _second_null = partial(_second, structured_output=None)
    _third = partial(_second, session_id="s-3")

    def _assert_third_call(double, *, resume, last_cost_usd, prompt_text=None):
        """`prompt_text` `None` checks only the refusal's shape, for a row
        whose validation message the test does not spell out."""
        args, kwargs = double.calls[2]
        assert args == (_CONTAINER,)
        assert set(kwargs) == {"prompt", "options", "resume", "last_cost_usd"}
        assert kwargs["options"] == _extract_options()
        assert kwargs["resume"] == resume
        assert kwargs["last_cost_usd"] == last_cost_usd
        if prompt_text is None:
            assert kwargs["prompt"].startswith("not the schema: ")
            assert kwargs["prompt"].endswith("\n\n" + SPEC_REVIEW_EXTRACT_PROMPT)
        else:
            assert kwargs["prompt"] == prompt_text

    reask_prompt_null = (
        "not the schema: the turn returned no structured output"
        "\n\n" + SPEC_REVIEW_EXTRACT_PROMPT
    )

    v_no_claim = copy.deepcopy(V)
    del v_no_claim["findings"][0]["claim"]

    v_critical = copy.deepcopy(V)
    v_critical["findings"][0]["severity"] = "critical"

    v_extra_key = copy.deepcopy(V)
    v_extra_key["findings"][0]["note"] = "extra"

    # Every refused-value row: the second turn's own value, then a clean
    # third turn that returns `V`. All five give the same result.
    for bad_value in (v_no_claim, v_critical, v_extra_key, S):
        double = _Agent([_first(), _second_null(structured_output=bad_value), _third()])
        result = _run(double)
        assert len(double.calls) == 3
        _assert_third_call(double, resume="s-2", last_cost_usd=0.25)
        assert result == SpecReviewSession(
            text=F,
            cost_usd=1.0,
            error=None,
            resets_at=None,
            session_id="s-3",
            num_turns=11,
        )
        assert "scope" not in result.text

    # A null value, then a clean third turn.
    double = _Agent([_first(), _second_null(), _third()])
    result = _run(double)
    assert len(double.calls) == 3
    _assert_third_call(
        double, prompt_text=reask_prompt_null, resume="s-2", last_cost_usd=0.25
    )
    assert result == SpecReviewSession(
        text=F, cost_usd=1.0, error=None, resets_at=None, session_id="s-3", num_turns=11
    )
    assert "scope" not in result.text

    # A null value, second carries no session_id: the re-ask resumes the first.
    double = _Agent([_first(), _second_null(session_id=None), _third()])
    result = _run(double)
    assert len(double.calls) == 3
    _assert_third_call(
        double, prompt_text=reask_prompt_null, resume="s-1", last_cost_usd=0.25
    )
    assert result == SpecReviewSession(
        text=F, cost_usd=1.0, error=None, resets_at=None, session_id="s-3", num_turns=11
    )

    # Third also returns nothing structured: no fourth call.
    double = _Agent([_first(), _second_null(), _third(structured_output=None)])
    result = _run(double)
    assert len(double.calls) == 3
    assert result == SpecReviewSession(
        text="",
        cost_usd=1.0,
        error="not the schema: the turn returned no structured output",
        resets_at=None,
        session_id="s-3",
        num_turns=11,
    )

    # Third returns a refused value: no fourth call.
    double = _Agent([_first(), _second_null(), _third(structured_output=S)])
    result = _run(double)
    assert len(double.calls) == 3
    assert result.text == ""
    assert result.error is not None and result.error.startswith("not the schema: ")
    assert result.cost_usd == 1.0
    assert result.resets_at is None
    assert result.session_id == "s-3"
    assert result.num_turns == 11

    # Third returns V with no session_id.
    double = _Agent([_first(), _second_null(), _third(session_id=None)])
    result = _run(double)
    assert len(double.calls) == 3
    assert result == SpecReviewSession(
        text=F, cost_usd=1.0, error=None, resets_at=None, session_id="s-2", num_turns=11
    )

    # Third returns rejected, reset 9.
    double = _Agent([_first(), _second_null(), _third(status="rejected", resets_at=9)])
    result = _run(double)
    assert len(double.calls) == 3
    assert result == SpecReviewSession(
        text="", cost_usd=1.0, error=None, resets_at=9, session_id="s-3", num_turns=11
    )
    assert type(result.resets_at) is int

    # Third raises AgentFailed("api_error"), rejected, reset "soon".
    double = _Agent(
        [
            _first(),
            _second_null(),
            implement.AgentFailed(
                "api_error",
                _attempt(
                    status="rejected",
                    resets_at="soon",
                    cost=0.25,
                    session_id="s-3",
                    num_turns=2,
                ),
            ),
        ]
    )
    result = _run(double)
    assert len(double.calls) == 3
    assert result == SpecReviewSession(
        text="", cost_usd=1.0, error=None, resets_at=1, session_id="s-3", num_turns=11
    )

    # Third raises AgentFailed("cut") with an attempt.
    double = _Agent(
        [
            _first(),
            _second_null(),
            implement.AgentFailed(
                "cut", _attempt(cost=0.25, session_id="s-3", num_turns=2)
            ),
        ]
    )
    result = _run(double)
    assert len(double.calls) == 3
    assert result == SpecReviewSession(
        text="",
        cost_usd=1.0,
        error="cut",
        resets_at=None,
        session_id="s-3",
        num_turns=11,
    )

    # Third raises AgentFailed("gone") with no attempt.
    double = _Agent([_first(), _second_null(), implement.AgentFailed("gone")])
    result = _run(double)
    assert len(double.calls) == 3
    assert result == SpecReviewSession(
        text="",
        cost_usd=0.75,
        error="gone",
        resets_at=None,
        session_id="s-2",
        num_turns=9,
    )

    # Third is the killed turn.
    double = _Agent([_first(), _second_null(), _KILLED])
    result = _run(double)
    assert len(double.calls) == 3
    _assert_third_call(
        double, prompt_text=reask_prompt_null, resume="s-2", last_cost_usd=0.25
    )
    assert result == SpecReviewSession(
        text="",
        cost_usd=1.0,
        error="the agent produced no result event",
        resets_at=None,
        session_id="s-2",
        num_turns=9,
    )

    # Second at cost 3.0, third the killed turn: `last_cost_usd` caps at 1.0.
    double = _Agent([_first(), _second_null(cost=3.0), _KILLED])
    result = _run(double)
    assert len(double.calls) == 3
    _assert_third_call(
        double, prompt_text=reask_prompt_null, resume="s-2", last_cost_usd=1.0
    )
    assert result == SpecReviewSession(
        text="",
        cost_usd=4.5,
        error="the agent produced no result event",
        resets_at=None,
        session_id="s-2",
        num_turns=9,
    )

    # Third raises an exception the module does not know about.
    double = _Agent([_first(), _second_null(), RuntimeError("boom")])
    with pytest.raises(RuntimeError):
        _run(double)
    assert len(double.calls) == 3


def test_the_spec_writer_system_prompt_fills_the_same_declarations_as_the_reviews(
    tmp_path, monkeypatch
):
    import saffron.spec_review as sr
    from saffron.gates.core import size
    from saffron.repos.policy import GateDeclaration, Policy

    shared_template = "G\n{gates}\nP\n{protected}\nE\n{elevate_on}\nC\n{ceilings}\n"
    (tmp_path / "spec-review.md").write_text(shared_template)
    writer_path = tmp_path / "spec-writer.md"
    writer_path.write_text(shared_template)

    policy = Policy(
        gates={
            "tests": GateDeclaration(blocking=True),
            "lint": GateDeclaration(blocking=False),
        },
        protected=["uv.lock", "docs/{a,b}.md"],
        elevate_on=["saffron/ledger.py"],
    )
    monkeypatch.setitem(size._CEILINGS, "feature", 2999)

    assert sr.SPEC_WRITER_PROMPT == "spec-writer.md"

    for one_policy in (policy, Policy()):
        assert sr.spec_writer_system_prompt(
            one_policy, prompts_dir=tmp_path
        ) == sr.spec_review_system_prompt(one_policy, prompts_dir=tmp_path)

    filled = sr.spec_writer_system_prompt(policy, prompts_dir=tmp_path).splitlines()
    for line in (
        "- `lint` (advisory)",
        "- `docs/{a,b}.md`",
        "- `feature`: 2999 changed tokens",
    ):
        assert line in filled

    writer_path.write_text("W\n{gates}\n")
    assert sr.spec_writer_system_prompt(policy, prompts_dir=tmp_path) == (
        "W\n- `tests`\n- `lint` (advisory)\n"
    )


def test_cores_spec_writer_prompts_fill_every_slot_and_name_no_repo_tool():
    import re

    from saffron.agents import artifacts, context
    from saffron.repos.policy import GateDeclaration, Policy
    from saffron.spec_review import (
        SPEC_WRITER_EXTRACT_PROMPT,
        spec_writer_system_prompt,
    )

    policy = Policy(
        gates={
            "tests": GateDeclaration(blocking=True),
            "lint": GateDeclaration(blocking=False),
        },
        protected=["uv.lock", "docs/{a,b}.md"],
        elevate_on=["saffron/ledger.py"],
    )
    rendered = spec_writer_system_prompt(policy, prompts_dir=context.PROMPTS_DIR)
    for slot in ("{gates}", "{protected}", "{elevate_on}", "{ceilings}"):
        assert slot not in rendered
    for block in (
        "- `tests`\n- `lint` (advisory)",
        "- `uv.lock`\n- `docs/{a,b}.md`",
        "- `saffron/ledger.py`",
        "- `feature`: 3000 changed tokens",
    ):
        assert block in rendered

    raw_writer = (context.PROMPTS_DIR / "spec-writer.md").read_text()
    writer_lines = raw_writer.splitlines()
    for line in (
        "Your Bash runs as an account that can read /work but cannot write it.",
        "To run anything that writes, clone the tree first: "
        "git clone -q /work /tmp/w && cd /tmp/w",
        "Call a tool by its full path when its name does not resolve.",
        "Measure any list of wrong builds you add with a throwaway script.",
    ):
        assert line in writer_lines
    assert sorted(re.findall(r"\{[^{}]*\}", raw_writer)) == [
        "{ceilings}",
        "{elevate_on}",
        "{gates}",
        "{protected}",
    ]

    raw_extract = (context.TURNS_DIR / "spec-writer-extract.md").read_text()
    extract_lines = raw_extract.splitlines()
    for line in (
        "Put the whole spec file in the `spec` field, frontmatter first.",
        "Do not wrap the file in a code fence.",
    ):
        assert line in extract_lines
    nonblank = [line for line in extract_lines if line.strip()]
    assert nonblank[-3:] == [
        "Answer now in the required structured format.",
        "Do not change files.",
        "Do not run commands.",
    ]
    assert re.findall(r"\{[^{}]*\}", raw_extract) == []

    assert context.turn_prompt("spec-writer-extract") == SPEC_WRITER_EXTRACT_PROMPT
    assert artifacts.EXTRACTION_PROMPT not in SPEC_WRITER_EXTRACT_PROMPT

    forbidden = [
        ".claude",
        "CLAUDE.md",
        "DESIGN.md",
        "CONTEXT.md",
        "driver.py",
        "pytest",
        "uv run",
        "make check",
        "ruff",
        "prek",
        "saffron/",
        "docs/",
        "/opt/",
        "://",
        "the reviewer",
        "<output>",
        "output block",
    ]
    writer_lower = raw_writer.lower()
    extract_lower = raw_extract.lower()
    for word in forbidden:
        assert word.lower() not in writer_lower
        assert word.lower() not in extract_lower


def test_the_spec_writer_format_is_the_schema_of_one_string_field():
    import json

    import pydantic

    from saffron.spec_review import SPEC_WRITER_FORMAT, _SpecWriterReply

    root = _SpecWriterReply.model_json_schema()
    assert {"type": "json_schema", "schema": root} == SPEC_WRITER_FORMAT
    assert root["type"] == "object"
    assert root["required"] == ["spec"]
    assert set(root["properties"]) == {"spec"}
    assert root["properties"]["spec"]["type"] == "string"
    assert root["additionalProperties"] is False

    value = "---\nid: X\n---\n  body  \n"
    reply = _SpecWriterReply.model_validate({"spec": value})
    assert reply.spec == value

    refused = [
        {},
        {"spec": 3},
        {"spec": None},
        {"spec": "x", "extra": 1},
        json.dumps({"spec": "x"}),
    ]
    for bad in refused:
        with pytest.raises(pydantic.ValidationError):
            _SpecWriterReply.model_validate(bad)


# An `<output>` block sits inside the spec text, so a reader that parses
# text instead of the schema's value would still look right.
_WRITE_SPEC = "---\nid: SY-1\n---\nbody quotes <output>a</output> here\n"
_WRITE_V = {"spec": _WRITE_SPEC}
_WRITE_B = "<output>\n" + _WRITE_SPEC + "</output>"


def _write_options():
    from saffron.spec_review import (
        SPEC_SESSION_TOOLS,
        SPEC_WRITER_BUDGET_USD,
        SPEC_WRITER_MAX_TURNS,
    )

    return implement.agent_options(
        system_prompt=_SYSTEM_PROMPT,
        max_turns=SPEC_WRITER_MAX_TURNS,
        budget_usd=SPEC_WRITER_BUDGET_USD,
        tools=SPEC_SESSION_TOOLS,
    )


def _write_extract_options():
    from saffron.spec_review import SPEC_WRITER_EXTRACT_BUDGET_USD, SPEC_WRITER_FORMAT

    return _write_options() | {
        "max_budget_usd": SPEC_WRITER_EXTRACT_BUDGET_USD,
        "output_format": SPEC_WRITER_FORMAT,
    }


def _run_writer(double):
    from saffron.spec_review import run_spec_writer

    return run_spec_writer(
        _CONTAINER, system_prompt=_SYSTEM_PROMPT, prompt=_PROMPT, agent=double
    )


def _draft(**overrides):
    return _attempt(
        **{"text": "t", "cost": 0.5, "session_id": "s-1", "num_turns": 7} | overrides
    )


def _write_extract(**overrides):
    base = {
        "text": "t",
        "cost": 0.25,
        "session_id": "s-2",
        "num_turns": 7,
        "structured_output": _WRITE_V,
    }
    return _attempt(**base | overrides)


def _write_third(**overrides):
    base = {
        "text": "t",
        "cost": 0.25,
        "session_id": "s-3",
        "num_turns": 7,
        "structured_output": _WRITE_V,
    }
    return _attempt(**base | overrides)


def _assert_write_first_call(double):
    args, kwargs = double.calls[0]
    assert args == (_CONTAINER,)
    assert kwargs == {"prompt": _PROMPT, "options": _write_options()}
    assert "output_format" not in kwargs["options"]


def _assert_write_second_call(double, *, last_cost_usd=0.5, resume="s-1"):
    from saffron.spec_review import SPEC_WRITER_EXTRACT_PROMPT

    args, kwargs = double.calls[1]
    assert args == (_CONTAINER,)
    assert kwargs == {
        "prompt": SPEC_WRITER_EXTRACT_PROMPT,
        "options": _write_extract_options(),
        "resume": resume,
        "last_cost_usd": last_cost_usd,
    }


def _write_expected(text, cost, error, resets_at, session_id, turns):
    from saffron.agents.artifacts import hash_artifact
    from saffron.spec_review import SpecWriterSession

    return SpecWriterSession(
        text=text,
        cost_usd=cost,
        error=error,
        resets_at=resets_at,
        session_id=session_id,
        num_turns=turns,
        spec_sha=hash_artifact(text) if text else None,
    )


def test_a_spec_writer_session_returns_the_extraction_turns_spec():
    from saffron.spec_review import (
        SPEC_WRITER_BUDGET_USD,
        SPEC_WRITER_EXTRACT_BUDGET_USD,
        SPEC_WRITER_MAX_TURNS,
        SPEC_WRITER_SESSION_USD,
        SPEC_WRITER_TIMEOUT_S,
    )

    assert SPEC_WRITER_MAX_TURNS == 120
    assert type(SPEC_WRITER_MAX_TURNS) is int
    assert SPEC_WRITER_BUDGET_USD == 17.0
    assert SPEC_WRITER_EXTRACT_BUDGET_USD == 1.5
    assert SPEC_WRITER_SESSION_USD == 18.5
    assert SPEC_WRITER_TIMEOUT_S == 3600

    final = _write_extract()
    padded = _write_extract(structured_output={"spec": "\n  " + _WRITE_SPEC + "\n\n"})
    conflicting = _write_extract(text="<output>\n---\nid: SY-9\n---\nwrong\n</output>")

    # A clean extraction turn, and its equal-text variants.
    for second in (final, padded, conflicting):
        double = _Agent([_draft(), second])
        result = _run_writer(double)
        assert len(double.calls) == 2
        _assert_write_first_call(double)
        _assert_write_second_call(double)
        assert result == _write_expected(_WRITE_SPEC, 0.75, None, None, "s-2", 14)

    # First status allowed, reset 9, the same clean second turn.
    double = _Agent([_draft(status="allowed", resets_at=9), final])
    result = _run_writer(double)
    assert len(double.calls) == 2
    _assert_write_second_call(double)
    assert result == _write_expected(_WRITE_SPEC, 0.75, None, None, "s-2", 14)

    # Second is the killed turn.
    double = _Agent([_draft(), _KILLED])
    result = _run_writer(double)
    assert len(double.calls) == 2
    _assert_write_second_call(double)
    assert result == _write_expected(
        "", 1.0, "the agent produced no result event", None, "s-1", 7
    )

    # First at cost 4.0, second the killed turn: `last_cost_usd` caps at 1.5.
    double = _Agent([_draft(cost=4.0), _KILLED])
    result = _run_writer(double)
    assert len(double.calls) == 2
    _assert_write_second_call(double, last_cost_usd=1.5)
    assert result == _write_expected(
        "", 5.5, "the agent produced no result event", None, "s-1", 7
    )

    # Second raises AgentFailed("api_error") with its own turns and cost.
    double = _Agent(
        [_draft(), implement.AgentFailed("api_error", _attempt(cost=0.5, num_turns=7))]
    )
    result = _run_writer(double)
    assert len(double.calls) == 2
    assert result == _write_expected("", 1.0, "api_error", None, "s-1", 14)

    # First returned, rejected, reset R.
    for reset, given in (
        (1755800000, 1755800000),
        (10**20, 10**20),
        (None, 1),
        ("soon", 1),
        (True, 1),
        (1755800000.0, 1),
        (0, 1),
        (-5, 1),
    ):
        double = _Agent(
            [
                _attempt(
                    text="t",
                    cost=0.25,
                    status="rejected",
                    resets_at=reset,
                    session_id="s-1",
                    num_turns=7,
                )
            ]
        )
        result = _run_writer(double)
        assert len(double.calls) == 1
        _assert_write_first_call(double)
        assert result == _write_expected("", 0.25, None, given, "s-1", 7)
        assert type(result.resets_at) is int

        # Raised, rejected, the same reset.
        double = _Agent(
            [
                implement.AgentFailed(
                    "api_error",
                    _attempt(
                        status="rejected",
                        resets_at=reset,
                        cost=0.125,
                        session_id="s-1",
                        num_turns=7,
                    ),
                )
            ]
        )
        result = _run_writer(double)
        assert len(double.calls) == 1
        assert result == _write_expected("", 0.125, None, given, "s-1", 7)
        assert type(result.resets_at) is int

    # Second returned, rejected.
    double = _Agent(
        [
            _draft(),
            _attempt(
                text="t",
                cost=0.0625,
                status="rejected",
                resets_at=1755800000,
                num_turns=7,
                structured_output=_WRITE_V,
            ),
        ]
    )
    result = _run_writer(double)
    assert len(double.calls) == 2
    assert result == _write_expected("", 0.5625, None, 1755800000, "s-1", 14)
    assert type(result.resets_at) is int

    double = _Agent(
        [
            _draft(),
            _attempt(
                text="t",
                cost=0.0625,
                status="rejected",
                resets_at=-5,
                num_turns=7,
                structured_output=_WRITE_V,
            ),
        ]
    )
    result = _run_writer(double)
    assert len(double.calls) == 2
    assert result == _write_expected("", 0.5625, None, 1, "s-1", 14)

    # Second raises AgentFailed, rejected, no reset.
    double = _Agent(
        [
            _draft(),
            implement.AgentFailed(
                "api_error",
                _attempt(status="rejected", resets_at=None, cost=0.0625, num_turns=7),
            ),
        ]
    )
    result = _run_writer(double)
    assert len(double.calls) == 2
    assert result == _write_expected("", 0.5625, None, 1, "s-1", 14)
    assert type(result.resets_at) is int

    # First raises, not rejected, with an attempt.
    double = _Agent(
        [
            implement.AgentFailed(
                "idle bound",
                _attempt(
                    cost=0.0625,
                    session_id="s-1",
                    num_turns=7,
                    structured_output=_WRITE_V,
                ),
            )
        ]
    )
    result = _run_writer(double)
    assert len(double.calls) == 1
    assert result == _write_expected("", 0.0625, "idle bound", None, "s-1", 7)

    # First raises, with no attempt at all.
    double = _Agent([implement.AgentFailed("no result")])
    result = _run_writer(double)
    assert len(double.calls) == 1
    assert result == _write_expected("", 0.0, "no result", None, None, 0)

    # Second raises AgentFailed, not rejected, with an attempt.
    double = _Agent(
        [
            _draft(),
            implement.AgentFailed(
                "api_error",
                _attempt(cost=0.125, num_turns=7, structured_output=_WRITE_V),
            ),
        ]
    )
    result = _run_writer(double)
    assert len(double.calls) == 2
    assert result == _write_expected("", 0.625, "api_error", None, "s-1", 14)

    double = _Agent(
        [
            _draft(),
            implement.AgentFailed(
                "idle bound", _attempt(cost=0.125, num_turns=7, session_id=None)
            ),
        ]
    )
    result = _run_writer(double)
    assert len(double.calls) == 2
    assert result == _write_expected("", 0.625, "idle bound", None, "s-1", 14)

    # Second raises AgentFailed, with no attempt at all.
    double = _Agent([_draft(), implement.AgentFailed("no result")])
    result = _run_writer(double)
    assert len(double.calls) == 2
    assert result == _write_expected("", 0.5, "no result", None, "s-1", 7)

    # First returned, with no session_id: no second call.
    double = _Agent([_draft(session_id=None)])
    result = _run_writer(double)
    assert len(double.calls) == 1
    _assert_write_first_call(double)
    assert result == _write_expected(
        "", 0.5, "no session to extract from", None, None, 7
    )

    # Any other exception propagates, from either turn.
    double = _Agent([RuntimeError("runner died")])
    with pytest.raises(RuntimeError):
        _run_writer(double)
    assert len(double.calls) == 1

    double = _Agent([_draft(), RuntimeError("boom")])
    with pytest.raises(RuntimeError):
        _run_writer(double)
    assert len(double.calls) == 2


def test_a_spec_writer_re_asks_once_when_its_extraction_is_not_the_schema():
    from dataclasses import replace

    from saffron.spec_review import SPEC_WRITER_EXTRACT_PROMPT, _SpecWriterReply

    def _validation_message(value):
        try:
            _SpecWriterReply.model_validate(value)
        except Exception as exc:  # pydantic.ValidationError
            return f"not the schema: {exc}"
        raise AssertionError("value unexpectedly validated")

    m_null = "not the schema: the turn returned no structured output"
    reask_prompt_null = m_null + "\n\n" + SPEC_WRITER_EXTRACT_PROMPT

    second_n = _write_extract(structured_output=None, text=_WRITE_B)
    second_k = _write_extract(
        structured_output={"spec": "x", "extra": 1}, text=_WRITE_B
    )
    second_z = _write_extract(structured_output={"spec": 3}, text=_WRITE_B)
    second_j = _write_extract(structured_output=json.dumps(_WRITE_V), text=_WRITE_B)
    second_o = _write_extract(structured_output={}, text=_WRITE_B)

    def _assert_third_call(double, *, resume, last_cost_usd, prompt_text=None):
        args, kwargs = double.calls[2]
        assert args == (_CONTAINER,)
        assert set(kwargs) == {"prompt", "options", "resume", "last_cost_usd"}
        assert kwargs["options"] == _write_extract_options()
        assert kwargs["resume"] == resume
        assert kwargs["last_cost_usd"] == last_cost_usd
        if prompt_text is None:
            assert kwargs["prompt"].startswith("not the schema: ")
            assert kwargs["prompt"].endswith("\n\n" + SPEC_WRITER_EXTRACT_PROMPT)
        else:
            assert kwargs["prompt"] == prompt_text

    # Every refused second-value row: a clean third turn that returns V.
    for second in (second_n, second_k, second_z, second_j, second_o):
        double = _Agent([_draft(), second, _write_third()])
        result = _run_writer(double)
        assert len(double.calls) == 3
        _assert_third_call(double, resume="s-2", last_cost_usd=0.25)
        assert result == _write_expected(_WRITE_SPEC, 1.0, None, None, "s-3", 21)

    # A null second value, second carries no session_id: the re-ask resumes
    # the first turn's.
    double = _Agent([_draft(), replace(second_n, session_id=None), _write_third()])
    result = _run_writer(double)
    assert len(double.calls) == 3
    _assert_third_call(
        double, prompt_text=reask_prompt_null, resume="s-1", last_cost_usd=0.25
    )
    assert result == _write_expected(_WRITE_SPEC, 1.0, None, None, "s-3", 21)

    # Third returns, with no session_id.
    double = _Agent([_draft(), second_n, _write_third(session_id=None)])
    result = _run_writer(double)
    assert len(double.calls) == 3
    assert result == _write_expected(_WRITE_SPEC, 1.0, None, None, "s-2", 21)

    # Second N, third N: both refused.
    double = _Agent([_draft(), second_n, _write_third(structured_output=None)])
    result = _run_writer(double)
    assert len(double.calls) == 3
    _assert_third_call(
        double, prompt_text=reask_prompt_null, resume="s-2", last_cost_usd=0.25
    )
    assert result == _write_expected("", 1.0, m_null, None, "s-3", 21)

    # Second N, third K: the third's own message is kept.
    k_value = {"spec": "x", "extra": 1}
    double = _Agent([_draft(), second_n, _write_third(structured_output=k_value)])
    result = _run_writer(double)
    assert len(double.calls) == 3
    assert result == _write_expected(
        "", 1.0, _validation_message(k_value), None, "s-3", 21
    )

    # Second K, third N: the re-ask's own message is kept.
    double = _Agent([_draft(), second_k, _write_third(structured_output=None)])
    result = _run_writer(double)
    assert len(double.calls) == 3
    assert result == _write_expected("", 1.0, m_null, None, "s-3", 21)

    # Third returns rejected.
    double = _Agent([_draft(), second_n, _write_third(status="rejected", resets_at=9)])
    result = _run_writer(double)
    assert len(double.calls) == 3
    assert result == _write_expected("", 1.0, None, 9, "s-3", 21)
    assert type(result.resets_at) is int

    double = _Agent([_draft(), second_n, _write_third(status="rejected", resets_at=0)])
    result = _run_writer(double)
    assert len(double.calls) == 3
    assert result == _write_expected("", 1.0, None, 1, "s-3", 21)

    # Third raises AgentFailed, rejected, reset "soon".
    double = _Agent(
        [
            _draft(),
            second_n,
            implement.AgentFailed(
                "api_error",
                _attempt(
                    status="rejected",
                    resets_at="soon",
                    cost=0.25,
                    session_id="s-3",
                    num_turns=7,
                ),
            ),
        ]
    )
    result = _run_writer(double)
    assert len(double.calls) == 3
    assert result == _write_expected("", 1.0, None, 1, "s-3", 21)

    # Third raises AgentFailed("cut") with an attempt of value V.
    double = _Agent(
        [
            _draft(),
            second_n,
            implement.AgentFailed(
                "cut",
                _attempt(
                    cost=0.25, session_id="s-3", num_turns=7, structured_output=_WRITE_V
                ),
            ),
        ]
    )
    result = _run_writer(double)
    assert len(double.calls) == 3
    assert result == _write_expected("", 1.0, "cut", None, "s-3", 21)

    # Third is the killed turn.
    double = _Agent([_draft(), second_n, _KILLED])
    result = _run_writer(double)
    assert len(double.calls) == 3
    _assert_third_call(
        double, prompt_text=reask_prompt_null, resume="s-2", last_cost_usd=0.25
    )
    assert result == _write_expected(
        "", 1.0, "the agent produced no result event", None, "s-2", 14
    )

    # Second at cost 3.0, third the killed turn: `last_cost_usd` caps at 1.5.
    double = _Agent([_draft(), replace(second_n, cost_usd_est=3.0), _KILLED])
    result = _run_writer(double)
    assert len(double.calls) == 3
    _assert_third_call(
        double, prompt_text=reask_prompt_null, resume="s-2", last_cost_usd=1.5
    )
    assert result == _write_expected(
        "", 5.0, "the agent produced no result event", None, "s-2", 14
    )

    # Third raises AgentFailed("gone") with no attempt.
    double = _Agent([_draft(), second_n, implement.AgentFailed("gone")])
    result = _run_writer(double)
    assert len(double.calls) == 3
    assert result == _write_expected("", 0.75, "gone", None, "s-2", 14)

    # Third raises an exception the module does not know about.
    double = _Agent([_draft(), second_n, RuntimeError("boom")])
    with pytest.raises(RuntimeError):
        _run_writer(double)
    assert len(double.calls) == 3
