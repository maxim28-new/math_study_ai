import { describe, expect, it } from "vitest";

import { orthoExtents, WORKSHOP_VIEW } from "../apps/web/src/scene/camera.ts";
import { isLandscapeInput, playSize } from "../apps/web/src/scene/orientation.ts";
import { readPlayLayout } from "../apps/web/src/scene/viewport.ts";

describe("workshop camera fit", () => {
  it("keeps a phone landscape view zoomed in so the table fills the short side", () => {
    const view = orthoExtents(844 / 390);
    expect(view.halfHeight).toBe(WORKSHOP_VIEW.halfHeight);
    expect(view.halfWidth).toBeCloseTo(WORKSHOP_VIEW.halfHeight * (844 / 390));
  });
});

describe("device orientation", () => {
  it("treats a 90 degree phone tilt as landscape even if the page is still tall", () => {
    expect(isLandscapeInput({ type: "landscape-primary", width: 390, height: 844 })).toBe(true);
    expect(isLandscapeInput({ angle: 90, width: 390, height: 844 })).toBe(true);
    expect(isLandscapeInput({ angle: -90, width: 390, height: 844 })).toBe(true);
    expect(isLandscapeInput({ type: "portrait-primary", width: 844, height: 390 })).toBe(false);
  });

  it("swaps width and height when iOS keeps the first portrait viewport", () => {
    const layout = playSize({ angle: 90, width: 390, height: 844 });
    expect(layout).toMatchObject({
      width: 844,
      height: 390,
      landscape: true,
      viewportStuck: true,
      rotate: "cw",
    });
  });

  it("does not rotate a desktop landscape window", () => {
    const layout = readPlayLayout({ width: 1280, height: 720 }, null, null);
    expect(layout.landscape).toBe(true);
    expect(layout.viewportStuck).toBe(false);
    expect(layout.rotate).toBeNull();
  });
});
