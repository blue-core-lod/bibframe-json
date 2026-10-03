"""A predictable, opinionated JSON shape for BIBFRAME.

The shape itself is the artifact, and none of it is Python: a JSON-LD context
that produces it, two JSON Schemas that check it, and a corpus of documents
with expected verdicts so an implementation in any language can prove it
agrees. What is here is the tooling that maintains those and one way of using
them.

    validate(record)    check a record against the shipped schemas
    schema(name)        "linked" for one resource, "bounded" for a document
                        holding several, or "ontology"
    registry()          the shipped schemas, for resolving between them
    context()           the JSON-LD context that produces the shape
    CONTEXT_URL         where that context is published, for a document that
                        names it rather than carrying a copy

Every artifact is published under a version segment, and this package ships
each version it has published:

    VERSIONS, CURRENT   the versions on offer, and the one written today
    context_url(v)      where version v's context is published
    context_for(url)    the shipped context a URL names, so that reading a
                        document that names one costs no network
    document_loader()   the same thing as a pyld loader

Those last two matter more than they look. rdflib fetches a remote @context
while parsing and pyld fetches one while framing, which is slow enough that
callers have been known to strip the context on write and put a hardcoded one
back on read -- losing any record of which version framed the document. With
these the URL can stay in the document and still cost nothing to read.

Reading a record into objects is a separate job and deliberately not one this
package does. See conformance/README.md.
"""

from bibframe_json.validate import (
    BOUNDED,
    CONTEXT_URL,
    CURRENT,
    LINKED,
    ONTOLOGY,
    VERSIONS,
    Finding,
    context,
    context_for,
    context_url,
    document_loader,
    registry,
    schema,
    validate,
)

__all__ = [
    "BOUNDED",
    "CONTEXT_URL",
    "CURRENT",
    "LINKED",
    "ONTOLOGY",
    "VERSIONS",
    "Finding",
    "context",
    "context_for",
    "context_url",
    "document_loader",
    "registry",
    "schema",
    "validate",
]
