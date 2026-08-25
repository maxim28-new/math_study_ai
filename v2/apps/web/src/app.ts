import { createInitialPrototypeState, type InteractionPrototypeState } from "./prototype/state.ts";
import { createWorkshopCamera, resizeWorkshopCamera } from "./scene/camera.ts";
import { bindWorkshopDrag } from "./scene/drag.ts";
import { WorkshopRenderer, type DragVisual } from "./scene/renderer.ts";
import { bindViewportResize, readPlayLayout } from "./scene/viewport.ts";

export function bootWorkshop(canvas: HTMLCanvasElement): () => void {
  const app = document.getElementById("app");
  const rotateGate = document.getElementById("rotateGate");
  const hintBar = document.getElementById("hintBar");
  let state = createInitialPrototypeState();
  let visual: DragVisual | null = null;
  let frame = 0;
  let dragBound = false;

  const first = currentLayout(canvas, app);
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

  const bindDrag = (): void => {
    if (dragBound) {
      return;
    }
    unbindDrag = bindWorkshopDrag({
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
    dragBound = true;
  };

  let unbindDrag = (): void => undefined;

  const onResize = (): void => {
    const layout = currentLayout(canvas, app);
    document.documentElement.classList.toggle("is-landscape", layout.landscape);
    document.documentElement.classList.toggle("is-portrait", !layout.landscape);
    document.documentElement.classList.toggle("force-landscape-cw", layout.rotate === "cw");
    document.documentElement.classList.toggle("force-landscape-ccw", layout.rotate === "ccw");
    if (rotateGate) {
      rotateGate.hidden = layout.landscape;
    }
    if (hintBar) {
      hintBar.hidden = !layout.landscape;
    }
    if (layout.landscape) {
      bindDrag();
    }
    const width = app?.clientWidth || layout.width;
    const height = app?.clientHeight || layout.height;
    renderer.setSize(width, height);
    resizeWorkshopCamera(camera, width / Math.max(height, 1));
    requestDraw();
  };

  const unbindViewport = bindViewportResize(onResize);
  onResize();

  return () => {
    unbindDrag();
    unbindViewport();
    if (frame) {
      window.cancelAnimationFrame(frame);
    }
    renderer.dispose();
  };
}

function currentLayout(canvas: HTMLCanvasElement, app: HTMLElement | null) {
  const fallback = {
    width: app?.clientWidth || canvas.clientWidth || window.innerWidth || 1280,
    height: app?.clientHeight || canvas.clientHeight || window.innerHeight || 720,
  };
  return readPlayLayout(
    fallback,
    window.visualViewport,
    window.screen,
    typeof (window as Window & { orientation?: number }).orientation === "number"
      ? (window as Window & { orientation?: number }).orientation
      : undefined,
  );
}
