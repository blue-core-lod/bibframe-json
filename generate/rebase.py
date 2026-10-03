"""Move every published URL in the repository to a different host.

A `$id` names a host, and which host is a decision about where this is
published rather than anything about the schema. Hosting and identity travel
together: a relative `$ref` resolves against the `$id` of the file it appears
in, not against wherever you fetched that file, so serving the schemas
anywhere other than the path their own `$id`s name leaves every reference
resolving to nothing.

    uv run python generate/rebase.py https://example.org/bibframe-json

Then re-run generate/bundle.py and read the diff. tests/test_artifacts.py is
what refuses the half-finished version.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://bibframe-json.org"


def rebase(new_base: str) -> None:
    """Move every URL in the repository to a different host.

    `$id`s name a host, and which host is a decision about where this is
    published rather than anything about the schema -- so it is worth being
    one command instead of a sweep that misses the test fixtures. What it
    rewrites is tracked files only, found by grep, so an untracked corpus is
    left alone.
    """
    new_base = new_base.rstrip("/")
    found = subprocess.run(
        ["git", "grep", "-l", BASE],
        cwd=ROOT,
        capture_output=True,
        text=True,
        # git grep exits 1 for "found nothing", which is not an error here but
        # is not a success either -- it means the base is already gone, and
        # rewriting nothing while reporting a move would be the worst outcome.
        check=False,
    )
    if found.returncode > 1:
        raise SystemExit(f"git grep failed: {found.stderr.strip()}")
    touched = [line for line in found.stdout.splitlines() if line]
    if not touched:
        raise SystemExit(f"nothing references {BASE}; is it already rebased?")
    for name in touched:
        path = ROOT / name
        path.write_text(path.read_text().replace(BASE, new_base))
    print(f"rebased {len(touched)} files to {new_base}")
    print("now re-run generate/bundle.py, and check git diff")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: rebase.py <new base url>")
    rebase(sys.argv[1])
