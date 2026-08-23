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

export function clientToNdc(clientX: number, clientY: number, rect: RectLike): THREE.Vector2 {
  return new THREE.Vector2(
    ((clientX - rect.left) / rect.width) * 2 - 1,
    -((clientY - rect.top) / rect.height) * 2 + 1,
  );
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
