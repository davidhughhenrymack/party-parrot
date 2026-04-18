/**
 * Venue editor fixture geometry aligned with desktop OpenGL renderers:
 * parrot/vj/renderers/bulb.py, moving_head.py, mirrorball.py, motionstrip.py, laser.py
 *
 * FixtureRenderer uses cube_size = 0.8; body_size = cube_size * 0.4.
 * Three.js venue coords: X = audience left–right, Y = downstage–upstage, Z = height.
 */

export const DESKTOP_CUBE_SIZE = 0.8;

export function desktopBodySize() {
  return DESKTOP_CUBE_SIZE * 0.4;
}

const MOVING_HEAD_TYPES = new Set([
  'chauvet_spot_110',
  'chauvet_spot_160',
  'chauvet_rogue_beam_r2',
  'chauvet_move_9ch',
  'chauvet_intimidator_hybrid_140sr',
  'chauvet_intimidator_hybrid_140sr_13ch',
]);

export function isMovingHeadFixtureType(fixtureType) {
  return MOVING_HEAD_TYPES.has(fixtureType);
}

function parLikeDimensions() {
  const bs = desktopBodySize();
  // PAR / theatre can: long axis along beam (stage Y), roughly square cross-section (X × Z)
  return {
    bodyWidth: bs,
    bodyDepth: bs * 2.25,
    bodyHeight: bs * 1.05,
  };
}

function movingHeadDimensions() {
  const bs = desktopBodySize();
  const baseHeight = bs * 0.42;
  const headHeight = bs * 0.5;
  const headCenterZ = baseHeight + bs * 0.3 + headHeight / 2;
  return {
    baseWidth: bs * 1.2,
    baseDepth: bs * 0.8,
    baseHeight,
    headWidth: bs * 0.5,
    headDepth: bs * 1.2,
    headHeight,
    headOffsetZ: headCenterZ - baseHeight,
  };
}

function motionstripDimensions(numBulbs) {
  const cube = DESKTOP_CUBE_SIZE;
  return {
    bodyWidth: numBulbs * 0.22,
    bodyDepth: cube * 0.3,
    bodyHeight: cube * 0.2,
    numBulbs,
    bulbSpacing: 0.22,
  };
}

function laserDimensions() {
  const s = DESKTOP_CUBE_SIZE * 0.5;
  return {
    bodyWidth: s,
    bodyDepth: s,
    bodyHeight: s,
  };
}

/** @param {number} count @param {typeof import('three')} THREE */
function mirrorballDirectionsTHREE(count, THREE) {
  const out = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < count; i += 1) {
    const elev = 1 - (i / Math.max(1, count - 1)) * 2;
    const r = Math.sqrt(Math.max(0, 1 - elev * elev));
    const theta = golden * i;
    const x = Math.cos(theta) * r;
    const y = Math.sin(theta) * r;
    out.push(new THREE.Vector3(x, y, elev).normalize());
  }
  return out;
}

function mirrorballModel() {
  const bs = desktopBodySize();
  const sphereRadius = bs * 0.9;
  return {
    kind: 'mirrorball',
    sphereRadius,
    beamCount: 36,
    beamLength: 2.4,
    beamConeRadius: bs * 0.07,
    coneLength: 2.4,
    coneRadius: bs * 0.2,
  };
}

/**
 * Full visual description for cones, lens, and mesh construction.
 */
export function resolveFixtureVisualModel(fixtureType) {
  const bs = desktopBodySize();
  if (fixtureType === 'mirrorball') {
    return mirrorballModel();
  }
  if (fixtureType === 'motionstrip_38') {
    return {
      kind: 'motionstrip',
      ...motionstripDimensions(8),
      coneLength: 2.8,
      coneRadius: bs * 1.85,
    };
  }
  if (fixtureType === 'chauvet_colorband_pix_36ch') {
    return {
      kind: 'motionstrip',
      ...motionstripDimensions(12),
      coneLength: 2.8,
      coneRadius: bs * 2.0,
    };
  }
  if (MOVING_HEAD_TYPES.has(fixtureType)) {
    const mh = movingHeadDimensions();
    return {
      kind: 'moving_head',
      ...mh,
      coneLength: 6.5,
      coneRadius: bs * 0.58,
    };
  }
  if (fixtureType === 'five_beam_laser' || fixtureType === 'two_beam_laser') {
    const lz = laserDimensions();
    return {
      kind: 'laser',
      ...lz,
      coneLength: 5.0,
      coneRadius: bs * 0.38,
    };
  }
  const par = parLikeDimensions();
  return {
    kind: 'bulb',
    ...par,
    coneLength: 3.5,
    coneRadius: bs * 1.0,
  };
}

/**
 * Beam origin in moving-head headPivotGroup local space (lens slightly in front of +Y face).
 * @param {ReturnType<typeof resolveFixtureVisualModel>} model
 */
export function beamOriginMovingHeadAimLocal(model) {
  // Head mesh is centered on headPivotGroup; lens sits slightly in front of the +Y face.
  const halfDepth = model.headDepth * 0.5;
  return {
    y: halfDepth + model.headDepth * 0.12,
    z: model.headHeight * 0.05,
  };
}

/**
 * @param {import('three').MeshStandardMaterial} bodyMaterial
 * @returns {{ aimGroup?: import('three').Group, headPivotGroup?: import('three').Group, stripPanGroup?: import('three').Group, mirrorballBeamMaterials?: import('three').MeshBasicMaterial[], mirrorballBeamsGroup?: import('three').Group }}
 */
export function addFixtureOpaqueMeshes(THREE, runtimeAxesGroup, bodyMaterial, model, entityKey) {
  const userData = { entityKey };

  if (model.kind === 'mirrorball') {
    const r = model.sphereRadius;
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(r, 28, 20),
      bodyMaterial
    );
    sphere.position.set(0, 0, r);
    sphere.userData = userData;
    runtimeAxesGroup.add(sphere);

    const dirs = mirrorballDirectionsTHREE(model.beamCount, THREE);
    const beamMaterials = [];
    const L = model.beamLength;
    const tipR = model.beamConeRadius;
    const beamSpinGroup = new THREE.Group();
    beamSpinGroup.position.set(0, 0, r);
    beamSpinGroup.userData = userData;
    runtimeAxesGroup.add(beamSpinGroup);
    for (let i = 0; i < dirs.length; i += 1) {
      const dir = dirs[i];
      const mat = new THREE.MeshBasicMaterial({
        color: 0xf8fafc,
        transparent: true,
        opacity: 0,
        side: THREE.DoubleSide,
        depthWrite: false,
      });
      beamMaterials.push(mat);
      const cone = new THREE.Mesh(new THREE.ConeGeometry(tipR, L, 6, 1, true), mat);
      cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
      cone.position.copy(dir.clone().multiplyScalar(r - L / 2));
      cone.userData = userData;
      beamSpinGroup.add(cone);
    }
    return { mirrorballBeamMaterials: beamMaterials, mirrorballBeamsGroup: beamSpinGroup };
  }

  if (model.kind === 'moving_head') {
    const base = new THREE.Mesh(
      new THREE.BoxGeometry(model.baseWidth, model.baseDepth, model.baseHeight),
      bodyMaterial
    );
    base.position.z = model.baseHeight / 2;
    base.userData = userData;
    runtimeAxesGroup.add(base);

    const aimGroup = new THREE.Group();
    aimGroup.position.set(0, 0, model.baseHeight);
    const headPivotGroup = new THREE.Group();
    // Pivot at the center of the yoke / base of the head (horizontal centerline), not the rear face,
    // so pan/tilt rotate around the physical joint.
    headPivotGroup.position.set(0, 0, model.headOffsetZ);
    const head = new THREE.Mesh(
      new THREE.BoxGeometry(model.headWidth, model.headDepth, model.headHeight),
      bodyMaterial
    );
    head.position.set(0, 0, 0);
    head.userData = userData;
    headPivotGroup.add(head);
    aimGroup.add(headPivotGroup);
    runtimeAxesGroup.add(aimGroup);
    return { aimGroup, headPivotGroup };
  }

  if (model.kind === 'motionstrip') {
    const stripPanGroup = new THREE.Group();
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(model.bodyWidth, model.bodyDepth, model.bodyHeight),
      bodyMaterial
    );
    body.position.z = model.bodyHeight / 2;
    body.userData = userData;
    stripPanGroup.add(body);
    runtimeAxesGroup.add(stripPanGroup);
    return { stripPanGroup };
  }

  if (model.kind === 'laser') {
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(model.bodyWidth, model.bodyDepth, model.bodyHeight),
      bodyMaterial
    );
    body.position.z = model.bodyHeight / 2;
    body.userData = userData;
    runtimeAxesGroup.add(body);
    return {};
  }

  const body = new THREE.Mesh(
    new THREE.BoxGeometry(model.bodyWidth, model.bodyDepth, model.bodyHeight),
    bodyMaterial
  );
  body.position.z = model.bodyHeight / 2;
  body.userData = userData;
  runtimeAxesGroup.add(body);
  return {};
}

export function beamOriginLocal(model) {
  if (model.kind === 'mirrorball') {
    return { y: 0, z: model.sphereRadius * 2 };
  }
  if (model.kind === 'moving_head') {
    const halfDepth = model.headDepth * 0.5;
    return {
      y: halfDepth + model.headDepth * 0.12,
      z: model.baseHeight + model.headOffsetZ + model.headHeight * 0.05,
    };
  }
  if (model.kind === 'motionstrip') {
    return {
      y: model.bodyDepth * 0.7,
      z: model.bodyHeight,
    };
  }
  if (model.kind === 'laser') {
    return {
      y: 0,
      z: model.bodyHeight,
    };
  }
  return {
    y: model.bodyDepth / 2,
    z: model.bodyHeight / 2,
  };
}

export function lensRadiusForModel(model) {
  if (model.kind === 'mirrorball') {
    return model.sphereRadius * 0.12;
  }
  if (model.kind === 'laser') {
    return desktopBodySize() * 0.15;
  }
  if (model.kind === 'bulb') {
    return desktopBodySize() * 0.42;
  }
  return desktopBodySize() * 0.25;
}
