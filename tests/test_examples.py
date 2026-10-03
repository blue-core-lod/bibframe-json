"""The `examples` in each definition, checked against that definition.

JSON Schema's `examples` keyword is annotation: no validator checks it, and a
wrong example is worse than none because it is the first thing a reader
copies. These are all trimmed from real records -- from example/, from the
sampled corpus, and one Hub run through example/produce.py from bluecore_api's
test fixture -- so they should pass, and this is what says so.
"""

import json

import jsonschema
import pytest

import bibframe_json

LINKED = bibframe_json.schema("linked")
DEFINITIONS = sorted(LINKED["$defs"])


def validator_for(name: str) -> jsonschema.protocols.Validator:
    """A validator whose root is one definition out of the bundle.

    Pointing at `#/$defs/<name>` rather than the root, so an example is
    checked as the thing it is an example of and not as a whole record.
    """
    return jsonschema.Draft202012Validator(
        {
            "$schema": LINKED["$schema"],
            "$id": LINKED["$id"],
            "$defs": LINKED["$defs"],
            "$ref": f"#/$defs/{name}",
        }
    )


def test_most_definitions_carry_an_example():
    """So the parametrized test below cannot pass by finding nothing.

    Item has none: there is no Item in example/, in the sampled corpus, or in
    bluecore_api's fixtures, and inventing one would make it the only example
    here that is not a real record.
    """
    with_examples = [
        name for name in DEFINITIONS if LINKED["$defs"][name].get("examples")
    ]
    assert len(with_examples) >= 13
    without = set(DEFINITIONS) - set(with_examples)
    assert without == {"Item"}, without


@pytest.mark.parametrize(
    ("name", "index"),
    [
        (name, i)
        for name in DEFINITIONS
        for i, _ in enumerate(LINKED["$defs"][name].get("examples", []))
    ],
    ids=lambda value: str(value),
)
def test_an_example_validates_against_its_own_definition(name: str, index: int):
    example = LINKED["$defs"][name]["examples"][index]
    # str() on a ValidationError already names the failing path and the rule,
    # and asking for the fields individually only makes the type checker
    # unhappy: iter_errors is typed as yielding object.
    errors = sorted(validator_for(name).iter_errors(example), key=str)
    assert not errors, "\n\n".join(str(error) for error in errors)


def test_a_wrong_example_would_be_caught():
    """The test above is only worth having if it can fail."""
    errors = list(
        validator_for("Title").iter_errors({"@type": "Title", "mainTitle": "T"})
    )
    assert errors, "a scalar property should not validate as a Title"


def test_the_split_files_and_the_bundle_agree_on_examples():
    """bundle.py inlines the split files, so the examples have to survive it."""
    from pathlib import Path

    folder = (
        Path(__file__).resolve().parent.parent / "bibframe_json" / "schema" / "linked"
    )
    for path in folder.glob("*.json"):
        if path.stem == "main":
            continue
        written = json.loads(path.read_text()).get("examples")
        bundled = LINKED["$defs"].get(path.stem, {}).get("examples")
        assert written == bundled, f"{path.stem}: {written!r} != {bundled!r}"
