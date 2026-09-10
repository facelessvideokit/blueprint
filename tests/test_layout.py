#!/usr/bin/env python3
"""test_layout.py — refuse a content dimension written as a pixel literal.

WHY THIS EXISTS
---------------
A layout audit measured 39 rendered scenes and found 26 missing a limit **with
every existing gate green**. One template used 47% of the safe width, leaving
886px of dead ground. The cause was never a bug in the maths; it was fourteen
templates each holding their own pixel constants for how wide the frame is.

None of those constants was wrong when it was typed. They were wrong once
`safeBottom()` and caption-free rendering moved the frame underneath them — and
a literal cannot follow anything.

So the fix is not fourteen corrected numbers. It is: ask the box.

    bodyBox(t)         the rectangle this scene's body may occupy
    columns(box, n, g) n equal columns spanning the whole box
    lattice(box, n)    a lattice of n marks that fills the box

A cap on a column is a FRACTION of the box, never a pixel.

WHAT THIS SCANS
---------------
Every .tsx under src/demo and src/lib:

  1. it must reference `bodyBox`, or carry a reasoned waiver
  2. it must not assign a geometry-shaped name to a bare number >= 300

🔴 COMMENTS ARE STRIPPED BEFORE SCANNING, and the original's first run is why:
it failed on eight of its own explanations. Every fix in that audit quotes the
literal it replaced — "`bw = 420` centred at 960" — because a fix that does not
say what it replaced is a fix nobody can argue with later. **A lint that forbids
naming the bug teaches people to stop naming bugs.**

USAGE
    python3 tests/test_layout.py
    python3 tests/test_layout.py --self-test

EXIT CODES
    0  clean      1  literal found      2  self-test failure
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = [ROOT / "src" / "demo", ROOT / "src" / "lib"]

# File-level waivers. Deliberately EMPTY.
#
# 🔴 A whole-file waiver is almost always the wrong tool, and the first version of
# this test proved it: waiving the two files in the tree left the scan reporting
# "0/2 scanned" — a green gate that inspected nothing. If a file needs one line
# exempted, exempt THAT LINE (see ALLOW below), so the rest of the file stays
# under the gate.
WAIVERS: dict[str, str] = {}

# A per-line escape hatch that must carry a reason on the same line:
#
#     x: x0 + i * (w + GAP), y: SAFE.top + 300,  // qc-allow-literal: the bug, on purpose
#
# Checked against the ORIGINAL line, before comments are stripped — which is the
# only place the reason can live.
ALLOW = re.compile(r"qc-allow-literal:\s*\S")

BLOCK = re.compile(r"/\*.*?\*/", re.S)
LINE = re.compile(r"//[^\n]*")

# `const NAME = <number>` or `NAME: <number>`, where NAME looks like geometry AND
# the number is the WHOLE right-hand side. `W = 1920 - 2 * X` is derived and fine;
# `W = 1400` is not. Type sizes, opacities and durations are named differently and
# sit well under the threshold anyway.
GEOM = re.compile(
    r"\b(const\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*"
    r"(?P<val>\d{3,})\s*(?=[,;)}\]]|$)")
GEOM_NAMES = re.compile(
    r"^(x|y|w|h|W|H|X|Y|BW|BH|CW|CH|BX|BY|SX|SY|X0|X1|Y0|Y1|"
    r"boxW|boxH|gridW|gridH|cw|ch|bw|R|cx|cy|TOP|BOT|BOX|WBOX|left|top|width|height)$")
LIMIT = 300


def scan(paths: list[Path], waivers: dict) -> list[str]:
    problems: list[str] = []
    for path in paths:
        name = path.name
        rel = f"{path.parent.name}/{name}"
        src = path.read_text(encoding="utf-8")

        if name in waivers:
            continue

        if "bodyBox" not in src:
            problems.append(
                f"{rel}: lays out without `bodyBox` from lib/Layout. Either route it "
                f"through the body rectangle, or add it to WAIVERS in this file "
                f"with the reason.")

        # Blank the comments rather than dropping them, so line numbers survive.
        raw = src.splitlines()
        code = LINE.sub("", BLOCK.sub(lambda m: "\n" * m.group(0).count("\n"), src))
        for line_no, line in enumerate(code.splitlines(), 1):
            # The pragma lives in the comment, so it must be read off the ORIGINAL.
            if line_no <= len(raw) and ALLOW.search(raw[line_no - 1]):
                continue
            for m in GEOM.finditer(line):
                if not GEOM_NAMES.match(m.group("name")):
                    continue
                if int(m.group("val")) < LIMIT:
                    continue
                problems.append(
                    f"{rel}:{line_no}: `{m.group('name')} = {m.group('val')}` — a "
                    f"content dimension as a pixel literal. Derive it from "
                    f"`bodyBox(t)` so it follows safeBottom() and captionFree.")
    return problems


def collect() -> list[Path]:
    files: list[Path] = []
    for d in SCAN_DIRS:
        if d.is_dir():
            files += sorted(d.glob("*.tsx"))
    return files


def self_test() -> int:
    """A gate that cannot fire reports PASS. Prove this one fires."""
    failures = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        clean = tmp / "Clean.tsx"
        clean.write_text(
            "import { bodyBox, columns } from '../lib/Layout';\n"
            "const box = bodyBox(t);\n"
            "const cards = columns(box, 3, 48);\n"
            "const h = Math.round(box.h * 0.68);\n")
        if scan([clean], {}):
            failures.append(f"clean file FAILED (false positive): {scan([clean], {})}")

        literal = tmp / "Literal.tsx"
        literal.write_text(
            "import { bodyBox } from '../lib/Layout';\n"
            "const box = bodyBox(t);\n"
            "const W = 1400;\n")
        if not scan([literal], {}):
            failures.append("`W = 1400` PASSED — the gate cannot fire")

        # The lesson that cost the original a run: a literal QUOTED IN A COMMENT
        # must not trip the scanner, or people stop documenting their fixes.
        commented = tmp / "Commented.tsx"
        commented.write_text(
            "import { bodyBox } from '../lib/Layout';\n"
            "/* was `W = 1400` centred at 960 — replaced by bodyBox() */\n"
            "// also had CW = 400\n"
            "const box = bodyBox(t);\n")
        if scan([commented], {}):
            failures.append("a literal quoted in a COMMENT tripped the scanner — "
                            "that teaches people to stop naming bugs")

        nobox = tmp / "NoBox.tsx"
        nobox.write_text("const x = 1;\n")
        if not scan([nobox], {}):
            failures.append("a file that never calls bodyBox PASSED — the gate cannot fire")

        # A waiver must actually waive.
        if scan([literal], {"Literal.tsx": "reason"}):
            failures.append("WAIVERS did not suppress a waived file")

        # The per-line pragma must exempt its line AND ONLY its line.
        pragma = tmp / "Pragma.tsx"
        pragma.write_text(
            "import { bodyBox } from '../lib/Layout';\n"
            "const box = bodyBox(t);\n"
            "const W = 1400; // qc-allow-literal: deliberate, for the demo\n"
            "const H = 1200;\n")
        got = scan([pragma], {})
        if len(got) != 1 or "H = 1200" not in got[0]:
            failures.append(f"per-line pragma wrong: expected only `H = 1200`, got {got}")

        # A pragma with no reason after the colon must NOT count.
        bare = tmp / "Bare.tsx"
        bare.write_text(
            "import { bodyBox } from '../lib/Layout';\n"
            "const box = bodyBox(t);\n"
            "const W = 1400; // qc-allow-literal:\n")
        if not scan([bare], {}):
            failures.append("a reasonless `qc-allow-literal:` suppressed the check")

    if failures:
        print("SELF-TEST FAILED:")
        for f in failures:
            print("  ✗", f)
        return 2
    print("self-test OK — clean passes; bare literal, missing bodyBox both FAIL; "
          "commented literals and waivers are respected")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    files = collect()
    if not files:
        print("no .tsx found to scan", file=sys.stderr)
        return 2

    problems = scan(files, WAIVERS)
    if problems:
        print("FAIL — hardcoded layout geometry:\n")
        for p in problems:
            print("  " + p)
        print(f"\n{len(problems)} problem(s). See the header of this file for why.")
        return 1

    waived = [f.name for f in files if f.name in WAIVERS]
    print(f"OK  {len(files) - len(waived)}/{len(files)} scanned files lay out from "
          f"lib/Layout ({len(waived)} reasoned waiver(s): {', '.join(waived) or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
