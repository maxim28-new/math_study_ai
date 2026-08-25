import { describe, expect, it } from "vitest";

import { orthoExtents, WORKSHOP_VIEW } from "../apps/web/src/scene/camera.ts";
import { isLandscapeInput, pickAngle, playSize, readChromeSize } from "../apps/web/src/scene/orientation.ts";
import { readPlayLayout, resolvePlayLayout } from "../apps/web/src/scene/viewport.ts";

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

  it("keeps forced landscape rotated while the browser window is still tall", () => {
    const first = playSize({ width: 390, height: 844, forced: true });
    const second = playSize({ width: 390, height: 844, forced: true });
    expect(first).toMatchObject({
      width: 844,
      height: 390,
      landscape: true,
      viewportStuck: true,
      rotate: "cw",
    });
    expect(second).toEqual(first);
  });

  it("does not rotate a desktop landscape window", () => {
    const layout = readPlayLayout({ width: 1280, height: 720 }, null);
    expect(layout.landscape).toBe(true);
    expect(layout.viewportStuck).toBe(false);
    expect(layout.rotate).toBeNull();
  });

  it("keeps forced rotate when CSS fake-landscape makes innerWidth look wide", () => {
    const portrait = { type: "portrait-primary" as const, angle: 0 };
    let last = readChromeSize({ width: 390, height: 844 }, false, null).lastPortrait;
    const afterClick = resolvePlayLayout(
      { width: 390, height: 844 },
      false,
      last,
      { orientation: portrait },
      { forced: true },
    );
    last = afterClick.lastPortrait;
    const afterSafariLie = resolvePlayLayout(
      { width: 844, height: 390 },
      true,
      last,
      { orientation: portrait },
      { forced: true, mediaLandscape: true },
    );
    expect(afterClick.layout).toMatchObject({
      width: 844,
      height: 390,
      landscape: true,
      viewportStuck: true,
      rotate: "cw",
    });
    expect(afterSafariLie.layout).toEqual(afterClick.layout);
  });

  it("drops CSS rotate once the device and window are both landscape", () => {
    const last = { width: 390, height: 844 };
    const layout = resolvePlayLayout(
      { width: 844, height: 390 },
      true,
      last,
      { orientation: { type: "landscape-primary", angle: 90 } },
      { forced: true, windowAngle: 90 },
    ).layout;
    expect(layout.viewportStuck).toBe(false);
    expect(layout.rotate).toBeNull();
    expect(layout.width).toBe(844);
    expect(layout.height).toBe(390);
  });
});
