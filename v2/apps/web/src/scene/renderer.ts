import * as THREE from "three";

import { groupFootprint, unitWorldPosition, WORKSHOP } from "../prototype/layout.ts";
import type { InteractionPrototypeState, PrototypeGroup } from "../prototype/state.ts";
import { GESTURE } from "./gestures.ts";

export interface DragVisual {
  groupId: string;
  worldX: number;
  worldZ: number;
  liftY: number;
  splitTake?: number;
}

const PILE_COLOR: Record<string, number> = {
  ten_a: 0xd4654a,
  ten_b: 0x2a8f88,
  six: 0xe3a53a,
};

const UNIT_COUNT = 26;

export class WorkshopRenderer {
  readonly scene = new THREE.Scene();
  readonly renderer: THREE.WebGLRenderer;
  readonly pickRoots: THREE.Object3D[] = [];

  private readonly cubes: THREE.InstancedMesh;
  private readonly dummy = new THREE.Object3D();
  private readonly tint = new THREE.Color();
  private readonly hitRoot = new THREE.Group();
  private readonly slotMeshes = new Map<string, THREE.Mesh>();
  private readonly splitHandle: THREE.Mesh;
  private readonly hitBoxes = new Map<string, THREE.Mesh>();
  private highlightedSlot: string | null = null;

  constructor(canvas: HTMLCanvasElement) {
    this.scene.background = new THREE.Color(0xb7c7d4);
    this.scene.fog = new THREE.Fog(0xb7c7d4, 28, 48);

    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    this.addLights();
    this.addWorkshop();

    const cubeGeo = new THREE.BoxGeometry(0.92, 0.92, 0.92);
    const cubeMat = new THREE.MeshStandardMaterial({
      roughness: 0.42,
      metalness: 0.04,
    });
    this.cubes = new THREE.InstancedMesh(cubeGeo, cubeMat, UNIT_COUNT);
    this.cubes.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.cubes.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(UNIT_COUNT * 3), 3);
    this.cubes.frustumCulled = false;
    this.scene.add(this.cubes);

    this.hitRoot.name = "hit-root";
    this.scene.add(this.hitRoot);
    this.pickRoots.push(this.hitRoot);

    const handleGeo = new THREE.BoxGeometry(0.34, 0.72, 0.72);
    const handleMat = new THREE.MeshStandardMaterial({
      color: 0xf4efe4,
      roughness: 0.55,
    });
    this.splitHandle = new THREE.Mesh(handleGeo, handleMat);
    this.splitHandle.visible = false;
    this.splitHandle.userData.entity = { kind: "split_handle", id: "" };
    this.hitRoot.add(this.splitHandle);
  }

  setSize(width: number, height: number): void {
    this.renderer.setSize(width, height, false);
  }

  render(camera: THREE.Camera): void {
    this.renderer.render(this.scene, camera);
  }

  dispose(): void {
    this.renderer.dispose();
    this.cubes.geometry.dispose();
    (this.cubes.material as THREE.Material).dispose();
    this.splitHandle.geometry.dispose();
    (this.splitHandle.material as THREE.Material).dispose();
  }

  sync(state: InteractionPrototypeState, visual: DragVisual | null): void {
    const groups = Object.values(state.groups);
    this.syncCubes(state, visual);
    this.syncHitBoxes(groups, visual);
    this.syncSplitHandle(state, visual);
    this.highlightSlot(visual ? slotUnderVisual(state, visual) : null);
  }

  private addLights(): void {
    const hemi = new THREE.HemisphereLight(0xfff3e0, 0x6d7d8a, 1.05);
    this.scene.add(hemi);
    const key = new THREE.DirectionalLight(0xfff1d2, 1.15);
    key.position.set(10, 18, 6);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0xc5d8ea, 0.35);
    fill.position.set(-8, 10, -6);
    this.scene.add(fill);
  }

  private addWorkshop(): void {
    const table = new THREE.Mesh(
      new THREE.BoxGeometry(WORKSHOP.tableWidth, 0.42, WORKSHOP.tableDepth),
      new THREE.MeshStandardMaterial({ color: 0xc4a06a, roughness: 0.82 }),
    );
    table.position.set(8, -0.21, 6);
    this.scene.add(table);

    const river = new THREE.Mesh(
      new THREE.BoxGeometry(2.4, 0.12, 5.2),
      new THREE.MeshStandardMaterial({ color: 0x3f86ad, roughness: 0.28 }),
    );
    river.position.set(8, 0.02, 9.4);
    this.scene.add(river);

    this.addSlot("bridge_left", 3.4, 9.4, 5.2);
    this.addSlot("bridge_right", 12.6, 9.4, 5.2);
  }

  private addSlot(id: string, x: number, z: number, width: number): void {
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(width, 0.28, 3.8),
      new THREE.MeshStandardMaterial({
        color: 0xb07a45,
        roughness: 0.55,
        emissive: 0x3a2412,
        emissiveIntensity: 0.35,
      }),
    );
    mesh.position.set(x, 0.14, z);
    mesh.userData.entity = { kind: "slot", id };
    this.scene.add(mesh);
    this.slotMeshes.set(id, mesh);
    this.pickRoots.push(mesh);
  }

  private syncCubes(state: InteractionPrototypeState, visual: DragVisual | null): void {
    let index = 0;
    for (const group of Object.values(state.groups)) {
      const origin = groupOrigin(group, visual);
      const count = group.unitIds.length;
      const splitTake = visual?.groupId === group.id ? visual.splitTake : undefined;
      for (let i = 0; i < count; i += 1) {
        const pos = unitWorldPosition(origin, i, count, group.slot);
        const peeling = splitTake !== undefined && i >= count - splitTake;
        this.dummy.position.set(pos.x, pos.y + (peeling ? 0.42 : 0) + extraLift(group, visual), pos.z);
        if (peeling) {
          this.dummy.position.x += group.slot === "bridge_right" ? -0.18 : 0.18;
        }
        this.dummy.rotation.set(0, 0, 0);
        this.dummy.updateMatrix();
        this.cubes.setMatrixAt(index, this.dummy.matrix);
        const unit = state.units[group.unitIds[i]];
        this.tint.set(PILE_COLOR[unit.sourcePile] ?? 0xcccccc);
        this.cubes.setColorAt(index, this.tint);
        index += 1;
      }
    }
    this.cubes.count = index;
    this.cubes.instanceMatrix.needsUpdate = true;
    if (this.cubes.instanceColor) {
      this.cubes.instanceColor.needsUpdate = true;
    }
  }

  private syncHitBoxes(groups: PrototypeGroup[], visual: DragVisual | null): void {
    const seen = new Set<string>();
    for (const group of groups) {
      seen.add(group.id);
      let box = this.hitBoxes.get(group.id);
      if (!box) {
        box = new THREE.Mesh(
          new THREE.BoxGeometry(1, 1, 1),
          new THREE.MeshBasicMaterial({
            color: 0xffffff,
            transparent: true,
            opacity: 0.001,
            depthWrite: false,
          }),
        );
        box.userData.entity = { kind: "group", id: group.id };
        this.hitRoot.add(box);
        this.hitBoxes.set(group.id, box);
      }
      box.userData.entity = { kind: "group", id: group.id };
      const origin = groupOrigin(group, visual);
      const footprint = groupFootprint(group.unitIds.length, group.slot);
      const width = group.slot === "bridge_right" ? -footprint.w : footprint.w;
      box.position.set(
        origin.x + (Math.abs(width) - 1) / 2 * Math.sign(width || 1),
        0.55 + extraLift(group, visual),
        origin.z + (footprint.d - 1) / 2,
      );
      box.scale.set(
        Math.abs(width) + GESTURE.hitPadding * 2,
        1.15,
        footprint.d + GESTURE.hitPadding * 2,
      );
    }
    for (const [id, box] of this.hitBoxes) {
      if (!seen.has(id)) {
        this.hitRoot.remove(box);
        box.geometry.dispose();
        (box.material as THREE.Material).dispose();
        this.hitBoxes.delete(id);
      }
    }
  }

  private syncSplitHandle(state: InteractionPrototypeState, visual: DragVisual | null): void {
    const focused = state.focusedGroupId ? state.groups[state.focusedGroupId] : null;
    if (!focused || focused.unitIds.length < 2) {
      this.splitHandle.visible = false;
      return;
    }
    const origin = groupOrigin(focused, visual);
    const count = focused.unitIds.length;
    const last = unitWorldPosition(origin, count - 1, count, focused.slot);
    const dir = focused.slot === "bridge_right" ? -1 : 1;
    this.splitHandle.visible = true;
    this.splitHandle.position.set(
      last.x + dir * (0.62 + GESTURE.splitHandleWorld * 0.15),
      0.58 + extraLift(focused, visual),
      last.z,
    );
    this.splitHandle.userData.entity = { kind: "split_handle", id: focused.id };
  }

  private highlightSlot(slotId: string | null): void {
    if (this.highlightedSlot === slotId) {
      return;
    }
    for (const [id, mesh] of this.slotMeshes) {
      const mat = mesh.material as THREE.MeshStandardMaterial;
      mat.color.set(id === slotId ? 0xb8874d : 0x8a6844);
    }
    this.highlightedSlot = slotId;
  }
}

function extraLift(group: PrototypeGroup, visual: DragVisual | null): number {
  if (visual?.groupId === group.id && visual.splitTake === undefined) {
    return visual.liftY;
  }
  return 0;
}

function groupOrigin(group: PrototypeGroup, visual: DragVisual | null): { x: number; z: number } {
  if (visual?.groupId === group.id && visual.splitTake === undefined) {
    return { x: visual.worldX, z: visual.worldZ };
  }
  return group.cell;
}

function slotUnderVisual(state: InteractionPrototypeState, visual: DragVisual): string | null {
  const group = state.groups[visual.groupId];
  if (!group || visual.splitTake !== undefined) {
    return null;
  }
  const { slots } = WORKSHOP;
  for (const id of Object.keys(slots) as Array<keyof typeof slots>) {
    const rect = slots[id];
    if (
      visual.worldX >= rect.x &&
      visual.worldX < rect.x + rect.w &&
      visual.worldZ >= rect.z &&
      visual.worldZ < rect.z + rect.d
    ) {
      return id;
    }
  }
  return null;
}
