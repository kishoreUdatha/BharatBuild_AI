"""
Put a GitHub App private key into backend/.env without ever displaying it.

A PEM is multi-line and an environment variable is not, so the newlines are
escaped as \\n - which `github_repos._app_jwt` un-escapes before signing.

Deliberately prints nothing but a confirmation and a fingerprint. Copying a
key through a terminal, a chat window or a screenshot is how it ends up
somewhere it cannot be taken back from.

    python backend/scripts/set_github_app_key.py ~/Downloads/<app>.private-key.pem
"""
from __future__ import annotations

import hashlib
import io
import os
import sys

# The compose file loads `env_file: - .env` from the project root, so that is
# the one the container actually reads. backend/.env is not passed to it.
ENV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".env")
KEY = "GITHUB_APP_PRIVATE_KEY"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__.strip())
        return 2

    pem_path = os.path.expanduser(sys.argv[1])
    if not os.path.exists(pem_path):
        print(f"No such file: {pem_path}")
        return 1

    pem = io.open(pem_path, encoding="utf-8").read().strip()
    if "PRIVATE KEY" not in pem:
        print("That file does not look like a PEM private key.")
        return 1

    # Shown so you can match it against the fingerprint GitHub lists, without
    # revealing anything about the key itself.
    digest = hashlib.sha256(pem.encode()).hexdigest()[:16]

    # Built without an f-string: a backslash inside an f-string expression is
    # a syntax error before Python 3.12, and this has to run on whatever the
    # machine has.
    escaped = pem.replace("\n", "\\n")
    line = KEY + "=" + escaped + "\n"

    existing = []
    if os.path.exists(ENV):
        existing = io.open(ENV, encoding="utf-8").read().splitlines(keepends=True)

    replaced = False
    out = []
    for row in existing:
        if row.startswith(f"{KEY}="):
            out.append(line)
            replaced = True
        else:
            out.append(row)
    if not replaced:
        if out and not out[-1].endswith("\n"):
            out.append("\n")
        out.append(line)

    io.open(ENV, "w", encoding="utf-8").write("".join(out))
    os.chmod(ENV, 0o600) if os.name != "nt" else None

    print(f"{'Replaced' if replaced else 'Added'} {KEY} in {ENV}")
    print(f"  file digest {digest}  ({len(pem)} bytes)")
    print("\nNow delete the downloaded .pem - the key lives in .env and "
          "nowhere else:")
    print(f"  rm {pem_path}")
    print("\nThen recreate the backend so it re-reads env_file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
