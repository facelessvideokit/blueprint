import { Config } from "@remotion/cli/config";

/**
 * 🔴 PIN THE COLOUR SPACE — before a version bump makes it a surprise.
 *
 * Remotion 4 renders effectively bt601. **Remotion 5 changes the default to
 * bt709.** If your coded scenes are cut against stills you judged by eye, taking
 * the new default silently shifts the colour of half your timeline relative to
 * the other half — with no error anywhere to explain it, on a project whose
 * whole visual identity is a locked palette.
 *
 * Pinned rather than upgraded, because the right moment to move to bt709 is a
 * deliberate one with a frame open in the editor next to a still.
 *
 * Verified present in 4.0.513: `typeof Config.setColorSpace === "function"`.
 */
Config.setColorSpace("bt601");

/**
 * PNG, and it is NOT free — recorded so the cost is a decision rather than a
 * default.
 *
 * PNG buys exactly one thing: an alpha channel, which matters only for overlay
 * scenes. Every opaque scene is ProRes 422 HQ, which has no alpha, and pays the
 * PNG cost for nothing.
 *
 * Left on PNG deliberately, because the alternative has not been measured: JPEG
 * frames would be compressed *before* the ProRes encode, Remotion's default jpeg
 * quality is 80, and its chroma subsampling is undocumented. On a type-heavy
 * library full of hairlines, a measured speed-up is not worth an unmeasured
 * quality loss on the master. If you revisit this, A/B a gradient frame and a
 * fine-text frame — never switch on the timing alone.
 *
 * Note `setVideoImageFormat` does not affect `remotion still`, so preview PNGs
 * are unaffected either way.
 */
Config.setVideoImageFormat("png");
Config.setOverwriteOutput(true);
