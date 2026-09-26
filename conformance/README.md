# Conformance corpus

Documents with expected verdicts, for checking an implementation of this shape
against the one in this repository. It is JSON, not Python: the point is that a
second implementation, in any language, can prove it agrees.

```
dialect/accept/<name>.json    one resource, which must validate
dialect/reject/<name>.json    one resource, which must not, and where it fails
cbd/accept/<name>.json        a Concise Bounded Description, which must validate
cbd/reject/<name>.json        ... which must not
```

A directory per schema, because a document is either one resource or a
description holding several, and the structural rules differ. `dialect/` cases
are checked against `schema/dialect.json` and `cbd/` cases against
`schema/cbd.json`.

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

1. Every document under `<schema>/accept/` validates against that schema.
2. Every document under `<schema>/reject/` does not.
3. For each rejected document, the set of paths reported is exactly the set in
   `errors` — no more and no fewer.

`errors` is a set rather than a list. How many failures land on a single path
depends on how the schema happens to be written — an `allOf` of three
subschemas that each reject the root reports it three times — and that is not a
fact about the document, so it is not something to hold another implementation
to. Which paths fail is.

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

- every document under `dialect/accept/` **parses**
- every document under `dialect/reject/` **also parses**

The second is not a mistake. These are defects in the shape, not in the JSON:
a blank node keeping its `@id` is still perfectly readable. Parsing and judging
are separate jobs, and a reader that refuses a malformed record is harder to
use than one that reads it and lets you ask.

## Running it

Against this implementation:

```sh
uv run pytest tests/test_conformance.py
```

Against any other, with any validator: walk each schema's two directories,
validate every `document` against that schema, and compare the paths.

## What the corpus is used for

Three things, and the third is the reason it is JSON rather than test code.

**It checks this implementation.** `tests/test_conformance.py` runs every case
against `schema/dialect.json` and against the Python reader, on every commit.

**It is the specification, in practice.** The `description` in each file is the
shortest statement of that rule anywhere in the repository — shorter than the
schema, shorter than the prose. `ls reject/` is a fair answer to "what does
this dialect actually require?"

**It is how a second implementation proves it agrees.** A schema tells you what
one validator thinks; a corpus tells two validators whether they think the same
thing. Nothing here is Python, so a reader in Ruby, JavaScript, Java or XSLT
can be held to exactly the same standard.

## Please add cases

This is the most useful contribution anyone can make to this repository, and it
needs no Python.

**If you have a record this shape handles badly** — it is rejected and you
believe it should not be, or accepted and you believe it should not be — that
is a case. Add the document, say what you expected, and open a pull request.
Even without the fix, the case is the valuable half: it turns a disagreement
about BIBFRAME into something two implementations can be measured against.

**If you are implementing this shape in another language** and hit something
ambiguous, the ambiguity is a missing case. Add one.

**If you are adding or changing a rule here**, add a case with it. A rule the
corpus does not cover is a rule no other implementation has been asked to
honour, and nothing will notice when it silently stops holding.

### How

One file, named for the rule rather than for the record it came from —
`blank-node-with-an-id`, not `hub-62a26d82`. Trim the document to the smallest
thing that shows the point, and change any real URIs to `https://x/1` unless
the actual URI is what the case is about.

```sh
cp conformance/dialect/reject/blank-node-with-an-id.json \
   conformance/dialect/reject/my-case.json
$EDITOR conformance/dialect/reject/my-case.json
uv run pytest tests/test_conformance.py          # if you have Python to hand
```

If you do not, that is fine: open the pull request and CI will tell you whether
the paths in `errors` match. Getting them wrong is not a problem — being
unsure is not a reason to leave the case out.
