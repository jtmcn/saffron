"""One-shot measurement: what `/v1/models` answers a subscription OAuth token.

Not imported by anything. Run by hand with a token in the environment of the
command itself, and record the result in
`docs/evidence/2026-09-05-token-probe-request-shape.md`:

    env CLAUDE_CODE_OAUTH_TOKEN=... uv run python \
      docs/evidence/scripts/2026-09-05-token-probe-shape.py

Prints one line per header combination. Never prints the token.
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request

from saffron.cell import proxy

_URL = f"https://{proxy.UPSTREAM_HOST}/v1/models"

_COMBINATIONS: list[tuple[str, dict[str, str]]] = [
    ("Authorization only", {}),
    ("+ anthropic-version", {"anthropic-version": "2023-06-01"}),
    ("+ anthropic-beta", {"anthropic-beta": "oauth-2025-04-20"}),
    (
        "all three",
        {
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "oauth-2025-04-20",
        },
    ),
]


def main() -> int:
    token = (os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") or "").strip()
    if not token:
        print("CLAUDE_CODE_OAUTH_TOKEN is unset", file=sys.stderr)
        return 2

    print(f"GET {_URL}")
    for label, extra in _COMBINATIONS:
        headers = {"Authorization": f"Bearer {token}", **extra}
        request = urllib.request.Request(_URL, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                print(f"  {label:24} -> {response.status}")
        except urllib.error.HTTPError as exc:
            body = exc.read(200).decode("utf-8", "replace").replace("\n", " ")
            print(f"  {label:24} -> {exc.code}  {body}")
        except urllib.error.URLError as exc:
            print(f"  {label:24} -> unreachable: {exc.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
