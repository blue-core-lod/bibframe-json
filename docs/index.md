# One JSON shape for BIBFRAME

<!-- card -->

<!-- readme -->

## What the shape guarantees

<!-- readme: What the shape guarantees -->

Those five rules are the whole contract, and everything else on this site is
either a consequence of them or a way of checking them.

## Where to start

| If you want to | Read |
| --- | --- |
| see what a record looks like | [The shape](shape.md) |
| read one document that explains a whole Instance | [A CBD](cbd.md) |
| check records, in any language | [Validating](validating.md) |
| write a reader and prove it agrees | [Checking an implementation](conformance.md) |
| change the shape, or the ontology mapping | [The project](project.md) |

## The files

Everything here is plain JSON, served from this site, and free of any
dependency on the Python that maintains it:

| | |
| --- | --- |
| [`{{base}}/context/bibframe.jsonld`](context/bibframe.jsonld) | the JSON-LD context that produces the shape — 251 terms |
| [`{{base}}/schema/dialect.json`](schema/dialect.json) | one resource: a Work, Instance, Hub or Item |
| [`{{base}}/schema/dialect/`](schema/dialect/main.json) | the same schema, one file per definition |
| [`{{base}}/schema/cbd.json`](schema/cbd.json) | a Concise Bounded Description |
| [`{{base}}/schema/ontology.json`](schema/ontology.json) | BIBFRAME's own domains and ranges, as constraints |
| [`{{base}}/example/cbd.json`](example/cbd.json) | a real CBD |
| [`{{base}}/conformance/`](conformance.md) | documents with expected verdicts |

The schemas reference each other relatively — `{"$ref": "Ref.json"}`,
`{"$ref": "dialect.json"}` — so they resolve against wherever they are served
from, whether that is this site or a copy on your disk.
