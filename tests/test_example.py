"""The shipped examples, checked against the schemas they claim to satisfy.

example/README.md says cbd.json validates against schema/cbd.json, and nothing
checked that until this file existed. An example that does not conform is
worse than no example: it is the first thing a reader copies.

The card on the front page is generated from example/instance.json, so it is
checked the same way -- every fragment of description it shows has to be a
string in the record. A hero with a hand-typed title would look identical and
mean nothing.
"""

import json
import re
from pathlib import Path

import pytest

import bibframe_json
from generate import site

EXAMPLES = sorted((site.ROOT / "example").glob("*.json"))


def test_there_are_examples():
    """An empty glob would make every test below pass by doing nothing."""
    assert {p.name for p in EXAMPLES} == {"cbd.json", "instance.json"}


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_an_example_conforms(path: Path):
    record = json.loads(path.read_text())
    findings = bibframe_json.validate(record, ontology=False)
    assert findings == [], "\n".join(str(f) for f in findings)


def test_the_two_examples_are_the_two_kinds_of_document():
    """One of each, because the difference between them is the whole point.

    instance.json names the Work it instantiates; cbd.json embeds it. If both
    were the same kind, validate()'s dispatch would be exercised in one
    direction only.
    """
    stored = json.loads((site.ROOT / "example" / "instance.json").read_text())
    cbd = json.loads((site.ROOT / "example" / "cbd.json").read_text())
    assert not bibframe_json.validate(
        stored, ontology=False, kind=bibframe_json.DIALECT
    )
    assert not bibframe_json.validate(cbd, ontology=False, kind=bibframe_json.CBD)
    # and the stored record is not mistakeable for a CBD
    assert bibframe_json.validate(stored, ontology=False, kind=bibframe_json.CBD)


def test_the_card_says_only_what_the_record_says():
    """Every word of description on the card comes from the record.

    The card is the one piece of design on the site that asserts something
    about a real item, so it is the one that must not be able to drift. ISBD
    punctuation and the tracing labels are the page's own; anything else has
    to be a value in example/instance.json.
    """
    record = json.loads((site.ROOT / "example" / "instance.json").read_text())

    def strings(node) -> set:
        if isinstance(node, str):
            return {node}
        if isinstance(node, dict):
            return set().union(*(strings(v) for v in node.values())) or set()
        if isinstance(node, list):
            return set().union(*(strings(v) for v in node)) or set()
        return set()

    in_record = strings(record)
    description = re.search(r'<p class="description">(.*?)</p>', site.card(), re.DOTALL)
    assert description, "the card has no description"

    # drop the marked-up delimiters, which are ISBD's and not the record's
    text = re.sub(r'<span class="d">.*?</span>', "\x1f", description.group(1))
    # a line break separates areas as much as a delimiter does, so it has to
    # separate fragments too, or three areas arrive as one string
    text = text.replace("<br>", "\x1f")
    for fragment in (f.strip() for f in text.split("\x1f")):
        if not fragment:
            continue
        cleaned = fragment.removeprefix("ISBN ").removesuffix(".")
        cleaned = re.sub(r"\s*\((\w+)\)$", "", cleaned)
        assert any(cleaned in value for value in in_record), (
            f"the card shows {fragment!r}, which is not in example/instance.json"
        )
