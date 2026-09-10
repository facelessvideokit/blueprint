---
description: Measure whether a rendered frame actually uses its frame, and report why not
argument-hint: [path to a rendered PNG, or a directory of them]
allowed-tools: Bash(python3:*), Read, Glob
---

Measure `$ARGUMENTS` with the layout gate in this plugin.

1. If `$ARGUMENTS` is empty, look for rendered frames under `out/` and say what
   you found before measuring anything.
2. Run `python3 ${CLAUDE_PLUGIN_ROOT}/tools/qc_layout.py` on each frame.
3. Report `hspread`, `vspread`, `fill` and the margins for each, and mark every
   frame under **0.90 hspread** as FAIL.
4. For each failure, do not just restate the number. Open the scene that
   produced it and find the cause, which is almost always **a content dimension
   written as a pixel literal** — a `min(<number>, ...)` cap, a hardcoded `X`
   offset, or a width constant. Quote the line.
5. Propose the fix as a derivation from `bodyBox` / `columns` / `lattice`
   (see the `coded-video-layout` skill), never as a corrected constant.

If every frame passes, say so plainly and stop — do not invent findings.
