import { createInitialPrototypeState, type InteractionPrototypeState } from "./prototype/state.ts";
import { createWorkshopCamera, resizeWorkshopCamera } from "./scene/camera.ts";
import { bindWorkshopDrag } from "./scene/drag.ts";
import { WorkshopRenderer, type DragVisual } from "./scene/renderer.ts";

export function bootWorkshop(canvas: HTMLCanvasElement): () => void {
  let state = createInitialPrototypeState();
  let visual: DragVisual | null = null;
  let frame = 0;

  const renderer = new WorkshopRenderer(canvas);
  const camera = createWorkshopCamera(sizeAspect(canvas));

  const draw = (): void => {
    frame = 0;
    renderer.sync(state, visual);
    renderer.render(camera);
  };

  const requestDraw = (): void => {
    if (frame) {
      return;
    }
    frame = window.requestAnimationFrame(draw);
  };

  const setState = (next: InteractionPrototypeState): void => {
    state = next;
    requestDraw();
  };

  const unbind = bindWorkshopDrag({
    canvas,
    camera,
    pickRoots: () => renderer.pickRoots,
    getState: () => state,
    setState,
    onVisual: (next) => {
      visual = next;
      requestDraw();
    },
  });

  const onResize = (): void => {
    const width = canvas.clientWidth || window.innerWidth;
    const height = canvas.clientHeight || window.innerHeight;
    renderer.setSize(width, height);
    resizeWorkshopCamera(camera, width / Math.max(height, 1));
    requestDraw();
  };

  window.addEventListener("resize", onResize);
  onResize();

  return () => {
    unbind();
    window.removeEventListener("resize", onResize);
    if (frame) {
      window.cancelAnimationFrame(frame);
    }
    renderer.dispose();
  };
}

function sizeAspect(canvas: HTMLCanvasElement): number {
  const width = canvas.clientWidth || window.innerWidth || 1280;
  const height = canvas.clientHeight || window.innerHeight || 720;
  return width / Math.max(height, 1);
}
