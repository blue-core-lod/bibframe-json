# Slides

`cbd-json.svg` is the source and `cbd-json.png` a 2560px export, for slide
software that will not place SVG. 16:9, 1920x1080.

```sh
python3 slides/make-cbd-json-slide.py
rsvg-convert -w 2560 slides/cbd-json.svg -o slides/cbd-json.png
```

The look is bluecore-models' `docs/slides`, deliberately: same stage, same
fonts, and the same palette, so a Work stays amber and an Instance stays teal
from one talk to the next. That is the distinction this slide is about, so the
colours are already doing the work before anybody reads the JSON.

Every key and value comes out of `example/cbd.json`, read at build time rather
than typed in, so the slide cannot drift from the record it claims to show.
The record is abridged to fit and the UUIDs are cut short with an ellipsis;
those are the only liberties.

The type size is computed from the longest line rather than set by hand, so
editing the record re-fits the slide instead of overflowing it.
