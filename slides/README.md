# Slides

`cbd-json.svg` is a Concise Bounded Description as JSON, to drop into a slide.
Just the record: no heading, no notes, no rule. 1280 wide, two thirds of a
1920 slide, and as tall as the record needs. `cbd-json.png` is a 2560px export
for software that will not place SVG.

```sh
python3 slides/make-cbd-json-slide.py
rsvg-convert -w 2560 slides/cbd-json.svg -o slides/cbd-json.png
```

It borrows the palette from bluecore-models' `docs/slides`, so a Work stays
amber and an Instance stays teal between talks. That is the distinction a CBD
turns on, so the amber band — the embedded Work, inside the Instance that is
the document — does some of the work before anyone reads the JSON.

Every key and value is read from `example/cbd.json` at build time rather than
typed in, so the image cannot drift from the record. It is abridged to fit and
the UUIDs are cut short with an ellipsis; that is the only liberty. The type
size is computed from the longest line, so editing the record re-fits the
image instead of overflowing it.
