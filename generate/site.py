"""Build the documentation site.

Two jobs, and the second is the one that matters.

The pages are a readable presentation of what the repository already says,
split so that a section can be linked to rather than scrolled to. They hold
almost no prose of their own: a page pulls a named section out of `README.md`
or inlines another Markdown file, so there is one copy of every sentence and
no second copy to drift. The tables of definitions and conformance cases are
read out of the files themselves for the same reason.

The artifacts -- the context, the schemas, the conformance corpus -- are copied
in at the paths their own `$id`s name. That is what turns
`https://blue-core-lod.github.io/bibframe-json/schema/dialect/Work.json` from a string in a field
called `$id` into a file a validator can fetch, and it is what lets
`{"$ref": "Ref.json"}` resolve over the network the way it already resolves on
disk.

Nothing built here is checked in. The site is assembled in CI and deployed, so
git holds one copy of each schema rather than two.
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import markdown
from pygments.formatters.html import HtmlFormatter

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = ROOT / "site"

# Every $id in the repository is rooted here, and the artifacts are served at
# the paths below it, so the two agree. `--rebase` moves both at once, and
# tests/test_site.py fails if they ever disagree.
BASE = "https://blue-core-lod.github.io/bibframe-json"

# Where each artifact is served, relative to BASE. The schema keys are the
# reason this mapping is written out rather than inferred: schemas live under
# bibframe_json/ so that hatchling ships them, and are served at /schema/ so
# that their $ids resolve.
ARTIFACTS = {
    "bibframe_json/context": "context",
    "bibframe_json/schema": "schema",
    "conformance": "conformance",
    "example": "example",
}

PAGES = (
    ("index.md", "bibframe-json", None),
    ("shape.md", "The shape", "The shape"),
    ("cbd.md", "A Concise Bounded Description", "A CBD"),
    ("validating.md", "Validating", "Validating"),
    ("conformance.md", "Checking an implementation", "Conformance"),
    ("project.md", "The project", "The project"),
)

LANGUAGES = {".json": "json", ".jsonld": "json", ".py": "python", ".sh": "sh"}


def section(document: Path, heading: str) -> str:
    """One `##` section of a Markdown file, without its heading.

    So that a page can present a section of the README rather than repeat it.
    The heading is dropped because the page supplies its own, which is often
    worded for someone who arrived from a link rather than from the top.

    With no heading, the text before the first `##`: the opening, minus the
    title and the CI badge, which say nothing to a reader who is not looking
    at the repository.
    """
    text = document.read_text()
    if not heading:
        opening = text.split("\n## ", 1)[0]
        opening = re.sub(r"\A#(?!#).*\n", "", opening)
        return re.sub(r"^\[!\[.*\n", "", opening, flags=re.MULTILINE).strip()
    pattern = rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)"
    found = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not found:
        raise SystemExit(f"{document.name} has no section '{heading}'")
    return found.group(1).strip()


def links(document: Path) -> str:
    """The reference-style link definitions a Markdown file ends with.

    `[BIBFRAME]` is written once at the foot of the README and used in several
    sections. Pulled out on its own, a section loses them and renders the
    bracket text verbatim, so they are appended to every page -- unused ones
    produce nothing.
    """
    defined = [
        line
        for line in document.read_text().splitlines()
        if re.match(r"^\[[^\]]+\]:\s", line)
    ]
    return "\n".join(defined)


def body(document: Path) -> str:
    """A Markdown file with its `#` title removed, for inlining under another.

    Its `##` headings are left alone. They and the including page's are peers,
    since the page supplies the title and nothing else above them.

    A path written for someone reading the repository is rewritten to where
    the same file is served, because `../bibframe_json/schema/` is how you
    reach the schemas from a subdirectory of a checkout and not how you reach
    them from a page.
    """
    text = re.sub(r"\A#(?!#).*\n", "", document.read_text()).strip()
    return text.replace("../bibframe_json/schema/", "/schema/")


def quote(path: Path, display: str) -> str:
    """A file as a fenced code block, so an example cannot be miscopied.

    The examples on the site are the files the tests run against. Pasting one
    into a page would make it a claim about those files instead of a view of
    them, and the two would part company the first time one changed.
    """
    language = LANGUAGES.get(path.suffix, "")
    return (
        f"*[`{display}`]({display})*\n\n```{language}\n{path.read_text().strip()}\n```"
    )


def definitions() -> str:
    """A table of the split dialect files, read out of the files.

    `title` and `description` are already written in each one -- they are what
    a validator surfaces -- so the reference page is the schemas talking about
    themselves.
    """
    rows = ["| Definition | What it is |", "| --- | --- |"]
    files = sorted((ROOT / "bibframe_json" / "schema" / "dialect").glob("*.json"))
    for path in [p for p in files if p.name == "main.json"] + [
        p for p in files if p.name != "main.json"
    ]:
        schema = json.loads(path.read_text())
        described = schema.get("description") or schema.get("title", "")
        rows.append(f"| [`{path.name}`](schema/dialect/{path.name}) | {described} |")
    return "\n".join(rows)


def cases() -> str:
    """The conformance corpus, listed. A case is a link to the document."""
    out = []
    for kind in sorted(p.name for p in (ROOT / "conformance").iterdir() if p.is_dir()):
        out.append(f"### `{kind}`\n")
        for verdict in ("accept", "reject"):
            folder = ROOT / "conformance" / kind / verdict
            if not folder.is_dir():
                continue
            listed = ", ".join(
                f"[{path.stem}](conformance/{kind}/{verdict}/{path.name})"
                for path in sorted(folder.glob("*.json"))
            )
            out.append(f"**{verdict}** — {listed}\n")
    return "\n".join(out)


def expand(text: str) -> str:
    """Resolve the directives a page uses to pull content from the repository."""

    def resolve(match: re.Match) -> str:
        kind, argument = match.group(1), match.group(2).strip()
        if kind == "readme":
            return section(ROOT / "README.md", argument)
        if kind == "markdown":
            return body(ROOT / argument)
        if kind == "include":
            return quote(ROOT / argument, argument)
        if kind == "definitions":
            return definitions()
        if kind == "cases":
            return cases()
        raise SystemExit(f"unknown directive: {kind}")

    return re.sub(
        r"<!--\s*(readme|markdown|include|definitions|cases)\s*:?([^>]*?)-->",
        resolve,
        text,
    )


def render(base: str = BASE, out: Path = OUT) -> None:
    out.mkdir(parents=True, exist_ok=True)
    layout = (DOCS / "_layout.html").read_text()
    nav = "\n".join(
        f'        <a href="{file.replace(".md", ".html")}">{label}</a>'
        for file, _, label in PAGES
        if label
    )

    for file, title, _ in PAGES:
        page = markdown.Markdown(
            extensions=["fenced_code", "tables", "toc", "attr_list", "codehilite"],
            extension_configs={"codehilite": {"guess_lang": False}},
        )
        source = expand((DOCS / file).read_text())
        source = f"{source}\n\n{links(ROOT / 'README.md')}\n"
        # Between pages, not to the repository: a link written as shape.md is
        # what makes the sources readable on GitHub too.
        content = page.convert(source).replace('.md"', '.html"')
        name = file.replace(".md", ".html")
        (out / name).write_text(
            layout.replace("{{title}}", html.escape(title))
            .replace("{{nav}}", nav)
            .replace("{{content}}", content)
            .replace("{{here}}", name)
            .replace("{{base}}", base)
        )

    # Two highlighting themes rather than one filtered: a light theme's token
    # colours on a dark background are unreadable, and inverting the block
    # turns dark blue keys into the background.
    style = (DOCS / "style.css").read_text()
    light = HtmlFormatter(style="friendly").get_style_defs(".codehilite")
    dark = HtmlFormatter(style="github-dark").get_style_defs(".codehilite")
    dark = "\n".join(f"    {line}" for line in dark.splitlines())
    (out / "style.css").write_text(
        f"{style}\n"
        f"/* pygments, light */\n{light}\n"
        f"/* pygments, dark */\n"
        f"@media (prefers-color-scheme: dark) {{\n{dark}\n}}\n"
    )

    for source_dir, served in ARTIFACTS.items():
        target = out / served
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(
            ROOT / source_dir,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.md"),
        )

    # A custom domain needs this file in the published directory. A project
    # page under github.io does not -- and must not have it, because Pages
    # reads it and would redirect the whole site to a domain that is not
    # serving it. Written or removed rather than written or skipped: a CNAME
    # left behind by an earlier build is how that happens.
    host = base.split("://", 1)[-1]
    cname = out / "CNAME"
    if "/" in host:
        cname.unlink(missing_ok=True)
    else:
        cname.write_text(f"{host}\n")

    print(f"{out.name}/ built for {base}: {len(PAGES)} pages")


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebase", metavar="URL", help="move every $id to a new host")
    args = parser.parse_args()
    if args.rebase:
        rebase(args.rebase)
        sys.exit(0)
    render()
