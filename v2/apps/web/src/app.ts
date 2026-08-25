import { createInitialPrototypeState, type InteractionPrototypeState } from "./prototype/state.ts";
import { createWorkshopCamera, resizeWorkshopCamera } from "./scene/camera.ts";
import { bindWorkshopDrag } from "./scene/drag.ts";
import { WorkshopRenderer, type DragVisual } from "./scene/renderer.ts";
import { bindViewportResize, resolvePlayLayout } from "./scene/viewport.ts";
import type { SizePair } from "./scene/orientation.ts";

const FORCE_KEY = "xiaoou-v2-force-landscape";
const FLIP_KEY = "xiaoou-v2-flip-rotate";

export function bootWorkshop(canvas: HTMLCanvasElement): () => void {
  const root = document.documentElement;
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
  let lastPortrait: SizePair | null = null;

  const first = currentLayout();
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

  const applyLayout = (): void => {
    const layout = currentLayout();
    const rotate = flipped && layout.rotate ? (layout.rotate === "cw" ? "ccw" : "cw") : layout.rotate;
    root.style.setProperty("--play-w", `${layout.width}px`);
    root.style.setProperty("--play-h", `${layout.height}px`);
    root.classList.toggle("is-landscape", layout.landscape);
    root.classList.toggle("is-portrait", !layout.landscape);
    root.classList.toggle("force-landscape-cw", rotate === "cw");
    root.classList.toggle("force-landscape-ccw", rotate === "ccw");
    if (rotateGate) {
      rotateGate.hidden = layout.landscape;
    }
    if (hintBar) {
      hintBar.hidden = !layout.landscape;
    }
    if (flipBtn) {
      flipBtn.hidden = !(layout.landscape && layout.viewportStuck);
    }
    if (layout.landscape) {
      bindDrag();
    }
    renderer.setSize(layout.width, layout.height);
    resizeWorkshopCamera(camera, layout.width / Math.max(layout.height, 1));
    requestDraw();
  };

  confirmBtn?.addEventListener("click", () => {
    forced = true;
    sessionStorage.setItem(FORCE_KEY, "1");
    applyLayout();
  });
  flipBtn?.addEventListener("click", () => {
    flipped = !flipped;
    sessionStorage.setItem(FLIP_KEY, flipped ? "1" : "0");
    applyLayout();
  });

  const unbindViewport = bindViewportResize(applyLayout);
  applyLayout();

  return () => {
    unbindDrag();
    unbindViewport();
    if (frame) {
      window.cancelAnimationFrame(frame);
    }
    renderer.dispose();
  };

  function currentLayout() {
    const win = window as Window & { orientation?: number };
    const forcing =
      root.classList.contains("force-landscape-cw") || root.classList.contains("force-landscape-ccw");
    const extras: { windowAngle?: number; mediaLandscape?: boolean; forced?: boolean } = {};
    if (typeof win.orientation === "number") {
      extras.windowAngle = win.orientation;
    }
    if (forced) {
      extras.forced = true;
    } else if (window.matchMedia("(orientation: landscape)").matches) {
      extras.mediaLandscape = true;
    }
    const vv = window.visualViewport;
    const live = {
      width: vv && vv.width > 0 ? vv.width : window.innerWidth,
      height: vv && vv.height > 0 ? vv.height : window.innerHeight,
    };
    const resolved = resolvePlayLayout(live, forcing, lastPortrait, window.screen, extras);
    lastPortrait = resolved.lastPortrait;
    return resolved.layout;
  }
}
