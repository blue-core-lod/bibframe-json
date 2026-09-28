#!/usr/bin/env python3
"""One slide: what a Concise Bounded Description looks like as JSON.

Same stage as bluecore-models/docs/slides: 1920x1080, Iowan Old Style for the
heading, Inter for everything that labels, SF Mono for anything a machine
wrote. It borrows that deck's palette on purpose, so Work stays amber and
Instance stays teal from one talk to the next -- which happens to be the exact
distinction this slide is about.

The record is example/cbd.json, abridged. Every key and value below is in that
file; the UUIDs are cut short with an ellipsis, which is the only liberty
taken, and the counts in the note are real.

    python3 slides/make-cbd-json-slide.py
    rsvg-convert -w 2560 slides/cbd-json.svg -o slides/cbd-json.png
"""

import json
import pathlib
from textwrap import wrap

HERE = pathlib.Path(__file__).resolve().parent
RECORD = HERE.parent / "example" / "cbd.json"
OUT = HERE / "cbd-json.svg"

# from bluecore-models/docs/make-cbd-slides.py, so the two decks agree
INK, MUTE, FAINT, RULE = "#15202b", "#6c7b87", "#93a0ab", "#dde3e8"
WORK, WORK_BG = "#b0743c", "#fbf2e7"
INST, INST_BG = "#2f7d7a", "#e8f4f3"
STR = "#3d4b57"

W, H = 1920, 1080
LEFT = 72
TOP = 232          # below the house rule at y=168
PANEL_W = W - 2 * LEFT   # the record gets the width; notes go beneath
PAD = 30
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
    out, i, in_string = [], 0, False
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

    # Fit the longest line, then fill the space that leaves. A slide read from
    # the back of a room wants the largest type that does not overflow, and
    # nothing here should need nudging by hand after an edit to the record.
    mono = min(24, int((PANEL_W - 2 * PAD - deepest * 26) / (widest * ADVANCE)))
    line_h = round(mono * 1.62)
    indent_w = round(mono * 1.25)

    body_h = len(lines) * line_h
    top = TOP + 18

    work_rows = [n for n, (kind, _, _) in enumerate(lines) if kind == "work"]
    band_y = top + work_rows[0] * line_h - round(mono * 1.15)
    band_h = (work_rows[-1] - work_rows[0] + 1) * line_h + 10

    panel_y = top - 52
    panel_h = body_h + 58

    body = []
    for n, (kind, indent, text) in enumerate(lines):
        y = top + n * line_h
        x = LEFT + PAD + indent * indent_w
        body.append(f'<text class="j" x="{x}" y="{y}">{coloured(text)}</text>')

    # the three things the slide is for, in the order the eye meets them
    notes = [
        (INST, "The document is the Instance",
         "You asked for one, and that is what you get."),
        (WORK, "instanceOf embeds the Work",
         "A stored record names it instead: there, the Work is a row of its own."),
        (MUTE, "hasInstance points back by URI",
         "A processor breaks the cycle there, which keeps the document finite."),
    ]
    # Three notes in a row beneath, rather than a column beside. The record
    # is the thing being shown, so it takes the width, and at full width the
    # longest line fits at the largest size this caps at.
    col_w = (PANEL_W - 2 * 40) // 3
    ny = panel_y + panel_h + 62
    for i, (colour, head, sub) in enumerate(notes):
        nx = LEFT + i * (col_w + 40)
        body.append(f'<rect x="{nx}" y="{ny - 26}" width="34" height="3" rx="1.5" fill="{colour}"/>')
        body.append(f'<text class="nh" x="{nx}" y="{ny + 14}">{esc(head)}</text>')
        for j, part in enumerate(wrap(sub, 52)):
            body.append(
                f'<text class="ns" x="{nx}" y="{ny + 44 + j * 26}">{esc(part)}</text>'
            )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<style>
  .h1 {{ font: 600 46px "Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif; fill:{INK} }}
  .sub {{ font: 400 23px "Inter","Helvetica Neue",Helvetica,Arial,sans-serif; fill:{MUTE} }}
  .j  {{ font: 400 {mono}px "SF Mono",SFMono-Regular,Menlo,Consolas,monospace; fill:{STR} }}
  .nh {{ font: 600 21px "Inter","Helvetica Neue",Helvetica,Arial,sans-serif; fill:{INK} }}
  .ns {{ font: 400 18.5px "Inter","Helvetica Neue",Helvetica,Arial,sans-serif; fill:{MUTE} }}
  .tag {{ font: 600 14px "Inter","Helvetica Neue",Helvetica,Arial,sans-serif; letter-spacing:1.6px }}
  .foot {{ font: 400 17px "Inter","Helvetica Neue",Helvetica,Arial,sans-serif; fill:{FAINT} }}
</style>
<rect width="{W}" height="{H}" fill="#ffffff"/>
<text class="h1" x="{LEFT}" y="92">One document explains the Instance</text>
<text class="sub" x="{LEFT}" y="138">A Concise Bounded Description in bibframe-json: the Instance at the root, with its Work embedded.</text>
<line x1="{LEFT}" y1="168" x2="{W - LEFT}" y2="168" stroke="{RULE}" stroke-width="1"/>

<rect x="{LEFT}" y="{panel_y}" width="{PANEL_W}" height="{panel_h}" rx="10"
      fill="#fcfdfd" stroke="{RULE}" stroke-width="1"/>
<rect x="{LEFT + 14}" y="{band_y}" width="{PANEL_W - 28}" height="{band_h}" rx="8"
      fill="{WORK_BG}" stroke="{WORK}" stroke-width="1.5"/>
<text class="tag" x="{LEFT + PAD}" y="{panel_y + 30}" fill="{INST}">INSTANCE</text>
<text class="tag" x="{LEFT + PANEL_W - 30}" y="{band_y + 26}" fill="{WORK}" text-anchor="end">WORK</text>
{chr(10).join(body)}

<text class="foot" x="{LEFT}" y="{H - 54}">Abridged from example/cbd.json, which validates against schema/cbd.json. Every property is an array, so a reader loops without checking.</text>
</svg>
"""


if __name__ == "__main__":
    OUT.write_text(svg())
    print(f"wrote {OUT.relative_to(HERE.parent)}")
