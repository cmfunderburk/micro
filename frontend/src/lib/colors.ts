/**
 * Shared color utilities for the simulation visualization.
 */

/**
 * Maps an alpha preference parameter (0-1) to a color on the red-blue spectrum.
 * Alpha near 0 (prefers good Y) appears red.
 * Alpha near 1 (prefers good X) appears blue.
 */
export function alphaToColor(alpha: number): string {
  // HSL interpolation: 0 (red) = hue 0, 1 (blue) = hue 240
  const hue = alpha * 240;
  return `hsl(${hue}, 70%, 50%)`;
}

/**
 * Parses HSL color string and returns components.
 */
export function parseHsl(color: string): { h: number; s: number; l: number } {
  const match = color.match(/\d+/g);
  if (!match || match.length < 3) {
    return { h: 0, s: 70, l: 50 };
  }
  return {
    h: Number(match[0]),
    s: Number(match[1]),
    l: Number(match[2]),
  };
}

/**
 * Converts HSL color to HSLA with specified alpha.
 */
export function hslToHsla(color: string, alpha: number): string {
  const { h, s, l } = parseHsl(color);
  return `hsla(${h}, ${s}%, ${l}%, ${alpha})`;
}
