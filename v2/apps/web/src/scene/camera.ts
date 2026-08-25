import * as THREE from "three";

const LOOK_AT = new THREE.Vector3(8, 0, 6);

/** Landscape half-height: table fills a phone on its side without cropping piles. */
export const WORKSHOP_VIEW = {
  halfHeight: 5.6,
} as const;

export function orthoExtents(aspect: number): { halfWidth: number; halfHeight: number } {
  const safe = aspect > 0.05 ? aspect : 1;
  const halfHeight = WORKSHOP_VIEW.halfHeight;
  return { halfWidth: halfHeight * safe, halfHeight };
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
  camera.position.set(16.5, 14, 16.5);
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
