# Faceless Video Kit — Blueprint

**The same scene, laid out two ways. One of them wastes 385px of the frame and
nothing in your toolchain notices.**

```
FAIL  before.png  hspread 0.77  vspread 0.75  fill 0.58  margins L192 R193
        hspread 0.77 < 0.90 — 385px of safe width unused
pass  after.png   hspread 1.00  vspread 0.70  fill 0.70  margins L0 R1
```

Both frames render. Both type-check. Both pass every unit test. The only thing
that tells them apart is measuring the pixels.

This repo is a runnable demonstration of that, plus the four rules behind it —
learned across a six-channel faceless-video operation, and written up in
[WHY_THIS_EXISTS.md](WHY_THIS_EXISTS.md). Those rules are the valuable part.

## Run it

```bash
npm install
npm run example
```

That will:

1. prove both gates can actually fail (`--self-test` on each)
2. refuse a pixel literal in the source
3. render `Before` and `After`
4. measure both — **`Before` fails**
5. build a Final Cut timeline and verify every baked-in media path

Needs Node 18+, Python 3.9+, and `numpy` + `Pillow`:

```bash
pip3 install numpy Pillow
```

## What's here

| | |
|---|---|
| `src/lib/Layout.tsx` | `bodyBox` / `columns` / `lattice` — ask the box, don't guess the frame |
| `src/demo/Chain.tsx` | one scene, drawn both ways |
| `tools/qc_layout.py` | measures whether a rendered frame uses its frame |
| `tools/make_fcpxml.py` | stills → Final Cut timeline, with the absolute-path check |
| `tests/test_layout.py` | refuses a content dimension written as a pixel literal |
| `remotion.config.ts` | why the colour space is pinned |

Every tool ships `--self-test`, which plants a real violation of every rule it
enforces and asserts each one is caught. A gate that cannot fire reports PASS.

## The four rules, in one line each

1. **No template decides how wide the frame is.** A cap is a fraction of the box, never a pixel.
2. **Ask `safeBottom()`, never `SAFE.bottom`.** Releasing height buys nothing if the arithmetic can't see it.
3. **A gate that cannot fire reports PASS.** Test the failure path, then trust it.
4. **The path is part of the artefact.** Dots break Remotion sequences; absolute `file://` URLs bake your machine into the timeline.

[The long version, with the measurements →](WHY_THIS_EXISTS.md)

## What this is not

This is the geometry layer and the rules — deliberately a small, complete,
runnable slice.

Not included here: the full scene library, type-legibility measurement (OCR
contrast per text run), motion assertions, golden-frame determinism, the audio
and caption lanes in the assembler, beat-matched frame timing, and stock-footage
selection.

## Licence

MIT. Take the rules; they are worth more than the code.
