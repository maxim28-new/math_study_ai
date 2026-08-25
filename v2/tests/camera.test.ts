import { describe, expect, it } from "vitest";

import { orthoExtents, WORKSHOP_VIEW } from "../apps/web/src/scene/camera.ts";
import { isLandscapeInput, pickAngle, pickWidestPair, playSize } from "../apps/web/src/scene/orientation.ts";
import { readPlayLayout } from "../apps/web/src/scene/viewport.ts";

describe("workshop camera fit", () => {
  it("keeps a phone landscape view zoomed in so the table fills the short side", () => {
    const view = orthoExtents(844 / 390);
    expect(view.halfHeight).toBe(WORKSHOP_VIEW.halfHeight);
    expect(view.halfWidth).toBeCloseTo(WORKSHOP_VIEW.halfHeight * (844 / 390));
  });
});

describe("device orientation", () => {
  it("does not let a stale portrait type hide a landscape window", () => {
    expect(isLandscapeInput({ type: "portrait-primary", width: 844, height: 390 })).toBe(true);
    expect(isLandscapeInput({ type: "portrait-primary", angle: 0, width: 390, height: 844 })).toBe(false);
    expect(isLandscapeInput({ type: "portrait-primary", angle: 90, width: 390, height: 844 })).toBe(true);
    expect(isLandscapeInput({ type: "portrait-primary", width: 390, height: 844, mediaLandscape: true })).toBe(true);
    expect(isLandscapeInput({ type: "portrait-primary", width: 390, height: 844, forced: true })).toBe(true);
  });

  it("prefers a landscape window.orientation over a 0 screen angle", () => {
    expect(pickAngle(90, 0)).toBe(90);
    expect(pickAngle(undefined, 0)).toBe(0);
  });

  it("prefers the widest viewport pair so a stuck visualViewport cannot win", () => {
    expect(pickWidestPair([{ width: 390, height: 844 }, { width: 844, height: 390 }])).toEqual({
      width: 844,
      height: 390,
    });
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
    const layout = readPlayLayout([{ width: 1280, height: 720 }], null);
    expect(layout.landscape).toBe(true);
    expect(layout.viewportStuck).toBe(false);
    expect(layout.rotate).toBeNull();
  });
});
