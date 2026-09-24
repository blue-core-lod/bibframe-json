"""Bundle the split dialect schema into one file.

`bibframe_json/schema/dialect/` is the source: one hand-maintained file per
definition, plus `main.json`, following IIIF v4's layout. This inlines them
into `bibframe_json/schema/dialect.json` so a consumer who would rather not
resolve references across files does not have to.

    uv run python generate/bundle.py

The split files were generated from Pydantic models until those moved to the
application that reads them. What that guarantee bought -- a schema that could
never accept less than the reader did -- is now bought by `conformance/`, which
holds any implementation to the same standard rather than only the one the
schema happened to be generated from.

What it cost is that the shared rules are no longer applied by a function at
build time. Every node definition has to carry them itself, and
`tests/test_split_schema.py` checks that each one does, so a definition added
without them fails rather than quietly validating less than its siblings.
"""

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
SPLIT = HERE.parent / "bibframe_json" / "schema" / "dialect"
OUTPUT = HERE.parent / "bibframe_json" / "schema" / "dialect.json"

# Written into each file so it can be served and referenced on its own; the
# bundle has one $id of its own and needs none of them.
PER_FILE = ("$id", "$schema")


def absolutise(node: object) -> object:
    """`Work.json` becomes `#/$defs/Work`, throughout.

    The inverse of what the split files do. A relative reference resolves
    against the enclosing $id, which the bundle does not have per definition,
    so references have to point inside it instead.
    """
    if isinstance(node, dict):
        return {
            key: f"#/$defs/{value.removesuffix('.json')}"
            if key == "$ref" and isinstance(value, str) and value.endswith(".json")
            else absolutise(value)
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [absolutise(item) for item in node]
    return node


def definition(path: pathlib.Path) -> dict:
    contents = json.loads(path.read_text())
    inlined = absolutise({k: v for k, v in contents.items() if k not in PER_FILE})
    assert isinstance(inlined, dict)
    return inlined


def build() -> dict:
    main = json.loads((SPLIT / "main.json").read_text())
    root = absolutise({k: v for k, v in main.items() if k != "$id"})
    assert isinstance(root, dict)
    return {
        **root,
        "$id": "https://bibframe-json.org/schema/dialect.json",
        "$defs": {
            path.stem: definition(path)
            for path in sorted(SPLIT.glob("*.json"))
            if path.stem != "main"
        },
    }


def main() -> None:
    bundle = build()
    OUTPUT.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n")
    text = json.dumps(bundle)
    print(
        f"read  {SPLIT.relative_to(HERE.parent)}/  {len(list(SPLIT.glob('*.json')))} files"
    )
    print(f"wrote {OUTPUT.relative_to(HERE.parent)}")
    print(f"  {len(bundle['$defs'])} definitions, {len(text):,} bytes")


if __name__ == "__main__":
    main()
