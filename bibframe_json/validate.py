"""Validate a record against the shipped JSON Schemas.

`validate()` checks a record against the two JSON Schemas in
`bibframe_json/<version>/schema/`. That is where the guarantees live:

    linked     the shape of one resource: arrays, references, value
               objects, blank nodes.

    bounded    the same, plus the Work embedded where it is referenced.
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

LINKED = "linked"
BOUNDED = "bounded"
ONTOLOGY = "ontology"

# Every artifact version this package ships, oldest first, and the one it
# writes. A version is a path segment in the published URLs and moves only
# when the context or the schemas change in a way that invalidates documents
# written against the previous one.
#
# Every published version is frozen, including the 0.x ones. What makes 0.x
# unstable is not that a version changes underneath you -- none of them do --
# but that the next one may break you with little notice. That distinction is
# the whole point: a migration can only read what was written against v0.1
# and write v0.2 if those two names mean exactly one thing each.
#
# While the package is on 0.x the two numbers move together, so 0.2.0 ships
# v0.1 and v0.2 and the version in a URL tells you which release introduced
# it. From 1.0.0 they decouple: the artifact version goes major-only, and
# adding one is a minor package release because the old ones are still
# shipped.
VERSIONS = ("v0.1",)
CURRENT = VERSIONS[-1]

# Where the artifacts are published. The version sits above the trees so that
# a relative $ref never changes: the schemas stay siblings inside a version,
# and {"$ref": "linked.json"} resolves within it exactly as it did when there
# was no version at all.
BASE = "https://bibframe-json.org"


def context_url(version: str = CURRENT) -> str:
    """Where a version's context is published.

    A document that names its context rather than inlining it -- which is what
    a document leaving your system should do -- has to name this exact URL,
    because a relative $ref and a context reference both resolve against where
    the file actually is. Anything that writes one needs the same string, so
    there is one place that builds it.
    """
    _check(version)
    return f"{BASE}/{version}/context/bibframe.jsonld"


def _check(version: str) -> None:
    if version not in VERSIONS:
        raise ValueError(
            f"no such version: {version!r}; shipped: {', '.join(VERSIONS)}"
        )


# The current version's context URL, for callers that do not care about
# versions. Kept as a constant because it is what a producer writes into a
# document, and a constant is easier to grep for than a call.
CONTEXT_URL = context_url(CURRENT)


class Finding(NamedTuple):
    """One thing wrong with a record.

    `layer` is "linked", "bounded" or "ontology", and it is the part a caller most
    needs:
    a linked or bounded finding is a defect in the shape, an ontology
    finding is a
    disagreement with BIBFRAME that may well be the ontology's fault.
    """

    layer: str
    path: str
    message: str

    @property
    def is_error(self) -> bool:
        return self.layer in (LINKED, BOUNDED)

    def __str__(self) -> str:
        where = self.path or "the record"
        return f"[{self.layer}] {where}: {self.message}"


@cache
def schema(name: str, version: str = CURRENT) -> dict[str, Any]:
    """One of the shipped schemas, by name.

    Read through importlib.resources rather than a relative path, so it works
    from an installed package and not only from a checkout. The schemas live
    inside bibframe_json/ for the same reason.
    """
    if name not in (LINKED, BOUNDED, ONTOLOGY):
        raise ValueError(f"no such schema: {name!r}")
    _check(version)
    text = (files("bibframe_json") / version / "schema" / f"{name}.json").read_text()
    return json.loads(text)


@cache
def context(version: str = CURRENT) -> dict[str, Any]:
    """The JSON-LD context that produces this shape.

    Shipped so a consumer can frame their own records into it, or point a
    JSON-LD processor at the same terms this library assumes.
    """
    _check(version)
    text = (
        files("bibframe_json") / version / "context" / "bibframe.jsonld"
    ).read_text()
    return json.loads(text)


def context_for(url: str) -> dict[str, Any] | None:
    """The shipped context a published URL names, or None if it names none.

    So that nothing has to go to the network to read a document that names its
    context. rdflib fetches a remote @context while parsing and pyld fetches
    one while framing, which is slow enough that `bluecore_models` strips the
    context on write and puts a hardcoded one back on read -- losing, in the
    process, any record of which version framed the document.

    With this the URL can stay in the document and still cost nothing:

        url = document.pop("@context")
        graph.parse(data=document, format="json-ld", context=context_for(url))

    See document_loader() for the pyld half.
    """
    for version in VERSIONS:
        if url == context_url(version):
            return context(version)
    return None


def document_loader(fallback: Any = None) -> Any:
    """A pyld document loader that answers for the shipped contexts offline.

        from pyld import jsonld
        jsonld.set_document_loader(bibframe_json.document_loader())

    Anything this package does not ship falls through to pyld's own loader, so
    installing this does not stop a caller resolving someone else's context --
    it only stops the network being asked for one we already have on disk.
    """
    from pyld import jsonld

    if fallback is None:
        fallback = jsonld.get_document_loader()

    def load(url: str, options: dict | None = None) -> dict:
        shipped = context_for(url)
        if shipped is None:
            return fallback(url, options or {})
        return {
            "contentType": "application/ld+json",
            "contextUrl": None,
            "documentUrl": url,
            "document": shipped,
        }

    return load


@cache
def registry() -> Registry:
    """The shipped schemas, addressable by their own $id.

    Hand this to a validator to check against one of them yourself:

        jsonschema.Draft202012Validator(schema("bounded"), registry=registry())

    bounded.json says `{"$ref": "linked.json"}` rather than carrying a copy of
    every definition, so something has to resolve that. A relative reference
    resolves against the enclosing $id, which is how the split definition files
    refer to each other too, and this registry is what turns those URIs back
    into the files on disk. Nothing is fetched.
    """
    known: Registry = Registry()
    for name in (LINKED, BOUNDED, ONTOLOGY):
        known = Resource.from_contents(schema(name)) @ known
    return known


@cache
def _validator(name: str) -> jsonschema.protocols.Validator:
    return jsonschema.Draft202012Validator(schema(name), registry=registry())


def _causes(error: jsonschema.ValidationError, depth: int = 0) -> Iterator:
    """The errors that actually explain a failure.

    Both schemas use anyOf -- the linked schema over four resource types and over the
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

    The one structural difference between a stored record and a BOUNDED, so it is
    what tells them apart. A bare URI is a reference to a row elsewhere; an
    object is the Work itself, which is what makes a bounded description
    explain itself.
    """
    if not isinstance(record, dict):
        return False
    instance_of = record.get("instanceOf")
    values = instance_of if isinstance(instance_of, list) else [instance_of]
    return any(isinstance(value, dict) for value in values)


def validate(
    record: dict[str, Any],
    *,
    shape: bool = True,
    ontology: bool = True,
    kind: str | None = None,
) -> list[Finding]:
    """Check a record against the schemas, and say what is wrong.

        for finding in validate(record):
            print(finding)

    Either layer can be asked for alone. `shape=True, ontology=False` is the
    useful gate in a pipeline, since those are the guarantees a consumer depends
    on; ontology-only is the interesting report to run across a corpus.

    Which structural schema applies is worked out from the document -- a
    bounded description embeds its Work where a linked one names it -- and
    `kind=BOUNDED` says so outright where that guess cannot help, since a
    bounded description whose Work has gone missing is indistinguishable from
    a linked one.

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
    # a bounded description whose Work has gone missing looks exactly like a
    # linked one, so asking for BOUNDED is the only way to be told about it.
    structural = kind or (BOUNDED if _embeds_its_work(record) else LINKED)
    layers = [
        name for name, wanted in ((structural, shape), (ONTOLOGY, ontology)) if wanted
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
