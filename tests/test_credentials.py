"""The credential shapes `EventLog` redacts, moved to one module with PACKAGE's
own scan (item 46, §5.4)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from saffron.events import BOUND_CHARS, Agent, EventLog, describe, read_log
from saffron.phases import package as package_phase

# Joined at runtime, like the token shapes below: a literal header is what PACKAGE refuses.
_KEY = "PRIVATE " + "KEY"
_HEADER = f"-----BEGIN RSA {_KEY}-----"


def _append_one(event: Agent, *, token: str | None = None) -> Agent:
    """Append `event` to a fresh log and return the one line read back."""
    with tempfile.TemporaryDirectory() as tmp:
        log = EventLog(Path(tmp) / "t", token=token)
        log.append(event)
        (logged,) = read_log(Path(tmp) / "t")
    assert isinstance(logged, Agent)
    return logged


def test_every_shape_package_refuses_is_redacted_from_the_log():
    """Every credential shape PACKAGE refuses is redacted from an `Agent`
    event before `EventLog.append` writes it, and named once in `redacted`."""
    cases = [
        ("an Anthropic API key", "sk-ant-" + "api03-" + "a" * 20),
        ("an Anthropic OAuth token", "sk-ant-" + "oat01-" + "b" * 20),
        ("a GitHub token", "ghp_" + "c" * 20),
        ("a GitHub token", "gho_" + "d" * 20),
        ("a GitHub token", "ghu_" + "e" * 20),
        ("a GitHub token", "ghs_" + "f" * 20),
        ("a GitHub token", "ghr_" + "g" * 20),
        ("an AWS access key id", "AKIA" + "H" * 16),
    ]
    for description, credential in cases:
        found = package_phase.find_credentials_in_text(
            credential, token=None, where="w"
        )
        assert found == [f"w: {description}"]

        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp) / "t"
            log = EventLog(task_dir, token=None)
            event = Agent(
                timestamp=1.0,
                spec_id="X",
                raw=False,
                event={"text": f"before {credential} after"},
            )
            log.append(event)
            written = (task_dir / "events.jsonl").read_text()
            assert credential not in written
            (logged,) = read_log(task_dir)
            assert isinstance(logged, Agent)
            assert logged.event is not None
            assert logged.redacted == (description,)
            assert "before " in logged.event["text"]
            assert " after" in logged.event["text"]
            assert credential not in logged.event["text"]
            # The inline marker itself names this shape, never a generic one.
            assert description in logged.event["text"]
            assert description in written

    body_line = "MIIBOGUSBODYLINEONLYONE=="
    key_block = f"{_HEADER}\n{body_line}\n-----END RSA {_KEY}-----"
    found = package_phase.find_credentials_in_text(key_block, token=None, where="w")
    assert found == ["w: a private key block"]
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp) / "t"
        log = EventLog(task_dir, token=None)
        event = Agent(
            timestamp=1.0,
            spec_id="X",
            raw=False,
            event={"text": f"before {key_block} after"},
        )
        log.append(event)
        written = (task_dir / "events.jsonl").read_text()
        assert body_line not in written
        assert key_block not in written
        (logged,) = read_log(task_dir)
        assert isinstance(logged, Agent)
        assert logged.event is not None
        assert logged.redacted == ("a private key block",)
        assert "before " in logged.event["text"]
        assert " after" in logged.event["text"]
        assert "a private key block" in logged.event["text"]
        assert "a private key block" in written

    # Two further blocks with no END line: a clipped `tool_use` input and a
    # bare raw line holding only the header.
    header = _HEADER
    clipped_body = "\n".join(f"line-of-body-{n}-abcdefghijklmnop" for n in range(4))
    clipped = (header + "\n" + clipped_body)[:200] + "...[clip]"
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp) / "t"
        log = EventLog(task_dir, token=None)
        event = Agent(
            timestamp=1.0,
            spec_id="X",
            raw=False,
            event={"type": "tool_use", "input": {"content": clipped}},
        )
        log.append(event)
        written = (task_dir / "events.jsonl").read_text()
        assert header not in written
        assert "line-of-body-0-abcdefghijklmnop" not in written
        assert "a private key block" in written
        (logged,) = read_log(task_dir)
        assert isinstance(logged, Agent)
        assert logged.redacted == ("a private key block",)

    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp) / "t"
        log = EventLog(task_dir, token=None)
        event = Agent(timestamp=1.0, spec_id="X", raw=True, line=header)
        log.append(event)
        written = (task_dir / "events.jsonl").read_text()
        assert header not in written
        assert "a private key block" in written
        (logged,) = read_log(task_dir)
        assert isinstance(logged, Agent)
        assert logged.redacted == ("a private key block",)


def test_an_agent_events_credentials_are_redacted_in_every_field():
    """Redaction reaches every cell-authored place in an `Agent` event. The
    witness covers the top level of `event`, a nested dict, a list element,
    a dict key, a raw `line`, and `detail`. It also covers the innermost
    string of a structure nested 999 deep, inside an event too large to
    keep whole."""
    key = "AKIA" + "Z" * 16
    description = "an AWS access key id"

    top = _append_one(
        Agent(timestamp=1.0, spec_id="X", raw=False, event={"text": f"a {key} b"})
    )
    assert key not in json.dumps(top.event)
    assert top.redacted == (description,)
    assert top.event is not None
    assert "a " in top.event["text"] and " b" in top.event["text"]

    nested = _append_one(
        Agent(
            timestamp=1.0,
            spec_id="X",
            raw=False,
            event={"outer": {"inner": f"a {key} b"}},
        )
    )
    assert key not in json.dumps(nested.event)
    assert nested.redacted == (description,)

    listed = _append_one(
        Agent(
            timestamp=1.0, spec_id="X", raw=False, event={"items": ["x", f"a {key} b"]}
        )
    )
    assert key not in json.dumps(listed.event)
    assert listed.redacted == (description,)

    keyed = _append_one(
        Agent(timestamp=1.0, spec_id="X", raw=False, event={f"a-{key}-b": "v"})
    )
    assert key not in json.dumps(keyed.event)
    assert keyed.redacted == (description,)
    assert keyed.event is not None
    assert any("a-" in k and "-b" in k for k in keyed.event)

    raw_line = _append_one(
        Agent(timestamp=1.0, spec_id="X", raw=True, line=f"a {key} b")
    )
    assert key not in (raw_line.line or "")
    assert raw_line.redacted == (description,)
    assert "a " in (raw_line.line or "") and " b" in (raw_line.line or "")

    detailed = _append_one(
        Agent(timestamp=1.0, spec_id="X", raw=False, detail=f"a {key} b")
    )
    assert key not in detailed.detail
    assert detailed.redacted == (description,)
    assert "a " in detailed.detail and " b" in detailed.detail

    def nest(value: object, depth: int) -> object:
        for _ in range(depth):
            value = [value]
        return value

    huge = "z" * (BOUND_CHARS * 2)
    deep_event = {"type": "text", "text": huge, "deep": nest(key, 999)}
    deep = _append_one(Agent(timestamp=1.0, spec_id="X", raw=False, event=deep_event))
    assert deep.bounded is True
    assert key not in (deep.line or "")
    assert deep.redacted == (description,)

    two_and_three = _append_one(
        Agent(
            timestamp=1.0,
            spec_id="X",
            raw=False,
            event={"text": f"{key} and {key}"},
            detail=f"a third {key}",
        )
    )
    assert key not in json.dumps(two_and_three.event)
    assert key not in two_and_three.detail
    assert two_and_three.redacted == (description,)

    clean = Agent(timestamp=1.0, spec_id="X", raw=False, event={"text": "nothing here"})
    assert _append_one(clean) == clean


def test_the_cells_own_token_is_redacted_under_packages_length_guard():
    """The cell's own token is redacted when `EventLog` is handed it, under
    PACKAGE's length guard unchanged."""
    token = "zz-" + "token-" + "abcdef0123456789"
    description = "the cell's own CLAUDE_CODE_OAUTH_TOKEN"

    nested = _append_one(
        Agent(
            timestamp=1.0,
            spec_id="X",
            raw=False,
            event={"outer": {"inner": f"x {token} y"}},
        ),
        token=token,
    )
    assert token not in json.dumps(nested.event)
    assert nested.redacted == (description,)

    raw_line = _append_one(
        Agent(timestamp=1.0, spec_id="X", raw=True, line=f"x {token} y"), token=token
    )
    assert token not in (raw_line.line or "")
    assert raw_line.redacted == (description,)

    detailed = _append_one(
        Agent(timestamp=1.0, spec_id="X", raw=False, detail=f"x {token} y"),
        token=token,
    )
    assert token not in detailed.detail
    assert detailed.redacted == (description,)

    for variant, variant_text in (
        (None, f"x {token} y"),
        ("", f"x {token} y"),
        # Exactly eight characters, and literally present in the text: the
        # guard is `> 8`, not `>= 8`, so this one must survive untouched.
        ("abcdefgh", "x abcdefgh y"),
    ):
        unchanged = Agent(timestamp=1.0, spec_id="X", raw=False, detail=variant_text)
        read_back = _append_one(unchanged, token=variant)
        assert read_back == unchanged
        assert (
            package_phase.find_credentials_in_text(
                variant_text, token=variant, where="w"
            )
            == []
        )


def test_a_credential_cut_by_the_size_bound_is_redacted_whole():
    """Redaction runs before the size bound, so a credential the bound's cut
    would split is never written in part."""
    token = "ghp_" + "a" * 20
    key = "sk-ant-" + "api03-" + "c" * 20

    probe_marker = "TEXTVALUEPROBE"
    probe = json.dumps({"text": probe_marker, "model": "m"})
    prefix_len = probe.index(probe_marker)
    pad_len = BOUND_CHARS - prefix_len - 14
    text_value = ("x" * pad_len) + token

    event = _append_one(
        Agent(
            timestamp=1.0,
            spec_id="X",
            raw=False,
            event={"text": text_value, "model": key},
        )
    )
    assert event.bounded is True
    assert token[:14] not in (event.line or "")
    assert key not in (event.line or "")
    assert event.usage is not None
    assert key not in json.dumps(event.usage)
    assert event.redacted == ("a GitHub token", "an Anthropic API key")


def test_a_redacted_event_read_back_says_what_was_redacted():
    """`describe` names what was redacted for an `Agent` read back from the
    log, even when the credential sat past the line's own cut."""
    key = "AKIA" + "Q" * 16
    description = "an AWS access key id"
    tail = "x" * 600 + key

    raw_line = _append_one(Agent(timestamp=1.0, spec_id="X", raw=True, line=tail))
    rendered = describe(raw_line)
    assert f"redacted: {description}" in rendered
    assert key not in rendered

    detailed = _append_one(Agent(timestamp=1.0, spec_id="X", raw=False, detail=tail))
    rendered = describe(detailed)
    assert f"redacted: {description}" in rendered
    assert key not in rendered

    dispatched = _append_one(
        Agent(
            timestamp=1.0, spec_id="X", raw=False, event={"type": "text", "text": tail}
        )
    )
    rendered = describe(dispatched)
    assert f"redacted: {description}" in rendered
    assert key not in rendered

    huge = "z" * (BOUND_CHARS * 2)
    bounded = _append_one(
        Agent(
            timestamp=1.0,
            spec_id="X",
            raw=False,
            event={"type": "text", "text": tail, "filler": huge},
        )
    )
    assert bounded.bounded is True
    rendered = describe(bounded)
    assert f"redacted: {description}" in rendered
    assert key not in rendered

    clean = _append_one(Agent(timestamp=1.0, spec_id="X", raw=True, line="hello world"))
    assert "redacted" not in describe(clean)


def test_the_credential_shapes_are_spelled_in_one_module():
    """The credential shapes are spelled in one module, `saffron/credentials.py`,
    which PACKAGE and `EventLog` both read."""
    import saffron
    from saffron.credentials import CREDENTIAL_SHAPES

    root = Path(saffron.__file__).parent
    for _description, pattern in CREDENTIAL_SHAPES:
        matches = sorted(
            p
            for p in root.rglob("*.py")
            if pattern.pattern in p.read_text(encoding="utf-8")
        )
        assert matches == [root / "credentials.py"]
