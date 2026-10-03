"""The conformance corpus, run against this implementation.

The corpus is data, not Python: every case under `conformance/` is a JSON file
any language can read, and this module is one consumer of them. That is the
point. A schema tells a second implementation what one validator thinks; a
corpus of documents with expected verdicts tells two validators whether they
think the same thing.

It also replaces the guarantee that generation used to provide. While the
linked schema was emitted from Pydantic models, a test could assert the two
agreed by construction. Those models now live in the application that reads
them, and the corpus asserts the same thing by example instead -- weaker in
principle, and holding for any implementation in any language rather than
only for the one the schema was generated from. bluecore_api runs the same
corpus against its models; see tests/schemas/ there.

A directory per schema, since a document is either one resource or a
description holding several and the structural rules differ.
"""

import json
import pathlib

import jsonschema
import pytest

from bibframe_json import BOUNDED, CONTEXT_URL, LINKED, registry, schema, validate

CORPUS = pathlib.Path(__file__).parent.parent / "conformance"
SCHEMAS = (LINKED, BOUNDED)


def cases(name: str, verdict: str) -> list[pathlib.Path]:
    found = sorted((CORPUS / name / verdict).glob("*.json"))
    assert found, f"no {name}/{verdict} cases -- is the corpus there?"
    return found


def every(verdict: str) -> list[tuple[str, pathlib.Path]]:
    return [(name, case) for name in SCHEMAS for case in cases(name, verdict)]


def label(value: object) -> str:
    return value.stem if isinstance(value, pathlib.Path) else str(value)


def read(path: pathlib.Path) -> dict:
    return json.loads(path.read_text())


def pointer(error: jsonschema.ValidationError) -> str:
    """Where the failure is, as a JSON Pointer -- the portable half of a finding.

    A message is this implementation's wording and no other's; a path is the
    same in every language, which is why the corpus records paths.
    """
    return "/" + "/".join(str(part) for part in error.path)


def validator(name: str) -> jsonschema.protocols.Validator:
    """With the registry: bounded.json references linked.json rather than
    carrying a copy of it, so something has to resolve that."""
    return jsonschema.Draft202012Validator(schema(name), registry=registry())


@pytest.mark.parametrize(("name", "case"), every("accept"), ids=label)
def test_each_schema_accepts_what_it_should(name, case):
    document = read(case)["document"]
    assert [pointer(e) for e in validator(name).iter_errors(document)] == []


@pytest.mark.parametrize(("name", "case"), every("reject"), ids=label)
def test_each_schema_rejects_what_it_should(name, case):
    """And at the paths the corpus names.

    Asserting where, not only that: a schema can reject a document for the
    wrong reason and look correct from a pass/fail count.

    The set of paths, not the list. How many failures land on one path depends
    on how the schema is written -- an allOf of three subschemas that each
    reject the root reports it three times -- and that is not a fact about the
    document, so it is not something to hold another implementation to.
    """
    expected = read(case)
    found = {pointer(e) for e in validator(name).iter_errors(expected["document"])}
    assert found == set(expected["errors"])


@pytest.mark.parametrize(("name", "case"), every("reject"), ids=label)
def test_validate_reports_every_rejection(name, case):
    """The wrapper agrees with the raw schema, and says something about it.

    iter_errors is what a consumer in another language sees; validate() adds
    the message, and picks the structural schema by looking for @graph. Both
    have to fire, or the corpus is checking the schema rather than the thing
    this package offers.
    """
    # `kind` explicitly: a bounded description that has lost its @graph looks
    # like a resource,
    # and guessing would check it against the wrong schema and find nothing
    findings = validate(read(case)["document"], ontology=False, kind=name)
    assert findings
    assert all(finding.is_error for finding in findings)


@pytest.mark.parametrize(("name", "case"), every("accept"), ids=label)
def test_validate_accepts_what_the_schema_accepts(name, case):
    assert validate(read(case)["document"], ontology=False, kind=name) == []


def test_a_linked_description_is_not_a_bounded_one():
    """The two differ by one thing, and it is the thing worth checking.

    A stored record names the Work it instantiates, because the Work is a row
    of its own. A bounded description embeds it. Both are the same resource otherwise, and
    both satisfy the linked schema -- a bounded description is a resource, it
    just
    carries more.
    """
    stored = {
        "@context": CONTEXT_URL,
        "@id": "https://x/instances/1",
        "@type": ["Instance"],
        "instanceOf": ["https://x/works/1"],
    }
    bounded = {
        "@context": CONTEXT_URL,
        "@id": "https://x/instances/1",
        "@type": ["Instance"],
        # the embedded Work carries no context of its own: it is a Work, not
        # a document, and only a document is required to name one
        "instanceOf": [{"@id": "https://x/works/1", "@type": ["Work"]}],
    }

    assert validate(stored, ontology=False) == []
    assert validate(bounded, ontology=False) == []
    assert validate(stored, ontology=False, kind=BOUNDED), "the Work is only named"
    assert validate(bounded, ontology=False, kind=BOUNDED) == []


def test_every_case_is_described():
    """The description is what a reader of the corpus learns the rule from."""
    for name in SCHEMAS:
        for verdict in ("accept", "reject"):
            for case in cases(name, verdict):
                assert read(case).get("description"), f"{name}/{verdict}/{case.name}"
