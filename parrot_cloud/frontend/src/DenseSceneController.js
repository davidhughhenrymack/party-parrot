import {
  addFixtureOpaqueMeshes,
  beamOriginLocal,
  beamOriginMovingHeadAimLocal,
  lensRadiusForModel,
  resolveFixtureVisualModel,
} from './fixtureModels.js';
import { tiltRadiansForWebHead } from './movingHeadPreviewMath.js';

export function createNoopSceneController(
  viewportEl,
  message = '3D viewport disabled in test mode.',
) {
  if (viewportEl && message != null) {
    viewportEl.textContent = message;
  }
  return {
    applyBootstrap() { },
    applyVjPreviewUrl() { },
    resetVideoWallToPlaceholder() { },
    updateFloorPreview() { },
    updateVideoWallPreview() { },
    setView() { },
    setSelection() { },
    setInteractionMode() { },
    setLightingMode() { },
    applyFixtureRuntimeState() { },
    destroy() { },
  };
}

export async function createSceneController({
  viewportEl,
  isTestMode,
  onSelectionChange,
  onFixtureContextMenu,
  onFixtureTransform,
  onFixtureTransformsBatch,
  onVideoWallTransform,
  onSceneObjectTransform,
  onTransformDragStateChange,
}) {
  if (isTestMode) {
    return createNoopSceneController(viewportEl);
  }

  try {
    const [THREE, { OrbitControls }, { TransformControls }] = await Promise.all([
      import('three'),
      import('three/addons/controls/OrbitControls.js'),
      import('three/addons/controls/TransformControls.js'),
    ]);

    return createThreeSceneController({
      THREE,
      OrbitControls,
      TransformControls,
      viewportEl,
      onSelectionChange,
      onFixtureContextMenu,
      onFixtureTransform,
      onFixtureTransformsBatch,
      onVideoWallTransform,
      onSceneObjectTransform,
      onTransformDragStateChange,
    });
  } catch (error) {
    console.error('Failed to initialize 3D viewport:', error);
    return createNoopSceneController(viewportEl, '3D viewport failed to load.');
  }
}

function createThreeSceneController({
  THREE,
  OrbitControls,
  TransformControls,
  viewportEl,
  onSelectionChange,
  onFixtureContextMenu,
  onFixtureTransform,
  onFixtureTransformsBatch,
  onVideoWallTransform,
  onSceneObjectTransform,
  onTransformDragStateChange,
}) {
  const localState = {
    venueSnapshot: null,
    venueScale: null,
    currentView: 'top',
    interactionMode: 'select',
    activeCamera: null,
    selectedEntityKey: null,
    /** @type {string[]} */
    selectedFixtureIds: [],
    multiDragInitialPivot: null,
    multiDragInitialPositions: null,
    entityMap: new Map(),
    dragSyncTimeoutId: null,
    lastFixtureDragSyncAt: 0,
    isTransformDragging: false,
    /** Ignore canvas background clicks that immediately follow a transform drag (they clear selection). */
    suppressCanvasDeselectUntil: 0,
    destroyed: false,
  };
  const fixtureDragSyncIntervalMs = 100;
  /** Upstage of table back edge (venue −y), meters — matches runtime / repository default. */
  /** 0 = silhouette plane flush to the table’s upstage edge (local −Y). */
  const DJ_SILHOUETTE_BEHIND_TABLE_EXTRA_M = 0;
  /** Extra downward offset (m) so feet sit on the table top; plane centering + texture padding read high at 0.02. */
  const DJ_SILHOUETTE_CLEARANCE_BELOW_TABLE_TOP_M = 0.22;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1b2430);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  viewportEl.replaceChildren(renderer.domElement);

  const perspectiveCamera = new THREE.PerspectiveCamera(48, 1, 0.1, 5000);
  const orthoCamera = new THREE.OrthographicCamera(-10, 10, 10, -10, 0.1, 5000);
  /** Venue floor is Z-up; perspective editing uses Z-up. OrbitControls must be constructed with this basis. */
  perspectiveCamera.up.set(0, 0, 1);
  localState.activeCamera = perspectiveCamera;

  const orbitControls = new OrbitControls(perspectiveCamera, renderer.domElement);
  orbitControls.enableDamping = true;
  orbitControls.enableZoom = true;
  orbitControls.rotateSpeed = 0.9;
  orbitControls.panSpeed = 0.9;
  orbitControls.minPolarAngle = 0.12;
  orbitControls.maxPolarAngle = Math.PI - 0.12;

  const transformControls = new TransformControls(perspectiveCamera, renderer.domElement);
  transformControls.setMode('translate');
  transformControls.setSpace('world');
  transformControls.size = 0.8;

  /** three.js names the center handle `XYZ` (octahedron in translate, box in uniform scale). */
  function hideTransformControlsCenterHandles(gizmoRoot) {
    if (!gizmoRoot?.gizmo || !gizmoRoot?.picker) {
      return;
    }
    for (const mode of ['translate', 'scale']) {
      const vis = gizmoRoot.gizmo[mode];
      const pick = gizmoRoot.picker[mode];
      for (const group of [vis, pick]) {
        if (!group?.children) {
          continue;
        }
        for (const child of group.children) {
          if (child.name === 'XYZ') {
            child.visible = false;
          }
        }
      }
    }
  }

  const transformControlsGizmo = transformControls._gizmo;
  if (transformControlsGizmo?.isTransformControlsGizmo) {
    const origUpdateMatrixWorld = transformControlsGizmo.updateMatrixWorld.bind(transformControlsGizmo);
    transformControlsGizmo.updateMatrixWorld = function updateMatrixWorldPatched(force) {
      origUpdateMatrixWorld(force);
      hideTransformControlsCenterHandles(this);
    };
  }

  scene.add(transformControls.getHelper());

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
  scene.add(ambientLight);
  const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
  directionalLight.position.set(10, -14, 18);
  scene.add(directionalLight);

  const LIGHTING_PRESETS = {
    default: {
      background: 0x1b2430,
      ambient: { color: 0xffffff, intensity: 0.9 },
      directional: { color: 0xffffff, intensity: 1.0, x: 10, y: -14, z: 18 },
      floorColor: 0x13202d,
    },
    bright: {
      background: 0x2a3444,
      ambient: { color: 0xffffff, intensity: 1.15 },
      directional: { color: 0xffffff, intensity: 0.65, x: 8, y: -12, z: 20 },
      floorColor: 0x1c2a3a,
    },
    contrast: {
      background: 0x0c1016,
      ambient: { color: 0xb8c4d4, intensity: 0.32 },
      directional: { color: 0xffffff, intensity: 1.55, x: 12, y: -16, z: 14 },
      floorColor: 0x0a121a,
    },
    night: {
      background: 0x05070c,
      ambient: { color: 0x4466aa, intensity: 0.22 },
      directional: { color: 0xffe8cc, intensity: 0.5, x: 6, y: -10, z: 12 },
      floorColor: 0x060a10,
    },
  };

  function setLightingMode(mode) {
    const preset = LIGHTING_PRESETS[mode] ?? LIGHTING_PRESETS.default;
    scene.background = new THREE.Color(preset.background);
    ambientLight.color.setHex(preset.ambient.color);
    ambientLight.intensity = preset.ambient.intensity;
    directionalLight.color.setHex(preset.directional.color);
    directionalLight.intensity = preset.directional.intensity;
    directionalLight.position.set(preset.directional.x, preset.directional.y, preset.directional.z);
    floorMaterial.color.setHex(preset.floorColor);
    floorMaterial.needsUpdate = true;
  }

  const sceneContent = new THREE.Group();
  scene.add(sceneContent);

  /** World-space pivot for translating multiple fixtures together (not cleared with sceneContent). */
  const multiSelectPivot = new THREE.Group();
  multiSelectPivot.name = 'multiFixturePivot';
  scene.add(multiSelectPivot);

  const floorMaterial = new THREE.MeshStandardMaterial({
    color: 0x13202d,
    metalness: 0.05,
    roughness: 0.92,
  });
  const floorMesh = new THREE.Mesh(new THREE.BoxGeometry(10, 10, 0.08), floorMaterial);
  floorMesh.position.set(0, 0, -0.04);
  scene.add(floorMesh);

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  let videoWallPlaceholderCanvas = null;

  const videoWallTexture = createVideoWallTexture();
  /** @type {AbortController | null} */
  let vjPreviewLoadAbortController = null;
  const djSilhouetteTexture = createDjSilhouetteTexture();

  function setMaterialDimmed(material, dimmed) {
    if (!material) {
      return;
    }
    material.transparent = dimmed;
    material.opacity = dimmed ? 0.7 : 1.0;
    material.needsUpdate = true;
  }

  function resizeRenderer() {
    const width = viewportEl.clientWidth;
    const height = viewportEl.clientHeight;
    renderer.setSize(width, height);

    perspectiveCamera.aspect = width / height || 1;
    perspectiveCamera.updateProjectionMatrix();

    const scale = localState.venueScale ?? { orthoWidth: 14, orthoDepth: 14 };
    const aspect = width / height || 1;
    const frustumWidth = Math.max(scale.orthoWidth, scale.orthoDepth * aspect, 8);
    const frustumHeight = frustumWidth / aspect;
    orthoCamera.left = -frustumWidth / 2;
    orthoCamera.right = frustumWidth / 2;
    orthoCamera.top = frustumHeight / 2;
    orthoCamera.bottom = -frustumHeight / 2;
    orthoCamera.updateProjectionMatrix();
  }

  function computeVenueScale(venueSnapshot) {
    const floorObject = getSceneObject(venueSnapshot, 'floor');
    const width = Math.max(floorObject?.width || venueSnapshot.floor_width || 1, 1);
    const depth = Math.max(floorObject?.height || venueSnapshot.floor_depth || 1, 1);
    return {
      width,
      depth,
      worldWidth: width,
      worldDepth: depth,
      orthoWidth: Math.max(width * 1.5, 8),
      orthoDepth: Math.max(depth * 1.5, 8),
      heightFocus: Math.max(8, venueSnapshot.floor_height || 10),
      maxDimension: Math.max(width, depth),
    };
  }

  function getSceneObject(venueSnapshot, kind) {
    return venueSnapshot?.scene_objects?.find((sceneObject) => sceneObject.kind === kind) ?? null;
  }

  function syncFloorMeshFromSnapshot() {
    if (!localState.venueSnapshot || !localState.venueScale) {
      return;
    }
    const floorObject = getSceneObject(localState.venueSnapshot, 'floor');
    if (floorObject) {
      floorMesh.position.copy(toScenePosition(floorObject.x, floorObject.y, floorObject.z));
      floorMesh.rotation.set(
        floorObject.rotation_x || 0,
        floorObject.rotation_y || 0,
        floorObject.rotation_z || 0
      );
    }
    floorMesh.scale.set(
      localState.venueScale.worldWidth / 10,
      localState.venueScale.worldDepth / 10,
      1
    );
  }

  function updateFloorPreview({ width, depth }) {
    if (!localState.venueSnapshot) {
      return;
    }
    const floorObject = getSceneObject(localState.venueSnapshot, 'floor');
    if (!floorObject) {
      return;
    }

    if (Number.isFinite(width) && width > 0) {
      floorObject.width = width;
      floorObject.x = 0;
      localState.venueSnapshot.floor_width = width;
    }
    if (Number.isFinite(depth) && depth > 0) {
      floorObject.height = depth;
      floorObject.y = 0;
      localState.venueSnapshot.floor_depth = depth;
    }

    localState.venueScale = computeVenueScale(localState.venueSnapshot);
    syncFloorMeshFromSnapshot();
    resizeRenderer();
    orbitControls.target.copy(
      localState.currentView === 'perspective' ? getFloorCenterTarget() : (() => {
        const flatTarget = getFloorCenterTarget();
        flatTarget.z = localState.venueScale.heightFocus * 0.5;
        return flatTarget;
      })()
    );
    orbitControls.update();
  }

  function getFloorCenterTarget() {
    const floorObject = getSceneObject(localState.venueSnapshot, 'floor');
    if (!floorObject || !localState.venueScale) {
      return new THREE.Vector3(0, 0, 0);
    }
    return toScenePosition(floorObject.x, floorObject.y, 0);
  }

  /**
   * OrbitControls maps camera offset into Y-up spherical space using _quat from the camera's
   * `up` at construction. When we switch activeCamera (Z-up perspective vs Y-up top ortho, etc.)
   * we must refresh that basis or mouse orbit drags couple azimuth/polar incorrectly.
   */
  function syncOrbitControlsSphericalBasis(controls) {
    const yUp = new THREE.Vector3(0, 1, 0);
    controls._quat.setFromUnitVectors(controls.object.up, yUp);
    controls._quatInverse.copy(controls._quat).invert();
  }

  function paintVideoWallPlaceholderCanvas(canvas, context) {
    const palette = [
      '#ff4d6d',
      '#fb7185',
      '#f59e0b',
      '#fde047',
      '#34d399',
      '#22d3ee',
      '#60a5fa',
      '#a78bfa',
    ];

    context.fillStyle = '#0b1020';
    context.fillRect(0, 0, canvas.width, canvas.height);

    for (let row = 0; row < canvas.height; row += 1) {
      for (let col = 0; col < canvas.width; col += 1) {
        const colorIndex = (row * 3 + col * 5 + (row % 3) * 7) % palette.length;
        context.fillStyle = palette[colorIndex];
        context.globalAlpha = 0.55 + ((row + col) % 4) * 0.1;
        context.fillRect(col, row, 1, 1);
      }
    }

    context.globalAlpha = 1;
    context.fillStyle = 'rgba(255,255,255,0.35)';
    for (let band = 0; band < canvas.height; band += 4) {
      context.fillRect(0, band, canvas.width, 1);
    }
  }

  function createVideoWallTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 18;
    const context = canvas.getContext('2d');
    paintVideoWallPlaceholderCanvas(canvas, context);
    videoWallPlaceholderCanvas = canvas;

    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.magFilter = THREE.NearestFilter;
    texture.minFilter = THREE.NearestFilter;
    // The screen mesh is a PlaneGeometry rotated ``-π/2`` around X so its
    // normal faces the audience (+Y). That rotation sends the plane's
    // original top edge (+Y, UV v=1) to world -Z — i.e. the bottom of the
    // viewer's screen — so the default ``flipY=true`` upload leaves the VJ
    // preview visually upside-down. Disable flipY once on the shared texture
    // so JPEG row 0 maps to UV v=0 and the post-rotation image reads right
    // side up. The placeholder pattern is rotationally symmetric so it is
    // unaffected by the change.
    texture.flipY = false;
    // ``toScenePosition`` flips venue X into three.js -X so the default
    // perspective camera (positioned audience-side at +Y, up=+Z) sees the
    // stage from the audience POV — its world-right axis points to three.js
    // -X. Because the video-wall plane has no parent rotation, the raw UV
    // ``u=0..1`` would map to local -X..+X which corresponds to camera
    // right..left — i.e. the preview image would read mirrored compared
    // to the raw ``/api/runtime/vj-preview`` JPEG. Flip the texture
    // horizontally to cancel that audience-view mirror.
    texture.wrapS = THREE.ClampToEdgeWrapping;
    texture.repeat.x = -1;
    texture.offset.x = 1;
    return texture;
  }

  function resetVideoWallToPlaceholder() {
    if (vjPreviewLoadAbortController) {
      vjPreviewLoadAbortController.abort();
      vjPreviewLoadAbortController = null;
    }
    if (!videoWallPlaceholderCanvas) {
      return;
    }
    const prevImg = videoWallTexture.image;
    if (
      prevImg
      && prevImg !== videoWallPlaceholderCanvas
      && typeof prevImg.close === 'function'
    ) {
      prevImg.close();
    }
    const ctx = videoWallPlaceholderCanvas.getContext('2d');
    paintVideoWallPlaceholderCanvas(videoWallPlaceholderCanvas, ctx);
    videoWallTexture.image = videoWallPlaceholderCanvas;
    videoWallTexture.magFilter = THREE.NearestFilter;
    videoWallTexture.minFilter = THREE.NearestFilter;
    videoWallTexture.colorSpace = THREE.SRGBColorSpace;
    videoWallTexture.needsUpdate = true;
  }

  function applyVjPreviewUrl(url) {
    if (vjPreviewLoadAbortController) {
      vjPreviewLoadAbortController.abort();
    }
    const ac = new AbortController();
    vjPreviewLoadAbortController = ac;
    void (async () => {
      try {
        const response = await fetch(url, {
          cache: 'no-store',
          credentials: 'same-origin',
          signal: ac.signal,
        });
        if (!response.ok) {
          if (!localState.destroyed) {
            resetVideoWallToPlaceholder();
          }
          return;
        }
        const blob = await response.blob();
        let decoded;
        try {
          decoded = await createImageBitmap(blob);
        } catch {
          decoded = await new Promise((resolve, reject) => {
            const objectUrl = URL.createObjectURL(blob);
            const img = new Image();
            img.onload = () => {
              URL.revokeObjectURL(objectUrl);
              resolve(img);
            };
            img.onerror = () => {
              URL.revokeObjectURL(objectUrl);
              reject(new Error('vj preview image decode failed'));
            };
            img.src = objectUrl;
          });
        }
        if (localState.destroyed || ac.signal.aborted) {
          if (decoded && typeof decoded.close === 'function') {
            decoded.close();
          }
          return;
        }
        const prevImg = videoWallTexture.image;
        if (
          prevImg
          && prevImg !== videoWallPlaceholderCanvas
          && typeof prevImg.close === 'function'
        ) {
          prevImg.close();
        }
        videoWallTexture.image = decoded;
        videoWallTexture.colorSpace = THREE.SRGBColorSpace;
        videoWallTexture.generateMipmaps = true;
        videoWallTexture.minFilter = THREE.LinearMipmapLinearFilter;
        videoWallTexture.magFilter = THREE.LinearFilter;
        videoWallTexture.needsUpdate = true;
      } catch (err) {
        if (err && err.name === 'AbortError') {
          return;
        }
        if (!localState.destroyed) {
          resetVideoWallToPlaceholder();
        }
      } finally {
        if (vjPreviewLoadAbortController === ac) {
          vjPreviewLoadAbortController = null;
        }
      }
    })();
  }

  function createDjSilhouetteTexture() {
    const texture = new THREE.TextureLoader().load('/api/assets/dj.png');
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  /**
   * Venue axes: x = audience-left (−) to audience-right (+), y = depth, z = height (AGENTS.md).
   * The perspective camera sits on +venue Y with up = +Z; that view maps world −X to the
   * screen's right. Negate x so stored venue x matches screen left/right and matches the
   * desktop OpenGL room (venue x → room X without that flip).
   */
  function toScenePosition(x, y, z) {
    return new THREE.Vector3(-x, y, z);
  }

  function fromScenePosition(vector) {
    return {
      x: -vector.x,
      y: vector.y,
      z: vector.z,
    };
  }

  function getEntityFromObject(object) {
    let current = object;
    while (current) {
      if (current.userData?.entityKey) {
        return localState.entityMap.get(current.userData.entityKey) ?? null;
      }
      current = current.parent;
    }
    return null;
  }

  function applySelectionVisuals() {
    const fixtureSelectionActive =
      localState.selectedFixtureIds.length > 0 ||
      (localState.selectedEntityKey &&
        localState.entityMap.get(localState.selectedEntityKey)?.type === 'fixture');

    setMaterialDimmed(floorMaterial, fixtureSelectionActive);
    const selectedFixtureSet = new Set(localState.selectedFixtureIds);
    localState.entityMap.forEach((entity, entityKey) => {
      const isSelected =
        entity.type === 'fixture'
          ? selectedFixtureSet.has(entityKey)
          : entityKey === localState.selectedEntityKey;
      entity.bodyMaterial.emissive?.setHex(isSelected ? 0x2563eb : 0x000000);
      entity.bodyMaterial.emissiveIntensity = isSelected ? 0.85 : 0.0;
      setMaterialDimmed(entity.bodyMaterial, fixtureSelectionActive && !isSelected);
      (entity.secondaryMaterials || []).forEach((material) => {
        setMaterialDimmed(material, fixtureSelectionActive && !isSelected);
      });
      if (entity.helperMaterial) {
        entity.helperMaterial.opacity = isSelected ? 0.22 : fixtureSelectionActive ? 0.056 : 0.08;
      }
      const strobeGate = entity.runtimeStrobeGate ?? 1;
      if (entity.coneMaterial) {
        const ro = entity.runtimeConeOpacity ?? 0;
        if (ro <= 1e-5) {
          entity.coneMaterial.opacity = 0;
        } else {
          let mul = 1.0;
          if (fixtureSelectionActive && !isSelected) {
            mul *= 0.62;
          }
          if (isSelected) {
            mul *= 1.28;
          }
          entity.coneMaterial.opacity = Math.min(1, ro * mul) * strobeGate;
        }
      }
      if (entity.prismMaterials && entity.prismMaterials.length > 0 && entity.prismOn) {
        const baseRo = entity.runtimeConeOpacity ?? 0;
        let mul = 1.0;
        if (fixtureSelectionActive && !isSelected) mul *= 0.62;
        if (isSelected) mul *= 1.28;
        const op = Math.min(1, baseRo * mul) * strobeGate;
        for (const m of entity.prismMaterials) {
          m.opacity = op;
        }
      }
      if (entity.lensMaterial && typeof entity.runtimeLensOpacity === 'number') {
        entity.lensMaterial.opacity = entity.runtimeLensOpacity * strobeGate;
      }
      if (entity.mirrorballBeamMaterials && entity.mirrorballBeamMaterials.length > 0) {
        const ro = entity.runtimeMirrorballOpacity ?? 0;
        if (ro <= 1e-5) {
          for (const m of entity.mirrorballBeamMaterials) {
            m.opacity = 0;
          }
        } else {
          let mul = 1.0;
          if (fixtureSelectionActive && !isSelected) {
            mul *= 0.62;
          }
          if (isSelected) {
            mul *= 1.28;
          }
          const o = Math.min(1, ro * mul) * strobeGate;
          for (const m of entity.mirrorballBeamMaterials) {
            m.opacity = o;
          }
        }
      }
    });
  }

  function clearSelection(options = {}) {
    const { notifyParent = true } = options;
    localState.selectedEntityKey = null;
    localState.selectedFixtureIds = [];
    transformControls.detach();
    multiSelectPivot.position.set(0, 0, 0);
    applySelectionVisuals();
    if (notifyParent) {
      onSelectionChange(null);
    }
  }

  function computeFixtureSelectionCenter(fixtureIds) {
    const center = new THREE.Vector3();
    let n = 0;
    fixtureIds.forEach((id) => {
      const entity = localState.entityMap.get(id);
      if (entity?.type === 'fixture') {
        center.add(entity.group.position);
        n += 1;
      }
    });
    if (n === 0) {
      return null;
    }
    center.multiplyScalar(1 / n);
    return center;
  }

  function setFixtureSelection(fixtureIds, options = {}) {
    const { notifyParent = true } = options;
    const unique = [...new Set(fixtureIds)].filter((id) => {
      const e = localState.entityMap.get(id);
      return e && e.type === 'fixture';
    });
    if (unique.length === 0) {
      clearSelection({ notifyParent });
      return;
    }

    localState.selectedFixtureIds = unique;
    localState.selectedEntityKey = unique.length === 1 ? unique[0] : 'multi_fixture';

    transformControls.detach();
    if (unique.length === 1) {
      const entity = localState.entityMap.get(unique[0]);
      transformControls.attach(entity.group);
    } else {
      transformControls.setMode('translate');
      const center = computeFixtureSelectionCenter(unique);
      if (!center) {
        clearSelection({ notifyParent });
        return;
      }
      multiSelectPivot.position.copy(center);
      multiSelectPivot.rotation.set(0, 0, 0);
      transformControls.attach(multiSelectPivot);
    }

    applySelectionVisuals();
    if (notifyParent) {
      const fixtures = unique
        .map((id) => localState.entityMap.get(id))
        .filter(Boolean)
        .map((e) => e.fixture);
      onSelectionChange({ type: 'fixture', fixtureIds: unique, fixtures });
    }
  }

  function setSelection(selection, options = {}) {
    const { notifyParent = true } = options;
    if (!selection) {
      clearSelection({ notifyParent });
      return;
    }

    if (selection.type === 'fixture') {
      const ids =
        Array.isArray(selection.fixtureIds) && selection.fixtureIds.length > 0
          ? selection.fixtureIds
          : selection.fixtureId
            ? [selection.fixtureId]
            : [];
      if (ids.length === 0) {
        clearSelection({ notifyParent });
        return;
      }
      setFixtureSelection(ids, { notifyParent });
      return;
    }

    localState.selectedFixtureIds = [];
    const entityKey = selection.type === 'dj_booth' ? 'dj_booth' : 'video_wall';
    const entity = localState.entityMap.get(entityKey);
    if (!entity) {
      clearSelection({ notifyParent });
      return;
    }

    localState.selectedEntityKey = entityKey;
    transformControls.attach(entity.group);
    applySelectionVisuals();
    if (notifyParent) {
      if (entity.type === 'dj_booth') {
        onSelectionChange({ type: 'dj_booth' });
      } else {
        onSelectionChange({ type: 'video_wall' });
      }
    }
  }

  function updatePointer(event) {
    const bounds = renderer.domElement.getBoundingClientRect();
    pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
    pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
    raycaster.setFromCamera(pointer, localState.activeCamera);
  }

  function syncInteractionMode() {
    if (localState.interactionMode === 'rotate') {
      orbitControls.enabled = true;
      orbitControls.enableRotate = localState.currentView === 'perspective';
      orbitControls.enablePan = false;
      orbitControls.screenSpacePanning = false;
      orbitControls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
      orbitControls.mouseButtons.RIGHT = THREE.MOUSE.ROTATE;
      renderer.domElement.style.cursor = 'grab';
      transformControls.enabled = false;
      orbitControls.update();
      return;
    }

    if (localState.interactionMode === 'pan') {
      orbitControls.enabled = true;
      orbitControls.enableRotate = false;
      orbitControls.enablePan = true;
      orbitControls.screenSpacePanning = true;
      orbitControls.mouseButtons.LEFT = THREE.MOUSE.PAN;
      orbitControls.mouseButtons.RIGHT = THREE.MOUSE.PAN;
      renderer.domElement.style.cursor = 'move';
      transformControls.enabled = false;
      return;
    }

    orbitControls.enabled = true;
    orbitControls.enableRotate = false;
    orbitControls.enablePan = false;
    orbitControls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
    orbitControls.mouseButtons.RIGHT = THREE.MOUSE.PAN;
    renderer.domElement.style.cursor = 'default';
    transformControls.enabled = true;
  }

  function buildFixtureTransformPayload(entity) {
    const domainPosition = fromScenePosition(entity.group.position);
    const rotation = entity.group.rotation;
    return {
      fixtureId: entity.fixture.id,
      x: domainPosition.x,
      y: domainPosition.y,
      z: domainPosition.z,
      rotation_x: rotation.x,
      rotation_y: rotation.y,
      rotation_z: rotation.z,
    };
  }

  function scheduleFixtureDragSync() {
    if (!localState.isTransformDragging) {
      return;
    }
    if (localState.selectedEntityKey === 'multi_fixture') {
      return;
    }
    const entity = localState.entityMap.get(localState.selectedEntityKey);
    if (!entity || entity.type !== 'fixture') {
      return;
    }

    const flush = () => {
      localState.dragSyncTimeoutId = null;
      const activeEntity = localState.entityMap.get(localState.selectedEntityKey);
      if (!activeEntity || activeEntity.type !== 'fixture') {
        return;
      }
      localState.lastFixtureDragSyncAt = Date.now();
      void onFixtureTransform(buildFixtureTransformPayload(activeEntity));
    };

    const elapsed = Date.now() - localState.lastFixtureDragSyncAt;
    if (elapsed >= fixtureDragSyncIntervalMs) {
      flush();
      return;
    }
    if (localState.dragSyncTimeoutId === null) {
      localState.dragSyncTimeoutId = window.setTimeout(
        flush,
        fixtureDragSyncIntervalMs - elapsed
      );
    }
  }

  function shouldSuppressCanvasDeselect() {
    return performance.now() < localState.suppressCanvasDeselectUntil;
  }

  function onPointerDown(event) {
    if (transformControls.axis) {
      return;
    }
    if (localState.interactionMode === 'pan' || localState.interactionMode === 'rotate') {
      return;
    }
    updatePointer(event);
    const groups = Array.from(localState.entityMap.values()).map((entity) => entity.group);
    const hits = raycaster.intersectObjects(groups, true);
    if (hits.length === 0) {
      if (localState.interactionMode === 'select' && !shouldSuppressCanvasDeselect()) {
        clearSelection();
      }
      return;
    }
    const entity = getEntityFromObject(hits[0].object);
    if (!entity) {
      if (localState.interactionMode === 'select' && !shouldSuppressCanvasDeselect()) {
        clearSelection();
      }
      return;
    }
    if (entity.type === 'fixture') {
      const fid = entity.fixture.id;
      if (event.metaKey || event.ctrlKey) {
        const next = new Set(localState.selectedFixtureIds);
        if (next.has(fid)) {
          next.delete(fid);
        } else {
          next.add(fid);
        }
        const arr = [...next];
        if (arr.length === 0) {
          clearSelection();
        } else {
          setFixtureSelection(arr);
        }
      } else {
        setSelection({ type: 'fixture', fixtureId: fid });
      }
    } else if (entity.type === 'dj_booth') {
      setSelection({ type: 'dj_booth' });
    } else {
      setSelection({ type: 'video_wall' });
    }
  }

  function onContextMenu(event) {
    event.preventDefault();
    if (localState.interactionMode === 'pan' || localState.interactionMode === 'rotate') {
      return;
    }
    updatePointer(event);
    const groups = Array.from(localState.entityMap.values())
      .filter((entity) => entity.type === 'fixture')
      .map((entity) => entity.group);
    const hits = raycaster.intersectObjects(groups, true);
    if (hits.length === 0) {
      return;
    }
    const entity = getEntityFromObject(hits[0].object);
    if (!entity || entity.type !== 'fixture') {
      return;
    }
    setSelection({ type: 'fixture', fixtureId: entity.fixture.id });
    onFixtureContextMenu({
      fixture: entity.fixture,
      x: event.clientX + 8,
      y: event.clientY + 8,
    });
  }

  function setView(viewName) {
    localState.currentView = viewName;
    const scale = localState.venueScale ?? {
      worldWidth: 12,
      worldDepth: 12,
      heightFocus: 10,
      maxDimension: 12,
    };
    const floorCenterTarget = getFloorCenterTarget();
    const flatTarget = floorCenterTarget.clone();
    flatTarget.z = scale.heightFocus * 0.5;
    if (viewName === 'perspective') {
      localState.activeCamera = perspectiveCamera;
      perspectiveCamera.position.set(0, scale.worldDepth * 1.35, scale.heightFocus * 0.95);
      perspectiveCamera.up.set(0, 0, 1);
      perspectiveCamera.lookAt(floorCenterTarget);
      orbitControls.enableRotate = true;
    } else if (viewName === 'front') {
      localState.activeCamera = orthoCamera;
      orthoCamera.zoom = 1;
      const frontEye = flatTarget.clone();
      frontEye.y -= scale.worldDepth * 1.6;
      orthoCamera.position.copy(frontEye);
      orthoCamera.up.set(0, 0, 1);
      orthoCamera.lookAt(flatTarget);
      orbitControls.enableRotate = false;
    } else if (viewName === 'side') {
      localState.activeCamera = orthoCamera;
      orthoCamera.zoom = 1;
      const sideEye = flatTarget.clone();
      sideEye.x += scale.worldWidth * 1.6;
      orthoCamera.position.copy(sideEye);
      orthoCamera.up.set(0, 0, 1);
      orthoCamera.lookAt(flatTarget);
      orbitControls.enableRotate = false;
    } else {
      localState.activeCamera = orthoCamera;
      orthoCamera.zoom = 1;
      orthoCamera.position.set(0, 0, scale.maxDimension * 3.2);
      orthoCamera.up.set(0, 1, 0);
      orthoCamera.lookAt(floorCenterTarget);
      orbitControls.enableRotate = false;
    }
    orbitControls.object = localState.activeCamera;
    syncOrbitControlsSphericalBasis(orbitControls);
    orbitControls.target.copy(viewName === 'perspective' ? floorCenterTarget : flatTarget);
    orbitControls.update();
    transformControls.camera = localState.activeCamera;
    syncInteractionMode();
  }

  function setInteractionMode(mode) {
    localState.interactionMode = mode;
    syncInteractionMode();
  }

  /** Max cone opacity when dimmer is 1; at dimmer 0 the cone is fully faded out. */
  const CONE_OPACITY_AT_FULL_DIM = 0.5;

  function applyFixtureRuntimeVisual(entity, vis, rgb, dim) {
    const dimClamped = Math.max(0, Math.min(1, dim));
    const r = Math.min(1, rgb[0] * dimClamped);
    const g = Math.min(1, rgb[1] * dimClamped);
    const b = Math.min(1, rgb[2] * dimClamped);
    // `strobe` mirrors the desktop renderer: when dimmer>0 and strobe>0, the
    // beam toggles on/off at 5–30 Hz (see FixtureRenderer.get_effective_dimmer
    // in parrot/vj/renderers/base.py). The gating itself happens in the
    // animate() loop — here we just record the base strobe amount so the
    // per-frame tick knows whether/how fast to flicker.
    entity.runtimeStrobe = typeof vis.strobe === 'number'
      ? Math.max(0, Math.min(1, vis.strobe))
      : 0;
    // Intentionally do NOT recolour `entity.bodyMaterial` — the housing keeps
    // its neutral dark shell. DMX colour is visible through the beam and lens
    // materials below.
    if (entity.coneMaterial) {
      entity.coneMaterial.color.setRGB(
        Math.min(1, r * 1.15),
        Math.min(1, g * 1.15),
        Math.min(1, b * 1.15)
      );
      entity.runtimeConeOpacity = dimClamped * CONE_OPACITY_AT_FULL_DIM;
      entity.coneMaterial.opacity =
        entity.runtimeConeOpacity * (entity.runtimeStrobeGate ?? 1);
    }
    const prismOn = vis.prism_on === true;
    const prismSpeed =
      typeof vis.prism_rotate_speed === 'number'
        ? Math.max(-1, Math.min(1, vis.prism_rotate_speed))
        : 0;
    entity.prismOn = prismOn;
    entity.prismRotateSpeed = prismSpeed;
    if (entity.prismGroup) {
      entity.prismGroup.visible = prismOn;
    }
    if (entity.coneMesh) {
      entity.coneMesh.visible = !prismOn;
    }
    // Focus ∈ [0 wide, 1 tight] narrows the beam/prism sub-beams' base radius.
    // Geometry tips are at the lens; scaling X/Z shrinks the far end. Must match
    // FOCUS_TIGHT_MULT / FOCUS_WIDE_MULT in parrot/vj/renderers/moving_head.py.
    const focus = typeof vis.focus === 'number'
      ? Math.max(0, Math.min(1, vis.focus))
      : 0;
    const focusWidth = 1.0 + (0.22 - 1.0) * focus;
    if (entity.coneMesh) {
      entity.coneMesh.scale.set(focusWidth, 1, focusWidth);
    }
    if (entity.prismSubMeshes && entity.prismSubMeshes.length > 0) {
      for (const sub of entity.prismSubMeshes) {
        sub.scale.set(focusWidth, 1, focusWidth);
      }
    }
    if (entity.prismMaterials && entity.prismMaterials.length > 0) {
      const subOp = prismOn ? dimClamped * CONE_OPACITY_AT_FULL_DIM : 0;
      for (const m of entity.prismMaterials) {
        m.color.setRGB(
          Math.min(1, r * 1.15),
          Math.min(1, g * 1.15),
          Math.min(1, b * 1.15)
        );
        m.opacity = subOp;
      }
    }
    if (entity.lensMaterial) {
      entity.lensMaterial.color.setRGB(
        Math.min(1, r + 0.12),
        Math.min(1, g + 0.12),
        Math.min(1, b + 0.12)
      );
      entity.runtimeLensOpacity = 0.35 + dimClamped * 0.58;
      entity.lensMaterial.opacity =
        entity.runtimeLensOpacity * (entity.runtimeStrobeGate ?? 1);
    }
    if (entity.aimGroup && entity.headPivotGroup) {
      // Pan-then-tilt kinematics: `aimGroup` is the parent (yoke pan around
      // Z/up), `headPivotGroup` is the child (head tilt around X). Three.js
      // composes world = R_pan * R_tilt, which matches real moving-head
      // mechanics. See fixtureModels.js for the matching comment and
      // parrot/vj/renderers/moving_head.py::_moving_body_rotation for the
      // desktop equivalent.
      // Tilt convention: logical tilt_deg = 135° means "head straight up"
      // (mechanical center of a Chauvet 270° sweep). See
      // `movingHeadPreviewMath.tiltRadiansForWebHead` and
      // `parrot/vj/moving_head_visual.tilt_radians_for_render` — the desktop
      // renderer and the web preview agree on which logical tilt value = up.
      const pan = typeof vis.pan_deg === 'number' ? THREE.MathUtils.degToRad(vis.pan_deg) : 0;
      const tilt = typeof vis.tilt_deg === 'number' ? tiltRadiansForWebHead(vis.tilt_deg) : 0;
      entity.aimGroup.rotation.set(0, 0, 0);
      entity.aimGroup.rotation.order = 'ZXY';
      entity.aimGroup.rotation.z = -pan;
      entity.headPivotGroup.rotation.set(0, 0, 0);
      entity.headPivotGroup.rotation.order = 'ZXY';
      entity.headPivotGroup.rotation.x = tilt;
    } else {
      // Fallback for legacy placements without a split aim/tilt pivot. With
      // `rotation.order = 'ZXY'` Three.js applies the intrinsic rotations in
      // Z-then-X-then-Y order: the group first pans (around Z/up), and the
      // tilt (around X) is then applied in the *panned* frame — matching real
      // moving-head mechanics, same result as the split parent/child groups
      // above.
      const pivotGroup = entity.headPivotGroup ?? entity.aimGroup;
      if (pivotGroup) {
        const pan = typeof vis.pan_deg === 'number' ? THREE.MathUtils.degToRad(vis.pan_deg) : 0;
        const tilt = typeof vis.tilt_deg === 'number' ? tiltRadiansForWebHead(vis.tilt_deg) : 0;
        pivotGroup.rotation.order = 'ZXY';
        pivotGroup.rotation.z = -pan;
        pivotGroup.rotation.x = tilt;
      }
    }
    if (entity.stripPanGroup && typeof vis.bar_pan_deg === 'number') {
      entity.stripPanGroup.rotation.x = THREE.MathUtils.degToRad(vis.bar_pan_deg);
    }
    if (entity.mirrorballBeamMaterials && entity.mirrorballBeamMaterials.length > 0) {
      const baseOp = dimClamped * 0.14;
      entity.runtimeMirrorballOpacity = baseOp;
      // Mirrorball now has a dimmer + RGB DMX footprint — tint the reflected
      // sparkles with the fixture's raw color (not the dim-pre-multiplied
      // `r/g/b`), since opacity alone carries the dim. The small floor keeps
      // a sparkle feel on deep hues.
      const br = Math.min(1, rgb[0] + 0.08);
      const bg = Math.min(1, rgb[1] + 0.08);
      const bb = Math.min(1, rgb[2] + 0.08);
      const gatedOp = baseOp * (entity.runtimeStrobeGate ?? 1);
      for (const m of entity.mirrorballBeamMaterials) {
        m.color.setRGB(br, bg, bb);
        m.opacity = gatedOp;
      }
    }
  }

  function applyFixtureRuntimeState(payload) {
    if (!payload || Number(payload.version) !== 1 || !Array.isArray(payload.fixtures)) {
      return;
    }
    const byId = new Map(
      payload.fixtures.map((entry) => [String(entry.id), entry]),
    );
    localState.entityMap.forEach((entity) => {
      if (entity.type !== 'fixture') {
        return;
      }
      const vis = byId.get(String(entity.fixture.id));
      if (!vis || !Array.isArray(vis.rgb) || vis.rgb.length < 3) {
        entity.runtimeStrobe = 0;
        entity.runtimeStrobeGate = 1;
        if (entity.coneMaterial) {
          entity.runtimeConeOpacity = 0;
          entity.coneMaterial.opacity = 0;
        }
        if (entity.mirrorballBeamMaterials && entity.mirrorballBeamMaterials.length > 0) {
          entity.runtimeMirrorballOpacity = 0;
          for (const m of entity.mirrorballBeamMaterials) {
            m.opacity = 0;
          }
        }
        return;
      }
      const dim = typeof vis.dimmer === 'number' ? vis.dimmer : 0;
      applyFixtureRuntimeVisual(entity, vis, vis.rgb, dim);
    });
    applySelectionVisuals();
  }

  function createFixtureEntity(fixture) {
    const group = new THREE.Group();
    group.position.copy(toScenePosition(fixture.x, fixture.y, fixture.z));
    group.rotation.set(fixture.rotation_x || 0, fixture.rotation_y || 0, fixture.rotation_z || 0);
    group.userData = { entityKey: fixture.id };

    const runtimeAxesGroup = new THREE.Group();
    group.add(runtimeAxesGroup);
    const profile = resolveFixtureVisualModel(fixture.fixture_type);

    // Housing stays a neutral dark colour at all times. DMX colour only drives
    // the beam cone, the lens bulb, and (via selection) the emissive tint —
    // matching how real moving heads / PARs look from the audience.
    const bodyMaterial = new THREE.MeshStandardMaterial({
      color: fixture.is_manual ? 0x3d3620 : 0x2d333d,
      metalness: 0.08,
      roughness: 0.56,
    });
    const secondaryMaterials = [];

    const placed = addFixtureOpaqueMeshes(THREE, runtimeAxesGroup, bodyMaterial, profile, fixture.id);
    const beamParent =
      placed.headPivotGroup ?? placed.aimGroup ?? placed.stripPanGroup ?? runtimeAxesGroup;

    let coneMaterial = null;
    let lensMaterial = null;
    let coneMeshRef = null;
    let prismGroupRef = null;
    let prismMaterialsRef = [];
    let prismSubMeshesRef = [];
    if (profile.kind !== 'mirrorball') {
      let beam;
      if (placed.headPivotGroup) {
        beam = beamOriginMovingHeadAimLocal(profile);
      } else if (placed.stripPanGroup) {
        beam = { y: profile.bodyDepth * 0.7, z: profile.bodyHeight };
      } else {
        beam = beamOriginLocal(profile);
      }

      const coneLength = profile.coneLength;
      const coneRadius = profile.coneRadius;
      coneMaterial = new THREE.MeshBasicMaterial({
        color: fixture.is_manual ? 0xfbbf24 : 0xfb7185,
        transparent: true,
        opacity: 0,
        side: THREE.DoubleSide,
        depthWrite: false,
      });
      // ConeGeometry: tip at +Y, base at -Y. Beam should be narrow at the lens and widen along the throw;
      // flip 180° so the tip sits on the lens (same convention as ArrowHelper cone).
      const coneMesh = new THREE.Mesh(
        new THREE.ConeGeometry(coneRadius, coneLength, 24, 1, true),
        coneMaterial
      );
      coneMesh.rotateX(Math.PI);
      coneMesh.position.set(0, beam.y + coneLength / 2, beam.z);
      coneMesh.userData = { entityKey: fixture.id };
      beamParent.add(coneMesh);
      coneMeshRef = coneMesh;

      // Prism splay group: 7 thinner cones splayed off-axis around the main beam.
      // Hidden by default; shown when runtime reports `prism_on` for this fixture.
      if (profile.kind === 'moving_head') {
        const prismGroup = new THREE.Group();
        prismGroup.position.set(0, beam.y, beam.z);
        prismGroup.visible = false;
        prismGroup.userData = { entityKey: fixture.id };
        const facets = 7;
        // Wide-splay prism fan: more angle, chunkier sub-cones so the prism mode
        // reads clearly as a splayed beam rather than a tight bundle.
        const splayRad = THREE.MathUtils.degToRad(18);
        const subR = coneRadius * 0.75;
        const subL = coneLength;
        for (let i = 0; i < facets; i += 1) {
          const mat = new THREE.MeshBasicMaterial({
            color: fixture.is_manual ? 0xfbbf24 : 0xfb7185,
            transparent: true,
            opacity: 0,
            side: THREE.DoubleSide,
            depthWrite: false,
          });
          prismMaterialsRef.push(mat);
          const sub = new THREE.Mesh(
            new THREE.ConeGeometry(subR, subL, 16, 1, true),
            mat
          );
          // Sub-cone's tip sits at the facet-group origin along its local +Y.
          sub.rotateX(Math.PI);
          sub.position.set(0, subL / 2, 0);
          prismSubMeshesRef.push(sub);
          const facetGroup = new THREE.Group();
          facetGroup.rotation.order = 'YXZ';
          facetGroup.rotation.y = (2 * Math.PI * i) / facets;
          facetGroup.rotation.x = splayRad;
          facetGroup.add(sub);
          prismGroup.add(facetGroup);
        }
        beamParent.add(prismGroup);
        prismGroupRef = prismGroup;
      }

      lensMaterial = new THREE.MeshBasicMaterial({
        color: fixture.is_manual ? 0xfbbf24 : 0xf8fafc,
        transparent: true,
        opacity: 0.95,
      });
      const lens = new THREE.Mesh(
        new THREE.SphereGeometry(lensRadiusForModel(profile), 12, 12),
        lensMaterial
      );
      lens.position.set(0, beam.y, beam.z);
      lens.userData = { entityKey: fixture.id };
      beamParent.add(lens);
      secondaryMaterials.push(lensMaterial);
    }

    const hitRadius = profile.kind === 'mirrorball' ? Math.max(0.55, profile.sphereRadius * 1.15) : 0.62;
    const hitMesh = new THREE.Mesh(
      new THREE.SphereGeometry(hitRadius, 16, 16),
      new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.001,
        depthWrite: false,
      })
    );
    hitMesh.userData = { entityKey: fixture.id };
    group.add(hitMesh);

    sceneContent.add(group);
    const entityBase = {
      type: 'fixture',
      fixture,
      group,
      bodyMaterial,
      secondaryMaterials,
      helperMaterial: null,
      coneMaterial,
      lensMaterial,
      aimGroup: placed.aimGroup ?? null,
      headPivotGroup: placed.headPivotGroup ?? null,
      stripPanGroup: placed.stripPanGroup ?? null,
      profile,
    };
    if (profile.kind === 'mirrorball') {
      localState.entityMap.set(fixture.id, {
        ...entityBase,
        mirrorballBeamMaterials: placed.mirrorballBeamMaterials ?? [],
        mirrorballBeamsGroup: placed.mirrorballBeamsGroup ?? null,
        runtimeMirrorballOpacity: 0,
        runtimeConeOpacity: 0,
      });
    } else {
      localState.entityMap.set(fixture.id, {
        ...entityBase,
        runtimeConeOpacity: 0,
        coneMesh: coneMeshRef,
        prismGroup: prismGroupRef,
        prismMaterials: prismMaterialsRef,
        prismSubMeshes: prismSubMeshesRef,
        prismOn: false,
        prismRotateSpeed: 0,
      });
    }
  }

  function createVideoWallEntity(videoWall) {
    const sceneObject = getSceneObject(localState.venueSnapshot, 'video_wall');
    const group = new THREE.Group();
    group.position.copy(toScenePosition(videoWall.x, videoWall.y, videoWall.z));
    if (sceneObject) {
      group.rotation.set(
        sceneObject.rotation_x || 0,
        sceneObject.rotation_y || 0,
        sceneObject.rotation_z || 0
      );
    }
    group.userData = { entityKey: 'video_wall' };

    const bodyMaterial = new THREE.MeshStandardMaterial({
      color: videoWall.locked ? 0x24381d : 0x111827,
      metalness: 0.22,
      roughness: 0.58,
    });
    const wallWidth = Math.max(videoWall.width, 0.8);
    const wallDepth = Math.max(videoWall.depth, 0.1);
    const wallHeight = Math.max(videoWall.height, 0.8);
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(
        wallWidth,
        wallDepth,
        wallHeight
      ),
      bodyMaterial
    );
    body.userData = { entityKey: 'video_wall' };
    group.add(body);

    const screenMaterial = new THREE.MeshStandardMaterial({
      map: videoWallTexture,
      emissive: new THREE.Color(videoWall.locked ? 0x60a5fa : 0xffffff),
      emissiveMap: videoWallTexture,
      emissiveIntensity: videoWall.locked ? 0.45 : 0.75,
      metalness: 0.02,
      roughness: 0.22,
      side: THREE.DoubleSide,
    });
    const screen = new THREE.Mesh(
      new THREE.PlaneGeometry(wallWidth * 0.94, wallHeight * 0.94),
      screenMaterial
    );
    screen.rotation.x = -Math.PI / 2;
    screen.position.set(0, wallDepth / 2 + 0.01, 0);
    screen.userData = { entityKey: 'video_wall' };
    group.add(screen);

    const hitMesh = new THREE.Mesh(
      new THREE.BoxGeometry(
        Math.max(wallWidth, 0.9),
        Math.max(wallDepth, 0.18),
        Math.max(wallHeight, 0.9)
      ),
      new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.001,
        depthWrite: false,
      })
    );
    hitMesh.userData = { entityKey: 'video_wall' };
    group.add(hitMesh);

    sceneContent.add(group);
    localState.entityMap.set('video_wall', {
      type: 'video_wall',
      group,
      bodyMaterial,
      secondaryMaterials: [screenMaterial],
    });
  }

  function updateVideoWallPreview({ width, height }) {
    if (!localState.venueSnapshot) {
      return;
    }
    const entity = localState.entityMap.get('video_wall');
    if (!entity) {
      return;
    }
    const prev = localState.venueSnapshot.video_wall;
    const vw = { ...prev };
    if (Number.isFinite(width) && width > 0) {
      vw.width = width;
    }
    if (Number.isFinite(height) && height > 0) {
      vw.height = height;
    }
    localState.venueSnapshot.video_wall = vw;
    const sceneObject = getSceneObject(localState.venueSnapshot, 'video_wall');
    if (sceneObject) {
      if (Number.isFinite(width) && width > 0) {
        sceneObject.width = width;
      }
      if (Number.isFinite(height) && height > 0) {
        sceneObject.height = height;
      }
    }

    const wasSelected = localState.selectedEntityKey === 'video_wall';
    transformControls.detach();
    sceneContent.remove(entity.group);
    entity.group.traverse((child) => {
      if (child.geometry) {
        child.geometry.dispose();
      }
    });
    localState.entityMap.delete('video_wall');
    createVideoWallEntity(vw);
    if (wasSelected) {
      const nextEntity = localState.entityMap.get('video_wall');
      if (nextEntity) {
        localState.selectedEntityKey = 'video_wall';
        transformControls.attach(nextEntity.group);
        applySelectionVisuals();
      }
    }
    resizeRenderer();
  }

  function createDjBoothEntity(djTable, djCutout) {
    if (!djTable || !djCutout) {
      return;
    }

    const group = new THREE.Group();
    group.position.copy(toScenePosition(djTable.x, djTable.y, djTable.z));
    group.rotation.set(
      djTable.rotation_x || 0,
      djTable.rotation_y || 0,
      djTable.rotation_z || 0
    );
    group.userData = { entityKey: 'dj_booth' };

    const tableMaterial = new THREE.MeshStandardMaterial({
      color: 0x2d1b16,
      metalness: 0.04,
      roughness: 0.9,
    });
    const table = new THREE.Mesh(
      new THREE.BoxGeometry(
        Math.max(djTable.width, 0.2),
        Math.max(djTable.depth, 0.2),
        Math.max(djTable.height, 0.2)
      ),
      tableMaterial
    );
    table.position.set(0, 0, 0);
    table.userData = { entityKey: 'dj_booth' };
    group.add(table);

    const depth = Math.max(djTable.depth, 0.02);
    const silH = Math.max(djCutout.height, 0.1);
    const tableHalfH = Math.max(djTable.height, 0.2) / 2;
    const behindLocalY = -(depth / 2 + DJ_SILHOUETTE_BEHIND_TABLE_EXTRA_M);
    /** Feet sit along local −Z from the plane center (texture + rotation.z); place feet just under table top. */
    const cutLocalZ =
      tableHalfH + silH / 2 - DJ_SILHOUETTE_CLEARANCE_BELOW_TABLE_TOP_M;

    const cutout = new THREE.Mesh(
      new THREE.PlaneGeometry(Math.max(djCutout.width, 0.3), Math.max(djCutout.height, 0.5)),
      new THREE.MeshBasicMaterial({
        map: djSilhouetteTexture,
        color: 0xffffff,
        transparent: true,
        opacity: 1,
        alphaTest: 0.02,
        side: THREE.DoubleSide,
      })
    );
    cutout.position.set(0, behindLocalY, cutLocalZ);
    cutout.rotation.x = -Math.PI / 2;
    cutout.rotation.z = Math.PI;
    cutout.userData = { entityKey: 'dj_booth' };
    group.add(cutout);

    const hitMesh = new THREE.Mesh(
      new THREE.BoxGeometry(2.2, 1.6, 2.0),
      new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.001,
        depthWrite: false,
      })
    );
    hitMesh.userData = { entityKey: 'dj_booth' };
    group.add(hitMesh);

    sceneContent.add(group);
    localState.entityMap.set('dj_booth', {
      type: 'dj_booth',
      group,
      bodyMaterial: tableMaterial,
      secondaryMaterials: [cutout.material],
      djTable,
      djCutout,
    });
  }

  function applyBootstrap(venueSnapshot) {
    const previousSelectedEntityKey = localState.selectedEntityKey;
    const previousFixtureSelectionIds =
      localState.selectedFixtureIds.length >= 2
        ? [...localState.selectedFixtureIds]
        : previousSelectedEntityKey &&
          localState.entityMap.get(previousSelectedEntityKey)?.type === 'fixture'
          ? [previousSelectedEntityKey]
          : [];
    const previousVenueId = localState.venueSnapshot?.summary?.id ?? null;
    /** Keep orbit pose when the same venue is reloaded (e.g. after PATCH / WS); setView() resets camera by design. */
    let preservedOrbit = null;
    if (
      previousVenueId !== null
      && venueSnapshot?.summary?.id === previousVenueId
    ) {
      preservedOrbit = {
        target: orbitControls.target.clone(),
        position: localState.activeCamera.position.clone(),
        /** setView() forces orthoCamera.zoom = 1; restore after rebuild (top/front/side). */
        orthoZoom:
          localState.activeCamera === orthoCamera ? orthoCamera.zoom : null,
      };
    }

    localState.venueSnapshot = venueSnapshot;
    localState.venueScale = venueSnapshot ? computeVenueScale(venueSnapshot) : null;
    sceneContent.clear();
    localState.entityMap.clear();
    localState.selectedEntityKey = null;
    localState.selectedFixtureIds = [];
    transformControls.detach();

    if (!venueSnapshot) {
      applySelectionVisuals();
      if (previousSelectedEntityKey) {
        onSelectionChange(null);
      }
      resizeRenderer();
      return;
    }

    syncFloorMeshFromSnapshot();

    createVideoWallEntity(venueSnapshot.video_wall);
    createDjBoothEntity(
      getSceneObject(venueSnapshot, 'dj_table'),
      getSceneObject(venueSnapshot, 'dj_cutout')
    );
    venueSnapshot.fixtures.forEach(createFixtureEntity);
    resizeRenderer();
    setView(localState.currentView);

    if (preservedOrbit) {
      orbitControls.target.copy(preservedOrbit.target);
      localState.activeCamera.position.copy(preservedOrbit.position);
      if (
        preservedOrbit.orthoZoom != null
        && localState.activeCamera === orthoCamera
      ) {
        orthoCamera.zoom = preservedOrbit.orthoZoom;
        orthoCamera.updateProjectionMatrix();
      }
      orbitControls.update();
    }

    const restoreIds =
      previousVenueId !== null &&
        venueSnapshot?.summary?.id === previousVenueId &&
        previousFixtureSelectionIds.length > 0 &&
        previousFixtureSelectionIds.every((id) => localState.entityMap.has(id))
        ? previousFixtureSelectionIds
        : null;

    if (restoreIds) {
      setFixtureSelection(restoreIds);
    } else {
      const restoreKey =
        previousSelectedEntityKey != null ? String(previousSelectedEntityKey) : null;
      if (restoreKey && localState.entityMap.has(restoreKey)) {
        const entity = localState.entityMap.get(restoreKey);
        localState.selectedEntityKey = restoreKey;
        if (entity.type === 'fixture') {
          localState.selectedFixtureIds = [restoreKey];
        }
        transformControls.attach(entity.group);
        applySelectionVisuals();
      } else {
        applySelectionVisuals();
        if (previousSelectedEntityKey || previousFixtureSelectionIds.length) {
          onSelectionChange(null);
        }
      }
    }
  }

  transformControls.addEventListener('dragging-changed', (event) => {
    if (event.value) {
      localState.isTransformDragging = true;
      orbitControls.enabled = false;
      renderer.domElement.style.cursor = 'grabbing';
      if (localState.selectedEntityKey === 'multi_fixture') {
        localState.multiDragInitialPivot = multiSelectPivot.position.clone();
        localState.multiDragInitialPositions = new Map();
        localState.selectedFixtureIds.forEach((id) => {
          const ent = localState.entityMap.get(id);
          if (ent?.type === 'fixture') {
            localState.multiDragInitialPositions.set(id, ent.group.position.clone());
          }
        });
      }
      onTransformDragStateChange?.(true);
      return;
    }
    localState.isTransformDragging = false;
    localState.multiDragInitialPivot = null;
    localState.multiDragInitialPositions = null;
    localState.suppressCanvasDeselectUntil = performance.now() + 320;
    syncInteractionMode();
    onTransformDragStateChange?.(false);
  });

  transformControls.addEventListener('objectChange', () => {
    if (
      localState.selectedEntityKey === 'multi_fixture' &&
      localState.multiDragInitialPivot &&
      localState.multiDragInitialPositions
    ) {
      const delta = new THREE.Vector3().subVectors(
        multiSelectPivot.position,
        localState.multiDragInitialPivot
      );
      localState.selectedFixtureIds.forEach((id) => {
        const ent = localState.entityMap.get(id);
        const initial = localState.multiDragInitialPositions.get(id);
        if (ent?.type === 'fixture' && initial) {
          ent.group.position.copy(initial).add(delta);
        }
      });
      return;
    }
    scheduleFixtureDragSync();
  });

  transformControls.addEventListener('mouseUp', async () => {
    if (!localState.selectedEntityKey) {
      return;
    }

    if (localState.selectedEntityKey === 'multi_fixture' && onFixtureTransformsBatch) {
      if (localState.dragSyncTimeoutId !== null) {
        window.clearTimeout(localState.dragSyncTimeoutId);
        localState.dragSyncTimeoutId = null;
      }
      const payloads = localState.selectedFixtureIds
        .map((id) => localState.entityMap.get(id))
        .filter((e) => e && e.type === 'fixture')
        .map((e) => buildFixtureTransformPayload(e));
      if (payloads.length > 0) {
        await onFixtureTransformsBatch(payloads);
      }
      return;
    }

    const entity = localState.entityMap.get(localState.selectedEntityKey);
    if (!entity) {
      return;
    }

    if (localState.dragSyncTimeoutId !== null) {
      window.clearTimeout(localState.dragSyncTimeoutId);
      localState.dragSyncTimeoutId = null;
    }

    const domainPosition = fromScenePosition(entity.group.position);
    const rotation = entity.group.rotation;
    if (entity.type === 'fixture') {
      await onFixtureTransform(buildFixtureTransformPayload(entity));
    } else if (entity.type === 'video_wall') {
      await onVideoWallTransform({
        x: domainPosition.x,
        y: domainPosition.y,
        z: domainPosition.z,
      });
    } else if (entity.type === 'dj_booth') {
      const newTable = {
        x: domainPosition.x,
        y: domainPosition.y,
        z: domainPosition.z,
      };
      const rot = entity.group.rotation;
      const depth = Math.max(entity.djTable.depth, 0.02);
      const silH = Math.max(entity.djCutout.height, 0.1);
      const tableHalfH = Math.max(entity.djTable.height, 0.2) / 2;
      const behindLocalY = -(depth / 2 + DJ_SILHOUETTE_BEHIND_TABLE_EXTRA_M);
      const cutLocalZ =
        tableHalfH + silH / 2 - DJ_SILHOUETTE_CLEARANCE_BELOW_TABLE_TOP_M;
      const offset = new THREE.Vector3(0, behindLocalY, cutLocalZ);
      offset.applyEuler(rot);
      const cutVenue = {
        x: newTable.x + offset.x,
        y: newTable.y + offset.y,
        z: newTable.z + offset.z,
      };
      await onSceneObjectTransform({
        type: 'dj_booth',
        objects: [
          {
            kind: 'dj_table',
            x: newTable.x,
            y: newTable.y,
            z: newTable.z,
            rotation_x: rot.x,
            rotation_y: rot.y,
            rotation_z: rot.z,
          },
          {
            kind: 'dj_cutout',
            x: cutVenue.x,
            y: cutVenue.y,
            z: cutVenue.z,
            rotation_x: rot.x,
            rotation_y: rot.y,
            rotation_z: rot.z,
          },
        ],
      });
    }
  });

  renderer.domElement.addEventListener('pointerdown', onPointerDown);
  renderer.domElement.addEventListener('contextmenu', onContextMenu);
  window.addEventListener('resize', resizeRenderer);

  resizeRenderer();
  setView('perspective');
  setInteractionMode('select');

  function animate() {
    if (localState.destroyed) {
      return;
    }
    requestAnimationFrame(animate);
    orbitControls.update();
    const now = performance.now();
    const mbSpin = now * 0.00012;
    // Prism splay group rotation: rotate_speed in [-1,1] → ~0.5 Hz at full speed.
    const prismPhase = now * 0.001 * Math.PI;
    // Strobe gate: mirrors `FixtureRenderer.get_effective_dimmer` in
    // parrot/vj/renderers/base.py — strobe 0..1 maps to 5..30 Hz on/off.
    const timeSec = now / 1000;
    let strobeGateChanged = false;
    localState.entityMap.forEach((entity) => {
      if (entity.type === 'fixture' && entity.mirrorballBeamsGroup) {
        entity.mirrorballBeamsGroup.rotation.z = mbSpin;
      }
      if (
        entity.type === 'fixture' &&
        entity.prismGroup &&
        entity.prismOn &&
        entity.prismRotateSpeed !== 0
      ) {
        entity.prismGroup.rotation.y = prismPhase * entity.prismRotateSpeed;
      }
      if (entity.type === 'fixture') {
        const strobe = entity.runtimeStrobe ?? 0;
        let gate = 1;
        if (strobe > 0) {
          const hz = 5.0 + strobe * 25.0;
          gate = Math.floor(timeSec * hz) % 2 === 1 ? 1 : 0;
        }
        if ((entity.runtimeStrobeGate ?? 1) !== gate) {
          entity.runtimeStrobeGate = gate;
          strobeGateChanged = true;
        }
      }
    });
    if (strobeGateChanged) {
      applySelectionVisuals();
    }
    renderer.render(scene, localState.activeCamera);
  }
  animate();

  return {
    applyBootstrap,
    applyVjPreviewUrl,
    resetVideoWallToPlaceholder,
    updateFloorPreview,
    updateVideoWallPreview,
    setView,
    setSelection,
    setInteractionMode,
    setLightingMode,
    applyFixtureRuntimeState,
    destroy() {
      localState.destroyed = true;
      if (vjPreviewLoadAbortController) {
        vjPreviewLoadAbortController.abort();
        vjPreviewLoadAbortController = null;
      }
      renderer.domElement.removeEventListener('pointerdown', onPointerDown);
      renderer.domElement.removeEventListener('contextmenu', onContextMenu);
      window.removeEventListener('resize', resizeRenderer);
      if (localState.dragSyncTimeoutId !== null) {
        window.clearTimeout(localState.dragSyncTimeoutId);
      }
      transformControls.detach();
      renderer.dispose();
      viewportEl.replaceChildren();
    },
  };
}
