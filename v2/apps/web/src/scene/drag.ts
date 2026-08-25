import * as THREE from "three";

import { slotAt, snapCell, type Cell } from "../prototype/layout.ts";
import {
  applyPrototypeCommand,
  groupAtCell,
  type InteractionPrototypeState,
  type PrototypeCommand,
} from "../prototype/state.ts";
import {
  movementExceeded,
  reduceGesture,
  splitTakeFromDelta,
  type GestureState,
} from "./gestures.ts";
import {
  clientToLocal,
  clientToNdc,
  ndcFromLocal,
  parseCssMatrix,
  pickEntity,
  worldPointOnTable,
  type EntityHit,
} from "./picking.ts";
import type { DragVisual } from "./renderer.ts";

interface DragControllerOptions {
  canvas: HTMLCanvasElement;
  camera: THREE.Camera;
  pickRoots: () => THREE.Object3D[];
  getState: () => InteractionPrototypeState;
  setState: (state: InteractionPrototypeState) => void;
  onVisual: (visual: DragVisual | null) => void;
}

interface PointerSession {
  pointerId: number;
  startX: number;
  startY: number;
  origin: Cell;
}

export function bindWorkshopDrag(options: DragControllerOptions): () => void {
  const { canvas } = options;
  const raycaster = new THREE.Raycaster();
  let gesture: GestureState = { phase: "idle" };
  let session: PointerSession | null = null;

  const ndcAt = (clientX: number, clientY: number): THREE.Vector2 => {
    const stage = canvas.parentElement;
    if (!stage) {
      return clientToNdc(clientX, clientY, canvas.getBoundingClientRect());
    }
    const matrix = parseCssMatrix(getComputedStyle(stage).transform);
    const local = clientToLocal(
      clientX,
      clientY,
      stage.getBoundingClientRect(),
      stage.clientWidth,
      stage.clientHeight,
      matrix,
    );
    return ndcFromLocal(local.x, local.y, stage.clientWidth, stage.clientHeight);
  };

  const hitAt = (clientX: number, clientY: number): EntityHit | null => {
    return pickEntity(raycaster, options.camera, ndcAt(clientX, clientY), options.pickRoots());
  };

  const cellAt = (clientX: number, clientY: number): Cell | null => {
    const point = tablePoint(clientX, clientY);
    return point ? snapCell(point.x, point.z) : null;
  };

  const tablePoint = (clientX: number, clientY: number): THREE.Vector3 | null => {
    return worldPointOnTable(raycaster, options.camera, ndcAt(clientX, clientY), 0);
  };

  const dispatch = (command: PrototypeCommand): void => {
    const result = applyPrototypeCommand(options.getState(), command);
    if (result.ok) {
      options.setState(result.state);
    }
  };

  const clearVisual = (): void => {
    options.onVisual(null);
  };

  const onPointerDown = (event: PointerEvent): void => {
    if (session) {
      return;
    }
    canvas.setPointerCapture(event.pointerId);
    const hit = hitAt(event.clientX, event.clientY);
    session = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      origin: cellAt(event.clientX, event.clientY) ?? { x: 0, z: 0 },
    };
    if (!hit || (hit.kind !== "group" && hit.kind !== "split_handle")) {
      gesture = reduceGesture(gesture, { type: "pointer_down_empty" });
      dispatch({ type: "focus", groupId: null });
      return;
    }
    const group = options.getState().groups[hit.id];
    if (group) {
      session.origin = { ...group.cell };
    }
    gesture = reduceGesture(gesture, {
      type: "pointer_down",
      intent: hit.kind === "split_handle" ? "split_handle" : "group",
      groupId: hit.id,
    });
  };

  const onPointerMove = (event: PointerEvent): void => {
    if (!session || session.pointerId !== event.pointerId) {
      return;
    }
    const moved = movementExceeded(event.clientX - session.startX, event.clientY - session.startY);
    gesture = reduceGesture(gesture, { type: "pointer_move", moved });
    if (gesture.phase === "dragging_group") {
      const point = tablePoint(event.clientX, event.clientY);
      if (!point) {
        return;
      }
      options.onVisual({
        groupId: gesture.groupId,
        worldX: point.x,
        worldZ: point.z,
        liftY: 0.38,
      });
      return;
    }
    if (gesture.phase === "choosing_split") {
      const point = tablePoint(event.clientX, event.clientY);
      const group = options.getState().groups[gesture.groupId];
      if (!point || !group) {
        return;
      }
      const along = group.slot === "bridge_right" ? session.origin.x - point.x : point.x - session.origin.x;
      options.onVisual({
        groupId: gesture.groupId,
        worldX: group.cell.x,
        worldZ: group.cell.z,
        liftY: 0,
        splitTake: splitTakeFromDelta(along, group.unitIds.length),
      });
    }
  };

  const finish = (event: PointerEvent, cancelled: boolean): void => {
    if (!session || session.pointerId !== event.pointerId) {
      return;
    }
    const current = gesture;
    gesture = reduceGesture(gesture, cancelled ? { type: "pointer_cancel" } : { type: "pointer_up" });
    if (!cancelled && current.phase === "pending_drag") {
      dispatch({ type: "focus", groupId: current.groupId });
    } else if (!cancelled && current.phase === "dragging_group") {
      commitDrag(current.groupId, cellAt(event.clientX, event.clientY) ?? session.origin);
    } else if (!cancelled && current.phase === "choosing_split") {
      commitSplit(current.groupId, event);
    } else if (cancelled && "groupId" in current) {
      dispatch({ type: "focus", groupId: current.groupId });
    }
    session = null;
    clearVisual();
    try {
      canvas.releasePointerCapture(event.pointerId);
    } catch {
      // Capture may already be gone after pointercancel.
    }
  };

  const commitDrag = (groupId: string, cell: Cell): void => {
    const state = options.getState();
    const slot = slotAt(cell);
    if (slot) {
      dispatch({ type: "place_on_slot", groupId, slot });
      return;
    }
    const other = groupAtCell(state, cell, groupId);
    if (other) {
      dispatch({ type: "merge_groups", fromId: groupId, intoId: other });
      return;
    }
    dispatch({ type: "move_group", groupId, cell });
  };

  const commitSplit = (groupId: string, event: PointerEvent): void => {
    const state = options.getState();
    const group = state.groups[groupId];
    if (!group) {
      return;
    }
    const point = tablePoint(event.clientX, event.clientY);
    if (!point) {
      return;
    }
    const along = group.slot === "bridge_right" ? group.cell.x - point.x : point.x - group.cell.x;
    const take = splitTakeFromDelta(along, group.unitIds.length);
    if (take < 1) {
      return;
    }
    const cell = snapCell(point.x, point.z);
    dispatch({ type: "split_group", groupId, take, cell });
  };

  const onLostCapture = (event: PointerEvent): void => {
    if (session && session.pointerId === event.pointerId) {
      finish(event, true);
    }
  };

  const preventScroll = (event: TouchEvent): void => {
    event.preventDefault();
  };

  const onPointerUp = (event: PointerEvent): void => finish(event, false);
  const onPointerCancel = (event: PointerEvent): void => finish(event, true);

  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("pointerup", onPointerUp);
  canvas.addEventListener("pointercancel", onPointerCancel);
  canvas.addEventListener("lostpointercapture", onLostCapture);
  canvas.addEventListener("touchmove", preventScroll, { passive: false });

  return () => {
    canvas.removeEventListener("pointerdown", onPointerDown);
    canvas.removeEventListener("pointermove", onPointerMove);
    canvas.removeEventListener("pointerup", onPointerUp);
    canvas.removeEventListener("pointercancel", onPointerCancel);
    canvas.removeEventListener("lostpointercapture", onLostCapture);
    canvas.removeEventListener("touchmove", preventScroll);
  };
}
