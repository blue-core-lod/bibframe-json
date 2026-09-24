"""The split schema and the bundle, held to each other.

`schema/dialect/` is one file per definition, following IIIF v4's layout, and
`schema/dialect.json` is the same schema with the definitions inlined. Both are
written from one build, so they cannot drift by accident -- but "cannot drift
by accident" is a claim about a generator, and the thing a consumer depends on
is that the two accept and reject the same documents. That is what this checks,
over the corpus, so the claim is tested rather than asserted.

The split files are also the only part of this package that is exercised
through a real `$ref` resolver, since `validate()` reads the bundle. Without
this, a broken relative reference would ship unnoticed.
"""

import json
import pathlib

import jsonschema
import pytest
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from bibframe_json import DIALECT, schema

SPLIT = pathlib.Path(__file__).parent.parent / "bibframe_json" / "schema" / "dialect"
CORPUS = pathlib.Path(__file__).parent.parent / "conformance"


def documents() -> list[tuple[str, dict, bool]]:
    cases = []
    for verdict, valid in (("accept", True), ("reject", False)):
        for path in sorted((CORPUS / verdict).glob("*.json")):
            cases.append((path.stem, json.loads(path.read_text())["document"], valid))
    return cases


@pytest.fixture(scope="module")
def from_split():
    """A validator over the split files, resolving $refs between them."""
    registry = Registry()
    for path in SPLIT.glob("*.json"):
        contents = json.loads(path.read_text())
        registry = Resource(contents=contents, specification=DRAFT202012) @ registry
    main = json.loads((SPLIT / "main.json").read_text())
    return jsonschema.Draft202012Validator(main, registry=registry)


@pytest.fixture(scope="module")
def from_bundle():
    return jsonschema.Draft202012Validator(schema(DIALECT))


@pytest.mark.parametrize(
    ("name", "document", "valid"),
    documents(),
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_the_split_files_agree_with_the_bundle(
    from_split, from_bundle, name, document, valid
):
    """Same verdict and same paths, for every case in the corpus."""

    def paths(validator):
        return sorted(
            "/" + "/".join(map(str, e.path)) for e in validator.iter_errors(document)
        )

    split, bundle = paths(from_split), paths(from_bundle)
    assert split == bundle, f"{name}: split says {split}, bundle says {bundle}"
    assert bool(split) is not valid


def test_every_definition_is_a_file_and_every_file_is_reachable():
    """The bundle's $defs and the directory are the same set, and main.json is
    the only extra -- a definition that is not a file cannot be referenced by
    one, and a file nothing refers to is dead."""
    bundled = set(schema(DIALECT)["$defs"])
    files = {path.stem for path in SPLIT.glob("*.json")}
    assert files == bundled | {"main"}


def test_the_files_reference_each_other_relatively():
    """A relative $ref resolves against the enclosing $id, which is what lets
    the definitions be files without any of them naming where they live. An
    absolute reference, or a leftover `#/$defs/...`, would break that."""
    for path in sorted(SPLIT.glob("*.json")):
        contents = path.read_text()
        assert (
            f'"$id": "https://bibframe-json.org/schema/dialect/{path.name}"' in contents
        )
        for ref in json.loads(contents).get("$defs", {}):
            raise AssertionError(f"{path.name} still carries $defs: {ref}")
        assert "#/$defs/" not in contents, path.name
