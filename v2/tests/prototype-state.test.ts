import { describe, expect, it } from "vitest";

import {
  applyPrototypeCommand,
  createInitialPrototypeState,
  occupantOfSlot,
  prototypeIssues,
  restorePrototypeState,
  serializePrototypeState,
} from "../apps/web/src/prototype/state.ts";

function expectHealthy(state: ReturnType<typeof createInitialPrototypeState>): void {
  expect(prototypeIssues(state)).toEqual([]);
}

describe("InteractionPrototypeState", () => {
  it("starts with 26 unique units from 10, 10, and 6", () => {
    const state = createInitialPrototypeState();
    expectHealthy(state);
    const piles = Object.values(state.units).reduce(
      (acc, unit) => {
        acc[unit.sourcePile] += 1;
        return acc;
      },
      { ten_a: 0, ten_b: 0, six: 0 },
    );
    expect(piles).toEqual({ ten_a: 10, ten_b: 10, six: 6 });
    expect(Object.keys(state.groups)).toHaveLength(3);
  });

  it("round-trips through JSON", () => {
    const state = createInitialPrototypeState();
    const restored = restorePrototypeState(serializePrototypeState(state));
    expect(restored).toEqual(state);
    expectHealthy(restored);
  });

  it("moves a whole group without dropping units", () => {
    const start = createInitialPrototypeState();
    const result = applyPrototypeCommand(start, {
      type: "move_group",
      groupId: "group_six",
      cell: { x: 4, z: 4 },
    });
    expect(result.ok).toBe(true);
    if (!result.ok) {
      return;
    }
    expect(result.state.groups.group_six.cell).toEqual({ x: 4, z: 4 });
    expectHealthy(result.state);
    expect(start.groups.group_six.cell).toEqual({ x: 12, z: 2 });
  });

  it("splits a ten without losing or duplicating units", () => {
    const start = createInitialPrototypeState();
    const result = applyPrototypeCommand(start, {
      type: "split_group",
      groupId: "group_ten_a",
      take: 4,
      cell: { x: 3, z: 5 },
    });
    expect(result.ok).toBe(true);
    if (!result.ok) {
      return;
    }
    expect(result.state.groups.group_ten_a.unitIds).toHaveLength(6);
    expect(result.state.groups.group_1.unitIds).toHaveLength(4);
    expect(result.state.focusedGroupId).toBe("group_1");
    expectHealthy(result.state);
  });

  it("rejects a split that would empty the source", () => {
    const start = createInitialPrototypeState();
    const result = applyPrototypeCommand(start, {
      type: "split_group",
      groupId: "group_six",
      take: 6,
      cell: { x: 0, z: 0 },
    });
    expect(result).toEqual({ ok: false, reason: "invalid_split", state: start });
  });

  it("merges two groups into one collection", () => {
    const start = createInitialPrototypeState();
    const result = applyPrototypeCommand(start, {
      type: "merge_groups",
      fromId: "group_six",
      intoId: "group_ten_a",
    });
    expect(result.ok).toBe(true);
    if (!result.ok) {
      return;
    }
    expect(result.state.groups.group_ten_a.unitIds).toHaveLength(16);
    expect(result.state.groups.group_six).toBeUndefined();
    expectHealthy(result.state);
  });

  it("snaps a group onto an empty bridge slot", () => {
    const start = createInitialPrototypeState();
    const result = applyPrototypeCommand(start, {
      type: "place_on_slot",
      groupId: "group_ten_a",
      slot: "bridge_left",
    });
    expect(result.ok).toBe(true);
    if (!result.ok) {
      return;
    }
    expect(result.state.groups.group_ten_a.slot).toBe("bridge_left");
    expect(occupantOfSlot(result.state, "bridge_left")).toBe("group_ten_a");
    expectHealthy(result.state);
  });

  it("merges onto an occupied slot instead of dropping units", () => {
    const first = applyPrototypeCommand(createInitialPrototypeState(), {
      type: "place_on_slot",
      groupId: "group_ten_a",
      slot: "bridge_left",
    });
    expect(first.ok).toBe(true);
    if (!first.ok) {
      return;
    }
    const second = applyPrototypeCommand(first.state, {
      type: "place_on_slot",
      groupId: "group_six",
      slot: "bridge_left",
    });
    expect(second.ok).toBe(true);
    if (!second.ok) {
      return;
    }
    expect(second.state.groups.group_ten_a.unitIds).toHaveLength(16);
    expect(second.state.groups.group_six).toBeUndefined();
    expect(occupantOfSlot(second.state, "bridge_left")).toBe("group_ten_a");
    expectHealthy(second.state);
  });

  it("keeps the original state reference when a command fails", () => {
    const start = createInitialPrototypeState();
    const result = applyPrototypeCommand(start, {
      type: "focus",
      groupId: "group_missing",
    });
    expect(result.ok).toBe(false);
    expect(result.state).toBe(start);
  });
});
