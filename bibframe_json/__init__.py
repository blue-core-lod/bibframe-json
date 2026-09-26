"""A predictable, opinionated JSON shape for BIBFRAME.

The shape itself is the artifact, and none of it is Python: a JSON-LD context
that produces it, two JSON Schemas that check it, and a corpus of documents
with expected verdicts so an implementation in any language can prove it
agrees. What is here is the tooling that maintains those and one way of using
them.

    validate(record)    check a record against the shipped schemas
    schema(name)        "dialect" for one resource, "cbd" for a document
                        holding several, or "ontology"
    registry()          the shipped schemas, for resolving between them
    context()           the JSON-LD context that produces the shape

Reading a record into objects is a separate job and deliberately not one this
package does. See conformance/README.md.
"""

from bibframe_json.validate import (
    CBD,
    DIALECT,
    ONTOLOGY,
    Finding,
    context,
    registry,
    schema,
    validate,
)

__all__ = [
    "CBD",
    "DIALECT",
    "ONTOLOGY",
    "Finding",
    "context",
    "registry",
    "schema",
    "validate",
]
