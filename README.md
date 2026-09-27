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
  "@context": "https://blue-core-lod.github.io/bibframe-json/context/bibframe.jsonld",
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
Seven properties are written that way: `instanceOf`, `hasInstance`, `itemOf`,
`hasItem`, `electronicLocator`, `generationProcess`, `descriptionLevel`.

`hasInstance` is on that list now and was excluded for a while. The argument
against it was a measurement — a bare string 262 times, a node with a URI 61
times, a node with **no** URI 39 times — taken from the wrong population. It
was drawn from CBDs, where every referenced Instance is described in the
document by definition, so there are no bare references to count. In a stored
record the reference is all there is. The 39 blank nodes are real and remain
unaddressed: an Instance with no URI cannot be written as a reference at all.

The list is cbd-01.md's, minus `rdf:type`. Which is also why the two contexts
in the Blue Core family now agree — across 120 stored records they produce
identical triples.

## The context

The schema never requires `@context`. A document may carry it as a URL, carry
it inlined, or leave it out, and all three conform — there are conformance
cases for each, because a producer should not have to guess.

But leaving it out costs something that is easy to miss. Without a context the
document is JSON that happens to match this shape; with one it is also JSON-LD,
and `instanceOf` means `bf:instanceOf` rather than the string "instanceOf".
Nothing about reading it as plain JSON changes either way — which is the point
— so the recommendation is to name it and let the two audiences coexist:

```json
"@context": "https://blue-core-lod.github.io/bibframe-json/context/bibframe.jsonld"
```

**Name it rather than inlining it.** A URL is one line; the context is 251
terms. Measured over 59 CBDs from a running system, inlining it is 11,947
bytes per record and **61% of the document** — most of what you would send is
a copy of a vocabulary, and it changes nothing a reader can use, since a JSON
reader ignores it and a JSON-LD processor fetches and caches it once.

A record stored in a database is the exception, and Blue Core treats it as one:
the context is the same for every row, so storing it per row would be 251 terms
of duplication. `bluecore_models` strips it on write and the API puts it back
on read. Which is the general rule — a document that leaves your system names
its context, a row in your own table need not.

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

## Producing it

This says how to write a description down. It does not say what to describe, or
which entity a thing is, or how to model a relationship: that is the work of
[LC's BIBFRAME primer][primer], which is a reference guide to the model — a
section each for Works, Instances, Items and Hubs, and for titles, subjects,
identifiers, notes, contributions, relationships, provision activity and
administrative metadata, with implementation considerations throughout. Eleven
of the fifteen definitions in `schema/dialect/` have a section there, and [the
table on the shape page](docs/shape.md#the-definitions) links each one to it. Read
that for what a title is; read this for how to write one down.

### Compared with the primer

Aligning with it is not a goal. This shape is deliberately the more
constrained of the two, and the differences below are the constraints doing
their job rather than a gap to be closed — a reader of this shape can loop
without checking, and that is bought by ruling things out.

The primer shows each of its examples as RDF/XML, JSON-LD, Turtle and a graph.
Its JSON-LD is already nested rather than a flat dump, which is more than
`.cbd.jsonld` from id.loc.gov manages, and it differs from this shape in four
ways worth knowing if you have been reading it:

- a single value is a bare object, where this shape always uses an array
- `@type` is a string, where this shape uses a list of classes on a node
- terms are prefixed — `bf:title` — where this context uses `@vocab`, so
  `title`
- a blank node carries `"@id": "_:b0"`

The last one the primer itself argues against, in
[Properties and classes overview][overview]: a nodeID "can be, and is often,
omitted as parsers will supply their own blank node identifier when absent".
That is the reason this shape forbids it — a label a parser invents is not an
identifier, and keeping it makes two identical values distinguishable by
accident.

Two other things it says are load-bearing here. That when referencing a
resource you may "provide the URI, a label, or both" is why a reference in
this shape is a bare URI or a node with `rdfs:label` and either conforms. And
that for any property "the object should not be a literal in one triple and a
resource in another" is why only seven properties are written as bare URIs:
`@type: @id` on a property that sometimes embeds a node would produce exactly
that mixture.

If you already have RDF, the pipeline is four steps, of which framing is one
and the other three are the things framing will not do for you.
[`example/produce.py`](example/produce.py) is all four, depending on nothing but
`pyld`:

```sh
uv run python example/produce.py record.jsonld https://example.org/i/1
```

Copy it, port it, or read it as a specification of the pipeline. Each step
carries the reason it exists, because each was found by producing records and
validating them — which is the short way to find whatever is left.

Two things worth knowing before you run it.

**It normalises, so its output may not match what your system stores.** Both
forms of a reference conform — a bare URI and a `{"@id": ...}` wrapper — so a
record can be valid and still not be in the shape the context describes. Across
120 Blue Core records, `descriptionLevel` is a wrapper in all 114 of its
appearances and `electronicLocator` in both of its, because the context those
records were framed against does not declare those properties as references.
The output of `produce.py` does. Neither is wrong; they are not the same
document.

**A JSON-LD processor cannot expand a document that names a context it cannot
fetch.** `pyld` raises `loading remote context failed` on a record whose
`@context` is a URL, unless you configure a document loader. Pass the terms
instead while you are working locally:

```python
terms = bibframe_json.context()["@context"]
expanded = jsonld.expand({**record, "@context": terms})
```

### Which document to produce

Frame a resource on its own and its links come out as bare URIs — a stored
record, checked by `dialect.json`. Frame an Instance over a graph that also
holds its Work and the Work arrives embedded — a Concise Bounded Description,
checked by `cbd.json`. That difference is the whole of the second schema.

### Then check it

Whatever you build it with, the schemas are how you find out whether it worked,
and `conformance/` is how you find out whether your reader agrees with anyone
else's.

[primer]: https://bibframe.org/docs/view/documentation-bf-primer/index.md
[overview]: https://bibframe.org/docs/view/documentation-bf-primer/rdf-in-bibframe/properties-and-classes-overview.md

## Validating

Three schemas, and which you want depends on what you are holding:

| Schema | Checks |
| --- | --- |
| [`schema/dialect.json`](bibframe_json/schema/dialect.json) | one resource — a Work, Instance, Hub or Item |
| [`schema/cbd.json`](bibframe_json/schema/cbd.json) | a Concise Bounded Description: an Instance with its Work embedded |
| [`schema/ontology.json`](bibframe_json/schema/ontology.json) | BIBFRAME's own domains and ranges. Warnings rather than errors — when the data and the ontology disagree, the ontology is often the one that is behind |

They are draft 2020-12 and reference nothing outside themselves, so any
validator will run them. One thing to know before you start: `cbd.json` says
`{"$ref": "dialect.json"}` rather than carrying a copy of every definition, so
a validator needs both files loaded and something to resolve between them.

The examples below read the two files from a local `schema/` directory, which
is what a pipeline usually wants. If you fetch them at runtime instead, fetch
both from the published location: a relative `$ref` resolves against the `$id`
of the file it appears in, not against wherever you happened to get the file.

### Python

```python
import bibframe_json

for finding in bibframe_json.validate(record):
    print(finding)

# [dialect] subject/0: a blank node must not carry an @id
# [ontology] the record: mainTitle does not belong on ['Work']
```

Each `Finding` has a `layer`, a `path` and a `message`, and `is_error` is true
for the dialect layer. `validate(record, ontology=False)` is the useful gate in
a pipeline, since those are the guarantees a consumer depends on. Which
structural schema applies is worked out from the document; `kind="cbd"` says so
outright.

To drive `jsonschema` yourself, `registry()` is the part that resolves
`cbd.json`'s reference to `dialect.json`:

```python
import jsonschema
from bibframe_json import CBD, registry, schema

validator = jsonschema.Draft202012Validator(
    schema(CBD), registry=registry()
)
```

### JavaScript

Ajv, with both schemas added so each is found by the `$id` it declares:

```js
import Ajv2020 from "ajv/dist/2020.js";
import { readFileSync } from "node:fs";

const base = "https://blue-core-lod.github.io/bibframe-json/schema/";
const read = (name) => JSON.parse(readFileSync(`schema/${name}`, "utf8"));

const ajv = new Ajv2020({ allErrors: true, strict: false });
ajv.addSchema([read("dialect.json"), read("cbd.json")]);

const check = ajv.getSchema(base + "dialect.json");
if (!check(record)) {
    for (const error of check.errors) {
        console.log(error.instancePath || "(root)", error.message);
    }
}
```

`getSchema` rather than `compile`, because a schema that has been added cannot
also be compiled — Ajv throws `schema with key or id ... already exists`.
`strict: false` because Ajv's strict mode objects to `$comment` beside a
`$ref`.

### Ruby

`json_schemer`, which reads the draft from `$schema` and takes a resolver for
the one reference that crosses files:

```ruby
require "json"
require "json_schemer"

resolver = ->(uri) do
  JSON.parse(File.read(File.join("schema", File.basename(uri.path))))
end
schema = JSON.parse(File.read("schema/dialect.json"))
check = JSONSchemer.schema(schema, ref_resolver: resolver)

check.validate(record).each do |error|
  puts [error["data_pointer"], error["error"]].join(" ")
end
```

`data_pointer` is the path, and it comes out cleanest of the three. A scalar
where an array belongs gets one line here —

```
/dimensions value at `/dimensions` is not an array
```

— where Ajv reports the same failure plus two more at the root, `must match
"then" schema` and `must match "else" schema`, which are the `@type` dispatch
reporting that the record matched neither branch. True, and not the thing that
is wrong.

### At the command line

```sh
check-jsonschema --schemafile dialect.json record.json
```

### What the schemas will not tell you

The root dispatches on `@type` with `if`/`then`, so a failure is reported
against the resource type the record claims and at the path it happened, rather
than as "the document matched none of four types". Every definition carries a
one-line `description`, and so do the rules with something to explain, so a
validator that surfaces annotations will show them.

What does not travel is the last mile of message quality. A reference may be a
bare URI or a node, and a literal may be a bare string or a value object, so
both are an `anyOf`; when one branch fails, a validator can only say the value
matched neither. Finding the branch that was *meant* takes a short walk into
`error.context` — around fifteen lines in any language, and what `validate()`
does in `_causes()`. If you already know what you are holding, pointing
straight at the type instead — `dialect.json#/$defs/Work` — localises errors
without any of that.

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
`https://blue-core-lod.github.io/bibframe-json/schema/dialect/Work.json` from a
string in a field called `$id` into a file a validator can fetch, and what
makes `{"$ref": "Ref.json"}` resolve over the network the way it already
resolves on disk. `tests/test_site.py` fails if any `$id` and its served path
disagree.

### Where this is served, and why it is one command to move

A relative `$ref` resolves against the base URI its `$id` establishes, not
against the URL it was fetched from. So the `$id`s cannot name one host while
the files are served from another — `{"$ref": "Ref.json"}` would resolve
against the host in the `$id` and find nothing. Hosting and identity move
together or not at all, which is why moving them is one command:

```sh
uv run python generate/site.py --rebase https://example.org/bibframe-json
```

It rewrites every `$id`, fixture, test and page at once, and the test above is
what keeps that from being a sweep you can half-finish.

The org project page is a stopgap. `bibframe-json.org` would be the better
identity for something meant to be used outside Blue Core — a name that
survives the project moving between accounts — and it is worth settling before
the first release, because an `$id` is an identity and changing it after
someone has pinned one is a breaking change. Before a release it costs a
`--rebase` and nothing else.

## What is generated, and what is not

```
bibframe_json/context/bibframe.jsonld  generated   251 terms: @container: @set, @type: @id
bibframe_json/schema/ontology.json     generated   150 range + 110 domain constraints
bibframe_json/schema/dialect/          written     one resource, one file per definition
bibframe_json/schema/dialect.json      generated   the same schema, bundled from those
bibframe_json/schema/cbd.json          written     a CBD, referencing dialect.json
example/instance.json                  written     a real stored record, and the card on the front page
example/cbd.json                       written     a real CBD, and what its shape is for
conformance/                           written     documents and verdicts, for any implementation
docs/                                  written     six pages, mostly directives into the above
docs/fonts/                            vendored    Literata and IBM Plex Mono, OFL
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
