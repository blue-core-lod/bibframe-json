# bibframe-json

[![Test](https://github.com/edsu/bibframe-json/actions/workflows/test.yml/badge.svg)](https://github.com/edsu/bibframe-json/actions/workflows/test.yml)

*bibframe-json* provides a predictable, opinionated JSON shape for [BIBFRAME]
data. The goal is to make BIBFRAME data more accessible to people who want to
parse it as JSON without needing an RDF processing library, and knowledge of
the RDF data model. But perhaps it will also function as a gateway for people
who want to take a step beyond the JSON to learn more.

BIBFRAME is large and loosely constrained, and there are many ways to write it
as RDF and JSON-LD. bibframe-json describes one shape, documents what that
shape guarantees, and ships the context that produces it, the JSON Schemas that
check it, and a corpus of documents with expected verdicts so that a reader in
any language can be held to it. The shape is the framed JSON-LD Blue Core
stores per resource: a Work, Instance, Hub or Item.

bibframe-json follows the [LOUD](https://linked.art/loud/) principles, and the
`@container: @set` rule from
[Linked Art](https://linked.art/api/1.0/json-ld/) in particular: if a property
can ever have more than one value, it always has an array. That single decision
is what makes everything else here possible.

## What the shape guarantees

- every property is an array, even with one value
- references are plain URI strings, not `{"@id": ...}` wrappers
- no blank node carries an `@id`
- a value object has `@value` and at most one of `@type` or `@language`
- `@type` is a list of classes on a node, and a datatype string on a value
  object — tell them apart by whether `@value` is present

## The JSON

Here's what an abridged JSON Instance looks like:

```json
{
  "@id": "http://id.loc.gov/resources/instances/23867197",
  "@type": ["Instance"],
  "instanceOf": ["http://id.loc.gov/resources/works/23867197"],
  "title": [
    {
      "@type": ["Title"],
      "mainTitle": ["Minority voices from the academic superstructure"]
    }
  ],
  "identifiedBy": [
    { "@type": ["Lccn"], "rdf:value": ["  2024038899"] },
    {
      "@type": ["Isbn"],
      "qualifier": ["hardcover"],
      "rdf:value": ["9781668499092"]
    }
  ],
  "provisionActivity": [
    {
      "@type": ["ProvisionActivity", "Publication"],
      "bflc:simplePlace": ["Hershey, PA"],
      "bflc:simpleDate": ["[2025]"]
    }
  ]
}
```

Note `instanceOf` has a bare URI, because the context declares it `@type: @id`.
Six properties are written that way: `instanceOf`, `itemOf`, `hasItem`,
`electronicLocator`, `generationProcess`, `descriptionLevel`.

A literal keeps its language or its datatype when it has one:

```json
"title": [
  { 
    "@type": ["Title"],
    "mainTitle": ["Trudy Instituta Obshchcei Fiziki"]
  },
  {
    "@type": ["Title"],
    "mainTitle": [
      {
        "@value": "Труды Института Общц̳еи Физики",
        "@language": "ru-cyrl"
      }
    ]
  }
],
"date": [
  {
    "@value": "199X",
    "@type": "http://id.loc.gov/datatypes/edtf"
  }
]
```

Those two titles are one title in two scripts, and the language tag
is the only thing telling them apart. And `date` carries three datatypes in real
records — `xsd:date`, `xsd:dateTime` and EDTF — where EDTF encodes uncertainty,
so `199X` is not a date that can be parsed as one.

## From Python

```python
import json

import bibframe_json

record = json.load(open("instance.json"))

for finding in bibframe_json.validate(record, ontology=False):
    print(finding)
```

That is the whole API, plus `schema()` and `context()`. Reading a record into
objects is a separate job and not one this package does: it describes a shape
so that a reader in any language can be written against it, and shipping one
reader in one language would make that reader the specification. The Pydantic
models this started with now live in
[bluecore_api](https://github.com/blue-core-lod/bluecore_api), which is the
application they were shaped by, and they are held to `conformance/` like
anyone else's.

## Validating

A reader **parses**; `validate()` **judges**. They are not the same, and the
difference is worth keeping in mind: parsing a record into objects checks the
fields that reader declares and quietly accepts the rest, and of the 136
properties in real records only about a dozen are worth declaring. A record can
parse perfectly and still be malformed.

```python
for finding in bibframe_json.validate(record):
    print(finding)

# [dialect] subject/0: a blank node must not carry an @id
# [ontology] the record: mainTitle does not belong on ['Work'] according to its rdfs:domain
```

Each `Finding` has a `layer`, a `path` and a `message`, and `is_error` is true
for the dialect layer. Either layer can be asked for on its own —
`validate(record, ontology=False)` is the useful gate in a pipeline, since those
are the guarantees a consumer depends on.

The two schemas ship with the package and answer different questions. Both are
plain JSON Schema, usable from any language:

```python
from bibframe_json import context, schema

schema("dialect")     # one resource
schema("cbd")         # a document holding several of them
registry()            # the schemas, for resolving between them
schema("ontology")    # BIBFRAME's domains and ranges, as constraints
context()             # the JSON-LD context that produces the shape
```

There are two structural schemas because there are two kinds of document, and
they differ by one thing. A stored record names the Work it instantiates —
`"instanceOf": ["https://.../works/1"]` — because the Work is a row of its own.
A Concise Bounded Description embeds it, so the document explains the Instance
without fetching anything. `schema("cbd")` is that claim and little else; see
`example/` for a real one and for what the difference buys.

LC specified the RDF/XML serialization of a CBD and left the JSON-LD as an RDF
dump — `.cbd.jsonld` from id.loc.gov is a flat array of expanded nodes. This is
a proposal for the JSON-LD, and it takes the one liberty XML could not: the
document is rooted at the Instance rather than holding every resource as a
sibling.

`schema("cbd")` references `dialect.json` rather than inlining it, so the
definitions exist in one place. A validator therefore needs both files and
something to resolve between them — `registry()` is that, and about five lines
in any language:

```python
import jsonschema
from bibframe_json import CBD, registry, schema

jsonschema.Draft202012Validator(schema(CBD), registry=registry())
```

`validate()` works out which schema applies by looking at the document, and
takes `kind="cbd"` to say outright.

## Using the schemas without Python

They are draft 2020-12, self-contained, and reference nothing outside
themselves, so any validator will run them:

```sh
check-jsonschema --schemafile dialect.json record.json
```

The root dispatches on `@type` with `if`/`then`, so a failure is reported
against the resource type the record claims and at the path it happened, rather
than as "the document matched none of four types". Every definition carries a
one-line `description`, and so do the rules with something to explain — a
validator that surfaces annotations will show them.

What does not travel is the last mile of message quality. A reference may be a
bare URI or a node, and a literal may be a bare string or a value object, so
both are an `anyOf`; when one fails, a validator can only say the value matched
neither branch. Finding the branch that was *meant* takes a short walk into
`error.context`, which is what `validate()` does in `_causes()`. Around fifteen
lines in any language, and worth writing if you are validating at scale.

If you already know what you are holding, skip the dispatch and point at the
type directly — `dialect.json#/$defs/Work` — which localises errors a little
further still.

## Checking an implementation

`conformance/` holds documents with expected verdicts, as JSON rather than as
anyone's test framework:

```
conformance/dialect/accept/<name>.json    one resource, must validate
conformance/dialect/reject/<name>.json    must not, and the paths where it fails
conformance/cbd/accept/<name>.json        a CBD, must validate
conformance/cbd/reject/<name>.json        must not
```

Walk the two directories, validate each `document` against the dialect schema,
compare the paths. Messages are not part of the contract — they are each
implementation's own wording — but paths are, and the path is the part a
cataloguer needs.

A rule with no case there is a rule no other implementation has been asked to
honour, so a new constraint wants a case as well as a schema change. See
`conformance/README.md`.

## Measuring against real records

`conformance/` says what the shape requires. To find out what the data
actually does, there is a fetcher:

```sh
uv run python generate/sample.py --count 60    # into corpus/, gitignored
```

It pulls recent Works and Instances from the Activity Streams change feed and
reframes each one through `bluecore_models.frame_jsonld`, which is what the
ORM applies on write — so the sample is the shape the database holds rather
than whatever a row happens to contain today. That distinction is not
academic: sampled straight from the API, a third of stage was still in the
pre-coercion shape, with 41 of 51 properties appearing as a bare value in some
record. Reframed, the same 120 records went from 39 rejections to one.

The corpus is not checked in. It is whatever stage held on the day, and it
goes stale as soon as the catalogue moves; a finding worth keeping belongs in
`conformance/` as a case.

The dialect schema is structural: arrays, references, value objects, blank
nodes. It says nothing about which BIBFRAME types may appear where, so a record
can satisfy it and still put an `Agent` where a `Title` belongs.

The ontology schema is that second question, generated from the
`rdfs:domain` and `rdfs:range` statements in BIBFRAME's vocabulary. Those are
*inference rules* under OWL. So asserting that `bf:title` has domain `bf:Work`
does not make a non-Work invalid, it infers the subject is a Work. We read them
as closed-world constraints instead, the way SHACL does, and emits the result
as JSON Schema.

Its findings are warnings rather than errors. Four constraints are excluded
outright, listed in `OVERRIDES` with reasons, because every real use violates
them and the ontology is the likelier culprit:

| Property | Ontology says | Every real use |
| --- | --- | --- |
| `bf:relief` | domain `bf:Instance` | `bf:Cartographic`, a Work |
| `bf:mediumComponent` | domain `bf:Work` | `bf:Ensemble` |
| `bf:ensembleSize` | domain `bf:Work` | `bf:Ensemble` |
| `bf:mediumOfPerformance` | range `bf:MediumOfPerformance` | `mads:Medium` |

The flip also has most purchase over a full BIBFRAME graph rather than a stored
resource: 99.8% of assertions conform in a CBD from id.loc.gov, while in a stored
per-resource record only 39% of node values carry a `@type` a range can check —
Blue Core keeps a referenced resource's description in its own row.

## Documentation

`generate/site.py` builds a documentation site and deploys it from CI. It does
two things, and the second is the one that matters:

```sh
uv run python generate/site.py    # into site/, gitignored
```

The pages hold almost no prose of their own — each pulls a named section out of
this README, inlines a Markdown file, or reads a table out of the schemas, so
there is one copy of every sentence and the examples are the files the tests
run against.

And it copies the context, the schemas and the conformance corpus in at the
paths their own `$id`s name. That is what turns
`https://bibframe-json.org/schema/dialect/Work.json` from a string in a field
called `$id` into a file a validator can fetch, and what makes
`{"$ref": "Ref.json"}` resolve over the network the way it already resolves on
disk. `tests/test_site.py` fails if any `$id` and its served path disagree.

**That domain is not registered yet**, so the `$id`s currently identify without
locating — which JSON Schema permits, and which costs nothing until someone
wants to fetch one. Two ways to finish it: point `bibframe-json.org` at GitHub
Pages, or move everything to the project page with

```sh
uv run python generate/site.py --rebase https://edsu.github.io/bibframe-json
```

which rewrites every `$id`, fixture and page at once. The test is what keeps
that from being a sweep you can half-finish.

## What is generated, and what is not

```
bibframe_json/context/bibframe.jsonld  generated   251 terms: @container: @set, @type: @id
bibframe_json/schema/ontology.json     generated   150 range + 110 domain constraints
bibframe_json/schema/dialect/          written     one resource, one file per definition
bibframe_json/schema/dialect.json      generated   the same schema, bundled from those
bibframe_json/schema/cbd.json          written     a CBD, referencing dialect.json
example/cbd.json                       written     a real CBD, and what its shape is for
conformance/                           written     documents and verdicts, for any implementation
docs/                                  written     six pages, mostly directives into the above
site/                                  generated   the pages, and the artifacts at their own URLs
generate/bibframe.rdf                  vendored    BIBFRAME 3.0.1, issued 2025-12-03
```

The dialect comes in two forms from one build. `schema/dialect/` is one file
per definition, following [IIIF v4's
layout](https://github.com/IIIF/presentation-validator/tree/main/schema/v4):
`Title.json` is a page you can read, it is addressable on its own, and the
files reference each other relatively, so `{"$ref": "Ref.json"}` resolves
against wherever the directory is served from. Start at `main.json`.

`schema/dialect.json` is the same schema with the definitions inlined, for
anyone who would rather not resolve references across files. The two are
checked against each other over the whole conformance corpus, so either is
safe to depend on.

```
uv run python generate/from_ontology.py    # context + ontology schema
uv run python generate/bundle.py           # dialect.json, bundled from schema/dialect/
uv run python generate/site.py             # the documentation site
uv run pytest                              # 154 tests, no corpus or network
```

Enumerating 251 `@container` declarations is mechanical, so it is generated
from the ontology; deciding which dozen properties are worth naming in the
schema is editorial, so `schema/dialect/` is written by hand. `rdflib` is a dev
dependency — the ontology is read at build time and nothing at runtime parses
RDF. The only runtime dependency is `jsonschema`.

The dialect was generated from Pydantic models until those moved to the
application that reads them. That arrangement guaranteed the schema could never
accept less than the reader did, which is a real thing to lose — `conformance/`
is what replaces it, and it holds any implementation to the same standard
rather than only the one the schema came from.

It also means the rules every node carries — that unmodelled properties are
still arrays, that a keyword is not a property, that a blank node keeps no
`@id`, that `@type` may be a string — are no longer merged in by one function
at build time. Each definition carries them itself, and
`tests/test_split_schema.py` checks that each one does: a definition written
without them would validate less than its siblings and nothing else would
notice. Both times a rule has gone missing here it was exactly that shape of
mistake.

## Status

This is meant to be updated as BIBFRAME changes and as the shape is found
wanting. Please send issues and PRs — and if you have a record this shape
handles badly, the most useful thing you can send is a case in `conformance/`,
which needs no Python at all. The project is built primarily for use cases in
the [Blue Core] project, but the overarching goal is to make BIBFRAME more
shareable as JSON, in any language.

[BIBFRAME]: https://bibframe.org
[Blue Core]: https://bluecore.info/
