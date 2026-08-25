import {
  playSize,
  readOrientationInput,
  type PlaySize,
} from "./orientation.ts";

export interface ViewportSize {
  width: number;
  height: number;
}

export function readPlayLayout(
  fallback: ViewportSize,
  view: Pick<VisualViewport, "width" | "height"> | null = null,
  screenLike: { orientation?: { type?: string; angle?: number } } | null = null,
  windowAngle?: number,
): PlaySize {
  return playSize(readOrientationInput(view, fallback, screenLike, windowAngle));
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
