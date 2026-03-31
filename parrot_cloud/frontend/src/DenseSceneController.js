export function createNoopSceneController(viewportEl) {
  if (viewportEl) {
    viewportEl.textContent = '3D viewport disabled in test mode.';
  }
  return {
    applyBootstrap() {},
    updateFloorPreview() {},
    setView() {},
    setSelection() {},
    setInteractionMode() {},
    destroy() {},
  };
}

export async function createSceneController({
  viewportEl,
  isTestMode,
  onSelectionChange,
  onFixtureContextMenu,
  onFixtureTransform,
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
      onVideoWallTransform,
      onSceneObjectTransform,
      onTransformDragStateChange,
    });
  } catch (error) {
    console.error('Failed to initialize 3D viewport:', error);
    if (viewportEl) {
      viewportEl.textContent = '3D viewport failed to load.';
    }
    return createNoopSceneController(viewportEl);
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
    entityMap: new Map(),
    dragSyncTimeoutId: null,
    lastFixtureDragSyncAt: 0,
    isTransformDragging: false,
    destroyed: false,
  };
  const fixtureDragSyncIntervalMs = 100;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1b2430);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  viewportEl.replaceChildren(renderer.domElement);

  const perspectiveCamera = new THREE.PerspectiveCamera(48, 1, 0.1, 5000);
  const orthoCamera = new THREE.OrthographicCamera(-10, 10, 10, -10, 0.1, 5000);
  localState.activeCamera = orthoCamera;

  const orbitControls = new OrbitControls(localState.activeCamera, renderer.domElement);
  orbitControls.enableDamping = true;
  orbitControls.enableZoom = true;
  orbitControls.rotateSpeed = 0.9;
  orbitControls.panSpeed = 0.9;
  orbitControls.minPolarAngle = 0.12;
  orbitControls.maxPolarAngle = Math.PI - 0.12;

  const transformControls = new TransformControls(localState.activeCamera, renderer.domElement);
  transformControls.setMode('translate');
  transformControls.setSpace('world');
  transformControls.size = 0.8;
  scene.add(transformControls.getHelper());

  scene.add(new THREE.AmbientLight(0xffffff, 0.9));
  const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
  directionalLight.position.set(10, -14, 18);
  scene.add(directionalLight);

  const sceneContent = new THREE.Group();
  scene.add(sceneContent);

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

  const videoWallTexture = createVideoWallTexture();
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

  function createVideoWallTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 18;
    const context = canvas.getContext('2d');
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

    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.magFilter = THREE.NearestFilter;
    texture.minFilter = THREE.NearestFilter;
    return texture;
  }

  function createDjSilhouetteTexture() {
    const texture = new THREE.TextureLoader().load('/api/assets/dj.png');
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  function toScenePosition(x, y, z) {
    return new THREE.Vector3(x, y, z);
  }

  function fromScenePosition(vector) {
    return {
      x: vector.x,
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
    const fixtureFocusedSelection =
      localState.selectedEntityKey &&
      localState.entityMap.get(localState.selectedEntityKey)?.type === 'fixture';

    setMaterialDimmed(floorMaterial, fixtureFocusedSelection);
    localState.entityMap.forEach((entity, entityKey) => {
      const isSelected = entityKey === localState.selectedEntityKey;
      entity.bodyMaterial.emissive?.setHex(isSelected ? 0x2563eb : 0x000000);
      entity.bodyMaterial.emissiveIntensity = isSelected ? 0.85 : 0.0;
      setMaterialDimmed(entity.bodyMaterial, fixtureFocusedSelection && !isSelected);
      (entity.secondaryMaterials || []).forEach((material) => {
        setMaterialDimmed(material, fixtureFocusedSelection && !isSelected);
      });
      if (entity.helperMaterial) {
        entity.helperMaterial.opacity = isSelected ? 0.22 : fixtureFocusedSelection ? 0.056 : 0.08;
      }
      if (entity.coneMaterial) {
        const baseOpacity = fixtureFocusedSelection && !isSelected
          ? entity.baseConeOpacity * 0.7
          : entity.baseConeOpacity;
        entity.coneMaterial.opacity = isSelected ? 0.34 : baseOpacity;
      }
    });
  }

  function clearSelection() {
    localState.selectedEntityKey = null;
    transformControls.detach();
    applySelectionVisuals();
    onSelectionChange(null);
  }

  function setSelection(selection) {
    if (!selection) {
      clearSelection();
      return;
    }

    const entityKey =
      selection.type === 'fixture'
        ? selection.fixtureId
        : selection.type === 'dj_booth'
          ? 'dj_booth'
          : 'video_wall';
    const entity = localState.entityMap.get(entityKey);
    if (!entity) {
      clearSelection();
      return;
    }

    localState.selectedEntityKey = entityKey;
    transformControls.attach(entity.group);
    applySelectionVisuals();
    if (entity.type === 'fixture') {
      onSelectionChange({ type: 'fixture', fixture: entity.fixture });
    } else if (entity.type === 'dj_booth') {
      onSelectionChange({ type: 'dj_booth' });
    } else {
      onSelectionChange({ type: 'video_wall' });
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
      const floorCenterTarget = getFloorCenterTarget();
      orbitControls.enabled = true;
      orbitControls.enableRotate = localState.currentView === 'perspective';
      orbitControls.enablePan = false;
      orbitControls.screenSpacePanning = false;
      orbitControls.target.copy(floorCenterTarget);
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

  function onPointerDown(event) {
    if (localState.interactionMode !== 'select') {
      return;
    }
    if (transformControls.axis) {
      return;
    }
    updatePointer(event);
    const groups = Array.from(localState.entityMap.values()).map((entity) => entity.group);
    const hits = raycaster.intersectObjects(groups, true);
    if (hits.length === 0) {
      clearSelection();
      return;
    }
    const entity = getEntityFromObject(hits[0].object);
    if (!entity) {
      clearSelection();
      return;
    }
    if (entity.type === 'fixture') {
      setSelection({ type: 'fixture', fixtureId: entity.fixture.id });
    } else if (entity.type === 'dj_booth') {
      setSelection({ type: 'dj_booth' });
    } else {
      setSelection({ type: 'video_wall' });
    }
  }

  function onContextMenu(event) {
    if (localState.interactionMode !== 'select') {
      return;
    }
    event.preventDefault();
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
      orthoCamera.position.set(0, -scale.worldDepth * 1.6, flatTarget.z);
      orthoCamera.up.set(0, 0, 1);
      orthoCamera.lookAt(flatTarget);
      orbitControls.enableRotate = false;
    } else if (viewName === 'side') {
      localState.activeCamera = orthoCamera;
      orthoCamera.position.set(scale.worldWidth * 1.6, 0, flatTarget.z);
      orthoCamera.up.set(0, 0, 1);
      orthoCamera.lookAt(flatTarget);
      orbitControls.enableRotate = false;
    } else {
      localState.activeCamera = orthoCamera;
      orthoCamera.position.set(0, 0, scale.maxDimension * 3.2);
      orthoCamera.up.set(0, 1, 0);
      orthoCamera.lookAt(floorCenterTarget);
      orbitControls.enableRotate = false;
    }
    orbitControls.object = localState.activeCamera;
    orbitControls.target.copy(viewName === 'perspective' ? floorCenterTarget : flatTarget);
    orbitControls.update();
    transformControls.camera = localState.activeCamera;
    syncInteractionMode();
  }

  function setInteractionMode(mode) {
    localState.interactionMode = mode;
    syncInteractionMode();
  }

  function fixtureVisualProfile(fixture) {
    if (fixture.fixture_type === 'motionstrip_38') {
      return {
        kind: 'motionstrip',
        bodyWidth: 0.84,
        bodyDepth: 0.096,
        bodyHeight: 0.16,
        coneLength: 6.0,
        coneRadius: 0.45,
      };
    }
    if (
      [
        'chauvet_spot_110',
        'chauvet_spot_160',
        'chauvet_rogue_beam_r2',
        'chauvet_move_9ch',
      ].includes(fixture.fixture_type)
    ) {
      return {
        kind: 'moving_head',
        baseWidth: 0.384,
        baseDepth: 0.256,
        baseHeight: 0.096,
        headWidth: 0.16,
        headDepth: 0.384,
        headHeight: 0.16,
        headOffsetZ: 0.216,
        coneLength: 15.0,
        coneRadius: 0.14,
      };
    }
    if (['five_beam_laser', 'two_beam_laser'].includes(fixture.fixture_type)) {
      return {
        kind: 'laser',
        bodyWidth: 0.4,
        bodyDepth: 0.4,
        bodyHeight: 0.4,
        coneLength: 12.0,
        coneRadius: 0.08,
      };
    }
    return {
      kind: 'bulb',
      bodyWidth: 0.32,
      bodyDepth: 0.096,
      bodyHeight: 0.32,
      coneLength: 8.0,
      coneRadius: 0.24,
    };
  }

  function createFixtureEntity(fixture) {
    const group = new THREE.Group();
    group.position.copy(toScenePosition(fixture.x, fixture.y, fixture.z));
    group.rotation.set(fixture.rotation_x || 0, fixture.rotation_y || 0, fixture.rotation_z || 0);
    group.userData = { entityKey: fixture.id };

    const runtimeAxesGroup = new THREE.Group();
    group.add(runtimeAxesGroup);
    const profile = fixtureVisualProfile(fixture);

    const bodyMaterial = new THREE.MeshStandardMaterial({
      color: fixture.is_manual ? 0xf59e0b : 0xef4444,
      metalness: 0.08,
      roughness: 0.56,
    });
    const secondaryMaterials = [];

    if (profile.kind === 'moving_head') {
      const base = new THREE.Mesh(
        new THREE.BoxGeometry(profile.baseWidth, profile.baseDepth, profile.baseHeight),
        bodyMaterial
      );
      base.position.z = profile.baseHeight / 2;
      base.userData = { entityKey: fixture.id };
      runtimeAxesGroup.add(base);

      const head = new THREE.Mesh(
        new THREE.BoxGeometry(profile.headWidth, profile.headDepth, profile.headHeight),
        bodyMaterial
      );
      head.position.set(0, 0, profile.baseHeight + profile.headOffsetZ);
      head.userData = { entityKey: fixture.id };
      runtimeAxesGroup.add(head);
    } else {
      const body = new THREE.Mesh(
        new THREE.BoxGeometry(profile.bodyWidth, profile.bodyDepth, profile.bodyHeight),
        bodyMaterial
      );
      body.position.z = profile.bodyHeight / 2;
      body.userData = { entityKey: fixture.id };
      runtimeAxesGroup.add(body);
    }

    const helperMaterial = new THREE.MeshBasicMaterial({
      color: 0x8ec5ff,
      transparent: true,
      opacity: 0.08,
      depthWrite: false,
    });
    const helperMesh = new THREE.Mesh(new THREE.SphereGeometry(0.42, 16, 16), helperMaterial);
    helperMesh.userData = { entityKey: fixture.id };
    runtimeAxesGroup.add(helperMesh);

    const coneLength = profile.coneLength;
    const coneRadius = profile.coneRadius;
    const coneMaterial = new THREE.MeshBasicMaterial({
      color: fixture.is_manual ? 0xfbbf24 : 0xfb7185,
      transparent: true,
      opacity: 0.18,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const coneMesh = new THREE.Mesh(
      new THREE.ConeGeometry(coneRadius, coneLength, 24, 1, true),
      coneMaterial
    );
    coneMesh.position.set(
      0,
      coneLength / 2 + (profile.kind === 'moving_head' ? profile.headDepth * 0.32 : profile.bodyDepth * 0.7),
      profile.kind === 'moving_head'
        ? profile.baseHeight + profile.headOffsetZ + profile.headHeight * 0.05
        : profile.bodyHeight
    );
    coneMesh.userData = { entityKey: fixture.id };
    runtimeAxesGroup.add(coneMesh);

    const lensMaterial = new THREE.MeshBasicMaterial({
      color: fixture.is_manual ? 0xfbbf24 : 0xf8fafc,
      transparent: true,
      opacity: 0.95,
    });
    const lens = new THREE.Mesh(new THREE.SphereGeometry(profile.kind === 'laser' ? 0.06 : 0.08, 12, 12), lensMaterial);
    lens.position.set(
      0,
      profile.kind === 'moving_head' ? profile.headDepth * 0.6 : profile.bodyDepth * 0.7,
      profile.kind === 'moving_head'
        ? profile.baseHeight + profile.headOffsetZ + profile.headHeight * 0.05
        : profile.bodyHeight
    );
    lens.userData = { entityKey: fixture.id };
    runtimeAxesGroup.add(lens);
    secondaryMaterials.push(lensMaterial);

    const hitMesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.62, 16, 16),
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
    localState.entityMap.set(fixture.id, {
      type: 'fixture',
      fixture,
      group,
      bodyMaterial,
      secondaryMaterials,
      helperMaterial,
      coneMaterial,
      baseConeOpacity: 0.18,
    });
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
      baseConeOpacity: 0,
    });
  }

  function createDjBoothEntity(djTable, djCutout) {
    if (!djTable || !djCutout) {
      return;
    }

    const anchor = new THREE.Vector3(
      (djTable.x + djCutout.x) / 2,
      (djTable.y + djCutout.y) / 2,
      (djTable.z + djCutout.z) / 2
    );
    const group = new THREE.Group();
    group.position.copy(toScenePosition(anchor.x, anchor.y, anchor.z));
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
    const tableOffset = new THREE.Vector3(
      djTable.x - anchor.x,
      djTable.y - anchor.y,
      djTable.z - anchor.z
    );
    table.position.copy(tableOffset);
    table.userData = { entityKey: 'dj_booth' };
    group.add(table);

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
    const cutoutOffset = new THREE.Vector3(
      djCutout.x - anchor.x,
      djCutout.y - anchor.y,
      djCutout.z - anchor.z
    );
    cutout.position.copy(cutoutOffset);
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
      anchor,
    });
  }

  function applyBootstrap(venueSnapshot) {
    localState.venueSnapshot = venueSnapshot;
    localState.venueScale = venueSnapshot ? computeVenueScale(venueSnapshot) : null;
    sceneContent.clear();
    localState.entityMap.clear();
    clearSelection();

    if (!venueSnapshot) {
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
  }

  transformControls.addEventListener('dragging-changed', (event) => {
    if (event.value) {
      localState.isTransformDragging = true;
      orbitControls.enabled = false;
      renderer.domElement.style.cursor = 'grabbing';
      onTransformDragStateChange?.(true);
      return;
    }
    localState.isTransformDragging = false;
    syncInteractionMode();
    onTransformDragStateChange?.(false);
  });

  transformControls.addEventListener('objectChange', () => {
    scheduleFixtureDragSync();
  });

  transformControls.addEventListener('mouseUp', async () => {
    if (!localState.selectedEntityKey) {
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
      const delta = {
        x: domainPosition.x - entity.anchor.x,
        y: domainPosition.y - entity.anchor.y,
        z: domainPosition.z - entity.anchor.z,
      };
      await onSceneObjectTransform({
        type: 'dj_booth',
        objects: [
          {
            kind: 'dj_table',
            x: entity.djTable.x + delta.x,
            y: entity.djTable.y + delta.y,
            z: entity.djTable.z + delta.z,
          },
          {
            kind: 'dj_cutout',
            x: entity.djCutout.x + delta.x,
            y: entity.djCutout.y + delta.y,
            z: entity.djCutout.z + delta.z,
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
    renderer.render(scene, localState.activeCamera);
  }
  animate();

  return {
    applyBootstrap,
    updateFloorPreview,
    setView,
    setSelection,
    setInteractionMode,
    destroy() {
      localState.destroyed = true;
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
