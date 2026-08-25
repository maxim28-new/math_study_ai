import {
  playSize,
  readOrientationInput,
  type PlaySize,
  type SizePair,
} from "./orientation.ts";

export function readPlayLayout(
  windowSize: SizePair,
  screenLike: { orientation?: { type?: string; angle?: number } } | null = null,
  extras: { windowAngle?: number; mediaLandscape?: boolean; forced?: boolean } = {},
): PlaySize {
  return playSize(readOrientationInput(windowSize, screenLike, extras));
}

export function bindViewportResize(onResize: () => void): () => void {
  const delayed = (): void => {
    onResize();
    window.setTimeout(onResize, 80);
    window.setTimeout(onResize, 320);
  };
  const media = window.matchMedia("(orientation: landscape)");
  const onMedia = (): void => delayed();
  window.addEventListener("resize", delayed);
  window.addEventListener("orientationchange", delayed);
  window.visualViewport?.addEventListener("resize", delayed);
  screen.orientation?.addEventListener("change", delayed);
  if (typeof media.addEventListener === "function") {
    media.addEventListener("change", onMedia);
  } else {
    media.addListener(onMedia);
  }
  return () => {
    window.removeEventListener("resize", delayed);
    window.removeEventListener("orientationchange", delayed);
    window.visualViewport?.removeEventListener("resize", delayed);
    screen.orientation?.removeEventListener("change", delayed);
    if (typeof media.removeEventListener === "function") {
      media.removeEventListener("change", onMedia);
    } else {
      media.removeListener(onMedia);
    }
  };
}
