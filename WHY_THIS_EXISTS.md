# Four rules for a coded video pipeline

Anyone can write a Remotion template. These are the four things that were learned
the expensive way, across a six-channel faceless-video operation, and they are the
only part of a pipeline that is genuinely hard to get right by reading the docs.

Every number below is measured, not estimated.

---

## 1. No template decides how wide the frame is

A layout audit measured all **39 rendered scenes** of one finished video.

- **11** used under 90% of the safe width
- **1** used **47%**, with **886px of dead ground** on one side
- **17** carried text at 3.0:1 contrast
- **26 of 39** were missing a limit — **with every existing gate green**

Nothing was broken. Type-checks passed, unit tests passed, snapshots passed. The
code ran correctly and produced a correct composition in half the frame.

The cause was the same line written fourteen times, once per template, each with
its own constants:

```
grid template     cw = min(230, 1200 / cols),  ox = SAFE.left + 340
ladder template   X = SAFE.left + 380,  W = 1000
list template     X = SAFE.left + 120,  W = 1400
chain template    CW = min(400, fair share)
flow template     BW = min(470, fair share)
unit template     cols = ceil(sqrt(n * 1.9))
```

Not one of those is wrong on its own. Together they mean the library holds
fourteen different opinions about how wide the frame is, and the widest of them
is 1400 of an available 1680.

**The frame was never the constraint. The constants were.**

The fix is not fourteen corrected numbers — corrected numbers go stale the moment
anything moves. The fix is to ask:

```ts
const box   = bodyBox(t);              // the rectangle this body may occupy
const cards = columns(box, 3, 48);     // n columns spanning the whole box
const marks = lattice(box, n);         // n marks that fill the box
```

**A cap on a column is a FRACTION of the box, never a pixel.** A three-step chain
capped at `min(400, fair share)` comes out 1280 wide inside 1680 and reads as a
centred island — horizontal spread **0.76**. A two-step chain with 820px cards is
a legible two-step chain; 400px cards either side of 800px of nothing just looks
unfinished.

`src/lib/Layout.tsx` is that helper. `tests/test_layout.py` refuses a new literal.

## 2. Ask `safeBottom()`, never `SAFE.bottom`

The frame reserves 242px at the bottom for a caption lane. A project that ships
no captions should get that height back — but a template holding a literal `814`
cannot see it.

On a nine-tier hierarchy, held to 814 the tiers come out **83px** each; released
to 1016 they come out **105px**. That is the difference between a rank label that
reads at feed size and one that does not.

Releasing the band buys nothing if the arithmetic cannot see it. The two changes
have to ship together, and everything downstream has to be derived.

## 3. A gate that cannot fire reports PASS

This is the one that keeps costing money, because a broken gate and a healthy
system look identical from the outside: both are green.

**Test the failure path. Confirm it FAILS. Then trust it.**

Two examples from building *this repository*, both caught within an hour:

- `qc_layout.py` measured **hspread 1.00 on both** the broken and the fixed
  scene. The demo drew a dashed safe-area guide spanning the safe area, and the
  measurer counted it as content. A gate is only as honest as the frame handed
  to it — so the guide now sits 8px *outside* the area it marks, and the
  full-width readout lives below `safeBottom` in the caption band.
- The first `--self-test` fixture failed its own clean case. The synthetic frame
  was 300px tall in a 750px safe area, so it tripped `vspread`. The fixture was
  wrong, not the gate — and without a self-test that plants a *known-good* frame
  as well as known-bad ones, that would have read as the gate being broken.

Every tool here ships `--self-test`, and each one plants a real violation of
every rule it enforces and asserts each is caught:

```bash
python3 plugin/tools/qc_layout.py --self-test
python3 tests/test_layout.py --self-test
```

The same discipline is why `test_layout.py` has a **per-line** escape hatch
rather than whole-file waivers. The first version waived both files in the tree
and reported `0/2 scanned` — a green gate that inspected nothing.

And: **strip comments before linting.** The original of that test failed on eight
of its own explanations, because every fix quotes the literal it replaced. A lint
that forbids naming the bug teaches people to stop naming bugs.

## 4. The path is part of the artefact

Two separate, expensive versions of the same mistake.

**Remotion splits an image-sequence output path on `.`** — so any absolute path
containing a dot fails, and a home directory like `/Users/name.surname/` breaks
every sequence render on that machine. Render sequences to a relative, dot-free
scratch directory.

**An FCPXML references media by absolute `file://` URL**, baked in at write time
from the writer's working directory. Run the assembler somewhere other than where
the media lives — a container, CI, a VM with the folder mounted elsewhere — and
it writes that machine's paths. The XML is valid. A verifier run *in the same
place* reports zero missing media, because from there the paths resolve. Then the
editor opens it and **every clip is red**. One project shipped **151 references**
that way.

Write the timeline beside the media, and verify against the real filesystem:

```bash
python3 plugin/tools/make_fcpxml.py --verify out/timeline.fcpxml
```

---

## Bonus: pin your colour space before a version bump does it for you

Remotion 4 renders effectively **bt601**. **Remotion 5 changes the default to
bt709.** If coded scenes are cut against stills you judged by eye, taking the new
default silently shifts the colour of half your timeline relative to the other
half, with no error anywhere to explain it.

```ts
Config.setColorSpace("bt601");   // remotion.config.ts
```

Pin it. Move deliberately, with a frame open in the editor next to a still.

---

## What this repository is

A runnable demonstration of rules 1, 3 and 4:

- `src/lib/Layout.tsx` — the box
- `src/demo/Chain.tsx` — one scene, drawn both ways
- `plugin/tools/qc_layout.py` — measures whether a frame uses its frame
- `plugin/tools/make_fcpxml.py` — stills to a timeline, with the path check
- `tests/test_layout.py` — refuses a pixel literal

`npm run example` renders both, measures both, and builds a timeline. The broken
one fails the gate. That is the whole point.

MIT licensed. Take the rules; they are worth more than the code.
