export interface OrientationInput {
  type?: string;
  angle?: number;
  width: number;
  height: number;
}

export interface PlaySize {
  width: number;
  height: number;
  landscape: boolean;
  viewportStuck: boolean;
  rotate: "cw" | "ccw" | null;
}

export function normalizeAngle(angle: number): number {
  return ((angle % 360) + 360) % 360;
}

export function isLandscapeInput(input: OrientationInput): boolean {
  if (input.type?.startsWith("landscape")) {
    return true;
  }
  if (input.type?.startsWith("portrait")) {
    return false;
  }
  if (typeof input.angle === "number") {
    const angle = normalizeAngle(input.angle);
    return angle === 90 || angle === 270;
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
  view: Pick<VisualViewport, "width" | "height"> | null,
  fallback: { width: number; height: number },
  screenLike: { orientation?: { type?: string; angle?: number } } | null,
  windowAngle?: number,
): OrientationInput {
  const width = view && view.width > 0 ? view.width : fallback.width;
  const height = view && view.height > 0 ? view.height : fallback.height;
  const input: OrientationInput = {
    width: Math.max(width, 1),
    height: Math.max(height, 1),
  };
  if (screenLike?.orientation?.type) {
    input.type = screenLike.orientation.type;
  }
  const angle = screenLike?.orientation?.angle ?? windowAngle;
  if (typeof angle === "number") {
    input.angle = angle;
  }
  return input;
}
