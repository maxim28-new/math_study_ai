import { describe, expect, it } from "vitest";

import {
  clientToLocal,
  invertCenterDelta,
  ndcFromLocal,
  parseCssMatrix,
} from "../apps/web/src/scene/picking.ts";

describe("forced-landscape picking", () => {
  it("maps the visual center back to the layout center after a uniform 90deg rotate", () => {
    // rotate(90deg): x' = -y, y' = x
    const matrix = { a: 0, b: 1, c: -1, d: 0 };
    const visual = { left: 0, top: 0, width: 390, height: 844 };
    const local = clientToLocal(195, 422, visual, 844, 390, matrix);
    expect(local.x).toBeCloseTo(422, 5);
    expect(local.y).toBeCloseTo(195, 5);
    const ndc = ndcFromLocal(local.x, local.y, 844, 390);
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
