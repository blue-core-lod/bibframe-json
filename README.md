# bibframe-json

[![Test](https://github.com/edsu/bibframe-json/actions/workflows/test.yml/badge.svg)](https://github.com/edsu/bibframe-json/actions/workflows/test.yml)

*bibframe-json* follows the [LOUD](https://linked.art/loud/) principles by 
providing a predictable, opinionated JSON shape for [BIBFRAME]
data. You can parse it without an RDF library or any knowledge of the RDF data
model. The hope is that it will encourage you to go on and learn more about the
ontology when you have time.

BIBFRAME is large and loosely constrained, and you can write it as RDF and
JSON-LD in many ways. *bibframe-json* describes one of them, says what it
guarantees, and ships the context that produces it, the JSON Schemas that check
it, and a corpus of documents with expected verdicts, so you can hold a reader
in any language to the same standard. The shape is the framed JSON-LD Blue Core
stores per resource: a Work, Instance, Hub or Item as well as the 
Concise Bounded Description (CBD) for composing them together.


## What the shape guarantees

- every property is an array, even with one value
- references are plain URI strings, not `{"@id": ...}` wrappers
- no blank node carries an `@id`
- a value object has `@value` and at most one of `@type` or `@language`
- `@type` is a list of classes on a node, and a datatype string on a value
  object. Tell them apart by whether `@value` is present

## The JSON

An abridged JSON Instance:

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

## The context

The schema requires `@context`. Carry it as a URL or carry it inlined. The URI
is provisional at the moment as this proposal is worked out:

```json
"@context": "https://blue-core-lod.github.io/bibframe-json/context/bibframe.jsonld"
```

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

Those two titles are one title in two scripts, and the language tag is all
that tells them apart. `date` carries three datatypes in real records:
`xsd:date`, `xsd:dateTime`, and EDTF. EDTF encodes uncertainty, so nothing
parses `199X` as a date.

## Producing it

*bibframe-json* says how to write a description down as JSON. For what to describe, which entity
a thing is, and how to model a relationship, read [LC's BIBFRAME
primer][primer]. It covers Works, Instances, Items and Hubs, and titles,
subjects, identifiers, notes, contributions, relationships, provision activity
and administrative metadata. Eleven of the fifteen definitions in
`schema/dialect/` have a section there, and [the table on the shape
page](docs/shape.md#the-definitions) links each one to it.

If you already have RDF, the pipeline is four steps, of which framing is one
and the other three are the things framing will not do for you.
[`example/produce.py`](example/produce.py) is all four, depending on nothing but
`pyld`:

```sh
uv run python example/produce.py record.jsonld https://example.org/i/1
```

Copy it, port it, or read it as a specification of the pipeline. Each step
carries the reason it exists, because we found each one by producing records
and validating them. Do the same and you will find whatever is left.

Two things to know before you run it.

**It normalises, so its output may not match what your system stores.** Both
forms of a reference conform, a bare URI and a `{"@id": ...}` wrapper, so a
record can be valid and still not sit in the shape the context describes.
Across 120 Blue Core records, `descriptionLevel` is a wrapper in all 114 of its
appearances and `electronicLocator` in both of its, because the context those
records were framed against does not declare those properties as references.
The context here does. Neither is wrong, and they are not the same document.

**A JSON-LD processor cannot expand a document that names a context it cannot
fetch.** `pyld` raises `loading remote context failed` on a record whose
`@context` is a URL, unless you configure a document loader. Pass the terms
instead while you are working locally:

```python
terms = bibframe_json.context()["@context"]
expanded = jsonld.expand({**record, "@context": terms})
```

### Which document to produce

Frame a resource on its own and its links come out as bare URIs. That is a
stored record, checked by `dialect.json`. Frame an Instance over a graph that
also holds its Work, and the Work arrives embedded: a Concise Bounded
Description, checked by `cbd.json`. That one difference is the whole of the
second schema.

### Then check it

Whatever you build it with, the schemas are how you find out whether it worked,
and `conformance/` is how you find out whether your reader agrees with anyone
else's.

[primer]: https://bibframe.org/docs/view/documentation-bf-primer/index.md

## Validating

There are three schemas, and which you want depends on what you are holding:

| Schema | Checks |
| --- | --- |
| [`schema/dialect.json`](bibframe_json/schema/dialect.json) | one resource: a Work, Instance, Hub or Item |
| [`schema/cbd.json`](bibframe_json/schema/cbd.json) | a Concise Bounded Description: an Instance with its Work embedded |

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
also be compiled. Ajv throws `schema with key or id ... already exists`.
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
where an array belongs gets one line:

```
/dimensions value at `/dimensions` is not an array
```

Ajv reports that same failure plus two more at the root, `must match "then"
schema` and `must match "else" schema`. Those are the `@type` dispatch saying
the record matched neither branch. Both true, neither the thing that is wrong.

### At the command line

```sh
check-jsonschema --schemafile dialect.json record.json
```

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
compare the paths. Messages fall outside the contract, since each
implementation words them its own way. Paths are inside it, and the path is the
part a cataloguer needs.

A rule with no case there is a rule nobody else has been asked to honour, so a
new constraint wants a case as well as a schema change. See
`conformance/README.md`.

## Measuring against real records

`conformance/` says what the shape requires. To find out what the data does,
use the fetcher to get Blue Core data:

```sh
uv run python generate/sample.py --count 60    # into corpus/, gitignored
```

It pulls recent Works and Instances from the Blue Core Activity Streams change
feed and reframes each one through `bluecore_models.frame_jsonld`, the same
function the ORM applies on write. You get the shape the database holds, not
whatever a row happens to contain today, and the difference is large: sampled
straight from the API, a third of the staging records were still in the
pre-coercion shape, with 41 of 51 properties appearing as a bare value
somewhere. Reframed, those 120 records went from 39 rejections to one.

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

Its findings are warnings rather than errors. We exclude four constraints
outright, listed in `OVERRIDES` with reasons, because every real use violates
them and the ontology is the likelier culprit:

| Property | Ontology says | Every real use |
| --- | --- | --- |
| `bf:relief` | domain `bf:Instance` | `bf:Cartographic`, a Work |
| `bf:mediumComponent` | domain `bf:Work` | `bf:Ensemble` |
| `bf:ensembleSize` | domain `bf:Work` | `bf:Ensemble` |
| `bf:mediumOfPerformance` | range `bf:MediumOfPerformance` | `mads:Medium` |

The flip has most purchase over a full BIBFRAME graph rather than a stored
resource. In a CBD from id.loc.gov, 99.8% of assertions conform; in a stored
per-resource record only 39% of node values carry a `@type` a range can check,
because Blue Core keeps a referenced resource's description in its own row.

## Documentation

`generate/site.py` builds a documentation site and deploys it from CI. It does
two things, and the second is the one that matters:

```sh
uv run python generate/site.py    # into site/, gitignored
```

The pages hold almost no prose of their own. Each pulls a named section out of
this README, inlines a Markdown file, or reads a table out of the schemas, so
there is one copy of every sentence, and the examples on the site are the files
the tests run against.

And it copies the context, the schemas and the conformance corpus in at the
paths their own `$id`s name. That is what turns
`https://blue-core-lod.github.io/bibframe-json/schema/dialect/Work.json` from a
string in a field called `$id` into a file a validator can fetch, and what
makes `{"$ref": "Ref.json"}` resolve over the network the way it already
resolves on disk. `tests/test_site.py` fails if any `$id` and its served path
disagree.

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

Enumerating 251 `@container` declarations is mechanical, so we generate it from
the ontology. Deciding which dozen properties are worth naming in the schema is
editorial, so we write `schema/dialect/` by hand. `rdflib` is a dev
dependency: the generators read the ontology at build time, and nothing parses
RDF at runtime. The only runtime dependency is `jsonschema`.

The dialect was generated from Pydantic models until those moved to the
application that reads them. That arrangement guaranteed the schema could never
accept less than the reader did, and losing it cost something real.
`conformance/` replaces it, and holds any implementation to the same standard
instead of only the one the schema came from.

It also means no single function merges in the rules every node carries: that
unmodelled properties are still arrays, that a keyword is not a property, that
a blank node keeps no `@id`, that `@type` may be a string. Each definition
carries them itself, and `tests/test_split_schema.py` checks that each one
does. A definition written without them would validate less than its siblings,
and nothing else would notice. Both times a rule has gone missing here, that
was the shape of the mistake.

## Status

We update this as BIBFRAME changes and as the shape turns out to be wanting.
Please send issues and PRs. If you have a record this shape handles badly, the
most useful thing you can send is a case in `conformance/`, which takes no
Python at all. Blue Core drives the work, and the wider aim is to make BIBFRAME
more shareable as JSON, in any language.

[BIBFRAME]: https://bibframe.org
[Blue Core]: https://bluecore.info/
