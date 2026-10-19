"""The credential shapes PACKAGE refuses to push (`DESIGN.md` §5.7), and the
ones `EventLog` redacts from `events.jsonl` before the write (§4.7). One
module, so neither reader drifts from the other (backlog item 46, §5.4, §9).
"""

from __future__ import annotations

import re

OWN_TOKEN_DESCRIPTION = "the cell's own CLAUDE_CODE_OAUTH_TOKEN"
_PRIVATE_KEY_HEADER = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")

# ponytail: a refusal and a redaction, not the `secrets` gate (§5.4). v1's to build.
# A shape not listed here still reaches the remote and the log unredacted.
CREDENTIAL_SHAPES = (
    ("an Anthropic API key", re.compile(r"sk-ant-api\d{2}-[A-Za-z0-9_\-]{16,}")),
    ("an Anthropic OAuth token", re.compile(r"sk-ant-oat\d{2}-[A-Za-z0-9_\-]{8,}")),
    ("a GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}")),
    ("an AWS access key id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("a private key block", _PRIVATE_KEY_HEADER),
)

# A header-only match would leave the key's body written, so `redact` sweeps
# from the header through the next END line instead.
_PRIVATE_KEY_BLOCK = re.compile(
    _PRIVATE_KEY_HEADER.pattern + r"(?:.*?-----END [A-Z ]*PRIVATE KEY-----|.*\Z)",
    re.DOTALL,
)


def matches_own_token(token: str | None, text: str) -> bool:
    """True when `text` carries the cell's own literal token. Length-guarded:
    a short or empty token would substring-match unrelated lines."""
    return bool(token) and len(token) > 8 and token in text


def redact(text: str, *, token: str | None) -> tuple[str, tuple[str, ...]]:
    """`text` with the cell's own token and every credential shape replaced,
    and the description of each kind that was found at least once. Never
    raises. Returns `text` unchanged, and an empty tuple, when nothing matched."""
    found: list[str] = []
    if matches_own_token(token, text) and token is not None:
        text = text.replace(token, f"[redacted: {OWN_TOKEN_DESCRIPTION}]")
        found.append(OWN_TOKEN_DESCRIPTION)
    for description, pattern in CREDENTIAL_SHAPES:
        sweep = _PRIVATE_KEY_BLOCK if pattern is _PRIVATE_KEY_HEADER else pattern
        new_text, count = sweep.subn(f"[redacted: {description}]", text)
        if count:
            text = new_text
            found.append(description)
    return text, tuple(found)
