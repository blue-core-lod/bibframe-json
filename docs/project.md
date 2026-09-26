# The project

## What is generated, and what is not

<!-- readme: What is generated, and what is not -->

## Measuring against real records

<!-- readme: Measuring against real records -->

## This site

The pages here hold almost no prose of their own. Each one pulls a named
section out of `README.md`, or inlines a Markdown file, or reads a table out of
the schemas — so there is one copy of every sentence, and the examples on the
site are the same files the tests run against.

`generate/site.py` builds it, and also copies the context, the schemas and the
conformance corpus in at the paths their own `$id`s name. That is the part that
is not decoration: it makes
`{{base}}/schema/dialect/Work.json` a file a validator can fetch.

## Status

<!-- readme: Status -->
