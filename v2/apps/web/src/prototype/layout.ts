export type SlotId = "bridge_left" | "bridge_right";

export interface Cell {
  x: number;
  z: number;
}

export interface SlotRect {
  x: number;
  z: number;
  w: number;
  d: number;
}

export const WORKSHOP = {
  tableWidth: 18,
  tableDepth: 14,
  cube: 1,
  gap: 0.08,
  piles: {
    ten_a: { x: 2, z: 2 },
    ten_b: { x: 7, z: 2 },
    six: { x: 12, z: 2 },
  },
  slots: {
    bridge_left: { x: 1, z: 8, w: 5, d: 4 },
    bridge_right: { x: 10, z: 8, w: 5, d: 4 },
  } satisfies Record<SlotId, SlotRect>,
  slotOrigin: {
    bridge_left: { x: 2, z: 9 },
    bridge_right: { x: 13, z: 9 },
  } satisfies Record<SlotId, Cell>,
} as const;

export function snapCell(worldX: number, worldZ: number): Cell {
  return { x: Math.round(worldX), z: Math.round(worldZ) };
}

export function cellsEqual(a: Cell, b: Cell): boolean {
  return a.x === b.x && a.z === b.z;
}

export function slotAt(cell: Cell): SlotId | null {
  for (const id of Object.keys(WORKSHOP.slots) as SlotId[]) {
    const rect = WORKSHOP.slots[id];
    if (
      cell.x >= rect.x &&
      cell.x < rect.x + rect.w &&
      cell.z >= rect.z &&
      cell.z < rect.z + rect.d
    ) {
      return id;
    }
  }
  return null;
}

export function groupFootprint(count: number, slot: SlotId | null): { w: number; d: number } {
  if (slot) {
    return { w: Math.max(1, count), d: 1 };
  }
  if (count >= 4) {
    const cols = Math.ceil(count / 2);
    return { w: cols, d: 2 };
  }
  return { w: Math.max(1, count), d: 1 };
}

export function unitLocalOffset(
  index: number,
  count: number,
  slot: SlotId | null,
): { x: number; z: number } {
  const stride = WORKSHOP.cube + WORKSHOP.gap;
  if (slot === "bridge_left") {
    return { x: index * stride, z: 0 };
  }
  if (slot === "bridge_right") {
    return { x: -index * stride, z: 0 };
  }
  if (count >= 4) {
    const cols = Math.ceil(count / 2);
    return { x: (index % cols) * stride, z: Math.floor(index / cols) * stride };
  }
  return { x: index * stride, z: 0 };
}

export function unitWorldPosition(
  origin: Cell,
  index: number,
  count: number,
  slot: SlotId | null,
): { x: number; y: number; z: number } {
  const local = unitLocalOffset(index, count, slot);
  return {
    x: origin.x + local.x,
    y: WORKSHOP.cube / 2,
    z: origin.z + local.z,
  };
}
