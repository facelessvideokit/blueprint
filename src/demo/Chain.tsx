import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { Theme, FRAME, SAFE, SAFE_W, safeBottom, demo } from "../theme";
import { bodyBox, columns, midX, Rect } from "../lib/Layout";

/**
 * THE SAME SCENE, LAID OUT TWICE.
 *
 * `mode: "literal"` is how this template was written before the audit: a card
 * width capped at a pixel literal, then the row centred in the frame. It is not
 * a strawman — it is the real shape of the defect, `min(400, fair share)`.
 *
 * `mode: "derived"` asks `bodyBox()` and `columns()` instead.
 *
 * Both draw identical content. Render them side by side and the difference is
 * 400px of dead ground per side that nobody chose and no gate caught.
 */

export type ChainProps = { mode: "literal" | "derived"; theme?: Theme };

const STEPS = [
  { k: "COLLECTED", v: "1,284" },
  { k: "MATCHED", v: "911" },
  { k: "SETTLED", v: "417" },
];

const GAP = 48;

/** The pre-audit geometry, reproduced exactly: a cap, then centre what is left. */
const literalBoxes = (): Rect[] => {
  const fair = (SAFE_W - (STEPS.length - 1) * GAP) / STEPS.length;
  const w = Math.min(400, fair); // 🔴 the pixel literal — this is the whole bug
  const total = STEPS.length * w + (STEPS.length - 1) * GAP;
  const x0 = FRAME.w / 2 - total / 2;
  return STEPS.map((_, i) => ({
    x: x0 + i * (w + GAP), y: SAFE.top + 300, w, h: 300, // qc-allow-literal: this IS the defect, reproduced so it can be measured
  }));
};

export const Chain: React.FC<ChainProps> = ({ mode, theme }) => {
  const t = theme ?? demo;
  const frame = useCurrentFrame();

  const box = bodyBox(t);
  const boxes = mode === "derived"
    // Height as a FRACTION of the box, never a pixel literal — so it follows
    // safeBottom() and a caption-free project for free. That is rule 1.
    ? columns(box, STEPS.length, GAP).map((c) => ({
        ...c, h: Math.round(box.h * 0.68), y: box.y + 60,
      }))
    : literalBoxes();

  const spread = (boxes[boxes.length - 1].x + boxes[boxes.length - 1].w - boxes[0].x) / SAFE_W;
  const dead = Math.round(SAFE_W - (boxes[boxes.length - 1].x + boxes[boxes.length - 1].w - boxes[0].x));

  return (
    <div style={{ width: FRAME.w, height: FRAME.h, background: t.bg, position: "relative",
                  fontFamily: "Helvetica Neue, Helvetica, Arial, sans-serif" }}>

      {/* THE SAFE AREA, drawn 8px OUTSIDE its own bounds.
          🔴 It has to sit outside, and finding that out is half the lesson. Drawn
          ON the safe rect, this guide is ink spanning the full safe width, so
          qc_layout measured hspread 1.00 on BOTH modes and passed the broken one.
          A gate is only as honest as the frame handed to it: decoration that
          spans the area you are measuring destroys the measurement. */}
      <div style={{ position: "absolute", left: SAFE.left - 8, top: SAFE.top - 8,
                    width: SAFE_W + 16, height: safeBottom(t) - SAFE.top + 16,
                    border: `2px dashed ${t.grid}` }} />

      {/* Centred, so the header does not anchor the content bbox to the left
          margin and mask the very defect this scene exists to show. */}
      <div style={{ position: "absolute", left: 0, top: SAFE.top + 28,
                    width: FRAME.w, textAlign: "center" }}>
        <div style={{ color: t.mute, fontSize: 26, letterSpacing: 7, fontWeight: 600 }}>
          {mode === "literal" ? "BEFORE — CAPPED AT A PIXEL LITERAL" : "AFTER — DERIVED FROM THE BOX"}
        </div>
        <div style={{ color: t.fg, fontSize: 68, fontWeight: 700, marginTop: 10 }}>
          Where the claims went
        </div>
      </div>

      {boxes.map((b, i) => {
        const at = interpolate(frame - i * 8, [0, 18], [0, 1],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return (
          <div key={i} style={{
            position: "absolute", left: b.x, top: b.y, width: b.w, height: b.h,
            background: t.ink, borderRadius: 14,
            borderBottom: `6px solid ${t.accent}`,
            opacity: at, transform: `translateY(${(1 - at) * 24}px)`,
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
          }}>
            <div style={{ color: t.fg, fontSize: 96, fontWeight: 700 }}>{STEPS[i].v}</div>
            <div style={{ color: t.mute, fontSize: 30, letterSpacing: 5, marginTop: 12 }}>
              {STEPS[i].k}
            </div>
          </div>
        );
      })}

      {/* THE READOUT LIVES BELOW `safeBottom`, in the caption band.
          Same reason as the guide: it spans the full width by design, so inside
          the safe area it would be the widest ink on the frame and every scene
          would measure 1.00. The band is outside what qc_layout measures, which
          is exactly where a full-width annotation belongs. */}
      <div style={{
        position: "absolute", left: SAFE.left, top: safeBottom(t) + 46,
        width: SAFE_W, display: "flex", justifyContent: "space-between",
        color: mode === "literal" ? "#FF6B6B" : t.accent, fontSize: 32, fontWeight: 600,
      }}>
        <span>horizontal spread {spread.toFixed(2)}</span>
        <span>{dead}px of safe width unused</span>
      </div>

      {/* Even a caption is sized off the box, not off a number someone liked. */}
      <div style={{
        position: "absolute", left: midX(box) - box.w * 0.18, top: safeBottom(t) + 112,
        width: box.w * 0.36, textAlign: "center",
        color: t.mute, fontSize: 24, letterSpacing: 4,
      }}>
        {mode === "literal" ? "min(400, fairShare)" : "columns(bodyBox(t), 3, 48)"}
      </div>
    </div>
  );
};
