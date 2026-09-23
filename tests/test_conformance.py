"""The conformance corpus, run against this implementation.

The corpus is data, not Python: `conformance/accept` and `conformance/reject`
are JSON files any language can read, and this module is one consumer of them.
That is the point. A schema alone does not tell a second implementation whether
it agrees with the first; a corpus of documents with expected verdicts does.

It also replaces the guarantee that generation used to provide. While the
dialect schema was emitted from the Pydantic models, a test could assert the
two agreed by construction. The corpus asserts it by example instead, which is
weaker in principle and stronger in practice: it holds for any implementation
in any language, not only for the one the schema was generated from.
"""

import json
import pathlib

import jsonschema
import pytest

from bibframe_json import DIALECT, load, schema, validate

CORPUS = pathlib.Path(__file__).parent.parent / "conformance"


def cases(verdict: str) -> list[pathlib.Path]:
    found = sorted((CORPUS / verdict).glob("*.json"))
    assert found, f"no {verdict} cases found -- is the corpus there?"
    return found


def read(path: pathlib.Path) -> dict:
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def dialect():
    return jsonschema.Draft202012Validator(schema(DIALECT))


def pointer(error: jsonschema.ValidationError) -> str:
    """Where the failure is, as a JSON Pointer -- the portable half of a finding.

    A message is this implementation's wording and no other's; a path is the
    same in every language, which is why the corpus records paths.
    """
    return "/" + "/".join(str(part) for part in error.path)


@pytest.mark.parametrize("case", cases("accept"), ids=lambda p: p.stem)
def test_the_schema_accepts_what_it_should(dialect, case):
    document = read(case)["document"]
    assert [pointer(e) for e in dialect.iter_errors(document)] == []


@pytest.mark.parametrize("case", cases("reject"), ids=lambda p: p.stem)
def test_the_schema_rejects_what_it_should(dialect, case):
    """And at the paths the corpus names.

    Asserting where, not only that: a schema can reject a document for the
    wrong reason and look correct from a pass/fail count.
    """
    expected = read(case)
    found = sorted(pointer(e) for e in dialect.iter_errors(expected["document"]))
    assert found == sorted(expected["errors"])


@pytest.mark.parametrize("case", cases("accept"), ids=lambda p: p.stem)
def test_the_models_parse_what_the_schema_accepts(case):
    """A published schema that accepts less than its own reader does is worse
    than no schema, because a consumer trusts it.

    The gap opened twice while this was being written, both times because a
    `mode="before"` validator is invisible to `model_json_schema()`. It is the
    same direction every time: the schema stricter than the models.
    """
    load(read(case)["document"])


@pytest.mark.parametrize("case", cases("reject"), ids=lambda p: p.stem)
def test_the_models_still_read_what_the_schema_refuses(case):
    """Parsing and judging are different, and the corpus has to show it.

    Every rejected document here is still readable -- these are defects in the
    shape, not in the JSON -- and load() is deliberately permissive about all
    of them. A consumer that wants to be told calls validate().
    """
    document = read(case)["document"]
    load(document)
    assert validate(document, ontology=False), "validate() reports what load() allows"


def test_every_case_is_described():
    """The description is what a reader of the corpus learns the rule from."""
    for verdict in ("accept", "reject"):
        for case in cases(verdict):
            assert read(case).get("description"), case.name
