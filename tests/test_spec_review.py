import json


def _block(obj: object, *, lang: str = "json") -> str:
    return f"```{lang}\n{json.dumps(obj)}\n```"


def _session(text: str, *, cost: float = 0.5, error=None, resets_at=None):
    from saffron.spec_review import SpecReviewSession

    return SpecReviewSession(text=text, cost_usd=cost, error=error, resets_at=resets_at)


def test_a_spec_review_routes_on_the_severities_in_its_last_json_block(monkeypatch):
    from saffron import spec_review as sr

    finding = {"claim": "c", "criterion": "1", "file": "f.py", "line": 1}

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
                                "criterion": "1",
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
