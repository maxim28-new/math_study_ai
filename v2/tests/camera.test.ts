import { describe, expect, it } from "vitest";

import { orthoExtents, WORKSHOP_VIEW } from "../apps/web/src/scene/camera.ts";
import { readViewportSize } from "../apps/web/src/scene/viewport.ts";

describe("workshop camera fit", () => {
  it("keeps the table width visible on a phone portrait aspect", () => {
    const view = orthoExtents(390 / 844);
    expect(view.halfWidth).toBe(WORKSHOP_VIEW.minHalfWidth);
    expect(view.halfHeight).toBeCloseTo(WORKSHOP_VIEW.minHalfWidth / (390 / 844));
  });

  it("does not zoom out a landscape tablet more than needed", () => {
    const view = orthoExtents(1.4);
    expect(view.halfHeight).toBe(WORKSHOP_VIEW.minHalfHeight);
    expect(view.halfWidth).toBeCloseTo(WORKSHOP_VIEW.minHalfHeight * 1.4);
  });
});

describe("viewport size", () => {
  it("prefers the visual viewport so iOS rotation is not stuck on the first paint", () => {
    const size = readViewportSize(
      { clientWidth: 390, clientHeight: 844 },
      { width: 844, height: 390 },
    );
    expect(size).toEqual({ width: 844, height: 390 });
  });

  it("falls back to the canvas box when visual viewport is missing", () => {
    const size = readViewportSize({ clientWidth: 1024, clientHeight: 768 }, null);
    expect(size).toEqual({ width: 1024, height: 768 });
  });
});
