import * as THREE from "three";

const LOOK_AT = new THREE.Vector3(8, 0, 6);

export const WORKSHOP_VIEW = {
  minHalfWidth: 11,
  minHalfHeight: 8.6,
} as const;

export function orthoExtents(aspect: number): { halfWidth: number; halfHeight: number } {
  const safe = aspect > 0.05 ? aspect : 1;
  let halfHeight = WORKSHOP_VIEW.minHalfHeight;
  let halfWidth = halfHeight * safe;
  if (halfWidth < WORKSHOP_VIEW.minHalfWidth) {
    halfWidth = WORKSHOP_VIEW.minHalfWidth;
    halfHeight = halfWidth / safe;
  }
  return { halfWidth, halfHeight };
}

export function createWorkshopCamera(aspect: number): THREE.OrthographicCamera {
  const { halfWidth, halfHeight } = orthoExtents(aspect);
  const camera = new THREE.OrthographicCamera(
    -halfWidth,
    halfWidth,
    halfHeight,
    -halfHeight,
    0.1,
    80,
  );
  camera.position.set(18, 15.5, 18);
  camera.lookAt(LOOK_AT);
  camera.updateProjectionMatrix();
  return camera;
}

export function resizeWorkshopCamera(
  camera: THREE.OrthographicCamera,
  aspect: number,
): void {
  const { halfWidth, halfHeight } = orthoExtents(aspect);
  camera.left = -halfWidth;
  camera.right = halfWidth;
  camera.top = halfHeight;
  camera.bottom = -halfHeight;
  camera.updateProjectionMatrix();
}
