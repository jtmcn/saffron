"""Backlog item 46: `events.jsonl` comes within reach of a credential scan.
`saffron.credentials` is the one module PACKAGE and `EventLog` both read.
Its shapes, its token check and its redaction are proved here. Never
imported at module scope, since the module does not exist at the tree base
(`DESIGN.md` §5.4, §9).
"""

from __future__ import annotations

import json
from pathlib import Path


def _only_agent(events, kind):
    """`read_log` returns the whole `Event` union. Every test here knows it
    wrote only `Agent`s. Narrowing here, once, is what lets the `types` gate
    see an attribute read off the right kind."""
    narrowed = []
    for event in events:
        assert isinstance(event, kind), f"log holds a {type(event).__name__}"
        narrowed.append(event)
    return narrowed


def _api_key() -> str:
    return "sk-ant-" + "api03-" + "a" * 20


def _oauth_token() -> str:
    return "sk-ant-" + "oat01-" + "a" * 20


def _github_token(letter: str) -> str:
    return f"gh{letter}_" + "a" * 20


def _aws_key() -> str:
    return "AKIA" + "A" * 16


def _private_key_header() -> str:
    return "-----BEGIN " + ("PRIVATE " + "KEY") + "-----"


def _private_key_end() -> str:
    return "-----END " + ("PRIVATE " + "KEY") + "-----"


def _private_key_block(body_line: str) -> str:
    return f"{_private_key_header()}\n{body_line}\n{_private_key_end()}"


def test_every_shape_package_refuses_is_redacted_from_the_log(tmp_path):
    from saffron.events import Agent, EventLog, read_log
    from saffron.phases.package import find_credentials_in_text

    body_line = "a" * 44
    block = _private_key_block(body_line)

    cases = [
        ("an Anthropic API key", _api_key()),
        ("an Anthropic OAuth token", _oauth_token()),
        *(("a GitHub token", _github_token(letter)) for letter in "pousr"),
        ("an AWS access key id", _aws_key()),
        ("a private key block", block),
    ]

    for index, (description, credential) in enumerate(cases):
        spec_id = f"CR-shape-{index}"
        text = f"before {credential} after"
        appended = {
            "type": "text",
            "text": text,
            "index": 3,
            "is_error": False,
            "n": None,
        }
        log = EventLog(tmp_path / spec_id)
        log.append(
            Agent(timestamp=1.0, spec_id=spec_id, raw=False, event=dict(appended))
        )

        scanned = find_credentials_in_text(text, token=None, where="where")
        assert scanned == [f"where: {description}"]

        written = (tmp_path / spec_id / "events.jsonl").read_text()
        assert credential not in written
        if description == "a private key block":
            assert body_line not in written

        (logged,) = _only_agent(read_log(tmp_path / spec_id), Agent)
        assert logged.redacted == (description,)
        assert logged.event is not None
        assert logged.event["type"] == "text"
        assert "before " in logged.event["text"]
        assert " after" in logged.event["text"]
        assert credential not in logged.event["text"]
        # The marker written in place of the credential names this shape,
        # not a generic one every shape would share.
        assert description in logged.event["text"]
        # Every other key, the non-string ones too, is read back unchanged.
        assert logged.event == {**appended, "text": logged.event["text"]}
        assert description in written

    # A clipped block, no END line: a header and four body lines inside a
    # `tool_use` input, cut at 200 characters the way `agent_runner.py` clips.
    raw_block = _private_key_header() + ("\n" + body_line) * 4
    clipped = raw_block[:200] + f"…(+{len(raw_block) - 200} chars)"
    spec_id = "CR-clipped-key"
    log = EventLog(tmp_path / spec_id)
    log.append(
        Agent(
            timestamp=1.0,
            spec_id=spec_id,
            raw=False,
            event={"type": "tool_use", "name": "Write", "input": {"content": clipped}},
        )
    )
    written = (tmp_path / spec_id / "events.jsonl").read_text()
    assert _private_key_header() not in written
    assert body_line not in written
    assert "a private key block" in written
    (logged,) = _only_agent(read_log(tmp_path / spec_id), Agent)
    assert logged.redacted == ("a private key block",)

    # A raw line holding the header alone, no body and no END line.
    spec_id = "CR-header-alone"
    log = EventLog(tmp_path / spec_id)
    log.append(
        Agent(timestamp=1.0, spec_id=spec_id, raw=True, line=_private_key_header())
    )
    written = (tmp_path / spec_id / "events.jsonl").read_text()
    assert _private_key_header() not in written
    assert "a private key block" in written
    (logged,) = _only_agent(read_log(tmp_path / spec_id), Agent)
    assert logged.redacted == ("a private key block",)


def test_an_agent_events_credentials_are_redacted_in_every_field(tmp_path):
    from saffron.events import Agent, EventLog, read_log

    aws = _aws_key()
    description = "an AWS access key id"

    def _written(spec_id):
        return (tmp_path / spec_id / "events.jsonl").read_text()

    def _logged(spec_id):
        (only,) = _only_agent(read_log(tmp_path / spec_id), Agent)
        return only

    # 1: a top-level string value of `event`.
    log = EventLog(tmp_path / "A1")
    log.append(
        Agent(
            timestamp=1.0,
            spec_id="A1",
            raw=False,
            event={"type": "text", "text": f"before {aws} after"},
        )
    )
    assert aws not in _written("A1")
    e1 = _logged("A1")
    assert e1.redacted == (description,)
    assert e1.event is not None
    assert "before " in e1.event["text"] and " after" in e1.event["text"]

    # 2: a value in a dict nested in it.
    log = EventLog(tmp_path / "A2")
    log.append(
        Agent(
            timestamp=1.0,
            spec_id="A2",
            raw=False,
            event={"type": "text", "nested": {"k": f"before {aws} after"}},
        )
    )
    assert aws not in _written("A2")
    e2 = _logged("A2")
    assert e2.redacted == (description,)
    assert e2.event is not None
    nested = e2.event["nested"]["k"]
    assert "before " in nested and " after" in nested

    # 3: an element of a list in it.
    log = EventLog(tmp_path / "A3")
    log.append(
        Agent(
            timestamp=1.0,
            spec_id="A3",
            raw=False,
            event={"type": "text", "items": [f"before {aws} after"]},
        )
    )
    assert aws not in _written("A3")
    e3 = _logged("A3")
    assert e3.redacted == (description,)
    assert e3.event is not None
    item = e3.event["items"][0]
    assert "before " in item and " after" in item

    # 4: a dict key.
    log = EventLog(tmp_path / "A4")
    log.append(
        Agent(
            timestamp=1.0,
            spec_id="A4",
            raw=False,
            event={"type": "text", f"before {aws} after": "value"},
        )
    )
    assert aws not in _written("A4")
    e4 = _logged("A4")
    assert e4.redacted == (description,)
    assert e4.event is not None
    (survivor_key,) = [k for k in e4.event if k != "type"]
    assert "before " in survivor_key and " after" in survivor_key

    # 5: a raw line.
    log = EventLog(tmp_path / "A5")
    log.append(Agent(timestamp=1.0, spec_id="A5", raw=True, line=f"before {aws} after"))
    assert aws not in _written("A5")
    e5 = _logged("A5")
    assert e5.redacted == (description,)
    assert e5.line is not None
    assert "before " in e5.line and " after" in e5.line

    # 6: `detail`.
    log = EventLog(tmp_path / "A6")
    log.append(
        Agent(timestamp=1.0, spec_id="A6", raw=False, detail=f"before {aws} after")
    )
    assert aws not in _written("A6")
    e6 = _logged("A6")
    assert e6.redacted == (description,)
    assert "before " in e6.detail and " after" in e6.detail

    # 7: the innermost string of a list nested 999 deep, inside an event too
    # large to keep whole. It precedes the padding, so it lands in the written line.
    deep: object = f"before {aws} after"
    for _ in range(999):
        deep = [deep]
    log = EventLog(tmp_path / "A7")
    log.append(
        Agent(
            timestamp=1.0,
            spec_id="A7",
            raw=False,
            event={"type": "text", "deep": deep, "text": "z" * 8192},
        )
    )
    assert aws not in _written("A7")
    e7 = _logged("A7")
    assert e7.redacted == (description,)
    assert e7.bounded is True
    assert e7.line is not None
    assert f"before [redacted: {description}] after" in e7.line

    # 8: two matches in one string, and a third in `detail`, named once.
    aws_b, aws_c = _aws_key(), _aws_key()
    log = EventLog(tmp_path / "A8")
    log.append(
        Agent(
            timestamp=1.0,
            spec_id="A8",
            raw=False,
            event={"type": "text", "text": f"{aws} middle {aws_b}"},
            detail=f"before {aws_c} after",
        )
    )
    assert aws not in _written("A8") and aws_b not in _written("A8")
    assert aws_c not in _written("A8")
    e8 = _logged("A8")
    assert e8.redacted == (description,)

    # An event carrying no credential reads back equal to the one appended.
    clean = Agent(timestamp=1.0, spec_id="A9", raw=False, event={"type": "text"})
    log = EventLog(tmp_path / "A9")
    log.append(clean)
    e9 = _logged("A9")
    assert e9 == clean


def test_the_cells_own_token_is_redacted_under_packages_length_guard(tmp_path):
    from saffron.events import Agent, EventLog, read_log
    from saffron.phases.package import find_credentials_in_text

    token = "tok-" + "9f2c7a1e5b"
    description = "the cell's own CLAUDE_CODE_OAUTH_TOKEN"

    def _written(spec_id):
        return (tmp_path / spec_id / "events.jsonl").read_text()

    def _logged(spec_id):
        (only,) = _only_agent(read_log(tmp_path / spec_id), Agent)
        return only

    log = EventLog(tmp_path / "T1", token=token)
    log.append(
        Agent(
            timestamp=1.0,
            spec_id="T1",
            raw=False,
            event={"type": "text", "nested": {"k": f"before {token} after"}},
        )
    )
    assert token not in _written("T1")
    assert _logged("T1").redacted == (description,)

    log = EventLog(tmp_path / "T2", token=token)
    log.append(
        Agent(timestamp=1.0, spec_id="T2", raw=True, line=f"before {token} after")
    )
    assert token not in _written("T2")
    assert _logged("T2").redacted == (description,)

    log = EventLog(tmp_path / "T3", token=token)
    log.append(
        Agent(timestamp=1.0, spec_id="T3", raw=False, detail=f"before {token} after")
    )
    assert token not in _written("T3")
    assert _logged("T3").redacted == (description,)

    # The guard: `None`, an empty token and an eight-character token in the
    # text all leave the event untouched, and PACKAGE's scan agrees.
    text = "value 12345678 end"
    for index, guarded in enumerate((None, "", "12345678")):
        spec_id = f"T-guard-{index}"
        event = Agent(timestamp=1.0, spec_id=spec_id, raw=True, line=text)
        log = EventLog(tmp_path / spec_id, token=guarded)
        log.append(event)
        assert _logged(spec_id) == event
        assert find_credentials_in_text(text, token=guarded, where="w") == []


def test_a_credential_cut_by_the_size_bound_is_redacted_whole(tmp_path):
    from saffron.events import BOUND_CHARS, Agent, EventLog, read_log

    token = _github_token("p")
    api_key = _api_key()

    def _event(pad_len: int) -> dict:
        return {
            "type": "text",
            "text": "P" * pad_len + token,
            "model": api_key,
            "input_tokens": 7,
        }

    probe = json.dumps(_event(0))
    prefix_len = probe.index(token)
    target_start = BOUND_CHARS - 14
    pad_len = target_start - prefix_len
    assert pad_len >= 0
    event_dict = _event(pad_len)
    assert json.dumps(event_dict).index(token) == target_start

    spec_id = "CR-bound-cut"
    log = EventLog(tmp_path / spec_id)
    log.append(Agent(timestamp=1.0, spec_id=spec_id, raw=False, event=event_dict))

    written = (tmp_path / spec_id / "events.jsonl").read_text()
    assert token[:14] not in written
    assert api_key not in written

    (logged,) = _only_agent(read_log(tmp_path / spec_id), Agent)
    assert logged.bounded is True
    assert logged.usage is not None
    assert api_key not in json.dumps(logged.usage)
    assert logged.usage["input_tokens"] == 7
    assert set(logged.redacted) == {"a GitHub token", "an Anthropic API key"}


def test_a_redacted_event_read_back_says_what_was_redacted(tmp_path):
    from saffron.events import Agent, EventLog, describe, read_log

    aws = _aws_key()
    description = "an AWS access key id"

    def _padded(suffix_len: int) -> str:
        return ("x" * 600) + aws + ("y" * suffix_len)

    def _logged(spec_id):
        (only,) = _only_agent(read_log(tmp_path / spec_id), Agent)
        return only

    # bounded
    log = EventLog(tmp_path / "D-bounded")
    log.append(
        Agent(
            timestamp=1.0,
            spec_id="D-bounded",
            raw=False,
            event={"type": "text", "text": _padded(8192)},
        )
    )
    bounded_event = _logged("D-bounded")
    assert bounded_event.bounded is True
    rendered = describe(bounded_event)
    assert f"redacted: {description}" in rendered
    assert aws not in rendered

    # raw
    log = EventLog(tmp_path / "D-raw")
    log.append(Agent(timestamp=1.0, spec_id="D-raw", raw=True, line=_padded(50)))
    rendered = describe(_logged("D-raw"))
    assert f"redacted: {description}" in rendered
    assert aws not in rendered

    # parsed event
    log = EventLog(tmp_path / "D-parsed")
    log.append(
        Agent(
            timestamp=1.0,
            spec_id="D-parsed",
            raw=False,
            event={"type": "text", "text": _padded(0)},
        )
    )
    parsed_event = _logged("D-parsed")
    assert parsed_event.event is not None
    rendered = describe(parsed_event)
    assert f"redacted: {description}" in rendered
    assert aws not in rendered

    # detail
    log = EventLog(tmp_path / "D-detail")
    log.append(Agent(timestamp=1.0, spec_id="D-detail", raw=False, detail=_padded(50)))
    rendered = describe(_logged("D-detail"))
    assert f"redacted: {description}" in rendered
    assert aws not in rendered

    # A raw line with nothing redacted renders without any mention of it.
    log = EventLog(tmp_path / "D-clean")
    log.append(Agent(timestamp=1.0, spec_id="D-clean", raw=True, line="nothing here"))
    assert "redacted" not in describe(_logged("D-clean"))


def test_the_credential_shapes_are_spelled_in_one_module():
    from saffron.credentials import CREDENTIAL_SHAPES

    root = Path(__file__).resolve().parent.parent / "saffron"
    credentials_file = root / "credentials.py"
    py_files = list(root.rglob("*.py"))

    for _, pattern in CREDENTIAL_SHAPES:
        source = pattern.pattern
        found_in = [f for f in py_files if source in f.read_text()]
        assert found_in == [credentials_file]
