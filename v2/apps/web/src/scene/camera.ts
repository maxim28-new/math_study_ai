import * as THREE from "three";

const FRUSTUM = 8.6;
const LOOK_AT = new THREE.Vector3(8, 0, 6);

export function createWorkshopCamera(aspect: number): THREE.OrthographicCamera {
  const camera = new THREE.OrthographicCamera(
    -FRUSTUM * aspect,
    FRUSTUM * aspect,
    FRUSTUM,
    -FRUSTUM,
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
  camera.left = -FRUSTUM * aspect;
  camera.right = FRUSTUM * aspect;
  camera.top = FRUSTUM;
  camera.bottom = -FRUSTUM;
  camera.updateProjectionMatrix();
}
