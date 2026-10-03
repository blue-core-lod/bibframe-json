"""Versioning, and the promise that reading a document needs no network.

A published URL is a promise twice over. A `$ref` resolves against the `$id`
of the file it appears in, so a schema served anywhere but the path its `$id`
names has references that resolve to nothing -- that is `test_artifacts.py`.
And a document that names its context is entitled to find it, which is what
the version segment is for.

What is here is the other half: every version this package claims to ship is
actually on disk, and the URL a document names resolves inside the package,
so nothing has to go to the network to read one.
"""

import json
import pathlib

import pytest

import bibframe_json
from bibframe_json.validate import BASE, CURRENT, VERSIONS

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_the_versions_declared_are_the_versions_on_disk():
    """VERSIONS is a claim about what a consumer can ask for.

    Compared against the directories rather than asserted non-empty, which
    would prove nothing: this catches a version declared and never created,
    and a directory added without being declared, which is the way a version
    would come to be served and not shipped.
    """
    on_disk = {
        path.name
        for path in (ROOT / "bibframe_json").iterdir()
        if path.is_dir() and (path / "context").is_dir()
    }
    assert on_disk == set(VERSIONS)
    for version in VERSIONS:
        assert bibframe_json.context(version), version
        for name in ("linked", "bounded", "ontology"):
            assert bibframe_json.schema(name, version)["$id"].startswith(
                f"{BASE}/{version}/"
            ), (name, version)


def test_current_is_the_last_version():
    """Oldest first, so the newest is the one written today."""
    assert CURRENT == VERSIONS[-1]


@pytest.mark.parametrize("version", VERSIONS)
def test_a_version_resolves_its_own_context_url(version: str):
    """The URL a document names, answered from the package.

    This is what lets a stored record keep its `@context` without a fetch, and
    so what lets a reader know which version framed it.
    """
    url = bibframe_json.context_url(version)
    assert url == f"{BASE}/{version}/context/bibframe.jsonld"
    assert bibframe_json.context_for(url) == bibframe_json.context(version)


def test_an_unknown_url_resolves_to_nothing():
    """So a caller can tell "not ours" from "ours but empty"."""
    assert bibframe_json.context_for("https://example.org/context.jsonld") is None
    assert bibframe_json.context_for(f"{BASE}/v999/context/bibframe.jsonld") is None


def test_an_unknown_version_is_refused():
    """Rather than reading a path that happens not to exist."""
    for call in (
        lambda: bibframe_json.context("v999"),
        lambda: bibframe_json.schema("linked", "v999"),
        lambda: bibframe_json.context_url("v999"),
    ):
        with pytest.raises(ValueError, match="no such version"):
            call()


def test_the_document_loader_answers_offline():
    """pyld's loader, without pyld's network.

    The fallback is replaced with one that raises, so a test that passes
    proves the shipped context came off disk rather than out of a cache or a
    live fetch that happened to succeed.
    """

    def refuse(url, options):
        raise AssertionError(f"went to the network for {url}")

    load = bibframe_json.document_loader(fallback=refuse)
    for version in VERSIONS:
        url = bibframe_json.context_url(version)
        assert load(url, {})["document"] == bibframe_json.context(version)

    with pytest.raises(AssertionError, match="went to the network"):
        load("https://example.org/other.jsonld", {})


def test_the_shipped_examples_name_a_context_that_resolves():
    """A document this repository ships must name a URL a reader can answer.

    Both examples carry `@context` because the schema requires it. If one
    named a version this package does not ship, every consumer following the
    documentation would fetch a 404 on their first attempt.
    """
    for name in ("bounded.json", "linked.json"):
        document = json.loads((ROOT / "example" / name).read_text())
        url = document["@context"]
        assert bibframe_json.context_for(url) is not None, f"{name} names {url}"
