/**
 * Venue editor fixture geometry aligned with desktop OpenGL renderers:
 * parrot/vj/renderers/bulb.py, moving_head.py, motionstrip.py, laser.py
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

function parLikeDimensions() {
  const bs = desktopBodySize();
  return {
    bodyWidth: bs,
    bodyDepth: bs * 0.3,
    bodyHeight: bs,
  };
}

function movingHeadDimensions() {
  const bs = desktopBodySize();
  const baseHeight = bs * 0.3;
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

/**
 * Full visual description for cones, lens, and mesh construction.
 */
export function resolveFixtureVisualModel(fixtureType) {
  const bs = desktopBodySize();
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
 * Beam origin in moving-head aim group local space (pivot at top of base).
 * @param {ReturnType<typeof resolveFixtureVisualModel>} model
 */
export function beamOriginMovingHeadAimLocal(model) {
  return {
    y: model.headDepth * 0.6,
    z: model.headOffsetZ + model.headHeight * 0.05,
  };
}

/**
 * @param {import('three').MeshStandardMaterial} bodyMaterial
 * @returns {{ aimGroup?: import('three').Group, stripPanGroup?: import('three').Group }}
 */
export function addFixtureOpaqueMeshes(THREE, runtimeAxesGroup, bodyMaterial, model, entityKey) {
  const userData = { entityKey };

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
    const head = new THREE.Mesh(
      new THREE.BoxGeometry(model.headWidth, model.headDepth, model.headHeight),
      bodyMaterial
    );
    head.position.set(0, 0, model.headOffsetZ);
    head.userData = userData;
    aimGroup.add(head);
    runtimeAxesGroup.add(aimGroup);
    return { aimGroup };
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
  if (model.kind === 'moving_head') {
    return {
      y: model.headDepth * 0.6,
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
    y: model.bodyDepth * 0.7,
    z: model.bodyHeight,
  };
}

export function lensRadiusForModel(model) {
  if (model.kind === 'laser') {
    return desktopBodySize() * 0.15;
  }
  return desktopBodySize() * 0.25;
}
