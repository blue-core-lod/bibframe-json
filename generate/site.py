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
    ("producing.md", "Producing it", "Producing it"),
    ("validating.md", "Validating", "Validating"),
    ("conformance.md", "Checking an implementation", "Conformance"),
)

LANGUAGES = {".json": "json", ".jsonld": "json", ".py": "python", ".sh": "sh"}


# A path written for someone reading the repository, and where the same file
# is served. bibframe_json/schema/ exists so hatchling ships the schemas with
# the package; the site serves them at schema/ so their own $ids resolve. The
# replacement is relative, not root-absolute: this is published under a path,
# so /schema/... would leave the project and 404.
SERVED = {
    "../bibframe_json/schema/": "schema/",
    "bibframe_json/schema/": "schema/",
    "bibframe_json/context/": "context/",
    # A link to another page is written docs/shape.md so it works on GitHub;
    # the site serves those pages flat. Matched with the link syntax attached
    # so that "docs/" in running prose, or in the table of what is generated,
    # is left alone.
    "](docs/": "](",
}


def as_served(text: str) -> str:
    """Point repository paths at where the site serves the same files."""
    for repo, served in SERVED.items():
        text = text.replace(repo, served)
    return text


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
    return as_served(found.group(1).strip())


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

    Repository paths are pointed at where the site serves the same files; see
    `as_served`.
    """
    text = re.sub(r"\A#(?!#).*\n", "", document.read_text()).strip()
    return as_served(text)


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


# Where the BIBFRAME primer explains what each of these is for. The primer is
# LC's reference guide to the model; this repository describes one way to write
# it down, so a definition that has a counterpart there should say so rather
# than paraphrase it. Eleven of fifteen do; Ref, Text, Resource and main are
# artefacts of the shape rather than parts of the model, and Classification has
# no section of its own.
PRIMER = "https://bibframe.org/docs/view/documentation-bf-primer/"
CLASSES = "data-model-resource-description-classes/"
COMMON = "data-model-common-properties-and-classes/"
EXPLAINED = {
    "Work.json": CLASSES + "works.md",
    "Instance.json": CLASSES + "instances.md",
    "Item.json": CLASSES + "items.md",
    "Hub.json": CLASSES + "hubs.md",
    "AdminMetadata.json": COMMON + "administrative-metadata.md",
    "Contribution.json": COMMON + "contributions-and-contributors.md",
    "Identifier.json": COMMON + "identifiers.md",
    "Note.json": COMMON + "notes.md",
    "ProvisionActivity.json": COMMON + "provision-activity.md",
    "Relation.json": COMMON + "relationships.md",
    "Title.json": COMMON + "titles.md",
}


def definitions() -> str:
    """A table of the split dialect files, read out of the files.

    `title` and `description` are already written in each one -- they are what
    a validator surfaces -- so the reference page is the schemas talking about
    themselves.
    """
    rows = [
        "| Definition | What it is | In the model |",
        "| --- | --- | --- |",
    ]
    files = sorted((ROOT / "bibframe_json" / "schema" / "dialect").glob("*.json"))
    for path in [p for p in files if p.name == "main.json"] + [
        p for p in files if p.name != "main.json"
    ]:
        schema = json.loads(path.read_text())
        described = schema.get("description") or schema.get("title", "")
        page = EXPLAINED.get(path.name)
        explains = f"[primer]({PRIMER}{page})" if page else ""
        rows.append(
            f"| [`{path.name}`](schema/dialect/{path.name}) | {described} | {explains} |"
        )
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
            out.append(f"**{verdict}**: {listed}\n")
    return "\n".join(out)


# The ISBD areas the card on the front page shows, in the order a card shows
# them, each with the delimiter that introduces it and how many line breaks
# precede it. This is the argument the hero makes: the punctuation is the
# structure, and it was the structure before JSON existed -- ISBD(M)
# standardised it in 1971.
#
# Areas 1 to 4 run on as one paragraph; the physical description starts a line
# of its own, and the note and the ISBN each start another. That is the layout
# of a card rather than of the standard, which says nothing about line breaks.
ISBD = (
    ("title", "", 0),
    ("responsibilityStatement", " / ", 0),
    ("editionStatement", ". \u2014 ", 0),
    ("provisionActivity", ". \u2014 ", 0),
    ("extent", "", 1),
    ("dimensions", " ; ", 0),
    ("note", "", 2),
    ("identifiedBy", "", 2),
)


def _imprint(record: dict) -> str:
    """Place : publisher, date -- ISBD area 4, from the bflc simple forms.

    The record also carries publicationStatement with the imprint already
    assembled, which is the same string a cataloguer typed. Taking the parts
    instead, because what the hero claims is that the parts are addressable.

    \0 marks a delimiter falling inside one area rather than between two, so
    area 4's " : " and ", " are coloured like every other delimiter.
    """
    activity = record["provisionActivity"][0]
    return (
        f"{activity['bflc:simplePlace'][0]}\x00 : \x00"
        f"{activity['bflc:simpleAgent'][0]}\x00, \x00"
        f"{activity['bflc:simpleDate'][0]}."
    )


def _isbn(record: dict) -> str:
    for identifier in record["identifiedBy"]:
        if "Isbn" in identifier.get("@type", []):
            qualifier = identifier.get("qualifier", [])
            said = f" ({qualifier[0]})" if qualifier else ""
            return f"ISBN {identifier['rdf:value'][0]}{said}"
    return ""


READERS = {
    "title": lambda r: r["title"][0]["mainTitle"][0],
    "responsibilityStatement": lambda r: r["responsibilityStatement"][0],
    "editionStatement": lambda r: r["editionStatement"][0],
    "provisionActivity": _imprint,
    "extent": lambda r: r["extent"][0]["rdfs:label"][0],
    "dimensions": lambda r: r["dimensions"][0] + ".",
    "note": lambda r: r["note"][0]["rdfs:label"][0],
    "identifiedBy": _isbn,
}


def _delimiter(before: str, delimiter: str) -> str:
    """A delimiter, marked up, with ISBD's one piece of arithmetic applied.

    An area delimiter is written ". \u2014 ", but an element that already ends
    in a full stop does not take a second one: "Madhusudan. \u2014 2nd revised
    edition", not "Madhusudan.. \u2014". Transcribed statements of
    responsibility very often end in a stop, so this is the ordinary case
    rather than an edge one.
    """
    if delimiter.startswith(".") and before.rstrip().endswith("."):
        delimiter = delimiter[1:]
    return f'<span class="d">{html.escape(delimiter)}</span>' if delimiter else ""


def compact_json(node: object, level: int = 0) -> str:
    """JSON, with any array of scalars kept on one line.

    json.dumps(indent=2) gives every value in this shape its own three lines,
    because every value is an array: the record on the front page runs to
    eighty lines of which most are a bracket. Beside a four-line catalogue
    card that loses the comparison the card is there to make.

    Arrays holding an object still break, so the nesting stays visible. The
    output is ordinary JSON -- tests/test_example.py parses it back.
    """
    pad, inner = "  " * level, "  " * (level + 1)
    if isinstance(node, dict):
        if not node:
            return "{}"
        pairs = ",\n".join(
            f"{inner}{json.dumps(key, ensure_ascii=False)}: "
            f"{compact_json(value, level + 1)}"
            for key, value in node.items()
        )
        return "{\n" + pairs + f"\n{pad}}}"
    if isinstance(node, list):
        if all(not isinstance(item, (dict, list)) for item in node):
            one = ", ".join(json.dumps(item, ensure_ascii=False) for item in node)
            return f"[{one}]"
        items = ",\n".join(f"{inner}{compact_json(item, level + 1)}" for item in node)
        return "[\n" + items + f"\n{pad}]"
    return json.dumps(node, ensure_ascii=False)


def card() -> str:
    """The signature: a catalogue card, and the JSON that is the same record.

    Generated from example/instance.json, so it is a view of a record that
    validates rather than a picture of one. tests/test_example.py checks that
    every fragment of description on it is a string in that file -- a card
    with a hand-typed title would look identical and mean nothing.

    Delimiters are marked up in both halves so they can be coloured, and the
    colour is what connects them: a line drawn between the two would not
    survive a narrow screen.

    There is no tracing block. A card's tracings name what else the item is
    filed under, so the position is the apparatus slot and listing the JSON
    keys there was tempting -- but the JSON directly below shows the same keys
    in the same order in bold, so it was a weaker copy of its own neighbour.
    The description carries no annotation either: a card's description is a
    transcription and takes no editorial marks.
    """
    record = json.loads((ROOT / "example" / "instance.json").read_text())
    out: list[str] = []
    keys: list[str] = []
    previous = ""
    for key, delimiter, breaks in ISBD:
        try:
            value = READERS[key](record)
        except (KeyError, IndexError):
            continue
        if not value:
            continue
        keys.append(key)
        if breaks:
            out.append("<br>" * breaks)
            previous = ""
        else:
            out.append(_delimiter(previous, delimiter))
        parts = html.escape(value).split("\x00")
        out.append(
            "".join(
                part if i % 2 == 0 else f'<span class="d">{part}</span>'
                for i, part in enumerate(parts)
            )
        )
        previous = value.replace("\x00", "")

    shown = {key: record[key] for key in keys if key in record}
    # The card shows one publication statement because that is what a card
    # does; showing the record's two here would make the halves disagree.
    if len(shown.get("provisionActivity", [])) > 1:
        shown["provisionActivity"] = shown["provisionActivity"][:1]
    quoted = markdown.markdown(
        "```json\n" + compact_json(shown) + "\n```",
        extensions=["fenced_code", "codehilite"],
        extension_configs={"codehilite": {"guess_lang": False}},
    )
    return f"""<figure class="plate">
  <div class="card" role="img" aria-label="A catalogue card for the record below">
    <p class="description">{"".join(out)}</p>
  </div>
  <div class="same">the same record</div>
  <div class="json">{quoted}</div>
  <p class="provenance">Abridged to the areas a card has room for. The whole
    record is <a href="example/instance.json">example/instance.json</a>.</p>
  <figcaption>
    The punctuation in the top half is ISBD, standardised in 1971; in the
    bottom half it is JSON. Both do the one job this project cares about:
    making a description parseable by someone who does not already understand
    it. The delimiter left unmarked sits inside a transcribed string, where
    nothing can reach it.
  </figcaption>
</figure>"""


def fields(page: str) -> str:
    """Wrap each `##` section so its heading can sit in the left rail.

    The rail is the layout's one structural claim: this documentation
    describes fields, so it is set as a record of fields -- a label to the
    left, its content indented beside it, which is what a catalogue card's
    hanging indent is for.

    Both heading levels get a label, so "Python" and "JavaScript" sit in the
    rail as readily as a top-level section does.

    Every child is wrapped, including a page that has no headings at all.
    Unwrapped, they become grid items of main directly and land in alternating
    columns -- the first paragraph beside the heading, the next table in the
    rail. A page with no h2 used to hit exactly that.

    Done to the HTML rather than in Markdown so the pages stay readable as
    Markdown on GitHub. CSS subgrid then lines every heading up with the
    page's own columns; without a wrapper there is no row to line up.
    """
    lede, *sections = re.split(r"(?=<h[23])", page)
    wrapped = "".join(
        f'<section class="field">\n{part}</section>\n' for part in sections
    )
    return f'<div class="lede">\n{lede}</div>\n{wrapped}'


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
        if kind == "card":
            return card()
        raise SystemExit(f"unknown directive: {kind}")

    return re.sub(
        r"<!--\s*(readme|markdown|include|definitions|cases|card)\s*:?([^>]*?)-->",
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
        # A link between pages is written .md, which is what makes the
        # sources readable on GitHub. The fragment has to survive: matching
        # only .md" left shape.md#the-definitions pointing at a file the site
        # does not serve.
        converted = re.sub(r'\.md(?=["#])', ".html", page.convert(source))
        content = fields(converted)
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
    shutil.copytree(
        DOCS / "fonts",
        out / "fonts",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("faces.css"),
    )
    # The @font-face rules go first, and url(fonts/...) in them is relative to
    # style.css, which sits at the root beside fonts/.
    # A page that has been removed from PAGES is still on disk from the build
    # before, and would still be deployed from a local build. Same class of
    # mistake as a stale CNAME, so it is swept the same way.
    wanted = {file.replace(".md", ".html") for file, _, _ in PAGES}
    for stale in out.glob("*.html"):
        if stale.name not in wanted:
            stale.unlink()

    style = (DOCS / "fonts" / "faces.css").read_text() + "\n"
    style += (DOCS / "style.css").read_text()

    def tokens_only(style: str) -> str:
        """The token colours, without the theme's own background.

        get_style_defs emits `.codehilite { background: ... }` alongside the
        token rules, and it is concatenated after this stylesheet, so it won
        -- putting a band of GitHub's grey around every block. The surface
        belongs to the palette; a code block and a catalogue card are the
        same object here.
        """
        defs = HtmlFormatter(style=style).get_style_defs(".codehilite")
        return "\n".join(
            line
            for line in defs.splitlines()
            if not re.match(r"^\.codehilite \{ background", line.strip())
        )

    light = tokens_only("friendly")
    dark = tokens_only("github-dark")
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
