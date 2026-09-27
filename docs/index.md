# One JSON shape for BIBFRAME

<!-- card -->

<!-- readme -->

## What the shape guarantees

<!-- readme: What the shape guarantees -->

Those five rules are the whole contract. Everything else on this site follows
from them or checks them.

## Where to start

| If you want to | Read |
| --- | --- |
| see what a record looks like | [The shape](shape.md) |
| read one document that explains a whole Instance | [A CBD](cbd.md) |
| write records in this shape | [Producing it](producing.md) |
| check records, in any language | [Validating](validating.md) |
| write a reader and prove it agrees | [Checking an implementation](conformance.md) |

How the schemas and the context are built, and what is measured against real
records, is in
[README.md](https://github.com/blue-core-lod/bibframe-json#readme), which is for people
working on the repository rather than with the data.

## The files

Everything here is plain JSON, served from this site, and free of any
dependency on the Python that maintains it:

| | |
| --- | --- |
| [`{{base}}/context/bibframe.jsonld`](context/bibframe.jsonld) | the JSON-LD context that produces the shape, 251 terms |
| [`{{base}}/schema/dialect.json`](schema/dialect.json) | one resource: a Work, Instance, Hub or Item |
| [`{{base}}/schema/dialect/`](schema/dialect/main.json) | the same schema, one file per definition |
| [`{{base}}/schema/cbd.json`](schema/cbd.json) | a Concise Bounded Description |
| [`{{base}}/schema/ontology.json`](schema/ontology.json) | BIBFRAME's own domains and ranges, as constraints |
| [`{{base}}/example/cbd.json`](example/cbd.json) | a real CBD |
| [`{{base}}/conformance/`](conformance.md) | documents with expected verdicts |

The schemas reference each other relatively, `{"$ref": "Ref.json"}` and
`{"$ref": "dialect.json"}`, so they resolve against wherever you serve them
from, this site or a copy on your disk.
