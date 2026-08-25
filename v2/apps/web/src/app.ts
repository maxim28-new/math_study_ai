import { createInitialPrototypeState, type InteractionPrototypeState } from "./prototype/state.ts";
import { createWorkshopCamera, resizeWorkshopCamera } from "./scene/camera.ts";
import { bindWorkshopDrag } from "./scene/drag.ts";
import { WorkshopRenderer, type DragVisual } from "./scene/renderer.ts";
import { bindViewportResize, readPlayLayout } from "./scene/viewport.ts";

const FORCE_KEY = "xiaoou-v2-force-landscape";
const FLIP_KEY = "xiaoou-v2-flip-rotate";

export function bootWorkshop(canvas: HTMLCanvasElement): () => void {
  const app = document.getElementById("app");
  const rotateGate = document.getElementById("rotateGate");
  const hintBar = document.getElementById("hintBar");
  const confirmBtn = document.getElementById("confirmLandscapeBtn");
  const flipBtn = document.getElementById("flipRotateBtn");
  let state = createInitialPrototypeState();
  let visual: DragVisual | null = null;
  let frame = 0;
  let dragBound = false;
  let forced = sessionStorage.getItem(FORCE_KEY) === "1";
  let flipped = sessionStorage.getItem(FLIP_KEY) === "1";

  const first = currentLayout(canvas, app, forced);
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
    const layout = currentLayout(canvas, app, forced);
    const rotate = flipped && layout.rotate ? (layout.rotate === "cw" ? "ccw" : "cw") : layout.rotate;
    document.documentElement.classList.toggle("is-landscape", layout.landscape);
    document.documentElement.classList.toggle("is-portrait", !layout.landscape);
    document.documentElement.classList.toggle("force-landscape-cw", rotate === "cw");
    document.documentElement.classList.toggle("force-landscape-ccw", rotate === "ccw");
    if (rotateGate) {
      rotateGate.hidden = layout.landscape;
    }
    if (hintBar) {
      hintBar.hidden = !layout.landscape;
    }
    if (flipBtn) {
      flipBtn.hidden = !(layout.landscape && (layout.viewportStuck || forced));
    }
    if (layout.landscape) {
      bindDrag();
    }
    window.requestAnimationFrame(() => {
      const width = app?.clientWidth || layout.width;
      const height = app?.clientHeight || layout.height;
      renderer.setSize(width, height);
      resizeWorkshopCamera(camera, width / Math.max(height, 1));
      requestDraw();
    });
  };

  confirmBtn?.addEventListener("click", () => {
    forced = true;
    sessionStorage.setItem(FORCE_KEY, "1");
    onResize();
  });
  flipBtn?.addEventListener("click", () => {
    flipped = !flipped;
    sessionStorage.setItem(FLIP_KEY, flipped ? "1" : "0");
    onResize();
  });

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

function currentLayout(canvas: HTMLCanvasElement, app: HTMLElement | null, forced: boolean) {
  const win = window as Window & { orientation?: number };
  const vv = window.visualViewport;
  const extras: { windowAngle?: number; mediaLandscape?: boolean; forced?: boolean } = {
    mediaLandscape: window.matchMedia("(orientation: landscape)").matches,
  };
  if (typeof win.orientation === "number") {
    extras.windowAngle = win.orientation;
  }
  if (forced) {
    extras.forced = true;
  }
  return readPlayLayout(
    [
      { width: window.innerWidth, height: window.innerHeight },
      { width: vv?.width ?? 0, height: vv?.height ?? 0 },
      { width: app?.clientWidth ?? 0, height: app?.clientHeight ?? 0 },
      { width: canvas.clientWidth, height: canvas.clientHeight },
    ],
    window.screen,
    extras,
  );
}
