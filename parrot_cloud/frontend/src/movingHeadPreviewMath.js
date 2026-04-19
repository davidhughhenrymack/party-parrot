/**
 * Moving-head preview math — must match `parrot/vj/moving_head_visual.py` exactly.
 *
 * Logical angles come from runtime JSON (`pan_deg`, `tilt_deg`); they are the same
 * `MovingHead` logical angles as the desktop VJ preview.
 */

/** @param {number} panDeg */
export function panRadiansForRender(panDeg) {
  return (Math.PI / 180) * Number(panDeg) * 0.5 + Math.PI;
}

/** @param {number} tiltDeg */
export function tiltRadiansForRender(tiltDeg) {
  const maxDeg = 200.0;
  const td = Math.max(0.0, Math.min(Number(tiltDeg), maxDeg));
  return (Math.PI / 180) * td * 0.5;
}

/**
 * Z-up Three.js `aimGroup.rotation.z` so pan matches `MovingHeadRenderer` (room +Y pan)
 * after the venue axis mapping in `DenseSceneController` / `toScenePosition`.
 *
 * Algebra (same as Python `aim_group_rotation_z_radians`): this equals `-(panRadiansForRender(pan) - π)`,
 * i.e. `-panDeg` scaled by 0.5 in radians — the +π in `panRadiansForRender` is the desktop
 * yoke offset and cancels for the web Euler.
 *
 * @param {number} panDeg
 */
export function aimGroupRotationZRadians(panDeg) {
  return -(panRadiansForRender(panDeg) - Math.PI);
}

export const MECHANICAL_TILT_MAX_DEG = 200.0;
