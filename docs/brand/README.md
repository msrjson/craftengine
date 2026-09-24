# CraftEngine brand

## The mark

A gear with an ignition bolt breaking out of it. The gear is what gets built;
the ignition is what the engine does.

The bolt deliberately breaks the ring rather than sitting inside it. A
symmetrical gear with something centred in it is the universal "settings"
icon, and a framework whose mark is indistinguishable from a settings button
has no mark.

| File | Use |
|---|---|
| `craftengine-mark.svg` | Two-tone, the default. Anywhere colour is available. |
| `craftengine-mark-mono.svg` | One colour, inheriting `currentColor` when inlined. Favicons at small sizes, single-ink printing, badges. |

The starter page a generated project serves inlines the mark rather than
linking it, because a generated project ships no static assets. That copy is
downstream of these files: change these, then the stub in
`data/engine/cli/skeleton/resources/views/welcome.forge.py.stub`.

## Palette

| Token | Value | Role |
|---|---|---|
| Brand | `#f97316` | The bolt, the wordmark, anything that should read first |
| Brand dark | `#ea580c` | The gear, outlines, the secondary half of the wordmark |
| Brand light | `#fb923c` | Highlights, hover states |
| Surface | `#0f172a` | Page background |
| Surface raised | `#1e293b` | Cards, pills, anything lifted off the background |
| Muted | `#94a3b8` | Secondary text |

These are mirrored in `data/engine/support/branding.py`, which is what the
console banner reads. The two are kept in step by hand; there are six values
and they change rarely.

## Wordmark

`CraftEngine`, one word, no space. Set in the interface's monospace stack at
weight 700 with `-0.04em` tracking. "Craft" is solid brand orange and "Engine"
is an outline in brand dark, so the two halves read as one word with a
hierarchy rather than as two words.

## The console banner

The console uses block characters, not the SVG: a terminal cannot draw one.
`craft.support.branding.WORDMARK_STACKED` is what the banner prints, on two
rows, because a terminal is eighty columns and the single-row form is
eighty-eight.

The same block art does **not** work in a browser. Block art needs the glyph to
fill its advance width exactly; the fonts a browser substitutes do not, so
adjacent blocks leave gaps and the letters collapse into a smear that gets
worse as the type grows. That is why the page is typographic and the terminal
is not.

## What not to do

- Do not recolour the mark outside the palette above.
- Do not put the bolt back inside the ring "to tidy it up". The break is the
  idea.
- Do not stretch either axis; the mark is square and scales uniformly.
- Do not set the wordmark as two words, or capitalise it as `CRAFTENGINE`.
