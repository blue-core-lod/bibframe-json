"""The conformance corpus, run against this implementation.

The corpus is data, not Python: `conformance/accept` and `conformance/reject`
are JSON files any language can read, and this module is one consumer of them.
That is the point. A schema alone does not tell a second implementation whether
it agrees with the first; a corpus of documents with expected verdicts does.

It also replaces the guarantee that generation used to provide. While the
dialect schema was emitted from Pydantic models, a test could assert the two
agreed by construction. Those models now live in the application that reads
them, and the corpus asserts the same thing by example instead -- weaker in
principle, and holding for any implementation in any language rather than only
for the one the schema was generated from. bluecore_api runs the same corpus
against its models; see tests/schemas/ there.
"""

import json
import pathlib

import jsonschema
import pytest

from bibframe_json import DIALECT, schema, validate

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


@pytest.mark.parametrize("case", cases("reject"), ids=lambda p: p.stem)
def test_validate_reports_every_rejection(case):
    """The wrapper agrees with the raw schema, and says something about it.

    iter_errors is what a consumer in another language sees; validate() adds
    the message. Both have to fire, or the corpus is checking the schema and
    not the thing this package actually offers.
    """
    findings = validate(read(case)["document"], ontology=False)
    assert findings
    assert all(finding.is_error for finding in findings)
