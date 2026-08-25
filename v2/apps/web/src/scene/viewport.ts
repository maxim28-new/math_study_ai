import {
  playSize,
  readOrientationInput,
  type PlaySize,
  type SizePair,
} from "./orientation.ts";

export interface ViewportSize {
  width: number;
  height: number;
}

export function readPlayLayout(
  pairs: SizePair[],
  screenLike: { orientation?: { type?: string; angle?: number } } | null = null,
  extras: { windowAngle?: number; mediaLandscape?: boolean; forced?: boolean } = {},
): PlaySize {
  return playSize(readOrientationInput(pairs, screenLike, extras));
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
  const poll = window.setInterval(onResize, 250);
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
    window.clearInterval(poll);
  };
}
