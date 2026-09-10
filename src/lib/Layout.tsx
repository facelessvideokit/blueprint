import { Theme, SAFE, SAFE_W, safeBottom } from "../theme";

/**
 * WHERE A TEMPLATE'S BODY GOES — the rectangle, computed once.
 *
 * WHAT THE AUDIT FOUND. A layout audit measured all 39 rendered scenes of one
 * finished video. Eleven used under 90% of the safe width. One used **47%**,
 * with **886px of dead ground** on a single side. Seventeen carried text at
 * 3.0:1 contrast. Every existing gate was green.
 *
 * The cause was the same line written fourteen times, once per template, each
 * with its own constants:
 *
 *     grid template      cw = min(230, 1200 / cols),  ox = SAFE.left + 340
 *     ladder template    X = SAFE.left + 380,  W = 1000
 *     list template      X = SAFE.left + 120,  W = 1400
 *     window template    W = 1200, X = 960 - W / 2
 *     chain template     CW = min(400, fair share)
 *     flow template      BW = min(470, fair share)
 *     fork template      panels 600 wide at SX +/- 430
 *     timeline template  X0 = SAFE.left + 90, X1 = SAFE.right - 90
 *     table template     W = SAFE_W - 120, height capped at 470
 *     unit template      cols = ceil(sqrt(n * 1.9))  — an aspect that is not the box's
 *
 * Not one of those is wrong on its own. Together they mean the library holds
 * fourteen different opinions about how wide the frame is, and the widest of
 * them is 1400 of an available 1680.
 *
 * 🔴 **THE FRAME WAS NEVER THE CONSTRAINT. THE CONSTANTS WERE.**
 *
 * WHY A HELPER RATHER THAN FOURTEEN CORRECTED NUMBERS. Because corrected
 * numbers go stale the next time anything moves — and something always moves.
 * A caption-free project releases 202px of height, and a template holding a
 * literal `814` cannot see it. The win of a helper is that ONE edit reaches
 * every template at once.
 *
 * WHAT IT IS NOT. It is not a layout engine and it does not position anything.
 * It answers one question — *what rectangle may this scene's body occupy* — and
 * leaves the composition inside it entirely to the template.
 */

export type Rect = { x: number; y: number; w: number; h: number };

/**
 * The vertical a title block actually needs, MEASURED rather than chosen: it
 * sits at `SAFE.top + 28`, draws a kicker at up to 28px with 7px tracking, then
 * a 68px headline with `marginTop: 10`. 28 + 34 + 10 + 82 = 154, plus 46 of air
 * so a body element does not touch the headline's descenders.
 *
 * The fourteen templates it replaced reserved between 180 and 320 for the same
 * block. 200 is inside that range and above the tightest of them, so nothing
 * collides that did not collide before.
 */
export const TITLE_H = 200;

/**
 * A footer chip's height plus its stand-off: 16px padding top and bottom around
 * a line of at most 47px, plus the 8px it sits above `safeBottom`, plus 12 of air.
 */
export const SLUG_H = 110;

/**
 * THE BODY RECTANGLE — full safe width, between the title block and the footer.
 *
 * `title` and `slug` default TRUE because nearly every template draws both; pass
 * false where one is genuinely absent and the body gets that space back.
 * `reserve` takes further px off the bottom for a template that stacks something
 * of its own down there — a key, a legend.
 *
 * `titleH` overrides `TITLE_H` for a template that draws a taller header of its
 * own. Naming the number at the one call site that has it beats a second
 * constant here that would be right for one template and wrong for the rest.
 *
 * The bottom comes from `safeBottom(t)`, never a literal — which is where a
 * caption-free project's extra 202px arrives. Releasing that band buys nothing
 * if a template's own arithmetic cannot see it.
 */
export const bodyBox = (
  t: Theme,
  opts?: { title?: boolean; slug?: boolean; reserve?: number; titleH?: number },
): Rect => {
  const top = SAFE.top + (opts?.title === false ? 0 : (opts?.titleH ?? TITLE_H));
  const bottom = safeBottom(t)
    - (opts?.slug === false ? 0 : SLUG_H)
    - (opts?.reserve ?? 0);
  return { x: SAFE.left, y: top, w: SAFE_W, h: Math.max(120, bottom - top) };
};

/**
 * n EQUAL COLUMNS THAT SPAN THE WHOLE BOX. No cap, deliberately.
 *
 * 🔴 THE CAP IS THE DEFECT. One template had `min(400, fair share)` and another
 * `min(470, ...)`, so on the common three-step chain — the shape both templates
 * are FOR — the row came out 1280 wide inside 1680 and read as a centred island.
 * Measured horizontal spread: **0.76**.
 *
 * A cap is only right if a wide card is worse than dead ground, and it is not: a
 * two-step chain with 820px cards is a legible two-step chain, while 400px cards
 * either side of 800px of nothing looks unfinished. If a template genuinely must
 * bound a column, it must bound it as a FRACTION OF THE BOX so the bound moves
 * when the box does — never as a pixel literal.
 */
export const columns = (box: Rect, n: number, gap: number): Rect[] => {
  const w = (box.w - (n - 1) * gap) / Math.max(1, n);
  return Array.from({ length: n }, (_, i) => ({
    x: box.x + i * (w + gap), y: box.y, w, h: box.h,
  }));
};

/**
 * A LATTICE OF `n` MARKS THAT FILLS THE BOX.
 *
 * 🔴 The template this replaced chose its column count as `ceil(sqrt(n * 1.9))`:
 * a block "a little wider than tall", which is how a unit block is set in print
 * and has nothing to do with the box it is being set into. With 5 marks in a box
 * 1680 x 350 that gave 4 columns and 2 rows, a 175px cell, and a block **700px
 * wide inside 1680** — horizontal spread 0.70, with 506px of dead ground on one
 * side.
 *
 * The lattice's aspect should come from the BOX's aspect, so the marks grow to
 * fill whatever they are given. Same five marks, same box: 5 columns, 1 row, a
 * 336px cell, spanning the full width. The mark got 1.9x bigger for free — which
 * on a template whose whole argument is *the picture IS the number* is not
 * cosmetic.
 *
 * `cols` is still honoured when authored: a scene that says "ten across" means it.
 */
export const lattice = (
  box: Rect, n: number, authoredCols?: number,
): { cols: number; rows: number; cell: number; x: number; y: number; w: number; h: number } => {
  /* 🔴 SEARCHED, NOT SOLVED IN CLOSED FORM — and the first version of this fix is
     why. `cols = sqrt(n * aspect)` is the right shape and still gets it wrong at
     small n, because `rows = ceil(n / cols)` is a STEP function: for n = 5 in a
     1680x552 box it returns 4 columns and therefore 2 rows, one of which holds a
     single mark, and the cell comes out 276px. Five columns in one row gives
     336px and fills the width. The objective is simply the biggest cell, `n` is
     at most 400, and the loop is 400 iterations of two divisions — so ask every
     column count and take the best rather than approximating the answer. */
  const best = (): number => {
    if (Number(authoredCols)) return Math.max(1, Math.round(Number(authoredCols)));
    let pick = 1, size = -1;
    for (let c = 1; c <= n; c++) {
      const s = Math.min(box.w / c, box.h / Math.ceil(n / c));
      if (s > size) { size = s; pick = c; }
    }
    return pick;
  };
  const cols = best();
  const rows = Math.ceil(n / cols);
  const cell = Math.min(box.w / cols, box.h / rows);
  const w = cols * cell, h = rows * cell;
  return {
    cols, rows, cell,
    x: box.x + (box.w - w) / 2,
    y: box.y + Math.max(0, (box.h - h) / 2),
    w, h,
  };
};

/** The centre of a box, for a template that genuinely is symmetrical about one. */
export const midX = (box: Rect): number => box.x + box.w / 2;
