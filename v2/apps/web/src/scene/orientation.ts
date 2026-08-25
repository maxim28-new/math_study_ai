export interface SizePair {
  width: number;
  height: number;
}

export interface OrientationInput extends SizePair {
  type?: string;
  angle?: number;
  mediaLandscape?: boolean;
  forced?: boolean;
}

export interface PlaySize extends SizePair {
  landscape: boolean;
  viewportStuck: boolean;
  rotate: "cw" | "ccw" | null;
}

export function normalizeAngle(angle: number): number {
  return ((angle % 360) + 360) % 360;
}

export function angleIsLandscape(angle: number): boolean {
  const abs = normalizeAngle(angle);
  return abs === 90 || abs === 270;
}

export function pickAngle(...angles: Array<number | undefined>): number | undefined {
  const nums = angles.filter((value): value is number => typeof value === "number");
  return nums.find(angleIsLandscape) ?? nums[0];
}

export function pickWidestPair(pairs: SizePair[]): SizePair {
  const usable = pairs.filter((pair) => pair.width > 0 && pair.height > 0);
  if (usable.length === 0) {
    return { width: 1, height: 1 };
  }
  return usable.reduce((best, cur) =>
    cur.width / cur.height > best.width / best.height ? cur : best,
  );
}

export function isLandscapeInput(input: OrientationInput): boolean {
  if (input.forced || input.mediaLandscape) {
    return true;
  }
  if (input.type?.startsWith("landscape")) {
    return true;
  }
  if (typeof input.angle === "number" && angleIsLandscape(input.angle)) {
    return true;
  }
  return input.width >= input.height;
}

export function rotateForStuckViewport(angle: number | undefined, stuck: boolean): "cw" | "ccw" | null {
  if (!stuck) {
    return null;
  }
  const abs = typeof angle === "number" ? normalizeAngle(angle) : 90;
  return abs === 270 ? "ccw" : "cw";
}

export function playSize(input: OrientationInput): PlaySize {
  const landscape = isLandscapeInput(input);
  const stuck = landscape ? input.width < input.height : input.width > input.height;
  if (stuck) {
    return {
      width: Math.max(input.height, 1),
      height: Math.max(input.width, 1),
      landscape,
      viewportStuck: true,
      rotate: rotateForStuckViewport(input.angle, true),
    };
  }
  return {
    width: Math.max(input.width, 1),
    height: Math.max(input.height, 1),
    landscape,
    viewportStuck: false,
    rotate: null,
  };
}

export function readOrientationInput(
  pairs: SizePair[],
  screenLike: { orientation?: { type?: string; angle?: number } } | null,
  extras: { windowAngle?: number; mediaLandscape?: boolean; forced?: boolean } = {},
): OrientationInput {
  const size = pickWidestPair(pairs);
  const input: OrientationInput = {
    width: size.width,
    height: size.height,
  };
  if (screenLike?.orientation?.type) {
    input.type = screenLike.orientation.type;
  }
  const angle = pickAngle(extras.windowAngle, screenLike?.orientation?.angle);
  if (typeof angle === "number") {
    input.angle = angle;
  }
  if (extras.mediaLandscape) {
    input.mediaLandscape = true;
  }
  if (extras.forced) {
    input.forced = true;
  }
  return input;
}
