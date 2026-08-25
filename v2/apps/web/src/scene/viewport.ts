import {
  deviceReportsLandscape,
  playSize,
  readChromeSize,
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

export function resolvePlayLayout(
  live: SizePair,
  forcing: boolean,
  lastPortrait: SizePair | null,
  screenLike: { orientation?: { type?: string; angle?: number } } | null = null,
  extras: { windowAngle?: number; mediaLandscape?: boolean; forced?: boolean } = {},
): { layout: PlaySize; lastPortrait: SizePair | null } {
  const probe = readOrientationInput(live, screenLike, extras);
  const nativeLandscape = deviceReportsLandscape(probe);
  const chrome = readChromeSize(live, forcing, lastPortrait, nativeLandscape);
  return {
    layout: playSize(readOrientationInput(chrome.size, screenLike, extras)),
    lastPortrait: chrome.lastPortrait,
  };
}

export function bindViewportResize(onResize: () => void): () => void {
  let frame = 0;
  let timeout = 0;
  const delayed = (): void => {
    if (!frame) {
      frame = window.requestAnimationFrame(() => {
        frame = 0;
        onResize();
      });
    }
    window.clearTimeout(timeout);
    timeout = window.setTimeout(onResize, 150);
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
    if (frame) {
      window.cancelAnimationFrame(frame);
    }
    window.clearTimeout(timeout);
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
