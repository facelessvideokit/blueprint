#!/usr/bin/env python3
"""make_fcpxml.py — a still sequence to a Final Cut timeline, with the path check.

WHY THIS EXISTS
---------------
Assembling a timeline is the easy half. The half that costs a day is that an
FCPXML references its media by **absolute `file://` URL**, baked in at write
time from the writer's working directory.

🔴 THE FAILURE THIS PREVENTS. Run an assembler somewhere other than the machine
that will open the result — a container, a CI box, a VM with the project folder
mounted at a different path — and it writes that machine's paths. The XML is
perfectly valid. A verifier run *in the same place* reports zero missing media,
because from there the paths resolve. Then the editor opens it and **every clip
is red**. One project shipped 151 references that way before anyone noticed the
verifier had only ever been asked the question from the one place that could not
see the problem.

So: write the timeline where the media lives, and `--verify` every path against
the real filesystem before you hand the file over. That check is not a formality;
it is the entire lesson.

USAGE
    python3 tools/make_fcpxml.py out/ --out out/timeline.fcpxml --seconds 4
    python3 tools/make_fcpxml.py --verify out/timeline.fcpxml
    python3 tools/make_fcpxml.py --self-test

EXIT CODES
    0  written / verified clean
    1  a referenced path does not exist
    2  bad invocation

The full kit's assembler adds audio lanes, burned-in caption tracks, per-frame
timing from a beat map, and transitions. This writes a still sequence — which is
enough to prove the round trip end to end.
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

FPS = 30
W, H = 1920, 1080


def rational(seconds: float, fps: int = FPS) -> str:
    """FCPXML wants rational time. Integer frames only — a fractional frame is
    how you get a one-frame gap that nobody sees until the export."""
    return f"{int(round(seconds * fps))}/{fps}s"


def file_url(p: Path) -> str:
    return "file://" + quote(str(p.resolve()))


def build(pngs: list[Path], seconds: float, project: str) -> ET.ElementTree:
    fcpxml = ET.Element("fcpxml", version="1.10")
    resources = ET.SubElement(fcpxml, "resources")
    ET.SubElement(resources, "format", {
        "id": "r0", "name": f"FFVideoFormat1080p{FPS}",
        "frameDuration": f"1/{FPS}s", "width": str(W), "height": str(H),
        "colorSpace": "1-1-1 (Rec. 709)",
    })

    for i, png in enumerate(pngs, 1):
        asset = ET.SubElement(resources, "asset", {
            "id": f"a{i}", "name": png.stem, "start": "0s", "duration": "0s",
            "hasVideo": "1", "format": "r0", "videoSources": "1",
        })
        ET.SubElement(asset, "media-rep", {
            "kind": "original-media", "src": file_url(png),
        })

    library = ET.SubElement(fcpxml, "library")
    event = ET.SubElement(library, "event", name=project)
    proj = ET.SubElement(event, "project", name=project)
    total = rational(seconds * len(pngs))
    sequence = ET.SubElement(proj, "sequence", {
        "format": "r0", "duration": total, "tcStart": "0s", "tcFormat": "NDF",
    })
    spine = ET.SubElement(sequence, "spine")

    for i, png in enumerate(pngs, 1):
        ET.SubElement(spine, "video", {
            "ref": f"a{i}", "name": png.stem,
            "offset": rational(seconds * (i - 1)),
            "duration": rational(seconds), "start": "0s",
        })

    return ET.ElementTree(fcpxml)


def write(tree: ET.ElementTree, out: Path) -> None:
    ET.indent(tree, space="  ")
    out.write_bytes(
        b'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n'
        + ET.tostring(tree.getroot(), encoding="utf-8"))


def verify(path: Path) -> int:
    """Resolve every media-rep src against THIS filesystem."""
    root = ET.parse(path).getroot()
    reps = root.findall(".//media-rep")
    if not reps:
        print("no media-rep elements — nothing references any media", file=sys.stderr)
        return 1

    missing = []
    for rep in reps:
        src = rep.get("src", "")
        local = Path(unquote(urlparse(src).path))
        ok = local.is_file()
        print(f"{'ok  ' if ok else 'MISS'}  {local}")
        if not ok:
            missing.append(local)

    print(f"\n{len(reps) - len(missing)}/{len(reps)} references resolve")
    if missing:
        print("\n🔴 These paths do not exist ON THIS MACHINE. If you wrote this",
              file=sys.stderr)
        print("   timeline somewhere other than where the media lives, the editor",
              file=sys.stderr)
        print("   will show every clip as red. Re-write it beside the media.",
              file=sys.stderr)
        return 1
    return 0


def self_test() -> int:
    """Plant the exact failure this tool exists to catch, and assert it fires.

    The claim in the README is that every tool here ships a self-test that
    plants a real violation. This one was missing it, which is the same class of
    bug it warns about: the verifier had only ever been asked the question from
    the one place that could not see the problem.

    So: build a real timeline over real files, verify it clean, then move the
    media out from under it — exactly what happens when a timeline is written on
    one machine and opened on another — and assert the verifier FAILS.
    """
    import contextlib
    import io
    import shutil
    import tempfile

    def quiet(fn, *a):
        """Run a reporter without its report. The verdict below is the output."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            return fn(*a)

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        media = tmp / "media"
        media.mkdir()
        # A 1x1 PNG is enough: nothing here reads pixels, only paths.
        blank = bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000a49444154789c6360000002000100"
            "05fe02fea7c2b3060000000049454e44ae426082")
        for name in ("a.png", "b.png"):
            (media / name).write_bytes(blank)

        timeline = media / "timeline.fcpxml"
        write(build(sorted(media.glob("*.png")), 4.0, "self-test"), timeline)

        if not timeline.is_file():
            return _st_fail(["the timeline was not written at all"])

        # 1. the clean case must PASS, or the refusal below proves nothing
        if quiet(verify, timeline) != 0:
            failures.append("a timeline written beside its media did NOT verify "
                            "clean — the known-good case is broken, so nothing "
                            "this test does afterwards can be trusted")

        # 2. every reference must be absolute — that is the whole trap
        text = timeline.read_text(encoding="utf-8")
        if 'src="file:///' not in text:
            failures.append("references are not absolute file:// URLs — the "
                            "portability trap this tool warns about is not "
                            "even present, so --verify measures nothing")

        # 3. move the media out from under it: the timeline is still valid XML
        #    and every path is now wrong. This is the 151-red-clips failure.
        moved = tmp / "somewhere_else"
        moved.mkdir()
        stranded = moved / "timeline.fcpxml"
        shutil.copy2(timeline, stranded)
        for name in ("a.png", "b.png"):
            shutil.move(str(media / name), str(moved / name))
        try:
            ET.parse(stranded)
        except ET.ParseError as exc:
            failures.append(f"the stranded timeline is not valid XML ({exc}) — "
                            "it must be, or the failure is caught by the parser "
                            "rather than by this gate")
        if quiet(verify, stranded) == 0:
            failures.append("verify() reported CLEAN on a timeline whose media "
                            "had been moved away — the gate cannot fire")

    if failures:
        return _st_fail(failures)
    print("self-test OK — a timeline beside its media verifies clean; "
          "references are absolute; moving the media away FAILS as it must")
    return 0


def _st_fail(msgs: list[str]) -> int:
    print("SELF-TEST FAILED:")
    for m in msgs:
        print("  \u2717", m)
    print("\nA gate that cannot fire reports PASS.")
    return 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?",
                    help="a directory of PNGs, or an .fcpxml with --verify")
    ap.add_argument("--out", help="where to write the .fcpxml")
    ap.add_argument("--seconds", type=float, default=4.0, help="seconds per still")
    ap.add_argument("--project", default="Faceless Video Kit Blueprint")
    ap.add_argument("--verify", action="store_true",
                    help="check an existing .fcpxml's paths against this filesystem")
    ap.add_argument("--self-test", action="store_true",
                    help="plant the failure this tool prevents, and prove it fires")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.path:
        ap.error("give a path, or --self-test")

    target = Path(args.path)
    if args.verify:
        if not target.is_file():
            print(f"not a file: {target}", file=sys.stderr)
            return 2
        return verify(target)

    if not target.is_dir():
        print(f"not a directory: {target}", file=sys.stderr)
        return 2
    pngs = sorted(target.glob("*.png"))
    if not pngs:
        print(f"no PNGs in {target}", file=sys.stderr)
        return 2
    if not args.out:
        ap.error("--out is required when writing")

    out = Path(args.out)
    write(build(pngs, args.seconds, args.project), out)
    print(f"wrote {out}  ({len(pngs)} stills, {args.seconds}s each, "
          f"{args.seconds * len(pngs):.0f}s total)")
    print("\nverifying the paths it just baked in:")
    return verify(out)


if __name__ == "__main__":
    raise SystemExit(main())
