"""The artifacts, and the one rule the docs site exists to uphold.

A relative `$ref` resolves against the `$id` of the file it appears in, not
against wherever you fetched that file. So a schema served anywhere other than
the path its own `$id` names has references that resolve to nothing, and the
whole published set is useless.

`artifacts.json` says where each tree is published.
`src/integrations/artifacts.mjs` copies them there and this reads the same file
rather than restating it, because the two disagreeing is exactly the failure
worth preventing.

None of this needs the site built: the mapping plus the source tree is enough
to know where every file will land.
"""

import json
import posixpath
import re
from pathlib import Path

import pytest

import bibframe_json

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "artifacts.json").read_text())
BASE = CONFIG["base"]
PUBLISH: dict[str, str] = CONFIG["publish"]


def published() -> dict[str, Path]:
    """Every file that will be served, by the path it will be served at."""
    served = {}
    for source, prefix in PUBLISH.items():
        for path in sorted((ROOT / source).rglob("*")):
            if not path.is_file() or path.suffix == ".md":
                continue
            relative = path.relative_to(ROOT / source)
            served[f"{prefix}/{relative.as_posix()}"] = path
    return served


def test_the_mapping_covers_what_it_claims():
    """An empty mapping would make every test below pass by doing nothing."""
    assert set(PUBLISH.values()) == {"context", "schema", "conformance", "example"}
    assert len(published()) > 40


@pytest.mark.parametrize(
    "url",
    [url for url, path in published().items() if path.suffix == ".json"],
)
def test_a_schema_is_served_at_the_url_its_id_names(url: str):
    """The invariant. Written by hand in the schema, computed here."""
    schema = json.loads(published()[url].read_text())
    if not isinstance(schema, dict) or "$id" not in schema:
        pytest.skip("not a schema with an $id")
    assert schema["$id"] == f"{BASE}/{url}"


def test_at_least_the_known_schemas_carry_an_id():
    """So that the test above cannot pass by skipping everything."""
    with_id = [
        url
        for url, path in published().items()
        if path.suffix == ".json"
        and isinstance(json.loads(path.read_text()), dict)
        and "$id" in json.loads(path.read_text())
    ]
    assert len(with_id) >= 18, with_id


def test_the_context_is_published_where_bibframe_json_says_it_is():
    """Three things name this URL and they have to agree.

    `CONTEXT_URL` is what a producer writes into a document, `example/cbd.json`
    is one that did, and this mapping decides where the file lands. A document
    naming a context that is not there is worse than one naming none: a
    JSON-LD processor fails on it, where it would have ignored the absence.
    """
    served = f"{BASE}/context/bibframe.jsonld"
    assert bibframe_json.CONTEXT_URL == served
    assert "context/bibframe.jsonld" in published()
    example = json.loads((ROOT / "example" / "cbd.json").read_text())
    assert example["@context"] == served


def test_the_conformance_corpus_is_published_whole():
    """A case nobody can fetch is a case no other implementation can run."""
    written = {
        path.relative_to(ROOT / "conformance").as_posix()
        for path in (ROOT / "conformance").rglob("*.json")
    }
    serving = {
        url.removeprefix("conformance/")
        for url in published()
        if url.startswith("conformance/")
    }
    assert written == serving


def pages() -> dict[str, Path]:
    """Each docs page, by the URL path it is served under.

    `index.mdx` is the site root and everything else gets a directory, which
    is what `trailingSlash: "always"` means. The depth matters: a link written
    `../schema/x` is right from `validating/` and walks out of the site
    entirely from the root.
    """
    found = {}
    for path in sorted((ROOT / "src" / "content" / "docs").glob("*.mdx")):
        slug = "" if path.stem == "index" else f"{path.stem}/"
        found[slug] = path
    return found


def test_every_artifact_link_in_the_pages_resolves():
    """Follow each link the way a browser would, from where the page is served.

    This is the check the link validator cannot do: the targets are files in
    the published trees rather than pages, so it refuses them as relative
    links and looks no further. Getting the depth wrong is silent otherwise --
    from the site root `../schema/dialect.json` leaves the site.
    """
    serving = published()
    assert pages(), "no pages found"
    checked = 0
    for slug, path in pages().items():
        text = path.read_text()
        for href in re.findall(r"\]\(([^)]+)\)", text) + re.findall(
            r'href="([^"]+)"', text
        ):
            if href.startswith(("http", "#", "mailto:", "/")):
                continue
            resolved = posixpath.normpath(posixpath.join(slug, href))
            # A link that walks above the site root is wrong whatever it
            # points at, and it is the mistake this test exists for: from the
            # root, ../schema/x leaves the site. Caught before the filter
            # below, which would otherwise skip it for not starting with a
            # published prefix.
            assert not resolved.startswith(".."), (
                f"{path.name} links to {href}, which from /{slug} escapes the "
                f"site root as {resolved}"
            )
            if resolved.split("/")[0] not in PUBLISH.values():
                continue
            assert resolved in serving, (
                f"{path.name} links to {href}, which from /{slug} resolves to "
                f"{resolved}, and nothing is published there"
            )
            checked += 1
    assert checked >= 6, f"only {checked} artifact links found; pattern wrong?"
