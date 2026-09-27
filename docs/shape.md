# The shape

<!-- readme: The JSON -->

## The context

<!-- readme: The context -->

## The definitions

A resource is checked by `dialect.json`, which comes in two forms from one
build: a single bundled file, and one file per definition. The split files are
the source. Each is a page you can read on its own, and each carries the rules
every node in the shape obeys, so no definition validates less than its
siblings.

<!-- definitions -->

Start at [`main.json`](schema/dialect/main.json). It dispatches on `@type` with
`if`/`then`, so a failure is reported against the resource type the record
claims rather than as "the document matched none of four types".

If you already know what you are holding, point at the type directly —
`dialect.json#/$defs/Work` — which localises errors a little further still.
