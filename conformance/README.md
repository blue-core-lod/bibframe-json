# Conformance corpus

Documents with expected verdicts, for checking an implementation of this shape
against the one in this repository. It is JSON rather than Python so that a
second implementation, in any language, can prove it agrees.

```
dialect/accept/<name>.json    a linked description, which must validate
dialect/reject/<name>.json    a linked description, which must not, and where it fails
cbd/accept/<name>.json        a bounded description, which must validate
cbd/reject/<name>.json        ... which must not
```

A directory per schema, because a document is either a linked
description or a bounded one, and the structural rules differ. `dialect/` cases
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

`description` names the rule the case is about, and states it more briefly
than anything else in the repository. Only files under `reject/` carry
`errors`.

## What conformance means

1. Every document under `<schema>/accept/` validates against that schema.
2. Every document under `<schema>/reject/` does not.
3. For each rejected document, the paths reported match the set in `errors`,
   no more and no fewer.

`errors` is a set rather than a list. How many failures land on one path
depends on how someone wrote the schema: an `allOf` of three subschemas that
each reject the root reports it three times. That says nothing about the
document, so holding another implementation to it would be unfair. Which paths
fail does say something, and that is the part of the contract.

Paths are [JSON Pointer](https://datatracker.ietf.org/doc/html/rfc6901) into
the document.

**Messages sit outside the contract, by choice.** Each implementation words
them its own way, and pinning them would turn the corpus into a test of one
library instead of the shape. Paths are the portable half of a finding: any
validator can say where, and the where is what a cataloger needs.

Insist on point 3. A schema can reject a document for the wrong reason and
still look right from a count of passes and failures.

## A reading implementation

If you are writing a reader and not only a validator, two further properties
hold, and `tests/test_conformance.py` asserts both:

- every document under `dialect/accept/` **parses**
- every document under `dialect/reject/` **also parses**

The second one is intended. These documents carry defects in the shape, not in
the JSON, and a blank node keeping its `@id` reads fine. Parsing and judging
are separate jobs. A reader that refuses a malformed record is harder to use
than one that reads it and lets you ask.

## Running it

Against this implementation:

```sh
uv run pytest tests/test_conformance.py
```

Against any other, with any validator: walk each schema's two directories,
validate every `document` against that schema, and compare the paths.

## What the corpus is used for

Three things, and the last of them is why it is JSON rather than test code.

**It checks this implementation.** `tests/test_conformance.py` runs every case
against `schema/dialect.json` and against the Python reader, on every commit.

**It serves as the specification in practice.** The `description` in each file
states its rule more briefly than the schema or the prose does. Run
`ls reject/` for a fair answer to what this dialect requires.

**It is how a second implementation proves it agrees.** A schema tells you what
one validator thinks. A corpus tells two validators whether they think the same
thing. Nothing here is Python, so you can hold a reader in Ruby, JavaScript,
Java or XSLT to the same standard.

## Please add cases

This is the most useful contribution you can make to this repository, and it
takes no Python.

**If you have a record this shape handles badly**, whether it is rejected and
you think it should pass or accepted and you think it should fail, that is a
case. Add the document, say what you expected, and open a pull request. The
case is the valuable half even without the fix, because it turns a disagreement
about BIBFRAME into something you can measure two implementations against.

**If you are implementing this shape in another language** and hit something
ambiguous, the ambiguity is a missing case. Add one.

**If you are adding or changing a rule here**, add a case with it. A rule the
corpus does not cover is a rule nobody else has been asked to honour, and
nothing will notice when it stops holding.

### How

One file, named for the rule rather than for the record it came from:
`blank-node-with-an-id`, not `hub-62a26d82`. Trim the document to the smallest
thing that shows the point, and change any real URIs to `https://x/1` unless
the URI is what the case is about.

```sh
cp conformance/dialect/reject/blank-node-with-an-id.json \
   conformance/dialect/reject/my-case.json
$EDITOR conformance/dialect/reject/my-case.json
uv run pytest tests/test_conformance.py          # if you have Python to hand
```

If you do not have Python to hand, open the pull request and CI will tell you
whether the paths in `errors` match. Getting them wrong costs nothing, so do
not let uncertainty keep the case out.
