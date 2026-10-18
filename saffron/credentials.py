"""The credential shapes `EventLog` and PACKAGE both redact against (item 46, §5.4).

One module, so a shape fixed here is fixed for the event log and the pushed
patch alike. Neither reader keeps its own copy.
"""

from __future__ import annotations

import re

OWN_TOKEN_DESCRIPTION = "the cell's own CLAUDE_CODE_OAUTH_TOKEN"

_PRIVATE_KEY_DESCRIPTION = "a private key block"
_PRIVATE_KEY_END = re.compile(r"-----END [A-Z ]*PRIVATE KEY-----")

# ponytail: a redaction, not the `secrets` gate, which is v1's to build (§5.4).
# A shape not listed here still passes both readers.
CREDENTIAL_SHAPES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("an Anthropic API key", re.compile(r"sk-ant-api\d{2}-[A-Za-z0-9_\-]{16,}")),
    ("an Anthropic OAuth token", re.compile(r"sk-ant-oat\d{2}-[A-Za-z0-9_\-]{8,}")),
    ("a GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}")),
    ("an AWS access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    (_PRIVATE_KEY_DESCRIPTION, re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)


def is_own_token(token: str | None, text: str) -> bool:
    """The literal-token check, length guard unchanged: a short or empty
    token would substring-match unrelated text."""
    return bool(token) and len(token) > 8 and token in text


def _placeholder(description: str) -> str:
    return f"<redacted: {description}>"


def _redact_private_key_blocks(text: str, header: re.Pattern[str]) -> tuple[str, bool]:
    """One block per header match: from the header through the next END
    line, or to the end of the string when none follows. Never anchored on
    the body's own characters, so a block clipped before its END line is
    still replaced whole."""
    hit = False
    while (match := header.search(text)) is not None:
        hit = True
        end = _PRIVATE_KEY_END.search(text, match.end())
        stop = end.end() if end is not None else len(text)
        text = (
            text[: match.start()] + _placeholder(_PRIVATE_KEY_DESCRIPTION) + text[stop:]
        )
    return text, hit


def redact(text: str, *, token: str | None) -> tuple[str, tuple[str, ...]]:
    """Replace the cell's own token, then every match of every credential
    shape, in `text`. Returns the new text and each kind's description,
    named once however many times it matched."""
    found: list[str] = []
    if token is not None and is_own_token(token, text):
        text = text.replace(token, _placeholder(OWN_TOKEN_DESCRIPTION))
        found.append(OWN_TOKEN_DESCRIPTION)
    for description, pattern in CREDENTIAL_SHAPES:
        if description == _PRIVATE_KEY_DESCRIPTION:
            text, hit = _redact_private_key_blocks(text, pattern)
        else:
            text, count = pattern.subn(_placeholder(description), text)
            hit = count > 0
        if hit:
            found.append(description)
    return text, tuple(found)
