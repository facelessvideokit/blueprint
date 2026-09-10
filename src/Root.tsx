import React from "react";
import { Composition } from "remotion";
import { Chain } from "./demo/Chain";
import { FRAME } from "./theme";

/**
 * Two compositions, same content, two geometries.
 *
 *   npx remotion render Before out/before.png --frame=40
 *   npx remotion render After  out/after.png  --frame=40
 *
 * Then measure both with tools/qc_layout.py. `Before` fails; `After` passes.
 */
export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Before"
      component={Chain}
      durationInFrames={60}
      fps={30}
      width={FRAME.w}
      height={FRAME.h}
      defaultProps={{ mode: "literal" as const }}
    />
    <Composition
      id="After"
      component={Chain}
      durationInFrames={60}
      fps={30}
      width={FRAME.w}
      height={FRAME.h}
      defaultProps={{ mode: "derived" as const }}
    />
  </>
);
