# Conformance corpus

Documents with expected verdicts, for checking an implementation of this shape
against the one in this repository. It is JSON, not Python: the point is that a
second implementation, in any language, can prove it agrees.

```
accept/<name>.json    a document that must validate
reject/<name>.json    a document that must not, and where it fails
```

Every case is one self-contained file. There is no manifest to keep in step
with the documents.

```json
{
  "description": "a parser-assigned _:b label addresses nothing outside its record",
  "document": { "@id": "https://x/1", "@type": ["Work"], "subject": [{"@id": "_:b0"}] },
  "errors": ["/subject/0"]
}
```

`description` says which rule the case is about, and is the shortest
explanation of that rule anywhere in the repository. `errors` is present only
under `reject/`.

## What conformance means

1. Every document under `accept/` validates against `schema/dialect.json`.
2. Every document under `reject/` does not.
3. For each rejected document, the failures are reported at exactly the paths
   in `errors` — no more and no fewer.

Paths are [JSON Pointer](https://datatracker.ietf.org/doc/html/rfc6901) into
the document.

**Messages are deliberately not part of the contract.** They are each
implementation's own wording, and pinning them would make the corpus a test of
one library rather than of the shape. Paths are the portable half of a finding:
every validator can say where, and the where is what a cataloguer needs.

Point 3 is the one worth insisting on. A schema can reject a document for the
wrong reason and still look right from a count of passes and failures.

## A reading implementation

If you are also writing a reader rather than only a validator, two further
properties hold, and `tests/test_conformance.py` asserts both:

- every document under `accept/` **parses**
- every document under `reject/` **also parses**

The second is not a mistake. These are defects in the shape, not in the JSON:
a blank node keeping its `@id` is still perfectly readable. Parsing and judging
are separate jobs, and a reader that refuses a malformed record is harder to
use than one that reads it and lets you ask.

## Running it

Against this implementation:

```sh
uv run pytest tests/test_conformance.py
```

Against any other, with any validator: walk the two directories, validate each
`document` against `schema/dialect.json`, and compare the paths.

## Adding a case

One file, named for the rule rather than the record. A rule the corpus does not
cover is a rule no other implementation has been asked to honour, so new
constraints want a case here as well as a schema change.
