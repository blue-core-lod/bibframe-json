"""Fetch a sample of real records into corpus/.

    uv run python generate/sample.py [--count 50] [--host https://stage.bcld.info]

Walks back from the newest page of the Activity Streams change feed and pulls
that many Works and Instances, then reframes each one.

The reframing is not cosmetic. What the API serves is whatever is in the
database, and a third of the records sampled from stage predate the coercion
that makes every property a list -- 41 of 51 distinct properties turned up as
a bare value in at least one record, `title` in 36 of 120. Those rows are
waiting on a reframe DAG that has not run. A corpus of them would measure the
backlog rather than the shape, and every question worth asking here is about
the shape.

So each record goes through bluecore_models.frame_jsonld, which is what the
ORM applies on write -- the same function, so the sample is what the database
will hold once the DAG has run, rather than this script's idea of it.

This is not `conformance/`, and the two should not be confused. Conformance
cases are written by hand, one per rule, and say what the shape requires.
These are whatever the catalogue actually holds, and are here to answer
questions about it: how often a property appears, what shapes it takes in
practice, whether a rule we are considering would reject real data. A claim
about real records wants measuring against these; a claim about the shape
wants a case over there.

Records are written under the uuid they are served at, so re-running updates
in place rather than accumulating duplicates.
"""

import argparse
import json
import pathlib
import time
import urllib.request

from bluecore_models.utils.graph import CONTEXT, _as_arrays, frame_jsonld
from pyld import jsonld

HERE = pathlib.Path(__file__).resolve().parent
CORPUS = HERE.parent / "corpus"
PAUSE = 0.1  # a courtesy to a shared staging box, not a rate limit


def get(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def recent(host: str, kind: str, count: int) -> list[str]:
    """The most recently changed records of one kind, newest page first."""
    feed = get(f"{host}/api/change_documents/{kind}/feed")
    page = feed["last"]["id"]
    seen: dict[str, None] = {}
    while page and len(seen) < count:
        body = get(page)
        for item in reversed(body.get("orderedItems", [])):
            seen.setdefault(item["object"]["id"], None)
            if len(seen) >= count:
                break
        # `prev` is a bare URL here, and an object elsewhere in the spec
        previous = body.get("prev")
        page = previous.get("id") if isinstance(previous, dict) else previous
        time.sleep(PAUSE)
    return list(seen)


def reframe(record: dict) -> dict:
    """The record in the shape the database will hold, via the ORM's own path.

    Mirrors bluecore_models' set_jsonld: the stored form has no @context, so
    framing cannot resolve the prefixes without putting one back first, and
    the result has it stripped again. Framing is idempotent, so a record that
    is already in shape passes through unchanged.
    """
    uri = record["@id"]
    framed = frame_jsonld(uri, {**record, "@context": CONTEXT})
    framed.pop("@context", None)
    return framed


def fetch(kind: str, uris: list[str]) -> int:
    into = CORPUS / kind
    into.mkdir(parents=True, exist_ok=True)
    written = 0
    for uri in uris:
        try:
            record = get(uri)
        except (OSError, ValueError) as error:  # gone between feed and fetch
            print(f"  skipped {uri}: {error}")
            continue
        (into / f"{uri.rstrip('/').rsplit('/', 1)[-1]}.json").write_text(
            json.dumps(reframe(record), indent=2, ensure_ascii=False) + "\n"
        )
        written += 1
        time.sleep(PAUSE)
    return written


# Work, Instance and Item stay at the top of a CBD and everything else nests
# inside them -- the arrangement cbd.py already makes for the XML serialization.
BF = "http://id.loc.gov/ontologies/bibframe/"
CBD_FRAME = {
    "@context": CONTEXT,
    "@type": [f"{BF}Work", f"{BF}Instance", f"{BF}Item"],
    "@embed": "@always",
}


def strip_blank_ids(node: object) -> object:
    """Drop the @id pyld assigns to a node that has none of its own.

    Framing several resources at once makes pyld label every description node
    _:b0, _:b1 and so on, because the same node could be referenced from more
    than one of them. The dialect says a blank node carries no @id, for the
    reason those labels exist: they are an artefact of this serialization and
    address nothing outside it, so keeping them makes two identical values
    distinguishable by accident.

    With them stripped every CBD member validates as a per-resource document,
    which is the whole finding: a CBD is an array of resources and not a
    different kind of thing. With them in place, none of them does.

    The same labels turn up in stored records that describe something in place
    -- a Work whose bf:relation embeds another Work -- so this belongs in
    bluecore-models beside _as_arrays rather than here.
    """
    if isinstance(node, dict):
        return {
            key: strip_blank_ids(value)
            for key, value in node.items()
            if not (key == "@id" and isinstance(value, str) and value.startswith("_:"))
        }
    if isinstance(node, list):
        return [strip_blank_ids(item) for item in node]
    return node


def cbds(uris: list[str]) -> int:
    """The CBD each Instance serves, framed into a shape worth reading.

    `.cbd.jsonld` is served expanded: a flat array of nodes with full property
    URIs, no @context and no nesting -- the opposite of the stored shape, and
    not something anyone would want to consume. Framing it against the same
    context gives `@graph` holding one entry per Work, Instance and Item, each
    in the per-resource shape, with vocabulary terms and description nodes
    nested inside. So a CBD is an array of resources rather than a different
    kind of document, which is most of what a schema for it would say.

    The other half is what changes: in a stored record `hasInstance` and
    `instanceOf` are bare URIs, because the other resource is a row of its
    own. Here they embed the whole node, because it is in the document. Both
    are right, and no single schema can say both.
    """
    into = CORPUS / "cbd"
    into.mkdir(parents=True, exist_ok=True)
    written = 0
    for uri in uris:
        try:
            expanded = get(f"{uri}.cbd.jsonld")
        except (OSError, ValueError) as error:
            print(f"  skipped {uri}: {error}")
            continue
        framed = strip_blank_ids(_as_arrays(jsonld.frame(expanded, CBD_FRAME)))
        (into / f"{uri.rstrip('/').rsplit('/', 1)[-1]}.cbd.json").write_text(
            json.dumps(framed, indent=2, ensure_ascii=False) + "\n"
        )
        written += 1
        time.sleep(PAUSE)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=50, help="of each kind")
    parser.add_argument("--host", default="https://stage.bcld.info")
    args = parser.parse_args()

    CORPUS.mkdir(exist_ok=True)
    for kind in ("works", "instances"):
        uris = recent(args.host, kind, args.count)
        written = fetch(kind, uris)
        print(
            f"  {kind}: {written} records into {(CORPUS / kind).relative_to(HERE.parent)}/"
        )


if __name__ == "__main__":
    main()
