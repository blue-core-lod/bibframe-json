"""Turn BIBFRAME RDF into this JSON shape.

Four steps, of which framing is one and the other three are the things framing
will not do for you. Every one of them was found by producing records and
validating them, which is the short way to find the rest.

Depends only on pyld. Copy it, port it, or read it as a specification of the
pipeline -- `bluecore_models.utils.graph` is the same four steps in the shape
of one library's needs.
"""

import json
import sys

from pyld import jsonld

from bibframe_json import CONTEXT_URL, context

# Keywords that hold one value by definition, so the array rule does not reach
# them. @context is a vocabulary rather than data; @id is one identifier.
SINGULAR = ("@context", "@id", "@value", "@language", "@direction", "@index")


def as_arrays(node: object) -> object:
    """Every property an array, which the context cannot promise on its own.

    `@container: @set` covers the terms the context declares -- 251 of them --
    and nothing else, so a property it has never heard of compacts to a bare
    value. Undeclared properties are not rare: `bflc:catalogerId` and
    Sinopia's `hasResourceTemplate` are both real, and 57 of 59 records tripped
    on exactly this before the coercion ran.

    @type is the exception that proves the rule twice. On a node it is a list
    of classes, so it gets wrapped; on a value object it is one datatype IRI,
    so it must not be. Telling them apart is what @value is for.
    """
    if isinstance(node, list):
        return [as_arrays(item) for item in node]
    if not isinstance(node, dict):
        return node
    literal = "@value" in node
    out: dict[str, object] = {}
    for key, value in node.items():
        if key in SINGULAR:
            out[key] = value
        elif key == "@type":
            out[key] = value if literal or isinstance(value, list) else [value]
        else:
            listed = value if isinstance(value, list) else [value]
            out[key] = [as_arrays(item) for item in listed]
    return out


def without_blank_ids(node: object) -> object:
    """Drop the @id a processor invents for a node that has none.

    Framing labels every description node `_:b0`, `_:b1` and so on, because
    the same node could in principle be referenced from more than one place.
    Those labels address nothing outside the document they appear in, so
    keeping them makes two identical values distinguishable by accident --
    which is why the shape says a blank node carries no @id.
    """
    if isinstance(node, list):
        return [without_blank_ids(item) for item in node]
    if not isinstance(node, dict):
        return node
    return {
        key: without_blank_ids(value)
        for key, value in node.items()
        if not (key == "@id" and isinstance(value, str) and value.startswith("_:"))
    }


def produce(expanded: object, uri: str, *, embed: str = "@once") -> dict:
    """Expanded JSON-LD in, one document in this shape out.

    `embed="@once"` describes a resource the first time it is reached and
    references it afterwards, which is what keeps a Concise Bounded
    Description finite. `@omitDefault` stops framing filling every property
    the frame names with null.

    For a per-resource record, frame the resource on its own and its links
    come out as bare URIs. For a CBD, frame the Instance over a graph that
    also holds its Work, and the Work arrives embedded -- that difference is
    the whole of schema/cbd.json.
    """
    framed = jsonld.frame(
        expanded,
        {
            "@context": context()["@context"],
            "@id": uri,
            "@embed": embed,
            "@omitDefault": True,
        },
    )
    document = without_blank_ids(as_arrays(framed))
    assert isinstance(document, dict)
    # Name the context rather than carrying the copy framing returns: inlined,
    # it is around 12,000 bytes per record and most of what you would send.
    document["@context"] = CONTEXT_URL
    return document


if __name__ == "__main__":
    # expand against this context rather than whatever the document names, so
    # the pipeline runs without fetching anything
    with open(sys.argv[1]) as handle:
        source = json.load(handle)
    expanded = jsonld.expand({**source, "@context": context()["@context"]})
    print(json.dumps(produce(expanded, sys.argv[2]), indent=2))
