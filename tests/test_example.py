"""The shipped examples, checked against the schemas they claim to satisfy.

example/README.md says bounded.json validates against schema/bounded.json, and nothing
checked that until this file existed. An example that does not conform is
worse than no example: it is the first thing a reader copies.

The card on the front page is generated from example/linked.json too, and
used to be checked here the same way: every fragment of description it showed
had to be a string in the record. That check went with the move to Astro,
because pytest cannot reach a component. The component indexes the fields it
needs directly, so a record missing one fails the build, but nothing now
catches a fragment it invented. Recovering that means a JavaScript test
runner.
"""

import json
from pathlib import Path

import pytest

import bibframe_json

ROOT = Path(__file__).resolve().parent.parent


EXAMPLES = sorted((ROOT / "example").glob("*.json"))


def test_there_are_examples():
    """An empty glob would make every test below pass by doing nothing."""
    assert {p.name for p in EXAMPLES} == {"bounded.json", "linked.json"}


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_an_example_conforms(path: Path):
    record = json.loads(path.read_text())
    findings = bibframe_json.validate(record, ontology=False)
    assert findings == [], "\n".join(str(f) for f in findings)


def test_the_two_examples_are_the_two_kinds_of_document():
    """One of each, because the difference between them is the whole point.

    linked.json names the Work it instantiates; bounded.json embeds it. If both
    were the same kind, validate()'s dispatch would be exercised in one
    direction only.
    """
    stored = json.loads((ROOT / "example" / "linked.json").read_text())
    bounded = json.loads((ROOT / "example" / "bounded.json").read_text())
    assert not bibframe_json.validate(stored, ontology=False, kind=bibframe_json.LINKED)
    assert not bibframe_json.validate(
        bounded, ontology=False, kind=bibframe_json.BOUNDED
    )
    # and the linked description is not mistakeable for a bounded one
    assert bibframe_json.validate(stored, ontology=False, kind=bibframe_json.BOUNDED)


def test_the_recipe_produces_what_it_claims():
    """example/produce.py is documentation, so it has to actually work.

    It is included verbatim on the site as the way to get from RDF into this
    shape. An example pipeline that does not produce a conforming document
    would be worse than no pipeline, since the reader has no way to tell.

    bounded.json comes back identical, which is the stronger claim: the shipped
    example is reproducible by the published recipe rather than by something
    only this repository has.
    """
    from pyld import jsonld

    from example.produce import produce

    terms = bibframe_json.context()["@context"]
    for name in ("linked", "bounded"):
        record = json.loads((ROOT / "example" / f"{name}.json").read_text())
        expanded = jsonld.expand({**record, "@context": terms})
        produced = produce(expanded, record["@id"])
        findings = bibframe_json.validate(produced, ontology=False)
        assert findings == [], f"{name}: " + "\n".join(str(f) for f in findings)

    bounded = json.loads((ROOT / "example" / "bounded.json").read_text())
    again = produce(jsonld.expand({**bounded, "@context": terms}), bounded["@id"])
    assert again == bounded, (
        "example/bounded.json is no longer what the recipe produces"
    )


def test_the_recipe_leaves_a_value_object_alone():
    """@type on a value object is a datatype, not a list of classes.

    The array rule has to skip it, and the only thing distinguishing the two
    cases is @value. Wrapping it would break every dated record, so it is
    worth a case of its own rather than relying on the round trip above
    happening to contain one.
    """
    from example.produce import as_arrays

    literal = {"@value": "199X", "@type": "http://id.loc.gov/datatypes/edtf"}
    assert as_arrays(literal) == literal

    node = {"@type": "Instance", "title": "T"}
    assert as_arrays(node) == {"@type": ["Instance"], "title": ["T"]}
