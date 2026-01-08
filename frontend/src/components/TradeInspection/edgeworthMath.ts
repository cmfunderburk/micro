/**
 * Mathematical utilities for Edgeworth box visualization.
 *
 * For Cobb-Douglas preferences: u(x, y) = x^α * y^(1-α)
 *
 * Reference: Kreps I Ch 15, MWG Ch 15
 */

/**
 * Compute Cobb-Douglas utility.
 */
export function cobbDouglasUtility(
  x: number,
  y: number,
  alpha: number
): number {
  if (x <= 0 || y <= 0) return 0;
  return Math.pow(x, alpha) * Math.pow(y, 1 - alpha);
}

/**
 * Compute points on a Cobb-Douglas indifference curve.
 *
 * For u(x, y) = x^α * y^(1-α), the indifference curve at utility u is:
 *     y = (u / x^α)^(1/(1-α))
 */
export function computeIndifferenceCurve(
  alpha: number,
  utility: number,
  xMin: number,
  xMax: number,
  nPoints: number = 50
): Array<[number, number]> {
  if (utility <= 0 || alpha <= 0 || alpha >= 1) {
    return [];
  }

  const points: Array<[number, number]> = [];
  const exponent = 1.0 / (1.0 - alpha);

  for (let i = 0; i < nPoints; i++) {
    const x = xMin + (xMax - xMin) * (i / (nPoints - 1));
    if (x <= 0) continue;

    try {
      const y = Math.pow(utility / Math.pow(x, alpha), exponent);
      if (y >= 0 && isFinite(y)) {
        points.push([x, y]);
      }
    } catch {
      continue;
    }
  }

  return points;
}

/**
 * Compute points on the contract curve.
 *
 * The contract curve is the locus of Pareto-efficient allocations where MRS_A = MRS_B.
 *
 * For Cobb-Douglas preferences:
 *     (α_A / (1-α_A)) * (y_A / x_A) = (α_B / (1-α_B)) * ((Y - y_A) / (X - x_A))
 *
 * Solving for y_A in terms of x_A:
 *     y_A = (α_B * (1-α_A) * Y * x_A) / (α_A * (1-α_B) * X + (α_B * (1-α_A) - α_A * (1-α_B)) * x_A)
 */
export function computeContractCurve(
  alphaA: number,
  alphaB: number,
  totalX: number,
  totalY: number,
  nPoints: number = 50
): Array<[number, number]> {
  if (alphaA <= 0 || alphaA >= 1 || alphaB <= 0 || alphaB >= 1) {
    return [];
  }

  const points: Array<[number, number]> = [];
  const X = totalX;
  const Y = totalY;

  // Coefficients for the contract curve equation
  const a1 = alphaA * (1 - alphaB);
  const a2 = alphaB * (1 - alphaA);

  for (let i = 0; i < nPoints; i++) {
    // x_A from 0 to X (excluding endpoints to avoid division by zero)
    const xA = 0.01 * X + 0.98 * X * (i / (nPoints - 1));

    // Compute denominator
    const denom = a1 * X + (a2 - a1) * xA;

    if (Math.abs(denom) < 1e-10) {
      continue;
    }

    const yA = (a2 * Y * xA) / denom;

    // Check bounds
    if (yA > 0 && yA < Y) {
      points.push([xA, yA]);
    }
  }

  return points;
}
