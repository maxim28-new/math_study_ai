import { describe, expect, it } from "vitest";

import { clientToNdc } from "../apps/web/src/scene/picking.ts";
import {
  GESTURE,
  movementExceeded,
  reduceGesture,
  splitTakeFromDelta,
  type GestureState,
} from "../apps/web/src/scene/gestures.ts";

describe("gesture thresholds", () => {
  it("keeps taps under 8px pending", () => {
    expect(movementExceeded(3, 4)).toBe(false);
    expect(movementExceeded(GESTURE.pendingDragPx, 0)).toBe(true);
  });

  it("peels at least one unit and never the whole group", () => {
    expect(splitTakeFromDelta(0.2, 10)).toBe(1);
    expect(splitTakeFromDelta(3.2, 10)).toBe(3);
    expect(splitTakeFromDelta(40, 10)).toBe(9);
    expect(splitTakeFromDelta(8, 1)).toBe(0);
  });
});

describe("gesture state machine", () => {
  it("turns a still tap into focus, not a drag", () => {
    let state: GestureState = { phase: "idle" };
    state = reduceGesture(state, { type: "pointer_down", intent: "group", groupId: "group_ten_a" });
    state = reduceGesture(state, { type: "pointer_move", moved: false });
    state = reduceGesture(state, { type: "pointer_up" });
    expect(state).toEqual({ phase: "focused_group", groupId: "group_ten_a" });
  });

  it("starts a whole-group drag only after the threshold", () => {
    let state: GestureState = { phase: "idle" };
    state = reduceGesture(state, { type: "pointer_down", intent: "group", groupId: "group_six" });
    state = reduceGesture(state, { type: "pointer_move", moved: true });
    expect(state).toEqual({ phase: "dragging_group", groupId: "group_six" });
  });

  it("uses the split handle path without colliding with group drag", () => {
    let state: GestureState = { phase: "focused_group", groupId: "group_ten_a" };
    state = reduceGesture(state, {
      type: "pointer_down",
      intent: "split_handle",
      groupId: "group_ten_a",
    });
    state = reduceGesture(state, { type: "pointer_move", moved: true });
    expect(state).toEqual({ phase: "choosing_split", groupId: "group_ten_a" });
  });

  it("does not drop the group on pointer cancel", () => {
    let state: GestureState = { phase: "idle" };
    state = reduceGesture(state, { type: "pointer_down", intent: "group", groupId: "group_ten_b" });
    state = reduceGesture(state, { type: "pointer_move", moved: true });
    state = reduceGesture(state, { type: "pointer_cancel" });
    expect(state).toEqual({ phase: "focused_group", groupId: "group_ten_b" });
  });
});

describe("picking helpers", () => {
  it("maps client pixels to NDC without depending on the camera", () => {
    const ndc = clientToNdc(75, 25, { left: 50, top: 0, width: 100, height: 100 });
    expect(ndc.x).toBeCloseTo(-0.5);
    expect(ndc.y).toBeCloseTo(0.5);
  });
});
