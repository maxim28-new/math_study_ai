export const GESTURE = {
  pendingDragPx: 8,
  splitHandleWorld: 0.62,
  hitPadding: 0.35,
} as const;

export type GestureIntent = "group" | "split_handle";

export type GestureState =
  | { phase: "idle" }
  | { phase: "pending_drag"; intent: GestureIntent; groupId: string }
  | { phase: "dragging_group"; groupId: string }
  | { phase: "choosing_split"; groupId: string }
  | { phase: "focused_group"; groupId: string };

export type GestureEvent =
  | { type: "pointer_down"; intent: GestureIntent; groupId: string }
  | { type: "pointer_down_empty" }
  | { type: "pointer_move"; moved: boolean }
  | { type: "pointer_up" }
  | { type: "pointer_cancel" };

export function movementExceeded(
  dx: number,
  dy: number,
  threshold = GESTURE.pendingDragPx,
): boolean {
  return dx * dx + dy * dy >= threshold * threshold;
}

export function splitTakeFromDelta(
  alongWorld: number,
  count: number,
  stride = 1.08,
): number {
  if (count <= 1) {
    return 0;
  }
  const raw = Math.round(Math.abs(alongWorld) / stride);
  return Math.min(count - 1, Math.max(1, raw < 1 ? 1 : raw));
}

export function reduceGesture(state: GestureState, event: GestureEvent): GestureState {
  if (event.type === "pointer_cancel") {
    if (state.phase === "idle") {
      return state;
    }
    if ("groupId" in state) {
      return { phase: "focused_group", groupId: state.groupId };
    }
    return { phase: "idle" };
  }

  if (event.type === "pointer_down_empty") {
    return { phase: "idle" };
  }

  if (event.type === "pointer_down") {
    return { phase: "pending_drag", intent: event.intent, groupId: event.groupId };
  }

  if (event.type === "pointer_move" && state.phase === "pending_drag" && event.moved) {
    if (state.intent === "split_handle") {
      return { phase: "choosing_split", groupId: state.groupId };
    }
    return { phase: "dragging_group", groupId: state.groupId };
  }

  if (event.type === "pointer_up") {
    if (state.phase === "pending_drag") {
      return { phase: "focused_group", groupId: state.groupId };
    }
    if (state.phase === "dragging_group" || state.phase === "choosing_split") {
      return { phase: "focused_group", groupId: state.groupId };
    }
    return state;
  }

  return state;
}
