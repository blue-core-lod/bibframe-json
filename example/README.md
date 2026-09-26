# `cbd.json` — a Concise Bounded Description

A real record from `stage.bcld.info`, framed. It validates against
`../bibframe_json/schema/cbd.json`.

LC defined how a CBD is serialized as RDF/XML and left the JSON-LD as an RDF
dump: `.cbd.jsonld` from id.loc.gov is a flat array of expanded nodes with full
property URIs and no nesting, and Blue Core's was the same. This is a proposal
for what it could be instead. The RDF is identical either way — only the
serialization differs.

## The shape

**The document is the Instance.** Not an array of resources to search through:
the thing you asked for is the thing you get, and everything else is described
where it is referenced.

That is the one place this departs from cbd-01.md, which puts every principal
resource side by side under a single `rdf:RDF`. XML has no natural root, so
siblings are the only option there; JSON has one, so it can be used. Marva is
unaffected — it reads the RDF/XML.

**`instanceOf` embeds the Work.** In a stored record it is a bare URI, because
the Work is a row of its own. That difference is what `schema/cbd.json`
checks, and it is the whole structural claim: a CBD explains its Instance
without fetching anything.

**The Work's `hasInstance` points back by URI.** A JSON-LD processor breaks the
cycle that way, and it is what keeps the document finite.

**Every property is an array**, even holding one value, so a reader can loop
without checking.

**`@context` is named rather than inlined**, which keeps the document about the
record instead of about the vocabulary.

## Producing one

Frame expanded JSON-LD with the Instance as the root:

```python
from pyld import jsonld

jsonld.frame(expanded, {
    "@context": context,                 # bibframe_json.context()
    "@id": "https://.../instances/<uuid>",
    "@embed": "@once",                   # embed the first time, reference after
    "@omitDefault": True,                # or absent properties come back null
})
```

Then two things the frame cannot do, both of which took finding out:

**Coerce every property to an array.** `@container: @set` in the context covers
the 251 terms the context declares, and nothing else. A property it has never
heard of — `bflc:catalogerId`, or Sinopia's `hasResourceTemplate` — compacts to
a bare value and breaks the guarantee. 57 of 59 sampled records tripped on
exactly that. `bluecore_models.utils.graph._as_arrays` is the coercion, and it
has to run after framing.

**Put `@type` in an array.** `@type` is a keyword, so no `@container` reaches
it, and a node with a single type compacts to a string. The dialect tolerates
both; this normalises for consistency.

## Measurements

Against 59 CBDs from a running system, comparing this with the sibling
arrangement:

| | bytes | resources described |
| --- | --- | --- |
| siblings under `@graph` | 520,362 | all |
| rooted at the Instance | 461,403 | all |

Nesting depth 3 to 8, mostly 5. Nothing is lost either way, including the two
cases that looked likely to break it: a Work with related Works that have
their own Instances, which land under the relation that reaches them, and
cbd-01.md's secondary Instance, which arrives under the Work's `hasInstance`
fully described.

## A caveat

The URIs are `stage.bcld.info` and will rot. This is here to be read, not
depended on.
