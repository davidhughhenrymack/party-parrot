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
    setExpensiveEffects() { },
    setNamedPositionPreviewOverride() { },
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
    lightingMode: 'default',
    expensiveEffects: {
      bloom: true,
      dynamicLighting: true,
    },
    multiDragInitialPivot: null,
    multiDragInitialPositions: null,
    entityMap: new Map(),
    dragSyncTimeoutId: null,
    lastFixtureDragSyncAt: 0,
    isTransformDragging: false,
    /** Ignore canvas background clicks that immediately follow a transform drag (they clear selection). */
    suppressCanvasDeselectUntil: 0,
    namedPositionPreviewOverrides: new Map(),
    destroyed: false,
  };
  const fixtureDragSyncIntervalMs = 100;
  /** Upstage of table back edge (venue −y), meters — matches runtime / repository default. */
  /** 0 = silhouette plane flush to the table’s upstage edge (local −Y). */
  const DJ_SILHOUETTE_BEHIND_TABLE_EXTRA_M = 0;
  /** Extra downward offset (m) so feet sit on the table top; plane centering + texture padding read high at 0.02. */
  const DJ_SILHOUETTE_CLEARANCE_BELOW_TABLE_TOP_M = 0.22;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x030407);
  scene.fog = new THREE.FogExp2(0x05070c, 0.018);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  viewportEl.replaceChildren(renderer.domElement);
  const BASE_RENDER_LAYER = 0;
  const BEAM_RENDER_LAYER = 1;

  const perspectiveCamera = new THREE.PerspectiveCamera(48, 1, 0.1, 5000);
  const orthoCamera = new THREE.OrthographicCamera(-10, 10, 10, -10, 0.1, 5000);
  /** Venue floor is Z-up; perspective editing uses Z-up. OrbitControls must be constructed with this basis. */
  perspectiveCamera.up.set(0, 0, 1);
  localState.activeCamera = perspectiveCamera;

  const bloomTargetOptions = {
    depthBuffer: false,
    stencilBuffer: false,
    format: THREE.RGBAFormat,
    type: THREE.UnsignedByteType,
  };
  const beamLayerTarget = new THREE.WebGLRenderTarget(1, 1, {
    ...bloomTargetOptions,
    depthBuffer: true,
  });
  const bloomPingTarget = new THREE.WebGLRenderTarget(1, 1, bloomTargetOptions);
  const bloomPongTarget = new THREE.WebGLRenderTarget(1, 1, bloomTargetOptions);
  const bloomCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const bloomQuadGeometry = new THREE.PlaneGeometry(2, 2);
  const bloomBlurMaterial = new THREE.ShaderMaterial({
    uniforms: {
      sourceTexture: { value: null },
      texelSize: { value: new THREE.Vector2(1, 1) },
      direction: { value: new THREE.Vector2(1, 0) },
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = vec4(position.xy, 0.0, 1.0);
      }
    `,
    fragmentShader: `
      uniform sampler2D sourceTexture;
      uniform vec2 texelSize;
      uniform vec2 direction;
      varying vec2 vUv;

      void main() {
        vec2 stepUv = texelSize * direction;
        vec4 sum = texture2D(sourceTexture, vUv) * 0.227027;
        sum += texture2D(sourceTexture, vUv + stepUv * 1.384615) * 0.316216;
        sum += texture2D(sourceTexture, vUv - stepUv * 1.384615) * 0.316216;
        sum += texture2D(sourceTexture, vUv + stepUv * 3.230769) * 0.070270;
        sum += texture2D(sourceTexture, vUv - stepUv * 3.230769) * 0.070270;
        gl_FragColor = sum;
      }
    `,
    depthTest: false,
    depthWrite: false,
  });
  const bloomCompositeMaterial = new THREE.ShaderMaterial({
    uniforms: {
      bloomTexture: { value: bloomPongTarget.texture },
      bloomStrength: { value: 2.05 },
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = vec4(position.xy, 0.0, 1.0);
      }
    `,
    fragmentShader: `
      uniform sampler2D bloomTexture;
      uniform float bloomStrength;
      varying vec2 vUv;

      void main() {
        vec3 glow = texture2D(bloomTexture, vUv).rgb * bloomStrength;
        float alpha = clamp(max(max(glow.r, glow.g), glow.b), 0.0, 0.72);
        gl_FragColor = vec4(glow, alpha);
      }
    `,
    transparent: true,
    blending: THREE.NormalBlending,
    depthTest: false,
    depthWrite: false,
  });
  const bloomScene = new THREE.Scene();
  const bloomQuad = new THREE.Mesh(bloomQuadGeometry, bloomBlurMaterial);
  bloomScene.add(bloomQuad);

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
  const RUNTIME_DIRECTIONAL_LIGHT_COUNT = 10;
  const runtimeDirectionalLights = Array.from({ length: RUNTIME_DIRECTIONAL_LIGHT_COUNT }, () => {
    const light = new THREE.DirectionalLight(0xffffff, 0);
    light.visible = false;
    light.target.position.set(0, 0, 0);
    scene.add(light);
    scene.add(light.target);
    return light;
  });

  const LIGHTING_PRESETS = {
    default: {
      background: 0x030407,
      editorBackground: 0x1b2430,
      ambient: { color: 0xffffff, intensity: 0.9 },
      directional: { color: 0xffffff, intensity: 1.0, x: 10, y: -14, z: 18 },
      floorColor: 0x13202d,
    },
    bright: {
      background: 0x07090d,
      editorBackground: 0x2a3444,
      ambient: { color: 0xffffff, intensity: 1.15 },
      directional: { color: 0xffffff, intensity: 0.65, x: 8, y: -12, z: 20 },
      floorColor: 0x1c2a3a,
    },
    contrast: {
      background: 0x020307,
      editorBackground: 0x0c1016,
      ambient: { color: 0xb8c4d4, intensity: 0.32 },
      directional: { color: 0xffffff, intensity: 1.55, x: 12, y: -16, z: 14 },
      floorColor: 0x0a121a,
    },
    night: {
      background: 0x05070c,
      editorBackground: 0x05070c,
      ambient: { color: 0x4466aa, intensity: 0.22 },
      directional: { color: 0xffe8cc, intensity: 0.5, x: 6, y: -10, z: 12 },
      floorColor: 0x060a10,
    },
  };

  function setLightingMode(mode) {
    localState.lightingMode = mode;
    applyLightingPreset();
  }

  function applyLightingPreset() {
    const mode = localState.lightingMode;
    const preset = LIGHTING_PRESETS[mode] ?? LIGHTING_PRESETS.default;
    const is3d = localState.currentView === 'perspective';
    const dynamicLightingEnabled = localState.expensiveEffects.dynamicLighting;
    const ambient3dScale = dynamicLightingEnabled ? 0.16 : 0.34;
    const key3dScale = dynamicLightingEnabled ? 0.18 : 0.42;
    scene.background = new THREE.Color(is3d ? preset.background : preset.editorBackground);
    scene.fog = is3d ? new THREE.FogExp2(0x05070c, 0.018) : null;
    ambientLight.color.setHex(preset.ambient.color);
    ambientLight.intensity = preset.ambient.intensity * (is3d ? ambient3dScale : 1.0);
    directionalLight.color.setHex(preset.directional.color);
    directionalLight.intensity = preset.directional.intensity * (is3d ? key3dScale : 1.0);
    directionalLight.position.set(preset.directional.x, preset.directional.y, preset.directional.z);
    floorMaterial.color.setHex(preset.floorColor);
    floorMaterial.color.multiplyScalar(0.62);
    floorMaterial.needsUpdate = true;
  }

  const sceneContent = new THREE.Group();
  scene.add(sceneContent);
  const danceFloorPeopleGroup = new THREE.Group();
  danceFloorPeopleGroup.name = 'danceFloorPeopleCutouts';
  scene.add(danceFloorPeopleGroup);

  /** World-space pivot for translating multiple fixtures together (not cleared with sceneContent). */
  const multiSelectPivot = new THREE.Group();
  multiSelectPivot.name = 'multiFixturePivot';
  scene.add(multiSelectPivot);

  const floorMaterial = new THREE.MeshStandardMaterial({
    color: 0x13202d,
    metalness: 0.0,
    roughness: 1.0,
    envMapIntensity: 0.0,
  });
  floorMaterial.specularIntensity = 0.12;
  floorMaterial.color.multiplyScalar(0.62);
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
  let danceFloorPersonTextures = [];
  let danceFloorPersonTextureLoadStarted = false;

  const DANCE_FLOOR_PERSON_STRIPS = [
    [0.055, 0.205],
    [0.145, 0.285],
    [0.235, 0.415],
    [0.375, 0.565],
    [0.545, 0.695],
    [0.655, 0.845],
    [0.795, 0.985],
  ];
  const SQFT_PER_SQM = 10.7639;
  const DANCE_FLOOR_PERSON_SQFT = 12;
  const DANCE_FLOOR_MIN_PEOPLE = 7;
  const DANCE_FLOOR_MAX_PEOPLE = 180;

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
    const bloomScale = Math.max(0.35, Math.min(0.6, window.devicePixelRatio > 1 ? 0.45 : 0.55));
    const bloomWidth = Math.max(1, Math.floor(width * bloomScale));
    const bloomHeight = Math.max(1, Math.floor(height * bloomScale));
    beamLayerTarget.setSize(bloomWidth, bloomHeight);
    bloomPingTarget.setSize(bloomWidth, bloomHeight);
    bloomPongTarget.setSize(bloomWidth, bloomHeight);
    bloomBlurMaterial.uniforms.texelSize.value.set(1 / bloomWidth, 1 / bloomHeight);

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
    updateDanceFloorPeopleCutouts();
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
    context.fillStyle = '#000000';
    context.fillRect(0, 0, canvas.width, canvas.height);
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
    // side up. The black placeholder is unaffected by the change.
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

  function keepLargestDarkComponent(imageData, darknessThreshold = 35) {
    const { data, width, height } = imageData;
    const total = width * height;
    const dark = new Uint8Array(total);
    const visited = new Uint8Array(total);
    for (let i = 0; i < total; i += 1) {
      const p = i * 4;
      const darkness = 255 - (data[p] + data[p + 1] + data[p + 2]) / 3;
      dark[i] = darkness > darknessThreshold ? 1 : 0;
    }

    let best = [];
    const stack = [];
    for (let i = 0; i < total; i += 1) {
      if (!dark[i] || visited[i]) {
        continue;
      }
      const component = [];
      stack.push(i);
      visited[i] = 1;
      while (stack.length > 0) {
        const current = stack.pop();
        component.push(current);
        const x = current % width;
        const y = Math.floor(current / width);
        for (let dy = -1; dy <= 1; dy += 1) {
          for (let dx = -1; dx <= 1; dx += 1) {
            if (dx === 0 && dy === 0) {
              continue;
            }
            const nx = x + dx;
            const ny = y + dy;
            if (nx < 0 || nx >= width || ny < 0 || ny >= height) {
              continue;
            }
            const ni = ny * width + nx;
            if (dark[ni] && !visited[ni]) {
              visited[ni] = 1;
              stack.push(ni);
            }
          }
        }
      }
      if (component.length > best.length) {
        best = component;
      }
    }

    const keep = new Uint8Array(total);
    for (const i of best) {
      keep[i] = 1;
    }
    for (let i = 0; i < total; i += 1) {
      const p = i * 4;
      if (!keep[i]) {
        data[p + 3] = 0;
        continue;
      }
      const darkness = 255 - (data[p] + data[p + 1] + data[p + 2]) / 3;
      const alpha = Math.max(0, Math.min(255, (darkness - 18) * 4.2));
      data[p] = 0;
      data[p + 1] = 0;
      data[p + 2] = 0;
      data[p + 3] = alpha;
    }
    return imageData;
  }

  function loadDanceFloorPersonTextures() {
    if (danceFloorPersonTextureLoadStarted) {
      return;
    }
    danceFloorPersonTextureLoadStarted = true;
    const img = new Image();
    img.onload = () => {
      danceFloorPersonTextures = DANCE_FLOOR_PERSON_STRIPS.map(([x0, x1], index) => {
        const srcX = Math.floor(x0 * img.width);
        const srcW = Math.max(1, Math.ceil((x1 - x0) * img.width));
        const canvas = document.createElement('canvas');
        canvas.width = 192;
        canvas.height = 384;
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, srcX, 0, srcW, img.height, 0, 0, canvas.width, canvas.height);
        const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height);
        ctx.putImageData(keepLargestDarkComponent(pixels), 0, 0);
        const texture = new THREE.CanvasTexture(canvas);
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.name = `dance-floor-person-${index}`;
        return texture;
      });
      updateDanceFloorPeopleCutouts();
    };
    img.onerror = () => {
      danceFloorPersonTextures = [];
    };
    img.src = '/api/assets/dance-floor-people.png';
  }

  function deterministicUnit(seed) {
    const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453;
    return x - Math.floor(x);
  }

  function danceFloorPersonPlacements(width, depth) {
    const areaSqft = Math.max(0, width * depth * SQFT_PER_SQM);
    const count = Math.max(
      DANCE_FLOOR_MIN_PEOPLE,
      Math.min(DANCE_FLOOR_MAX_PEOPLE, Math.round(areaSqft / DANCE_FLOOR_PERSON_SQFT)),
    );
    const aspect = Math.max(0.2, width / Math.max(depth, 0.2));
    const cols = Math.max(1, Math.ceil(Math.sqrt(count * aspect)));
    const rows = Math.max(1, Math.ceil(count / cols));
    const placements = [];
    for (let i = 0; i < count; i += 1) {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const jx = (deterministicUnit(i + 1) - 0.5) * 0.44;
      const jy = (deterministicUnit(i + 1009) - 0.5) * 0.44;
      placements.push({
        x: ((col + 0.5 + jx) / cols - 0.5) * 0.9,
        y: ((row + 0.5 + jy) / rows - 0.5) * 0.9,
        height: 1.55 + deterministicUnit(i + 2003) * 0.38,
      });
    }
    return placements;
  }

  function updateDanceFloorPeopleCutouts() {
    danceFloorPeopleGroup.clear();
    if (!localState.venueSnapshot || !localState.venueScale || danceFloorPersonTextures.length === 0) {
      return;
    }
    const floorObject = getSceneObject(localState.venueSnapshot, 'floor');
    const center = floorObject
      ? toScenePosition(floorObject.x, floorObject.y, floorObject.z)
      : new THREE.Vector3(0, 0, 0);
    const width = localState.venueScale.worldWidth;
    const depth = localState.venueScale.worldDepth;
    const floorTopZ = center.z + 0.05;

    danceFloorPersonPlacements(width, depth).forEach((placement, index) => {
      const texture = danceFloorPersonTextures[index % danceFloorPersonTextures.length];
      const h = placement.height;
      const w = h * 0.38;
      const x = center.x + placement.x * width;
      const y = center.y + placement.y * depth;
      const material = new THREE.MeshBasicMaterial({
        map: texture,
        color: 0x050505,
        transparent: true,
        blending: THREE.CustomBlending,
        blendEquation: THREE.AddEquation,
        blendSrc: THREE.ZeroFactor,
        blendDst: THREE.OneMinusSrcAlphaFactor,
        blendSrcAlpha: THREE.ZeroFactor,
        blendDstAlpha: THREE.OneFactor,
        alphaTest: 0.04,
        side: THREE.DoubleSide,
        depthWrite: true,
      });
      const cutout = new THREE.Mesh(new THREE.PlaneGeometry(w, h), material);
      cutout.position.set(x, y, floorTopZ + h / 2);
      const faceToCenter = new THREE.Vector2(center.x - x, center.y - y);
      const angle = faceToCenter.lengthSq() > 1e-6
        ? Math.atan2(faceToCenter.x, -faceToCenter.y)
        : 0;
      cutout.rotation.order = 'ZXY';
      cutout.rotation.z = angle;
      cutout.rotation.x = Math.PI / 2;
      cutout.userData = { isDanceFloorPersonCutout: true };
      danceFloorPeopleGroup.add(cutout);
    });
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

  /** Top surface of default floor slab in floorMesh local coords (half-thickness z = 0.04). */
  function floorPlaneNdFromMesh(floorMesh, THREE) {
    floorMesh.updateWorldMatrix(true, false);
    const corners = [
      new THREE.Vector3(-5, -5, 0.04),
      new THREE.Vector3(5, -5, 0.04),
      new THREE.Vector3(-5, 5, 0.04),
    ];
    for (let i = 0; i < corners.length; i += 1) {
      corners[i].applyMatrix4(floorMesh.matrixWorld);
    }
    const u = corners[1].clone().sub(corners[0]);
    const v = corners[2].clone().sub(corners[0]);
    const n = u.clone().cross(v);
    if (n.lengthSq() < 1e-14) {
      n.set(0, 0, 1);
    } else {
      n.normalize();
    }
    const d = n.dot(corners[0]);
    return { n, d };
  }

  /** Ray P(t) = origin + t dir, t >= 0; plane n·x = d. Returns min(maxLen, t_hit) or maxLen. */
  function clipRayToPlaneNd(origin, dir, maxLen, planeN, planeD, eps = 1e-5) {
    const denom = planeN.dot(dir);
    if (Math.abs(denom) < eps) {
      return maxLen;
    }
    const t = (planeD - planeN.dot(origin)) / denom;
    if (t <= 0) {
      return maxLen;
    }
    return Math.min(maxLen, t);
  }

  function raySphereHitDistance(origin, dir, center, radius, maxLen) {
    const oc = origin.clone().sub(center);
    const b = 2 * oc.dot(dir);
    const c = oc.dot(oc) - radius * radius;
    const disc = b * b - 4 * c;
    if (disc < 0) {
      return null;
    }
    const root = Math.sqrt(disc);
    const t0 = (-b - root) / 2;
    const t1 = (-b + root) / 2;
    const t = t0 > 0 ? t0 : t1 > 0 ? t1 : null;
    if (t === null || t > maxLen) {
      return null;
    }
    return t;
  }

  function clipRayToFloorAndMirrorballs(origin, dir, maxLen, planeN, planeD) {
    let clip = clipRayToPlaneNd(origin, dir, maxLen, planeN, planeD);
    const center = new THREE.Vector3();
    localState.entityMap.forEach((entity) => {
      if (
        entity.type !== 'fixture' ||
        entity.profile?.kind !== 'mirrorball' ||
        !entity.mirrorballBeamsGroup
      ) {
        return;
      }
      entity.mirrorballBeamsGroup.getWorldPosition(center);
      const hit = raySphereHitDistance(
        origin,
        dir,
        center,
        entity.profile.sphereRadius * 1.35,
        clip,
      );
      if (hit !== null) {
        clip = Math.min(clip, hit);
      }
    });
    return clip;
  }

  function fixtureBeamRayWorld(entity, THREE) {
    if (!entity.beamParent || !entity.beamTipLocal || entity.profile?.kind === 'mirrorball') {
      return null;
    }
    const maxLen = entity.maxBeamLength;
    if (!Number.isFinite(maxLen) || maxLen <= 0) {
      return null;
    }
    const origin = entity.beamTipLocal.clone();
    const far = entity.beamTipLocal.clone().add(new THREE.Vector3(0, maxLen, 0));
    entity.beamParent.localToWorld(origin);
    entity.beamParent.localToWorld(far);
    const dir = far.sub(origin);
    if (dir.lengthSq() < 1e-10) {
      return null;
    }
    dir.normalize();
    return { origin, dir, maxLen };
  }

  function updateMirrorballReflections(THREE) {
    const sourceBeams = [];
    localState.entityMap.forEach((entity) => {
      if (entity.type !== 'fixture' || entity.profile?.kind === 'mirrorball') {
        return;
      }
      const ray = fixtureBeamRayWorld(entity, THREE);
      const dim = Math.max(0, Math.min(1, entity.runtimeDimmerForStrobe ?? 0));
      const gate = entity.runtimeStrobeGate ?? 1;
      const beamOpacity = dim * CONE_OPACITY_AT_FULL_DIM * gate;
      if (!ray || beamOpacity <= 1e-4 || !Array.isArray(entity.runtimeRgb)) {
        return;
      }
      sourceBeams.push({
        ...ray,
        rgb: entity.runtimeRgb,
        opacity: beamOpacity,
        coneRadius: entity.profile?.coneRadius ?? 0.25,
        focusWidth: entity.focusWidth ?? 1,
      });
    });

    const mbCenter = new THREE.Vector3();
    const rayDirWorld = new THREE.Vector3();
    localState.entityMap.forEach((entity) => {
      if (
        entity.type !== 'fixture' ||
        entity.profile?.kind !== 'mirrorball' ||
        !entity.mirrorballBeamRecords?.length ||
        !entity.mirrorballBeamsGroup
      ) {
        return;
      }

      entity.mirrorballBeamsGroup.getWorldPosition(mbCenter);
      const sphereRadius = entity.profile.sphereRadius;
      const hits = [];
      for (const source of sourceBeams) {
        const tCenter = Math.max(0, mbCenter.clone().sub(source.origin).dot(source.dir));
        const coneAtCenter = source.coneRadius * source.focusWidth * (tCenter / source.maxLen);
        const hit = raySphereHitDistance(
          source.origin,
          source.dir,
          mbCenter,
          sphereRadius + coneAtCenter,
          source.maxLen,
        );
        if (hit === null) {
          continue;
        }
        hits.push({
          // Bounce visually back toward the incoming light direction.
          direction: source.dir.clone().multiplyScalar(-1),
          rgb: source.rgb,
          opacity: source.opacity,
        });
      }

      let strongest = 0;
      const mirrorballRotation = entity.mirrorballBeamsGroup.getWorldQuaternion(new THREE.Quaternion());
      for (const record of entity.mirrorballBeamRecords) {
        // Mirrorball cones have their narrow tip at the sphere and their wide
        // end away from it, so their visible travel direction is opposite the
        // stored surface direction.
        rayDirWorld.copy(record.directionLocal)
          .applyQuaternion(mirrorballRotation)
          .multiplyScalar(-1)
          .normalize();
        let bestScore = 0;
        let bestHit = null;
        for (const hit of hits) {
          const score = Math.max(0, rayDirWorld.dot(hit.direction));
          if (score > bestScore) {
            bestScore = score;
            bestHit = hit;
          }
        }
        if (!bestHit || bestScore < 0.72) {
          record.material.userData.runtimeOpacity = 0;
          record.material.opacity = 0;
          continue;
        }
        const spread = (bestScore - 0.72) / 0.28;
        const opacity = Math.min(0.32, bestHit.opacity * (0.18 + spread * 0.42));
        record.material.color.setRGB(
          Math.min(1, bestHit.rgb[0] + 0.08),
          Math.min(1, bestHit.rgb[1] + 0.08),
          Math.min(1, bestHit.rgb[2] + 0.08),
        );
        record.material.userData.runtimeOpacity = opacity;
        record.material.opacity = opacity;
        strongest = Math.max(strongest, opacity);
      }
      entity.runtimeMirrorballOpacity = strongest;
    });
  }

  function updateRuntimeDirectionalLights(THREE) {
    if (
      localState.currentView !== 'perspective' ||
      !localState.expensiveEffects.dynamicLighting
    ) {
      for (const light of runtimeDirectionalLights) {
        light.visible = false;
        light.intensity = 0;
      }
      return;
    }

    const activeBeams = [];
    localState.entityMap.forEach((entity) => {
      if (entity.type !== 'fixture' || entity.profile?.kind === 'mirrorball') {
        return;
      }
      const ray = fixtureBeamRayWorld(entity, THREE);
      const dim = Math.max(0, Math.min(1, entity.runtimeDimmerForStrobe ?? 0));
      const gate = entity.runtimeStrobeGate ?? 1;
      if (!ray || dim <= 1e-4 || gate <= 1e-4 || !Array.isArray(entity.runtimeRgb)) {
        return;
      }
      activeBeams.push({
        ...ray,
        rgb: entity.runtimeRgb,
        intensity: dim * gate,
      });
    });
    activeBeams.sort((a, b) => b.intensity - a.intensity);

    for (let i = 0; i < runtimeDirectionalLights.length; i += 1) {
      const light = runtimeDirectionalLights[i];
      const beam = activeBeams[i];
      if (!beam) {
        light.visible = false;
        light.intensity = 0;
        continue;
      }
      const [r, g, b] = beam.rgb;
      light.visible = true;
      light.color.setRGB(
        Math.min(1, r + 0.04),
        Math.min(1, g + 0.04),
        Math.min(1, b + 0.04),
      );
      light.intensity = Math.min(1.35, 0.2 + beam.intensity * 1.15);
      light.position.copy(beam.origin).addScaledVector(beam.dir, -2.5);
      light.target.position.copy(beam.origin).addScaledVector(beam.dir, 9.0);
      light.target.updateMatrixWorld();
    }
  }

  function setExpensiveEffects(next) {
    localState.expensiveEffects = {
      ...localState.expensiveEffects,
      ...next,
    };
    applyLightingPreset();
    if (!localState.expensiveEffects.dynamicLighting) {
      for (const light of runtimeDirectionalLights) {
        light.visible = false;
        light.intensity = 0;
      }
    }
  }

  function renderFullscreenMaterial(material, target) {
    bloomQuad.material = material;
    renderer.setRenderTarget(target);
    renderer.clear(true, true, true);
    renderer.render(bloomScene, bloomCamera);
  }

  function setSceneColorWrite(root, colorWrite) {
    const changed = [];
    root.traverse((object) => {
      const materials = Array.isArray(object.material)
        ? object.material
        : object.material
          ? [object.material]
          : [];
      for (const material of materials) {
        if (material && material.colorWrite !== colorWrite) {
          changed.push([material, material.colorWrite]);
          material.colorWrite = colorWrite;
        }
      }
    });
    return () => {
      for (const [material, previous] of changed) {
        material.colorWrite = previous;
      }
    };
  }

  function renderBeamBloomLayer(camera) {
    const savedBackground = scene.background;
    const savedAutoClear = renderer.autoClear;
    const savedClearColor = renderer.getClearColor(new THREE.Color()).clone();
    const savedClearAlpha = renderer.getClearAlpha();
    const savedRenderTarget = renderer.getRenderTarget();
    const savedCameraLayerMask = camera.layers.mask;

    scene.background = null;
    renderer.autoClear = true;
    renderer.setClearColor(0x000000, 0);
    renderer.setRenderTarget(beamLayerTarget);
    renderer.clear(true, true, true);

    // Prime the offscreen depth buffer with solid geometry, without writing
    // color, so bloomed beam pixels are occluded by tables, fixtures, walls, etc.
    camera.layers.set(BASE_RENDER_LAYER);
    const restoreColorWrite = setSceneColorWrite(scene, false);
    renderer.render(scene, camera);
    restoreColorWrite();

    camera.layers.set(BEAM_RENDER_LAYER);
    renderer.render(scene, camera);

    bloomBlurMaterial.uniforms.sourceTexture.value = beamLayerTarget.texture;
    bloomBlurMaterial.uniforms.direction.value.set(1, 0);
    renderFullscreenMaterial(bloomBlurMaterial, bloomPingTarget);

    bloomBlurMaterial.uniforms.sourceTexture.value = bloomPingTarget.texture;
    bloomBlurMaterial.uniforms.direction.value.set(0, 1);
    renderFullscreenMaterial(bloomBlurMaterial, bloomPongTarget);

    bloomCompositeMaterial.uniforms.bloomTexture.value = bloomPongTarget.texture;
    bloomQuad.material = bloomCompositeMaterial;
    renderer.setRenderTarget(savedRenderTarget);
    renderer.autoClear = false;
    renderer.render(bloomScene, bloomCamera);

    camera.layers.mask = savedCameraLayerMask;
    scene.background = savedBackground;
    renderer.setClearColor(savedClearColor, savedClearAlpha);
    renderer.autoClear = savedAutoClear;
  }

  function updateFixtureBeamsToFloorClip(entity, floorNd, THREE) {
    const maxL = entity.maxBeamLength;
    if (!Number.isFinite(maxL) || maxL <= 0) {
      return;
    }
    const { n, d } = floorNd;
    const fy = entity.focusWidth ?? 1;

    if (entity.coneMesh && entity.beamTipLocal && entity.beamParent) {
      const tipL = entity.beamTipLocal;
      const bp = entity.beamParent;
      const o = tipL.clone();
      const far = tipL.clone().add(new THREE.Vector3(0, maxL, 0));
      bp.localToWorld(o);
      bp.localToWorld(far);
      const dir = far.clone().sub(o).normalize();
      const clip = clipRayToFloorAndMirrorballs(o, dir, maxL, n, d);
      entity.coneMesh.scale.set(fy, clip / maxL, fy);
      entity.coneMesh.position.set(0, tipL.y + clip / 2, tipL.z);
    }

    if (entity.prismSubMeshes?.length) {
      for (const sub of entity.prismSubMeshes) {
        const hh = sub.geometry.parameters.height;
        const narrow = new THREE.Vector3(0, hh / 2, 0);
        const wide = new THREE.Vector3(0, -hh / 2, 0);
        sub.localToWorld(narrow);
        sub.localToWorld(wide);
        const dir = wide.clone().sub(narrow).normalize();
        const clip = clipRayToFloorAndMirrorballs(narrow, dir, maxL, n, d);
        sub.scale.set(fy, clip / maxL, fy);
        sub.position.set(0, clip / 2, 0);
      }
    }

    if (entity.motionstripBulbs?.length) {
      for (const bulb of entity.motionstripBulbs) {
        const tipL = bulb.beamTipLocal;
        const bp = entity.beamParent;
        const o = tipL.clone();
        const far = tipL.clone().add(new THREE.Vector3(0, maxL, 0));
        bp.localToWorld(o);
        bp.localToWorld(far);
        const dir = far.clone().sub(o).normalize();
        const clip = clipRayToFloorAndMirrorballs(o, dir, maxL, n, d);
        bulb.beamMesh.scale.set(fy, clip / maxL, fy);
        bulb.beamMesh.position.set(tipL.x, tipL.y + clip / 2, tipL.z);
      }
    }

    const mbGroup = entity.mirrorballBeamsGroup;
    if (mbGroup && entity.profile?.kind === 'mirrorball') {
      const L = entity.profile.beamLength;
      const r = entity.profile.sphereRadius;
      const md = new THREE.Vector3();
      const pos = new THREE.Vector3();
      mbGroup.children.forEach((cone) => {
        if (!(cone instanceof THREE.Mesh)) {
          return;
        }
        const narrow = new THREE.Vector3(0, L / 2, 0);
        const wide = new THREE.Vector3(0, -L / 2, 0);
        cone.localToWorld(narrow);
        cone.localToWorld(wide);
        const dir = wide.clone().sub(narrow).normalize();
        const clip = clipRayToPlaneNd(narrow, dir, L, n, d);
        cone.scale.set(1, clip / L, 1);
        md.set(0, 1, 0).applyQuaternion(cone.quaternion);
        pos.copy(md).multiplyScalar(r - clip / 2);
        cone.position.copy(pos);
      });
    }
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
        let mul = 1.0;
        if (fixtureSelectionActive && !isSelected) mul *= 0.62;
        if (isSelected) mul *= 1.28;
        // Lens tint/strobe lives in material.color (animate loop); opacity is dim × selection only.
        entity.lensMaterial.opacity = Math.min(1, entity.runtimeLensOpacity * mul);
      }
      if (entity.motionstripBulbs?.length) {
        let mul = 1.0;
        if (fixtureSelectionActive && !isSelected) mul *= 0.62;
        if (isSelected) mul *= 1.28;
        const gate = entity.runtimeStrobeGate ?? 1;
        for (const bulb of entity.motionstripBulbs) {
          const dim = bulb.runtimeDimmer ?? 0;
          bulb.lensMaterial.opacity = Math.min(1, (0.12 + dim * 0.88) * mul);
          bulb.beamMaterial.opacity = Math.min(1, dim * CONE_OPACITY_AT_FULL_DIM * mul) * gate;
        }
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
          for (const m of entity.mirrorballBeamMaterials) {
            const mo = m.userData.runtimeOpacity ?? ro;
            m.opacity = Math.min(1, mo * mul);
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
    applyLightingPreset();
    syncInteractionMode();
  }

  function setInteractionMode(mode) {
    localState.interactionMode = mode;
    syncInteractionMode();
  }

  const _annotForwardLocal = new THREE.Vector3();
  const _annotForwardWorld = new THREE.Vector3();
  const _annotWorldPos = new THREE.Vector3();
  const _annotWorldQuat = new THREE.Quaternion();

  /** Per-frame: DMX address labels float above each fixture in world space; front
   *  arrow shows on the floor in top view only. Sprites/arrows live on
   *  `sceneContent` (not on the fixture group) so housing tilt/inversion does
   *  not flip them under the floor. */
  function updateFixtureAnnotations() {
    const isTop = localState.currentView === 'top';
    localState.entityMap.forEach((entity) => {
      if (entity.type !== 'fixture') {
        return;
      }
      entity.group.updateWorldMatrix(true, false);
      entity.group.getWorldPosition(_annotWorldPos);

      if (entity.addressLabel) {
        entity.addressLabel.position.set(
          _annotWorldPos.x,
          _annotWorldPos.y,
          _annotWorldPos.z + entity.addressLabelOffsetZ,
        );
      }

      if (entity.topArrow) {
        entity.topArrow.visible = isTop;
        if (isTop) {
          entity.group.getWorldQuaternion(_annotWorldQuat);
          _annotForwardLocal.set(0, 1, 0);
          _annotForwardWorld
            .copy(_annotForwardLocal)
            .applyQuaternion(_annotWorldQuat);
          _annotForwardWorld.z = 0;
          if (_annotForwardWorld.lengthSq() < 1e-6) {
            entity.topArrow.visible = false;
          } else {
            _annotForwardWorld.normalize();
            // Top-view front marker uses the venue-editor convention: rotate
            // the fixture's local +Y forward vector 90° counter-clockwise on
            // the floor plane (x, y) without affecting the actual fixture
            // transform or beam direction.
            const x = _annotForwardWorld.x;
            _annotForwardWorld.x = -_annotForwardWorld.y;
            _annotForwardWorld.y = x;
            entity.topArrow.position.set(
              _annotWorldPos.x,
              _annotWorldPos.y,
              TOP_ARROW_FLOOR_Z,
            );
            entity.topArrow.setDirection(_annotForwardWorld);
          }
        }
      }
    });
  }

  /** Max cone opacity when dimmer is 1; at dimmer 0 the cone is fully faded out. */
  const CONE_OPACITY_AT_FULL_DIM = 0.5;

  function applyFixtureRuntimeVisual(entity, vis, rgb, dim) {
    const dimClamped = Math.max(0, Math.min(1, dim));
    entity.runtimeRgb = [
      Math.max(0, Math.min(1, rgb[0])),
      Math.max(0, Math.min(1, rgb[1])),
      Math.max(0, Math.min(1, rgb[2])),
    ];
    const r = Math.min(1, rgb[0] * dimClamped);
    const g = Math.min(1, rgb[1] * dimClamped);
    const b = Math.min(1, rgb[2] * dimClamped);
    // `strobe`: when dimmer>0 and strobe>0, animate() toggles a square-wave gate.
    // Web preview uses a slower Hz band than desktop (see animate); desktop remains
    // ~5–30 Hz in parrot/vj/renderers/base.py.
    entity.runtimeStrobe = typeof vis.strobe === 'number'
      ? Math.max(0, Math.min(1, vis.strobe))
      : 0;
    // Matches `FixtureRenderer.get_effective_dimmer`: strobe only modulates output when dimmer > 0.
    entity.runtimeDimmerForStrobe = dimClamped;
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
    entity.focusWidth = focusWidth;
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
      // Lens bulb RGB is driven every frame in animate(): beam × dim × strobe phase.
      // Opacity tracks dim only so we do not double-apply strobe (gate is in color).
      entity.runtimeLensOpacity = 0.28 + dimClamped * 0.72;
      entity.lensMaterial.opacity = entity.runtimeLensOpacity;
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
    if (entity.motionstripBulbs?.length) {
      const bulbStates = Array.isArray(vis.bulbs) ? vis.bulbs : [];
      entity.motionstripBulbs.forEach((bulb, index) => {
        const bulbVis = bulbStates[index] || {};
        const bulbRgb = Array.isArray(bulbVis.rgb) && bulbVis.rgb.length >= 3
          ? bulbVis.rgb
          : rgb;
        const bulbDimmer = typeof bulbVis.dimmer === 'number'
          ? Math.max(0, Math.min(1, bulbVis.dimmer))
          : 1;
        const effectiveDimmer = dimClamped * bulbDimmer;
        bulb.runtimeRgb = [
          Math.max(0, Math.min(1, bulbRgb[0])),
          Math.max(0, Math.min(1, bulbRgb[1])),
          Math.max(0, Math.min(1, bulbRgb[2])),
        ];
        bulb.runtimeDimmer = effectiveDimmer;
        const br = Math.min(1, bulb.runtimeRgb[0] * effectiveDimmer);
        const bg = Math.min(1, bulb.runtimeRgb[1] * effectiveDimmer);
        const bb = Math.min(1, bulb.runtimeRgb[2] * effectiveDimmer);
        bulb.lensMaterial.color.setRGB(br, bg, bb);
        bulb.beamMaterial.color.setRGB(
          Math.min(1, br * 1.15),
          Math.min(1, bg * 1.15),
          Math.min(1, bb * 1.15),
        );
        bulb.lensMaterial.opacity = 0.12 + effectiveDimmer * 0.88;
        bulb.beamMaterial.opacity = effectiveDimmer * CONE_OPACITY_AT_FULL_DIM;
      });
    }
    if (entity.mirrorballBeamMaterials && entity.mirrorballBeamMaterials.length > 0) {
      entity.runtimeMirrorballOpacity = 0;
      for (const m of entity.mirrorballBeamMaterials) {
        m.userData.runtimeOpacity = 0;
        m.opacity = 0;
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
      const fixtureId = String(entity.fixture.id);
      const override = localState.namedPositionPreviewOverrides.get(fixtureId);
      let vis = byId.get(fixtureId);
      if (override) {
        vis = {
          ...(vis ?? { id: fixtureId, rgb: [1, 1, 1], dimmer: 0 }),
          pan_deg: override.pan / 255 * 540,
          tilt_deg: override.tilt / 255 * 270,
        };
      }
      if (!vis || !Array.isArray(vis.rgb) || vis.rgb.length < 3) {
        entity.runtimeStrobe = 0;
        entity.runtimeDimmerForStrobe = 0;
        entity.runtimeStrobeGate = 1;
        entity.runtimeRgb = null;
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
        if (entity.motionstripBulbs?.length) {
          for (const bulb of entity.motionstripBulbs) {
            bulb.runtimeDimmer = 0;
            bulb.lensMaterial.color.setRGB(0.04, 0.04, 0.045);
            bulb.lensMaterial.opacity = 0.12;
            bulb.beamMaterial.opacity = 0;
          }
        }
        return;
      }
      const dim = typeof vis.dimmer === 'number' ? vis.dimmer : 0;
      applyFixtureRuntimeVisual(entity, vis, vis.rgb, dim);
    });
    applySelectionVisuals();
  }

  function setNamedPositionPreviewOverride(fixtureId, override) {
    const key = String(fixtureId);
    if (!override) {
      localState.namedPositionPreviewOverrides.delete(key);
    } else {
      localState.namedPositionPreviewOverrides.set(key, {
        pan: Number(override.pan),
        tilt: Number(override.tilt),
      });
    }
  }

  /** Floor-plane height (m) for the top-view front-direction arrow. Floats just above floor to avoid z-fight. */
  const TOP_ARROW_FLOOR_Z = 0.02;

  /** World-space Z above the fixture origin where the DMX address label floats. */
  function addressLabelOffsetForProfile(profile) {
    if (profile.kind === 'mirrorball') {
      return profile.sphereRadius * 2 + 0.28;
    }
    if (profile.kind === 'moving_head') {
      return (
        profile.baseHeight + profile.headOffsetZ + profile.headHeight * 0.5 + 0.32
      );
    }
    if (profile.kind === 'motionstrip') {
      return profile.bodyHeight + 0.28;
    }
    if (profile.kind === 'laser') {
      return profile.bodyHeight + 0.32;
    }
    return (profile.bodyHeight ?? 0.4) + 0.3;
  }

  /** Builds a small canvas-textured sprite showing the fixture's DMX start address. */
  function buildAddressLabelSprite(address) {
    const text = address != null ? String(address) : '?';
    const fontPx = 64;
    const padX = 22;
    const padY = 12;
    const measure = document.createElement('canvas').getContext('2d');
    measure.font = `600 ${fontPx}px ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace`;
    const textW = Math.ceil(measure.measureText(text).width);
    const w = textW + padX * 2;
    const h = fontPx + padY * 2;

    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    ctx.font = `600 ${fontPx}px ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // No background fill — labels float on transparent pixels. A dark stroke
    // around the white glyphs keeps the number legible against both light
    // (top-down floor) and dark (3D body) backdrops.
    ctx.lineJoin = 'round';
    ctx.lineWidth = 6;
    ctx.strokeStyle = 'rgba(8, 12, 20, 0.92)';
    ctx.strokeText(text, w / 2, h / 2 + 2);
    ctx.fillStyle = '#f8fafc';
    ctx.fillText(text, w / 2, h / 2 + 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.needsUpdate = true;

    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
      depthWrite: false,
    });
    const sprite = new THREE.Sprite(material);
    // World-space sprite scale: keep height fixed regardless of digit count.
    const heightM = 0.32;
    sprite.scale.set(heightM * (w / h), heightM, 1);
    // Draw after fixtures so the label sits on top of the body in all views.
    sprite.renderOrder = 9999;
    return sprite;
  }

  /** Small arrow on the floor plane pointing in the fixture's neutral (+local Y) direction. Top view only. */
  function buildTopFrontArrow(color) {
    const arrow = new THREE.ArrowHelper(
      new THREE.Vector3(0, 1, 0),
      new THREE.Vector3(0, 0, 0),
      0.7,
      color,
      0.2,
      0.14,
    );
    // Sit slightly above floor so we win the depth tie with the floor plane.
    arrow.position.z = TOP_ARROW_FLOOR_Z;
    arrow.visible = false;
    if (arrow.line?.material) {
      arrow.line.material.transparent = true;
      arrow.line.material.opacity = 0.9;
      arrow.line.material.depthTest = false;
    }
    if (arrow.cone?.material) {
      arrow.cone.material.transparent = true;
      arrow.cone.material.opacity = 0.9;
      arrow.cone.material.depthTest = false;
    }
    arrow.renderOrder = 9998;
    return arrow;
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

    const placed = addFixtureOpaqueMeshes(
      THREE,
      runtimeAxesGroup,
      bodyMaterial,
      profile,
      fixture.id,
      { beamLayer: BEAM_RENDER_LAYER },
    );
    const beamParent =
      placed.headPivotGroup ?? placed.aimGroup ?? placed.stripPanGroup ?? runtimeAxesGroup;

    let coneMaterial = null;
    let lensMaterial = null;
    let coneMeshRef = null;
    let prismGroupRef = null;
    let prismMaterialsRef = [];
    let prismSubMeshesRef = [];
    const motionstripBulbsRef = [];
    /** @type {import('three').Vector3 | null} */
    let beamTipLocal = null;
    if (profile.kind !== 'mirrorball') {
      let beam;
      if (placed.headPivotGroup) {
        beam = beamOriginMovingHeadAimLocal(profile);
      } else if (placed.stripPanGroup) {
        beam = { y: profile.bodyDepth * 0.7, z: profile.bodyHeight };
      } else {
        beam = beamOriginLocal(profile);
      }

      beamTipLocal = new THREE.Vector3(0, beam.y, beam.z ?? 0);

      const coneLength = profile.coneLength;
      const coneRadius = profile.coneRadius;
      if (profile.kind === 'motionstrip') {
        const numBulbs = profile.numBulbs ?? 8;
        const spacing = profile.bulbSpacing ?? 0.22;
        const startX = -((numBulbs - 1) * spacing) / 2;
        const bulbRadius = 0.1;
        for (let i = 0; i < numBulbs; i += 1) {
          const x = startX + i * spacing;
          const bulbTipLocal = new THREE.Vector3(x, beam.y, beam.z ?? 0);
          const beamMaterial = new THREE.MeshBasicMaterial({
            color: fixture.is_manual ? 0xfbbf24 : 0xfb7185,
            transparent: true,
            opacity: 0,
            side: THREE.DoubleSide,
            depthWrite: false,
            fog: false,
          });
          const beamMesh = new THREE.Mesh(
            new THREE.ConeGeometry(coneRadius / Math.max(1.8, numBulbs * 0.42), coneLength, 12, 1, true),
            beamMaterial,
          );
          beamMesh.rotateX(Math.PI);
          beamMesh.position.set(x, beam.y + coneLength / 2, beam.z ?? 0);
          beamMesh.userData = { entityKey: fixture.id };
          beamMesh.layers.set(BEAM_RENDER_LAYER);
          beamParent.add(beamMesh);

          const lensMat = new THREE.MeshBasicMaterial({
            color: 0x101014,
            transparent: true,
            opacity: 0.12,
          });
          const lens = new THREE.Mesh(
            new THREE.SphereGeometry(bulbRadius, 12, 12),
            lensMat,
          );
          lens.position.copy(bulbTipLocal);
          lens.userData = { entityKey: fixture.id };
          beamParent.add(lens);
          secondaryMaterials.push(lensMat);
          motionstripBulbsRef.push({
            beamMesh,
            beamMaterial,
            lensMaterial: lensMat,
            beamTipLocal: bulbTipLocal,
            runtimeRgb: [1, 1, 1],
            runtimeDimmer: 0,
          });
        }
      } else {
        coneMaterial = new THREE.MeshBasicMaterial({
          color: fixture.is_manual ? 0xfbbf24 : 0xfb7185,
          transparent: true,
          opacity: 0,
          side: THREE.DoubleSide,
          depthWrite: false,
          fog: false,
        });
        // ConeGeometry: tip at +Y, base at -Y. Beam should be narrow at the lens and widen along the throw;
        // flip 180° so the tip sits on the lens (same convention as ArrowHelper cone).
        const coneMesh = new THREE.Mesh(
          new THREE.ConeGeometry(coneRadius, coneLength, 24, 1, true),
          coneMaterial
        );
        coneMesh.rotateX(Math.PI);
        coneMesh.position.set(0, beam.y + coneLength / 2, beam.z ?? 0);
        coneMesh.userData = { entityKey: fixture.id };
        beamParent.add(coneMesh);
        coneMesh.layers.set(BEAM_RENDER_LAYER);
        coneMeshRef = coneMesh;
      }

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
            fog: false,
          });
          prismMaterialsRef.push(mat);
          const sub = new THREE.Mesh(
            new THREE.ConeGeometry(subR, subL, 16, 1, true),
            mat
          );
          // Sub-cone's tip sits at the facet-group origin along its local +Y.
          sub.rotateX(Math.PI);
          sub.position.set(0, subL / 2, 0);
          sub.layers.set(BEAM_RENDER_LAYER);
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

      if (profile.kind !== 'motionstrip') {
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

    // DMX start address label — sibling of the fixture group so we can keep it at
    // a world-space Z offset even when the fixture is tilted/inverted on a truss.
    const addressLabel = buildAddressLabelSprite(fixture.address);
    addressLabel.userData = { entityKey: fixture.id, isFixtureAnnotation: true };
    sceneContent.add(addressLabel);

    // Top-view "front" arrow — only meaningful for fixtures that have a single
    // forward-facing beam axis (skip the mirrorball which radiates in all dirs).
    let topArrow = null;
    if (profile.kind !== 'mirrorball') {
      topArrow = buildTopFrontArrow(fixture.is_manual ? 0xfbbf24 : 0xfb7185);
      topArrow.userData = { entityKey: fixture.id, isFixtureAnnotation: true };
      sceneContent.add(topArrow);
    }

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
      beamParent: profile.kind !== 'mirrorball' ? beamParent : null,
      beamTipLocal,
      maxBeamLength:
        profile.kind === 'mirrorball' ? profile.beamLength : profile.coneLength,
      focusWidth: 1,
      addressLabel,
      addressLabelOffsetZ: addressLabelOffsetForProfile(profile),
      topArrow,
    };
    if (profile.kind === 'mirrorball') {
      localState.entityMap.set(fixture.id, {
        ...entityBase,
        mirrorballBeamMaterials: placed.mirrorballBeamMaterials ?? [],
        mirrorballBeamRecords: placed.mirrorballBeamRecords ?? [],
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
        motionstripBulbs: motionstripBulbsRef,
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
    danceFloorPeopleGroup.clear();
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
    loadDanceFloorPersonTextures();
    updateDanceFloorPeopleCutouts();

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
    // Strobe gate: same square-wave idea as desktop, but slower Hz so the preview
    // reads clearly (desktop uses ~5–30 Hz in FixtureRenderer.get_effective_dimmer).
    const timeSec = now / 1000;
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
        const dimForStrobe = entity.runtimeDimmerForStrobe ?? 0;
        let gate = 1;
        if (strobe > 0 && dimForStrobe > 0) {
          // Slower than desktop: ~1.2–8 Hz (was ~5–30 Hz) for calmer preview flicker.
          const hz = 1.2 + strobe * 6.8;
          gate = Math.floor(timeSec * hz) % 2 === 1 ? 1 : 0;
        }
        if ((entity.runtimeStrobeGate ?? 1) !== gate) {
          entity.runtimeStrobeGate = gate;
        }
        // Lens bulb: match beam perception — color = beam RGB × dim × strobe phase.
        if (entity.lensMaterial && entity.runtimeRgb) {
          const [r0, g0, b0] = entity.runtimeRgb;
          const dim = Math.max(0, Math.min(1, dimForStrobe));
          if (dim < 1e-4) {
            entity.lensMaterial.color.setRGB(0.11, 0.11, 0.13);
          } else if (strobe > 0 && gate === 0) {
            const grey = 0.06 + dim * 0.07;
            entity.lensMaterial.color.setRGB(grey, grey, grey);
          } else {
            const ph = strobe > 0 ? gate : 1;
            entity.lensMaterial.color.setRGB(
              Math.min(1, r0 * dim * ph),
              Math.min(1, g0 * dim * ph),
              Math.min(1, b0 * dim * ph),
            );
          }
        }
        if (entity.motionstripBulbs?.length) {
          for (const bulb of entity.motionstripBulbs) {
            const [r0, g0, b0] = bulb.runtimeRgb ?? [1, 1, 1];
            const dim = Math.max(0, Math.min(1, bulb.runtimeDimmer ?? 0));
            const phase = strobe > 0 ? gate : 1;
            const lr = dim < 1e-4 ? 0.04 : Math.min(1, r0 * dim * phase);
            const lg = dim < 1e-4 ? 0.04 : Math.min(1, g0 * dim * phase);
            const lb = dim < 1e-4 ? 0.045 : Math.min(1, b0 * dim * phase);
            bulb.lensMaterial.color.setRGB(lr, lg, lb);
            bulb.beamMaterial.color.setRGB(
              Math.min(1, lr * 1.15),
              Math.min(1, lg * 1.15),
              Math.min(1, lb * 1.15),
            );
          }
        }
      }
    });
    updateRuntimeDirectionalLights(THREE);
    updateMirrorballReflections(THREE);
    applySelectionVisuals();

    const floorNd = floorPlaneNdFromMesh(floorMesh, THREE);
    localState.entityMap.forEach((entity) => {
      if (entity.type === 'fixture') {
        updateFixtureBeamsToFloorClip(entity, floorNd, THREE);
      }
    });

    updateFixtureAnnotations();

    const camera = localState.activeCamera;
    camera.layers.enableAll();
    renderer.autoClear = true;
    renderer.setRenderTarget(null);
    renderer.render(scene, camera);
    if (localState.expensiveEffects.bloom) {
      renderBeamBloomLayer(camera);
    }
    renderer.autoClear = true;
    camera.layers.enableAll();
  }
  animate();

  return {
    applyBootstrap,
    applyVjPreviewUrl,
    resetVideoWallToPlaceholder,
    updateFloorPreview,
    updateVideoWallPreview,
    /** Re-read viewport element size (call when grid layout changes the viewport width without a window resize). */
    resize: resizeRenderer,
    setView,
    setSelection,
    setInteractionMode,
    setLightingMode,
    setExpensiveEffects,
    setNamedPositionPreviewOverride,
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
