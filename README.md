# bibframe-json

[![Test](https://github.com/blue-core-lod/bibframe-json/actions/workflows/test.yml/badge.svg)](https://github.com/blue-core-lod/bibframe-json/actions/workflows/test.yml)

*bibframe-json* provides a predictable, opinionated JSON shape for
[BIBFRAME](https://bibframe.org) data, in the spirit of [Linked Open and
Usable Data](https://linked.art/loud/) (LOUD).

LOUD names the audience as developers, and holds that use cases rather than
ontological purity should drive what passes between systems. Two of its five
principles do most of the work here: *comprehensible by introspection*, so
the data makes sense by being looked at, and *few exceptions, instead many
consistent patterns*, so there is less to learn.

Here that means every property is an array, so you can loop without checking
whether this one happens to hold a single value. A blank node never carries
an identifier you have to reconcile. `title` means `bf:title` rather than a
URI you have to expand. You can read a record without an RDF library or any
knowledge of the RDF data model, and check one against the JSON Schemas
without reading any of this.

It ships a JSON-LD context that produces the shape, JSON Schemas that check
it, and a corpus of documents with expected verdicts so you can hold a reader
in any language to the same standard.

**Documentation: <https://bibframe-json.org/>**

It grew out of the [Blue Core](https://bluecore.info/) project, and the schema
is meant to be shared by anyone working with BIBFRAME JSON data.

The artifacts are published under **v0.1**. Every published version is
frozen, but several more are expected before v1, and each is a breaking
change from the one before. v1 is the point at which this becomes something
to build on. See [Versioning](https://bibframe-json.org/versioning/).

## Working on it

```sh
uv run pytest                              # the library and the schemas
uv run python generate/from_ontology.py    # context, ontology schema, vocabulary
uv run python generate/bundle.py           # linked.json, bundled from schema/linked/
cd docs && npm install && npm run dev      # the documentation site
```

The context, the ontology schema and `bibframe_json/vocabulary.json` are
generated from the BIBFRAME vocabulary vendored at `generate/bibframe.rdf`.
`bibframe_json/schema/linked/` is written by hand, one file per definition,
and `schema/linked.json` is those files bundled into one. CI regenerates and
diffs, so an edit to a generator that was not followed by a rebuild fails.

`generate/rebase.py` moves every `$id` and published URL to a different host in
one command. Hosting and identity travel together: a relative `$ref` resolves
against the `$id` of the file it appears in, not against wherever you fetched
it.

If you have a record this shape handles badly, the most useful thing you can
send is a case in `conformance/`, which takes no Python at all. See
[`conformance/README.md`](conformance/README.md).

[Blue Core](https://bluecore.info/) drives the work, and the wider aim is to
make BIBFRAME more shareable as JSON, in any language.
