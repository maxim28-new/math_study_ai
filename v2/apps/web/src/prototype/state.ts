import { groupFootprint, slotAt, WORKSHOP, type Cell, type SlotId } from "./layout.ts";

export type PrototypeUnitId = `unit_${number}`;
export type PrototypeGroupId = string;
export type SourcePile = "ten_a" | "ten_b" | "six";

export interface PrototypeUnit {
  id: PrototypeUnitId;
  sourcePile: SourcePile;
}

export interface PrototypeGroup {
  id: PrototypeGroupId;
  unitIds: PrototypeUnitId[];
  cell: Cell;
  slot: SlotId | null;
}

export interface InteractionPrototypeState {
  units: Record<PrototypeUnitId, PrototypeUnit>;
  groups: Record<PrototypeGroupId, PrototypeGroup>;
  focusedGroupId: PrototypeGroupId | null;
  nextGroupSerial: number;
}

export type PrototypeCommand =
  | { type: "focus"; groupId: PrototypeGroupId | null }
  | { type: "move_group"; groupId: PrototypeGroupId; cell: Cell }
  | { type: "split_group"; groupId: PrototypeGroupId; take: number; cell: Cell }
  | { type: "merge_groups"; fromId: PrototypeGroupId; intoId: PrototypeGroupId }
  | { type: "place_on_slot"; groupId: PrototypeGroupId; slot: SlotId };

export type ApplyResult =
  | { ok: true; state: InteractionPrototypeState }
  | { ok: false; reason: string; state: InteractionPrototypeState };

function cloneState(state: InteractionPrototypeState): InteractionPrototypeState {
  const groups: Record<PrototypeGroupId, PrototypeGroup> = {};
  for (const [id, group] of Object.entries(state.groups)) {
    groups[id] = {
      ...group,
      unitIds: [...group.unitIds],
      cell: { ...group.cell },
    };
  }
  return {
    units: { ...state.units },
    groups,
    focusedGroupId: state.focusedGroupId,
    nextGroupSerial: state.nextGroupSerial,
  };
}

function fail(state: InteractionPrototypeState, reason: string): ApplyResult {
  return { ok: false, reason, state };
}

function ok(state: InteractionPrototypeState): ApplyResult {
  return { ok: true, state };
}

function makeUnits(pile: SourcePile, start: number, count: number): PrototypeUnit[] {
  const units: PrototypeUnit[] = [];
  for (let i = 0; i < count; i += 1) {
    const id = `unit_${start + i}` as PrototypeUnitId;
    units.push({ id, sourcePile: pile });
  }
  return units;
}

export function createInitialPrototypeState(): InteractionPrototypeState {
  const tenA = makeUnits("ten_a", 1, 10);
  const tenB = makeUnits("ten_b", 11, 10);
  const six = makeUnits("six", 21, 6);
  const units: Record<PrototypeUnitId, PrototypeUnit> = {};
  for (const unit of [...tenA, ...tenB, ...six]) {
    units[unit.id] = unit;
  }
  return {
    units,
    groups: {
      group_ten_a: {
        id: "group_ten_a",
        unitIds: tenA.map((unit) => unit.id),
        cell: { ...WORKSHOP.piles.ten_a },
        slot: null,
      },
      group_ten_b: {
        id: "group_ten_b",
        unitIds: tenB.map((unit) => unit.id),
        cell: { ...WORKSHOP.piles.ten_b },
        slot: null,
      },
      group_six: {
        id: "group_six",
        unitIds: six.map((unit) => unit.id),
        cell: { ...WORKSHOP.piles.six },
        slot: null,
      },
    },
    focusedGroupId: null,
    nextGroupSerial: 1,
  };
}

export function prototypeIssues(state: InteractionPrototypeState): string[] {
  const issues: string[] = [];
  const unitIds = Object.keys(state.units);
  if (unitIds.length !== 26) {
    issues.push(`expected 26 units, got ${unitIds.length}`);
  }
  const seen = new Set<PrototypeUnitId>();
  for (const group of Object.values(state.groups)) {
    if (group.unitIds.length === 0) {
      issues.push(`empty group ${group.id}`);
    }
    const expectedSlot = slotAt(group.cell);
    if (group.slot !== expectedSlot) {
      issues.push(`group ${group.id} slot mismatch`);
    }
    for (const id of group.unitIds) {
      if (!state.units[id]) {
        issues.push(`missing unit ${id}`);
      }
      if (seen.has(id)) {
        issues.push(`duplicate unit ${id}`);
      }
      seen.add(id);
    }
  }
  if (seen.size !== unitIds.length) {
    issues.push("unowned or extra units");
  }
  if (state.focusedGroupId && !state.groups[state.focusedGroupId]) {
    issues.push("focused group missing");
  }
  return issues;
}

export function groupAtCell(
  state: InteractionPrototypeState,
  cell: Cell,
  except?: PrototypeGroupId,
): PrototypeGroupId | null {
  for (const group of Object.values(state.groups)) {
    if (group.id === except) {
      continue;
    }
    const footprint = groupFootprint(group.unitIds.length, group.slot);
    if (
      cell.x >= group.cell.x &&
      cell.x < group.cell.x + footprint.w &&
      cell.z >= group.cell.z &&
      cell.z < group.cell.z + footprint.d
    ) {
      return group.id;
    }
  }
  return null;
}

export function occupantOfSlot(
  state: InteractionPrototypeState,
  slot: SlotId,
  except?: PrototypeGroupId,
): PrototypeGroupId | null {
  for (const group of Object.values(state.groups)) {
    if (group.id !== except && group.slot === slot) {
      return group.id;
    }
  }
  return null;
}

function assignCell(group: PrototypeGroup, cell: Cell): void {
  group.cell = { ...cell };
  group.slot = slotAt(cell);
}

function requireGroup(
  state: InteractionPrototypeState,
  groupId: PrototypeGroupId,
): PrototypeGroup | null {
  return state.groups[groupId] ?? null;
}

function moveGroup(
  state: InteractionPrototypeState,
  groupId: PrototypeGroupId,
  cell: Cell,
): ApplyResult {
  const next = cloneState(state);
  const group = requireGroup(next, groupId);
  if (!group) {
    return fail(state, "unknown_group");
  }
  assignCell(group, cell);
  return ok(next);
}

function splitGroup(
  state: InteractionPrototypeState,
  groupId: PrototypeGroupId,
  take: number,
  cell: Cell,
): ApplyResult {
  const source = requireGroup(state, groupId);
  if (!source) {
    return fail(state, "unknown_group");
  }
  if (take < 1 || take >= source.unitIds.length) {
    return fail(state, "invalid_split");
  }
  const next = cloneState(state);
  const group = next.groups[groupId];
  const taken = group.unitIds.splice(group.unitIds.length - take, take);
  const newId = `group_${next.nextGroupSerial}`;
  next.nextGroupSerial += 1;
  next.groups[newId] = {
    id: newId,
    unitIds: taken,
    cell: { ...cell },
    slot: slotAt(cell),
  };
  next.focusedGroupId = newId;
  return ok(next);
}

function mergeGroups(
  state: InteractionPrototypeState,
  fromId: PrototypeGroupId,
  intoId: PrototypeGroupId,
): ApplyResult {
  if (fromId === intoId) {
    return fail(state, "same_group");
  }
  const next = cloneState(state);
  const from = requireGroup(next, fromId);
  const into = requireGroup(next, intoId);
  if (!from || !into) {
    return fail(state, "unknown_group");
  }
  into.unitIds.push(...from.unitIds);
  delete next.groups[fromId];
  if (next.focusedGroupId === fromId) {
    next.focusedGroupId = intoId;
  }
  return ok(next);
}

function placeOnSlot(
  state: InteractionPrototypeState,
  groupId: PrototypeGroupId,
  slot: SlotId,
): ApplyResult {
  const occupant = occupantOfSlot(state, slot, groupId);
  const origin = WORKSHOP.slotOrigin[slot];
  if (occupant) {
    const merged = mergeGroups(state, groupId, occupant);
    if (!merged.ok) {
      return merged;
    }
    return moveGroup(merged.state, occupant, origin);
  }
  return moveGroup(state, groupId, origin);
}

export function applyPrototypeCommand(
  state: InteractionPrototypeState,
  command: PrototypeCommand,
): ApplyResult {
  switch (command.type) {
    case "focus": {
      if (command.groupId && !state.groups[command.groupId]) {
        return fail(state, "unknown_group");
      }
      const next = cloneState(state);
      next.focusedGroupId = command.groupId;
      return ok(next);
    }
    case "move_group":
      return moveGroup(state, command.groupId, command.cell);
    case "split_group":
      return splitGroup(state, command.groupId, command.take, command.cell);
    case "merge_groups":
      return mergeGroups(state, command.fromId, command.intoId);
    case "place_on_slot":
      return placeOnSlot(state, command.groupId, command.slot);
    default: {
      const _never: never = command;
      return fail(state, `unknown_command:${JSON.stringify(_never)}`);
    }
  }
}

export function serializePrototypeState(state: InteractionPrototypeState): string {
  return JSON.stringify(state);
}

export function restorePrototypeState(raw: string): InteractionPrototypeState {
  return JSON.parse(raw) as InteractionPrototypeState;
}
