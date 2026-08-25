import { createInitialPrototypeState, type InteractionPrototypeState } from "./prototype/state.ts";
import { createWorkshopCamera, resizeWorkshopCamera } from "./scene/camera.ts";
import { bindWorkshopDrag } from "./scene/drag.ts";
import { WorkshopRenderer, type DragVisual } from "./scene/renderer.ts";
import { bindViewportResize, readViewportSize } from "./scene/viewport.ts";

export function bootWorkshop(canvas: HTMLCanvasElement): () => void {
  let state = createInitialPrototypeState();
  let visual: DragVisual | null = null;
  let frame = 0;

  const first = readViewportSize(canvas, window.visualViewport);
  const renderer = new WorkshopRenderer(canvas);
  const camera = createWorkshopCamera(first.width / first.height);

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
    const { width, height } = readViewportSize(canvas, window.visualViewport);
    renderer.setSize(width, height);
    resizeWorkshopCamera(camera, width / height);
    requestDraw();
  };

  const unbindViewport = bindViewportResize(onResize);
  onResize();

  return () => {
    unbind();
    unbindViewport();
    if (frame) {
      window.cancelAnimationFrame(frame);
    }
    renderer.dispose();
  };
}
