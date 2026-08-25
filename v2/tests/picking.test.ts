import { describe, expect, it } from "vitest";

import {
  clientToLocal,
  invertCenterDelta,
  ndcFromLocal,
  parseCssMatrix,
} from "../apps/web/src/scene/picking.ts";

describe("forced-landscape picking", () => {
  it("maps the visual center back to the layout center after rotate+scale", () => {
    const sx = 844 / 390;
    const sy = 390 / 844;
    // rotate(90deg) scale(sx, sy): x' = -sy*y, y' = sx*x
    const matrix = { a: 0, b: sx, c: -sy, d: 0 };
    const visual = { left: 0, top: 0, width: 390, height: 844 };
    const local = clientToLocal(195, 422, visual, 390, 844, matrix);
    expect(local.x).toBeCloseTo(195, 5);
    expect(local.y).toBeCloseTo(422, 5);
    const ndc = ndcFromLocal(local.x, local.y, 390, 844);
    expect(ndc.x).toBeCloseTo(0, 5);
    expect(ndc.y).toBeCloseTo(0, 5);
  });

  it("inverts a CSS matrix() string", () => {
    expect(parseCssMatrix("none")).toBeNull();
    expect(parseCssMatrix("matrix(0, 2, -0.5, 0, 0, 0)")).toEqual({
      a: 0,
      b: 2,
      c: -0.5,
      d: 0,
    });
    expect(parseCssMatrix("matrix3d(0, 2, 0, 0, -0.5, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)")).toEqual({
      a: 0,
      b: 2,
      c: -0.5,
      d: 0,
    });
    const restored = invertCenterDelta(0, 2, { a: 0, b: 2, c: -0.5, d: 0 });
    expect(restored.x).toBeCloseTo(1, 5);
    expect(restored.y).toBeCloseTo(0, 5);
  });
});
