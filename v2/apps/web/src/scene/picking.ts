import * as THREE from "three";

export type EntityKind = "group" | "split_handle" | "slot";

export interface EntityHit {
  kind: EntityKind;
  id: string;
}

export interface RectLike {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface Matrix2D {
  a: number;
  b: number;
  c: number;
  d: number;
}

export function ndcFromLocal(x: number, y: number, width: number, height: number): THREE.Vector2 {
  return new THREE.Vector2(
    (x / Math.max(width, 1)) * 2 - 1,
    -((y / Math.max(height, 1)) * 2 - 1),
  );
}

export function clientToNdc(clientX: number, clientY: number, rect: RectLike): THREE.Vector2 {
  return ndcFromLocal(clientX - rect.left, clientY - rect.top, rect.width, rect.height);
}

export function invertCenterDelta(dx: number, dy: number, matrix: Matrix2D): { x: number; y: number } {
  const det = matrix.a * matrix.d - matrix.b * matrix.c;
  if (Math.abs(det) < 1e-8) {
    return { x: dx, y: dy };
  }
  return {
    x: (matrix.d * dx - matrix.c * dy) / det,
    y: (-matrix.b * dx + matrix.a * dy) / det,
  };
}

export function clientToLocal(
  clientX: number,
  clientY: number,
  visual: RectLike,
  localWidth: number,
  localHeight: number,
  matrix: Matrix2D | null,
): { x: number; y: number } {
  const cx = visual.left + visual.width / 2;
  const cy = visual.top + visual.height / 2;
  let dx = clientX - cx;
  let dy = clientY - cy;
  if (matrix) {
    const local = invertCenterDelta(dx, dy, matrix);
    dx = local.x;
    dy = local.y;
  }
  return {
    x: dx + localWidth / 2,
    y: dy + localHeight / 2,
  };
}

export function parseCssMatrix(transform: string): Matrix2D | null {
  if (!transform || transform === "none") {
    return null;
  }
  const matrix3d = /matrix3d\(([^)]+)\)/.exec(transform);
  if (matrix3d) {
    const parts = matrix3d[1].split(",").map((part) => Number(part.trim()));
    if (parts.length >= 6 && parts.every((part) => !Number.isNaN(part))) {
      return { a: parts[0], b: parts[1], c: parts[4], d: parts[5] };
    }
  }
  const match = /matrix\(([^)]+)\)/.exec(transform);
  if (!match) {
    return null;
  }
  const parts = match[1].split(",").map((part) => Number(part.trim()));
  if (parts.length < 4 || parts.some((part) => Number.isNaN(part))) {
    return null;
  }
  return { a: parts[0], b: parts[1], c: parts[2], d: parts[3] };
}

export function pickEntity(
  raycaster: THREE.Raycaster,
  camera: THREE.Camera,
  ndc: THREE.Vector2,
  roots: THREE.Object3D[],
): EntityHit | null {
  raycaster.setFromCamera(ndc, camera);
  const hits = raycaster.intersectObjects(roots, true);
  for (const hit of hits) {
    const entity = readEntity(hit.object);
    if (entity) {
      return entity;
    }
  }
  return null;
}

export function readEntity(object: THREE.Object3D): EntityHit | null {
  let current: THREE.Object3D | null = object;
  while (current) {
    const entity = current.userData.entity as EntityHit | undefined;
    if (entity?.kind && entity.id) {
      return entity;
    }
    current = current.parent;
  }
  return null;
}

export function worldPointOnTable(
  raycaster: THREE.Raycaster,
  camera: THREE.Camera,
  ndc: THREE.Vector2,
  height = 0,
): THREE.Vector3 | null {
  raycaster.setFromCamera(ndc, camera);
  const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -height);
  const target = new THREE.Vector3();
  const hit = raycaster.ray.intersectPlane(plane, target);
  return hit;
}
