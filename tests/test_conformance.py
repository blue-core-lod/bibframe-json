"""The conformance corpus, run against this implementation.

The corpus is data, not Python: every case under `conformance/` is a JSON file
any language can read, and this module is one consumer of them. That is the
point. A schema tells a second implementation what one validator thinks; a
corpus of documents with expected verdicts tells two validators whether they
think the same thing.

It also replaces the guarantee that generation used to provide. While the
dialect schema was emitted from Pydantic models, a test could assert the two
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

from bibframe_json import CBD, DIALECT, registry, schema, validate

CORPUS = pathlib.Path(__file__).parent.parent / "conformance"
SCHEMAS = (DIALECT, CBD)


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
    """With the registry: cbd.json references dialect.json rather than
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
    """
    expected = read(case)
    found = sorted(
        pointer(e) for e in validator(name).iter_errors(expected["document"])
    )
    assert found == sorted(expected["errors"])


@pytest.mark.parametrize(("name", "case"), every("reject"), ids=label)
def test_validate_reports_every_rejection(name, case):
    """The wrapper agrees with the raw schema, and says something about it.

    iter_errors is what a consumer in another language sees; validate() adds
    the message, and picks the structural schema by looking for @graph. Both
    have to fire, or the corpus is checking the schema rather than the thing
    this package offers.
    """
    # `kind` explicitly: a CBD that has lost its @graph looks like a resource,
    # and guessing would check it against the wrong schema and find nothing
    findings = validate(read(case)["document"], ontology=False, kind=name)
    assert findings
    assert all(finding.is_error for finding in findings)


@pytest.mark.parametrize(("name", "case"), every("accept"), ids=label)
def test_validate_accepts_what_the_schema_accepts(name, case):
    assert validate(read(case)["document"], ontology=False, kind=name) == []


def test_a_cbd_is_checked_as_a_cbd_and_a_resource_as_a_resource():
    """validate() decides by looking, since the answer is in the document."""
    resource = {"@id": "https://x/1", "@type": ["Work"]}
    cbd = {"@graph": [resource]}
    assert validate(resource, ontology=False) == [], "guessed as a resource"
    assert validate(cbd, ontology=False) == [], "guessed as a CBD"
    # a resource is not a CBD: the envelope is the one thing the cbd schema
    # requires, and a resource does not carry it
    assert validate(resource, ontology=False, kind=CBD)


def test_the_dialect_does_not_reject_a_cbd():
    """Worth pinning, because it is a consequence rather than a decision.

    The dialect is open by design -- a property with no definition passes --
    and @graph is a keyword, so the array rule does not reach it either. A CBD
    therefore satisfies the per-resource schema as a Work carrying one unusual
    keyword. Rejecting it would mean requiring @type on every resource, which
    is a real tightening with data behind it and not something to slip in.

    So the guess in validate() is what separates them, and asking for the
    wrong `kind` is only caught in one direction.
    """
    cbd = {"@graph": [{"@id": "https://x/1", "@type": ["Work"]}]}
    assert validate(cbd, ontology=False, kind=DIALECT) == []


def test_every_case_is_described():
    """The description is what a reader of the corpus learns the rule from."""
    for name in SCHEMAS:
        for verdict in ("accept", "reject"):
            for case in cases(name, verdict):
                assert read(case).get("description"), f"{name}/{verdict}/{case.name}"
