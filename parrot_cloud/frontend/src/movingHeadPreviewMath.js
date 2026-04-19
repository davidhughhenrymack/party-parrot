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

/**
 * Desktop-side tilt rotation (radians around +X). Mirrors the Python
 * `tilt_radians_for_render` exactly — logical 135° = head straight up,
 * full mechanical sweep 0°..270° → ±135° from up.
 *
 * The web venue editor's head has its local forward aligned with +Y (not
 * the desktop's +Z), so `DenseSceneController` applies an equivalent but
 * differently-offset rotation — see `tiltRadiansForWebHead` below.
 *
 * @param {number} tiltDeg
 */
export function tiltRadiansForRender(tiltDeg) {
  const maxDeg = MECHANICAL_TILT_MAX_DEG;
  const td = Math.max(0.0, Math.min(Number(tiltDeg), maxDeg));
  return (Math.PI / 180) * (td - MECHANICAL_TILT_NEUTRAL_DEG) - Math.PI / 2;
}

/**
 * Web-side tilt rotation for `headPivotGroup.rotation.x` (Three.js, head's
 * local forward = +Y). At logical tilt = 135° the result is +π/2 so the beam
 * points along the aimGroup's +Z (venue up), matching the desktop renderer.
 *
 * Equivalent to `radians(tilt_deg - 45)`.
 *
 * @param {number} tiltDeg
 */
export function tiltRadiansForWebHead(tiltDeg) {
  const maxDeg = MECHANICAL_TILT_MAX_DEG;
  const td = Math.max(0.0, Math.min(Number(tiltDeg), maxDeg));
  return (Math.PI / 180) * (td - MECHANICAL_TILT_NEUTRAL_DEG) + Math.PI / 2;
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

export const MECHANICAL_TILT_MAX_DEG = 270.0;
/**
 * Logical tilt value meaning "head pointing straight up from the base" — the
 * mechanical center of a Chauvet 270° tilt sweep (see
 * `parrot/vj/moving_head_visual.py::mechanical_tilt_neutral_deg`).
 */
export const MECHANICAL_TILT_NEUTRAL_DEG = 135.0;
