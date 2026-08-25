export interface ViewportSize {
  width: number;
  height: number;
}

export function readViewportSize(
  canvas: Pick<HTMLCanvasElement, "clientWidth" | "clientHeight">,
  view: Pick<VisualViewport, "width" | "height"> | null = null,
  fallback: ViewportSize = { width: 1280, height: 720 },
): ViewportSize {
  if (view && view.width > 0 && view.height > 0) {
    return { width: view.width, height: view.height };
  }
  const width = canvas.clientWidth || fallback.width;
  const height = canvas.clientHeight || fallback.height;
  return { width: Math.max(width, 1), height: Math.max(height, 1) };
}

export function bindViewportResize(onResize: () => void): () => void {
  const delayed = (): void => {
    onResize();
    window.setTimeout(onResize, 80);
    window.setTimeout(onResize, 320);
  };
  window.addEventListener("resize", onResize);
  window.addEventListener("orientationchange", delayed);
  window.visualViewport?.addEventListener("resize", onResize);
  screen.orientation?.addEventListener("change", delayed);
  return () => {
    window.removeEventListener("resize", onResize);
    window.removeEventListener("orientationchange", delayed);
    window.visualViewport?.removeEventListener("resize", onResize);
    screen.orientation?.removeEventListener("change", delayed);
  };
}
