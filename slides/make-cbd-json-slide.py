#!/usr/bin/env python3
"""A Concise Bounded Description as JSON, to drop into a slide.

Just the record: no heading, no notes, no rule. 1280 wide, two thirds of a
1920 slide, and as tall as the record needs.

It borrows bluecore-models/docs/slides' palette on purpose, so Work stays
amber and Instance stays teal between talks. That is the distinction a CBD
turns on, so the amber band -- the embedded Work, inside the Instance that is
the document -- does some of the work before anyone reads the JSON.

Every key and value is read from example/cbd.json at build time rather than
typed in here, so the image cannot drift from the record. It is abridged and
the UUIDs are cut short with an ellipsis; that is the only liberty.

    python3 slides/make-cbd-json-slide.py
    rsvg-convert -w 2560 slides/cbd-json.svg -o slides/cbd-json.png
"""

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
RECORD = HERE.parent / "example" / "cbd.json"
OUT = HERE / "cbd-json.svg"

# from bluecore-models/docs/make-cbd-slides.py, so the two decks agree
INK, MUTE, FAINT, RULE = "#15202b", "#6c7b87", "#93a0ab", "#dde3e8"
WORK, WORK_BG = "#b0743c", "#fbf2e7"
INST, INST_BG = "#2f7d7a", "#e8f4f3"
STR = "#3d4b57"

# Two thirds of a 1920 slide. The height follows the record.
W = 1280
PAD = 34
TAG_H = 30
# SF Mono advances at about 0.6em, which is what lets the type size be
# computed from the longest line instead of guessed at and then nudged.
ADVANCE = 0.6


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def short(uri: str) -> str:
    """A URI cut to its first UUID segment, so a line fits on a slide."""
    head, _, tail = uri.rpartition("/")
    return f"{head}/{tail.split('-')[0]}-…" if "-" in tail else uri


def abridged() -> list[tuple[str, int, str]]:
    """The record as (kind, indent, text) lines.

    Written out rather than pretty-printed, because a slide wants one array
    per line and json.dumps gives three. Every value is read from the file so
    the slide cannot drift from the example it claims to show.
    """
    r = json.loads(RECORD.read_text())
    work = r["instanceOf"][0]
    title = r["title"][0]["mainTitle"][0]
    isbn = r["identifiedBy"][0]["rdf:value"][0]
    instance_uri, work_uri = short(r["@id"]), short(work["@id"])
    ctx = r["@context"].replace("https://blue-core-lod.github.io", "…")

    return [
        ("inst", 0, "{"),
        ("inst", 1, f'"@context": "{ctx}",'),
        ("inst", 1, f'"@id": "{instance_uri}",'),
        ("inst", 1, '"@type": ["Instance"],'),
        ("inst", 1, f'"title": [{{ "@type": ["Title"], "mainTitle": ["{title}"] }}],'),
        ("inst", 1, f'"identifiedBy": [{{ "@type": ["Isbn"], "rdf:value": ["{isbn}"] }}],'),
        ("inst", 1, '"instanceOf": ['),
        ("work", 2, "{"),
        ("work", 3, f'"@id": "{work_uri}",'),
        ("work", 3, '"@type": ["Work"],'),
        ("work", 3, f'"title": [{{ "@type": ["Title"], "mainTitle": ["{title}"] }}],'),
        ("work", 3, f'"hasInstance": ["{instance_uri}"]'),
        ("work", 2, "}"),
        ("inst", 1, "]"),
        ("inst", 0, "}"),
    ]


def coloured(text: str) -> str:
    """Keys in ink, strings in slate, punctuation quiet.

    Walked rather than matched, so a colon or a bracket inside a string stays
    the colour of the string. That is the same rule the site uses and the same
    reason: punctuation only means something when it is outside a literal.
    """
    out, i = [], 0
    while i < len(text):
        ch = text[i]
        if ch == '"':
            end = text.index('"', i + 1) if '"' in text[i + 1 :] else len(text) - 1
            token = text[i : end + 1]
            after = text[end + 1 :].lstrip()
            key = after.startswith(":")
            fill = INK if key else STR
            weight = "600" if key else "400"
            out.append(
                f'<tspan fill="{fill}" font-weight="{weight}">{esc(token)}</tspan>'
            )
            i = end + 1
        elif ch in "{}[],:":
            out.append(f'<tspan fill="{FAINT}">{esc(ch)}</tspan>')
            i += 1
        else:
            out.append(esc(ch))
            i += 1
    return "".join(out)


def svg() -> str:
    lines = abridged()
    deepest = max(indent for _, indent, _ in lines)
    widest = max(len(text) + indent * 2 for _, indent, text in lines)

    # Fit the longest line rather than guess and nudge, so editing the record
    # re-fits the image instead of overflowing it.
    mono = min(22, int((W - 2 * PAD - deepest * 24) / (widest * ADVANCE)))
    line_h = round(mono * 1.62)
    indent_w = round(mono * 1.3)

    top = PAD + TAG_H + mono
    height = top + (len(lines) - 1) * line_h + PAD + round(mono * 0.5)

    work = [n for n, (kind, _, _) in enumerate(lines) if kind == "work"]
    band_y = top + work[0] * line_h - round(mono * 1.2)
    band_h = (work[-1] - work[0] + 1) * line_h + 8

    body = [
        f'<text class="j" x="{PAD + 12 + indent * indent_w}" y="{top + n * line_h}">'
        f"{coloured(text)}</text>"
        for n, (kind, indent, text) in enumerate(lines)
    ]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" width="{W}" height="{height}">
<style>
  .j {{ font: 400 {mono}px "SF Mono",SFMono-Regular,Menlo,Consolas,monospace; fill:{STR} }}
  .tag {{ font: 600 13px "Inter","Helvetica Neue",Helvetica,Arial,sans-serif; letter-spacing:1.6px }}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{height - 1}" rx="10"
      fill="#fcfdfd" stroke="{RULE}" stroke-width="1"/>
<rect x="{PAD - 14}" y="{band_y}" width="{W - 2 * (PAD - 14)}" height="{band_h}" rx="8"
      fill="{WORK_BG}" stroke="{WORK}" stroke-width="1.5"/>
<text class="tag" x="{PAD}" y="{PAD + 14}" fill="{INST}">INSTANCE</text>
<text class="tag" x="{W - PAD}" y="{band_y + 22}" fill="{WORK}" text-anchor="end">WORK</text>
{chr(10).join(body)}
</svg>
"""


if __name__ == "__main__":
    OUT.write_text(svg())
    print(f"wrote {OUT.relative_to(HERE.parent)}")
