/**
 * The frame, and the six numbers every layout decision hangs off.
 *
 * This is the minimum a template needs to know about the picture it is drawing
 * into. In the full kit `theme.ts` also carries palettes, type scales and the
 * legibility floors; none of that is needed to demonstrate the geometry rules,
 * so none of it is here.
 */

export type Theme = {
  key: string;
  bg: string;
  ink: string;
  fg: string;
  mute: string;
  grid: string;
  accent: string;
  /**
   * TRUE when this video ships no burned-in caption layer.
   *
   * The frame reserves a band at the bottom for captions on a separate editor
   * lane. A project that ships no captions should get that height back — and
   * the only way a template can see it is by asking `safeBottom(t)` instead of
   * reading `SAFE.bottom` directly. That is rule 2.
   */
  captionFree?: boolean;
};

export const FRAME = { w: 1920, h: 1080 };

/** 242px at the bottom of the frame, reserved for a caption lane in the editor. */
export const CAPTION_BAND = { top: 838, bottom: 1080 };

export const SAFE = {
  top: 64,
  bottom: CAPTION_BAND.top - 24, // 814 — templates lay out above this
  left: 120,
  right: FRAME.w - 120,
};

export const SAFE_W = SAFE.right - SAFE.left; // 1680
export const SAFE_H = SAFE.bottom - SAFE.top; // 750

/**
 * The lowest y a template may lay out to.
 *
 * 🔴 ASK THIS, NEVER READ `SAFE.bottom` DIRECTLY. A caption-free project gets
 * 202px of height back here, and a template holding a literal `814` cannot see
 * it. On a nine-tier hierarchy that is the difference between 83px per tier and
 * 105px per tier — which is the difference between a label that reads at feed
 * size and one that does not.
 */
export const safeBottom = (t: Theme): number =>
  t.captionFree ? FRAME.h - 64 : SAFE.bottom;

/** A neutral theme, so the demo renders without any brand attached to it. */
export const demo: Theme = {
  key: "demo",
  bg: "#12141A",
  ink: "#2A2F3A",
  fg: "#F2F4F8",
  mute: "#8A93A6",
  grid: "#232833",
  accent: "#4CC2FF",
};
