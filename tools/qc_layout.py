#!/usr/bin/env python3
"""qc_layout.py — measure whether a rendered frame actually uses its frame.

WHY THIS EXISTS
---------------
A layout audit measured all 39 rendered scenes of one finished video. Eleven used
under 90% of the safe width. One used 47%, with 886px of dead ground on a single
side. **Every existing gate was green**, because every existing gate checked that
the code ran, not that the picture was any good.

Type checks, unit tests and snapshot tests all pass on a scene that renders a
correct composition into half the frame. The only thing that catches it is
measuring the pixels.

WHAT IT MEASURES
----------------
For each PNG: the content bounding box, and how much of the safe area it spans.

  hspread   content width  / safe width    (1.00 = spans the whole safe area)
  vspread   content height / safe height
  fill      bbox area      / safe area
  margins   dead ground on each side, in px
  skew      |left margin - right margin|   (a centred island has low skew and
                                            low hspread — that is the defect)

THE GROUND IS MEASURED, NOT ASSUMED. A scene may paint its own background, an
overlay paints none at all, and a still may sit on a photograph — so taking the
theme's hex would mis-measure exactly the frames worth measuring. The modal
colour of the frame's outer 40px ring IS the ground.

USAGE
    python3 tools/qc_layout.py out/                  # a directory of PNGs
    python3 tools/qc_layout.py out/before.png        # one frame
    python3 tools/qc_layout.py out/ --json report.json
    python3 tools/qc_layout.py --self-test           # prove the gate can fail

EXIT CODES
    0  every frame passes
    1  at least one frame fails
    2  bad invocation, or self-test failure

The full kit adds type legibility (OCR contrast per text run), motion assertions
and golden-frame determinism. This file is the geometry gate only.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

FRAME_W, FRAME_H = 1920, 1080

# Matches src/theme.ts. `bottom` reserves 242px for a caption lane; pass
# --caption-free for a project that ships no captions.
SAFE = {"top": 64, "left": 120, "right": 1800, "bottom": 814}
SAFE_CAPTION_FREE = {**SAFE, "bottom": FRAME_H - 64}

LIMITS = {
    # A scene using under 90% of the safe width is leaving a visible band of
    # nothing on at least one side. 0.90 is not a style opinion — below it, the
    # audit found dead ground you can see at feed size without measuring.
    "hspread_min": 0.90,
    # Vertical is looser: plenty of legitimate scenes are genuinely short.
    "vspread_min": 0.55,
    # Ink outside the safe margin. Full-bleed composites are exempt by nature —
    # pass --allow-overshoot for those.
    "overshoot_max": 0,
}

# Ink = anything meaningfully off the ground. 18 in Euclidean RGB sits above JPEG
# ringing and ProRes noise, and below any mark a template actually draws.
INK_DIST = 18.0
# A row or column counts as occupied only if it carries real ink, so one stray
# antialiased pixel cannot inflate the bbox to the whole frame.
MIN_RUN = 6


def measure(png: Path, caption_free: bool = False) -> dict:
    im = Image.open(png).convert("RGB")
    if im.size != (FRAME_W, FRAME_H):
        im = im.resize((FRAME_W, FRAME_H))
    a = np.asarray(im)

    box = SAFE_CAPTION_FREE if caption_free else SAFE
    L, T, R, B = box["left"], box["top"], box["right"], box["bottom"]

    ring = np.concatenate([
        a[:40].reshape(-1, 3), a[-40:].reshape(-1, 3),
        a[:, :40].reshape(-1, 3), a[:, -40:].reshape(-1, 3)])
    q = (ring // 8).astype(np.int32)
    codes = q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2]
    modal = np.bincount(codes).argmax()
    bg = np.array([(modal // 4096) * 8 + 4, ((modal // 64) % 64) * 8 + 4,
                   (modal % 64) * 8 + 4], dtype=np.float64)

    dist = np.sqrt(((a.astype(np.float64) - bg) ** 2).sum(axis=2))
    ink = dist > INK_DIST

    # Measure only inside the safe area: a dashed safe-area guide or a caption
    # band is not the scene's content.
    inner = np.zeros_like(ink)
    inner[T:B, L:R] = ink[T:B, L:R]

    col_ct, row_ct = inner.sum(axis=0), inner.sum(axis=1)
    cols = np.flatnonzero(col_ct >= MIN_RUN)
    rows = np.flatnonzero(row_ct >= MIN_RUN)
    if cols.size == 0 or rows.size == 0:
        return {"file": png.name, "blank": True}

    x0, x1 = int(cols[0]), int(cols[-1])
    y0, y1 = int(rows[0]), int(rows[-1])
    safe_w, safe_h = R - L, B - T

    margins = {"left": x0 - L, "right": R - x1, "top": y0 - T, "bottom": B - y1}
    return {
        "file": png.name,
        "blank": False,
        "bg": "#%02X%02X%02X" % tuple(int(v) for v in bg),
        "bbox": [x0, y0, x1 - x0, y1 - y0],
        "hspread": round((x1 - x0) / safe_w, 3),
        "vspread": round((y1 - y0) / safe_h, 3),
        "fill": round(((x1 - x0) * (y1 - y0)) / (safe_w * safe_h), 3),
        "margins": margins,
        # 🔴 A NEGATIVE MARGIN IS NOT SKEW, IT IS AN OVERSHOOT — and conflating
        # them cost a real diagnosis. Two templates reported a 92-152px "skew"
        # AFTER their layout was fixed, and both turned out to be ink drawn
        # OUTSIDE the safe margin on one side, not dead ground on the other.
        # Opposite defects, same number.
        "skew": abs(margins["left"] - margins["right"]),
        "overshoot": max(0, -min(margins["left"], margins["right"], margins["top"])),
        "dead_ground": safe_w - (x1 - x0),
    }


def verdict(m: dict, allow_overshoot: bool = False) -> list[str]:
    if m.get("blank"):
        return ["frame is blank inside the safe area"]
    fails = []
    if m["hspread"] < LIMITS["hspread_min"]:
        fails.append(
            f"hspread {m['hspread']:.2f} < {LIMITS['hspread_min']:.2f} "
            f"— {m['dead_ground']}px of safe width unused")
    if m["vspread"] < LIMITS["vspread_min"]:
        fails.append(f"vspread {m['vspread']:.2f} < {LIMITS['vspread_min']:.2f}")
    if not allow_overshoot and m["overshoot"] > LIMITS["overshoot_max"]:
        fails.append(f"ink {m['overshoot']}px outside the safe margin")
    return fails


def run(target: Path, caption_free: bool, allow_overshoot: bool,
        json_out: str | None) -> int:
    pngs = sorted(target.glob("*.png")) if target.is_dir() else [target]
    if not pngs:
        print(f"no PNGs found in {target}", file=sys.stderr)
        return 2

    records, failed = [], 0
    for png in pngs:
        m = measure(png, caption_free)
        fails = verdict(m, allow_overshoot)
        m["fails"] = fails
        records.append(m)
        mark = "FAIL" if fails else "pass"
        if m.get("blank"):
            print(f"{mark}  {m['file']}  (blank)")
        else:
            print(f"{mark}  {m['file']}  hspread {m['hspread']:.2f}  "
                  f"vspread {m['vspread']:.2f}  fill {m['fill']:.2f}  "
                  f"margins L{m['margins']['left']} R{m['margins']['right']}")
        for f in fails:
            print(f"        {f}")
        failed += bool(fails)

    if json_out:
        Path(json_out).write_text(json.dumps(records, indent=2))
        print(f"\nwrote {json_out}")

    print(f"\n{len(pngs) - failed}/{len(pngs)} passed")
    return 1 if failed else 0


def _synth(path: Path, content_w: int) -> None:
    """A frame with a content band of a given width, centred in the safe area.

    The band spans 150..700 vertically — inside the safe area and tall enough to
    clear `vspread_min`, so the only thing these fixtures vary is WIDTH. (The
    first version was 300px tall, which failed vspread and made the full-width
    fixture look like a false positive. The fixture was wrong, not the gate.)
    """
    a = np.full((FRAME_H, FRAME_W, 3), 18, dtype=np.uint8)
    cx = (SAFE["left"] + SAFE["right"]) // 2
    x0, x1 = cx - content_w // 2, cx + content_w // 2
    a[150:700, x0:x1] = 240
    Image.fromarray(a).save(path)


def self_test() -> int:
    """A gate that cannot fire reports PASS. Prove this one fires."""
    failures = []
    safe_w = SAFE["right"] - SAFE["left"]  # 1680
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        wide = tmp / "wide.png"
        _synth(wide, safe_w)
        m = measure(wide)
        if verdict(m):
            failures.append(f"full-width frame FAILED (false positive): {verdict(m)}")
        if m["hspread"] < 0.98:
            failures.append(f"full-width frame measured hspread {m['hspread']}, expected ~1.00")

        # 1280 of 1680 is the real defect the audit found: min(400, fair share)
        # on a three-step chain. Expected hspread 0.76.
        narrow = tmp / "narrow.png"
        _synth(narrow, 1280)
        m = measure(narrow)
        if not verdict(m):
            failures.append("1280-of-1680 frame PASSED — the gate cannot fire")
        if not (0.74 <= m["hspread"] <= 0.78):
            failures.append(f"1280-of-1680 measured hspread {m['hspread']}, expected ~0.76")

        # The worst frame in the audit: 47% of the safe width.
        worst = tmp / "worst.png"
        _synth(worst, int(safe_w * 0.47))
        m = measure(worst)
        if not verdict(m):
            failures.append("47%-width frame PASSED — the gate cannot fire")

        blank = tmp / "blank.png"
        Image.fromarray(np.full((FRAME_H, FRAME_W, 3), 18, dtype=np.uint8)).save(blank)
        if not verdict(measure(blank)):
            failures.append("blank frame PASSED — the gate cannot fire")

    if failures:
        print("SELF-TEST FAILED:")
        for f in failures:
            print("  ✗", f)
        return 2
    print("self-test OK — full-width passes; 0.76, 0.47 and blank all FAIL as they must")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", help="a PNG, or a directory of PNGs")
    ap.add_argument("--caption-free", action="store_true",
                    help="project ships no caption lane; the safe area runs 202px lower")
    ap.add_argument("--allow-overshoot", action="store_true",
                    help="full-bleed composite: ink outside the safe margin is the picture")
    ap.add_argument("--json", dest="json_out", help="write the full per-frame record here")
    ap.add_argument("--self-test", action="store_true",
                    help="prove the gate can fail, then exit")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.path:
        ap.error("give a PNG or a directory, or --self-test")
    return run(Path(args.path), args.caption_free, args.allow_overshoot, args.json_out)


if __name__ == "__main__":
    raise SystemExit(main())
