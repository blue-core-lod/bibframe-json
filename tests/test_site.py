"""The documentation site, checked for the two things it can get wrong.

One is ordinary: a page names a README section that has been renamed, or links
to a file that has moved, and the build produces a page with a hole in it.

The other is the point of the site. Every `$id` in the repository names a URL,
and a schema is only useful at that URL if the file is served there. The two
are written in different places -- the `$id` by hand in the schema, the path by
`ARTIFACTS` in the generator -- so nothing but a test keeps them together.
"""

import json
import re

import pytest

from generate import site


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> object:
    out = tmp_path_factory.mktemp("site")
    site.render(out=out)
    return out


def test_every_page_is_built(built):
    for file, _, _ in site.PAGES:
        page = built / file.replace(".md", ".html")
        assert page.exists(), f"{file} produced no page"
        assert page.read_text().strip().endswith("</html>")


def test_no_directive_survives_the_build(built):
    """A directive left in the output is one `expand` did not recognise."""
    for page in built.glob("*.html"):
        text = page.read_text()
        left = re.findall(r"<!--\s*(?:readme|markdown|include|definitions|cases)", text)
        assert not left, f"{page.name} has an unresolved directive"
        assert "{{" not in text, f"{page.name} has an unfilled placeholder"


def test_a_page_cannot_name_a_section_that_does_not_exist():
    """The failure mode this catches: a README heading is reworded.

    The page then renders with a gap where a whole section used to be, which
    is not visible in a diff of the pages, because they hold the directive
    rather than the prose.
    """
    with pytest.raises(SystemExit):
        site.section(site.ROOT / "README.md", "a heading nobody wrote")


def test_every_link_between_pages_resolves(built):
    for page in sorted(built.glob("*.html")):
        for href in re.findall(r'href="([^"]+)"', page.read_text()):
            if href.startswith(("http", "#", "mailto:")):
                continue
            assert (built / href).exists(), f"{page.name} links to missing {href}"


def test_a_schema_is_served_at_the_url_its_id_names(built):
    """What makes `$ref` resolve over the network as well as on disk.

    cbd.json says `{"$ref": "dialect.json"}` and the split dialect files say
    `{"$ref": "Ref.json"}`. A relative reference resolves against the
    enclosing `$id`, so those work over HTTP exactly when each file is served
    at the URL its own `$id` claims -- and not otherwise.
    """
    checked = 0
    for path in sorted(built.rglob("*.json")):
        try:
            schema = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if not isinstance(schema, dict) or "$id" not in schema:
            continue
        served = f"{site.BASE}/{path.relative_to(built)}"
        assert schema["$id"] == served, (
            f"{path.name} claims {schema['$id']} and is served at {served}"
        )
        checked += 1
    assert checked >= 18, f"only {checked} schemas checked; expected all of them"


def test_the_context_is_served_where_it_is_referenced(built):
    """The URL example/cbd.json names in its own @context."""
    example = json.loads((built / "example" / "cbd.json").read_text())
    named = example["@context"]
    assert named == f"{site.BASE}/context/bibframe.jsonld"
    assert (built / named.removeprefix(f"{site.BASE}/")).exists()


def test_a_project_page_publishes_no_cname(built):
    """A CNAME is how Pages is told to answer for a custom domain.

    Under a path -- blue-core-lod.github.io/bibframe-json -- there is no
    domain to claim, and a CNAME left over from a build that had one sends
    the whole site to a host that is not serving it. So the file is written
    or removed, never written or skipped.
    """
    host = site.BASE.split("://", 1)[1]
    if "/" in host:
        assert not (built / "CNAME").exists()
    else:
        assert (built / "CNAME").read_text().strip() == host


def test_a_stale_cname_is_cleared(tmp_path):
    """The build this caught: site/ is not emptied between runs."""
    (tmp_path / "CNAME").parent.mkdir(parents=True, exist_ok=True)
    site.render(base="https://bibframe-json.example", out=tmp_path)
    assert (tmp_path / "CNAME").exists()
    site.render(base="https://an-org.github.io/a-repo", out=tmp_path)
    assert not (tmp_path / "CNAME").exists()


def test_the_corpus_is_published_whole(built):
    """A case that is not served is a case no other implementation can run."""
    written = {
        path.relative_to(site.ROOT / "conformance")
        for path in (site.ROOT / "conformance").rglob("*.json")
    }
    served = {
        path.relative_to(built / "conformance")
        for path in (built / "conformance").rglob("*.json")
    }
    assert written == served
