"""Validate a record against the shipped JSON Schemas.

`validate()` checks a record against the two JSON Schemas in
`bibframe_json/schema/`. That is where the guarantees live:

    dialect    the shape: arrays, references, value objects, blank nodes.
               Errors -- a document that breaks these cannot be read reliably.

    ontology   BIBFRAME's own domains and ranges, read as constraints.
               Warnings -- when the data and the ontology disagree the ontology
               is often the one that is behind, and four constraints are
               excluded outright for that reason.

Reading a record is a separate job, and not one this package does: it
describes the shape rather than providing a way of working with it. A reader
in any language is held to the same standard by `conformance/`.
"""

import json
from collections.abc import Iterator
from functools import cache
from importlib.resources import files
from typing import Any, NamedTuple

import jsonschema
from referencing import Registry, Resource

DIALECT = "dialect"
CBD = "cbd"
ONTOLOGY = "ontology"


class Finding(NamedTuple):
    """One thing wrong with a record.

    `layer` is "dialect", "cbd" or "ontology", and it is the part a caller most
    needs:
    a dialect finding is a defect in the shape, an ontology finding is a
    disagreement with BIBFRAME that may well be the ontology's fault.
    """

    layer: str
    path: str
    message: str

    @property
    def is_error(self) -> bool:
        return self.layer in (DIALECT, CBD)

    def __str__(self) -> str:
        where = self.path or "the record"
        return f"[{self.layer}] {where}: {self.message}"


@cache
def schema(name: str) -> dict[str, Any]:
    """One of the shipped schemas, by name.

    Read through importlib.resources rather than a relative path, so it works
    from an installed package and not only from a checkout. The schemas live
    inside bibframe_json/ for the same reason.
    """
    if name not in (DIALECT, CBD, ONTOLOGY):
        raise ValueError(f"no such schema: {name!r}")
    text = (files("bibframe_json") / "schema" / f"{name}.json").read_text()
    return json.loads(text)


@cache
def context() -> dict[str, Any]:
    """The JSON-LD context that produces this shape.

    Shipped so a consumer can frame their own records into it, or point a
    JSON-LD processor at the same terms this library assumes.
    """
    text = (files("bibframe_json") / "context" / "bibframe.jsonld").read_text()
    return json.loads(text)


@cache
def registry() -> Registry:
    """The shipped schemas, addressable by their own $id.

    Hand this to a validator to check against one of them yourself:

        jsonschema.Draft202012Validator(schema("cbd"), registry=registry())

    cbd.json says `{"$ref": "dialect.json"}` rather than carrying a copy of
    every definition, so something has to resolve that. A relative reference
    resolves against the enclosing $id, which is how the split dialect files
    refer to each other too, and this registry is what turns those URIs back
    into the files on disk. Nothing is fetched.
    """
    known: Registry = Registry()
    for name in (DIALECT, CBD, ONTOLOGY):
        known = Resource.from_contents(schema(name)) @ known
    return known


@cache
def _validator(name: str) -> jsonschema.protocols.Validator:
    return jsonschema.Draft202012Validator(schema(name), registry=registry())


def _causes(error: jsonschema.ValidationError, depth: int = 0) -> Iterator:
    """The errors that actually explain a failure.

    Both schemas use anyOf -- the dialect over four resource types and over the
    shapes a literal or a reference may take, the ontology over string-or-array
    @type. jsonschema reports the anyOf itself, whose message is the whole record
    printed back at you with "is not valid under any of the given schemas". The
    reason is further down, in error.context.

    This is the problem IIIF hit: their v3 schema's 38 oneOf are why their
    validator needs a 414-line error processor. Worth noting that switching from
    oneOf to anyOf does not avoid it -- it avoids wrongly rejecting a record that
    matches two branches, which is a different bug.

    The keywords are named rather than taking the deepest or the first, because
    which branch is "the" failure depends on how the schema happens to be
    ordered, and a named set gives the same answer either way.
    """
    if not error.context or depth > 6:
        yield error
        return
    explains = {"not", "required", "pattern", "type", "minItems", "const", "enum"}
    found = [
        cause
        for sub in error.context
        for cause in _causes(sub, depth + 1)
        if cause.validator in explains
    ]
    yield from (found or [error])


def _describe(error: jsonschema.ValidationError) -> str:
    """A message that says what is wrong rather than which keyword noticed."""
    if error.validator == "required":
        present = error.instance if isinstance(error.instance, dict) else {}
        missing = [key for key in error.validator_value if key not in present]
        return f"missing {', '.join(missing)}" if missing else error.message
    if error.validator == "not":
        wrong = error.validator_value
        if wrong.get("properties", {}).get("@id", {}).get("pattern") == "^_:":
            return "a blank node must not carry an @id"
        required = list(wrong.get("required", []))
        if set(required) == {"@type", "@language"}:
            return "a value object carries at most one of @type or @language"
        if len(required) == 1 and not wrong.get("properties"):
            # the ontology's domain constraint: "if the node is not of the right
            # type, this property must be absent"
            types = (
                error.instance.get("@type")
                if isinstance(error.instance, dict)
                else None
            )
            on = f" on {types}" if types else ""
            return f"{required[0]} does not belong{on} according to its rdfs:domain"
        return "not allowed here"
    if error.validator == "minItems":
        return "is empty"
    return error.message


def _embeds_its_work(record: object) -> bool:
    """Whether bf:instanceOf holds a Work rather than a URI naming one.

    The one structural difference between a stored record and a CBD, so it is
    what tells them apart. A bare URI is a reference to a row elsewhere; an
    object is the Work itself, which is what makes a CBD self-explaining.
    """
    if not isinstance(record, dict):
        return False
    instance_of = record.get("instanceOf")
    values = instance_of if isinstance(instance_of, list) else [instance_of]
    return any(isinstance(value, dict) for value in values)


def validate(
    record: dict[str, Any],
    *,
    dialect: bool = True,
    ontology: bool = True,
    kind: str | None = None,
) -> list[Finding]:
    """Check a record against the schemas, and say what is wrong.

        for finding in validate(record):
            print(finding)

    Either layer can be asked for alone. `dialect=True, ontology=False` is the
    useful gate in a pipeline, since those are the guarantees a consumer depends
    on; ontology-only is the interesting report to run across a corpus.

    Which structural schema applies is worked out from the document -- a CBD
    carries @graph and a resource does not -- and `kind=CBD` says so outright
    where that guess cannot help, since a CBD missing its @graph is
    indistinguishable from a resource.

    Findings are deduplicated by path and message, because an anyOf can surface
    the same cause through more than one branch.
    """
    # (layer, path, message, validator), so the filter below can work on the
    # keyword rather than on the shape of the message
    raw: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    explained: set[tuple[str, str]] = set()

    # A record whose bf:instanceOf embeds the Work rather than naming it is a
    # Concise Bounded Description, and the structural schema for one says so.
    # Decided by looking, because a caller asking "is this well formed" should
    # not have to say which kind it holds and the answer is in the document.
    #
    # `kind` overrides that, and is worth having where the guess cannot help:
    # a CBD whose Work has gone missing looks exactly like a stored record, so
    # asking for CBD is the only way to be told about it.
    structural = kind or (CBD if _embeds_its_work(record) else DIALECT)
    layers = [
        name for name, wanted in ((structural, dialect), (ONTOLOGY, ontology)) if wanted
    ]
    for layer in layers:
        for error in _validator(layer).iter_errors(record):
            for cause in _causes(error):
                path = "/".join(str(part) for part in cause.absolute_path)
                message = _describe(cause)
                key = (layer, path, message)
                if key in seen:
                    continue
                seen.add(key)
                raw.append((layer, path, message, cause.validator))
                if cause.validator != "type":
                    explained.add((layer, path))

    # A failing anyOf reports every branch, so a node rejected for carrying an
    # @id also reports "is not of type string" from the branch that wanted a
    # bare URI. Where a path has a real explanation, the type complaint is
    # noise.
    #
    # And a type complaint about a whole value is noise when something inside
    # that value failed too: the branch that got further in is the one the
    # record was meant to match. A reference carrying a malformed property
    # reports "that property is not an array" at the property, and the outer
    # "this is not a string" only says it was not the other kind of reference.
    # Both are type failures, so neither explains the other by the rule above.
    inside = {(layer, path) for layer, path, _, _ in raw}

    def something_failed_inside(layer: str, path: str) -> bool:
        return any(
            other == layer and where.startswith(f"{path}/") for other, where in inside
        )

    return [
        Finding(layer, path, message)
        for layer, path, message, validator in raw
        if validator != "type"
        or not ((layer, path) in explained or something_failed_inside(layer, path))
    ]
