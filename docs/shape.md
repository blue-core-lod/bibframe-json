# The shape

<!-- readme: The JSON -->

That record is on the front page as a catalogue card. The whole of it is
[`example/instance.json`](example/instance.json): eighteen properties against
the eight a card has room for, which is most of what BIBFRAME adds to ISBD.

## The context

<!-- readme: The context -->

## The definitions

`dialect.json` checks a resource, and comes in two forms from one build: a
single bundled file, and one file per definition. The split files are the
source. You can read each on its own, and each carries the rules every node in
the shape obeys, so no definition validates less than its siblings.

<!-- definitions -->

Start at [`main.json`](schema/dialect/main.json). It dispatches on `@type` with
`if`/`then`, so a failure is reported against the resource type the record
claims rather than as "the document matched none of four types".

If you already know what you are holding, point at the type directly,
`dialect.json#/$defs/Work`, and the errors localise a little further still.
