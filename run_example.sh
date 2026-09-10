#!/usr/bin/env bash
# The whole point, in one command: render two versions of the same scene, measure
# both, and build a timeline. The broken one FAILS the gate. That is the demo.
#
#   bash run_example.sh
#
# Exits non-zero at the end, on purpose — `Before` is supposed to fail.

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "── 1. prove the gates can fail ────────────────────────────────────────"
python3 plugin/tools/qc_layout.py --self-test   || exit 2
python3 tests/test_layout.py --self-test || exit 2

echo
echo "── 2. refuse a pixel literal in the source ────────────────────────────"
python3 tests/test_layout.py || exit 1

echo
echo "── 3. render the same scene twice ─────────────────────────────────────"
# Relative output paths, deliberately: Remotion splits an image-sequence output
# path on "." — an absolute path through a home directory with a dot in it fails.
npx remotion still Before out/before.png --frame=40 || exit 1
npx remotion still After  out/after.png  --frame=40 || exit 1

echo
echo "── 4. measure what was actually drawn ─────────────────────────────────"
python3 plugin/tools/qc_layout.py out/
QC=$?

echo
echo "── 5. build a Final Cut timeline and verify every path ────────────────"
python3 plugin/tools/make_fcpxml.py out/ --out out/timeline.fcpxml --seconds 4 || exit 1

echo
if [ "$QC" -ne 0 ]; then
  echo "✅ EXPECTED: 'Before' failed the layout gate and 'After' passed."
  echo "   Same content, same code, two geometries — and only one of them uses"
  echo "   the frame you are paying for. Nothing else in the toolchain notices."
  echo "   See WHY_THIS_EXISTS.md."
  exit 0
fi

echo "⚠️  'Before' PASSED the gate. That should not happen — the gate is not"
echo "   measuring what it claims to. See rule 3 in WHY_THIS_EXISTS.md."
exit 1
