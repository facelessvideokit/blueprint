---
name: coded-video-layout
description: Four rules for coded video scenes, and the gates that prove they hold. Use when writing or reviewing a Remotion (or any coded) video scene or template, choosing widths, columns, caption bands or safe areas, deciding a cap on a column, rendering an image sequence, building or verifying an FCPXML timeline, pinning a colour space, or when a scene "renders fine" but looks like it is using half the frame. Also use when writing a QC gate for any of the above.
---

# Coded video layout — four rules

These are the four things that are genuinely hard to get right by reading the
docs, learned across a multi-channel faceless-video operation. Each one has a
gate in this plugin that proves it holds.

The measurement that motivates all of it: a layout audit of **39 rendered
scenes** in one finished video found **11 using under 90% of the safe width**,
one using **47%** with 886px of dead ground on a side, and **26 of 39 missing a
limit — with every existing gate green.** Nothing was broken. Type-checks
passed, unit tests passed, snapshots passed. The code was correct and produced a
correct composition in half the frame.

---

## Rule 1 — no template decides how wide the frame is

A cap on a column is a **fraction of the box, never a pixel.**

The failure is not one bad number, it is the same line written once per
template, each with its own constants — so the library ends up holding a dozen
different opinions about how wide the frame is, and the widest of them is
narrower than the frame. Corrected constants go stale the moment anything moves.

Ask the box instead:

```ts
const box   = bodyBox(t);              // the rectangle this body may occupy
const cards = columns(box, 3, 48);     // n columns spanning the whole box
const marks = lattice(box, n);         // n marks that fill the box
```

`src/lib/Layout.tsx` in this repo is that helper. A three-step chain capped at
`min(400, fair share)` comes out 1280 wide inside 1680 and reads as a centred
island — horizontal spread **0.76**. Two 820px cards are a legible two-step
chain; two 400px cards either side of 800px of nothing just look unfinished.

**When reviewing a scene:** every content dimension must derive from the box.
A bare pixel literal for a width, column count or cap is the defect, even when
the render looks acceptable at that one prop set.

## Rule 2 — ask `safeBottom()`, never `SAFE.bottom`

If the frame reserves a band at the bottom for captions, a project that ships no
captions should get that height back. A template holding the literal cannot see
it.

On a nine-tier hierarchy, held to 814px the tiers come out **83px** each;
released to 1016px they come out **105px**. That is the difference between a
rank label that reads at feed size and one that does not.

Releasing the band buys nothing unless the arithmetic downstream is derived, so
the two changes ship together.

## Rule 3 — a gate that cannot fire reports PASS

A broken gate and a healthy system look identical from the outside: both green.

**Test the failure path. Confirm it FAILS. Then trust it.**

Every tool here ships `--self-test`, which plants a real violation of every rule
it enforces and asserts each one is caught:

```bash
python3 tools/qc_layout.py --self-test
python3 tests/test_layout.py --self-test
```

Three ways this rule was broken while building *this* repo:

- The measurer reported **1.00 on both** the broken and the fixed scene. The
  demo drew a dashed safe-area guide spanning the safe area and the measurer
  counted it as content. **A decoration that spans the region you are measuring
  destroys the measurement.**
- A `--self-test` fixture failed its own clean case — the synthetic frame was
  300px tall in a 750px safe area, so it tripped the vertical check. The fixture
  was wrong, not the gate. Plant a known-**good** sample as well as known-bad
  ones, or a broken fixture reads as a broken gate.
- The first lint waived both files in the tree and reported **`0/2 scanned`** —
  a green gate that inspected nothing. Use **per-line** pragmas, never
  whole-file waivers.

And: **strip comments before linting.** A lint that forbids naming the bug
teaches people to stop naming bugs, because every good fix quotes the literal it
replaced.

## Rule 4 — the path is part of the artefact

Two expensive versions of the same mistake.

**Remotion splits an image-sequence output path on `.`** — so any absolute path
containing a dot fails, and a home directory with a dot in it breaks every
sequence render on that machine. Render sequences to a **relative, dot-free**
scratch directory.

**An FCPXML references media by absolute `file://` URL**, baked in at write time
from the writer's working directory. Run the assembler anywhere other than where
the media lives — a container, CI, a VM with the folder mounted elsewhere — and
it writes that machine's paths. The XML is valid. A verifier run *in the same
place* reports zero missing media, because from there the paths resolve. Then
the editor opens it and **every clip is red.** One project shipped 151
references that way.

Write the timeline beside the media, and verify against the real filesystem:

```bash
python3 tools/make_fcpxml.py --verify out/timeline.fcpxml
```

## Bonus — pin the colour space before a version bump does it for you

Remotion 4 renders effectively **bt601**; Remotion 5 changes the default to
**bt709**. If coded scenes are cut against stills judged by eye, taking the new
default silently shifts the colour of half the timeline relative to the other
half, with no error anywhere to explain it.

```ts
Config.setColorSpace("bt601");   // remotion.config.ts
```

---

## Running the gates

From the repo root (`${CLAUDE_PLUGIN_ROOT}`):

```bash
npm install && npm run example      # render both, measure both, build a timeline
python3 tools/qc_layout.py <frame.png>            # does it use its frame?
python3 tools/qc_layout.py --self-test            # prove the measurer fires
python3 tests/test_layout.py                      # refuse pixel literals
python3 tools/make_fcpxml.py --verify <file>      # do the baked paths resolve?
```

Needs Node 18+, Python 3.9+, `numpy` and `Pillow`.

**Thresholds** — `hspread` is the fraction of safe width the content actually
occupies. Below **0.90** something is wrong: either the content is capped in
pixels or the box was never asked. `fill` below ~0.55 usually means a scene that
should have been two columns is one.

## What is deliberately not here

The full scene library, type-legibility measurement (OCR contrast per text run),
motion assertions, golden-frame determinism, the audio and caption lanes in the
assembler, beat-matched frame timing, and stock-footage selection. This is the
geometry layer and the rules — a small, complete, runnable slice.
