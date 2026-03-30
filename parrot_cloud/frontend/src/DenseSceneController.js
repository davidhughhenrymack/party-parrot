export function createNoopSceneController(viewportEl) {
  if (viewportEl) {
    viewportEl.textContent = '3D viewport disabled in test mode.';
  }
  return {
    applyBootstrap() {},
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
}) {
  const localState = {
    venueSnapshot: null,
    venueScale: null,
    currentView: 'top',
    interactionMode: 'select',
    activeCamera: null,
    selectedEntityKey: null,
    entityMap: new Map(),
    destroyed: false,
  };

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x090d13);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  viewportEl.replaceChildren(renderer.domElement);

  const perspectiveCamera = new THREE.PerspectiveCamera(48, 1, 0.1, 5000);
  const orthoCamera = new THREE.OrthographicCamera(-10, 10, 10, -10, 0.1, 5000);
  localState.activeCamera = orthoCamera;

  const orbitControls = new OrbitControls(localState.activeCamera, renderer.domElement);
  orbitControls.enableDamping = true;
  orbitControls.screenSpacePanning = true;

  const transformControls = new TransformControls(localState.activeCamera, renderer.domElement);
  transformControls.setMode('translate');
  transformControls.setSpace('world');
  transformControls.size = 0.8;
  scene.add(transformControls);

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

  const gridHelper = new THREE.GridHelper(12, 12, 0x335577, 0x223344);
  scene.add(gridHelper);

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  const videoWallTexture = createVideoWallTexture();

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
    const planarScale = 0.02;
    return {
      width,
      depth,
      planarScale,
      worldWidth: width * planarScale,
      worldDepth: depth * planarScale,
      orthoWidth: 16,
      orthoDepth: 16,
      heightFocus: Math.max(8, venueSnapshot.floor_height || 10),
      maxDimension: Math.max(width, depth) * planarScale,
    };
  }

  function getSceneObject(venueSnapshot, kind) {
    return venueSnapshot?.scene_objects?.find((sceneObject) => sceneObject.kind === kind) ?? null;
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

  function toScenePosition(x, y, z) {
    const scale = localState.venueScale;
    return new THREE.Vector3(
      (x - scale.width / 2) * scale.planarScale,
      (y - scale.depth / 2) * scale.planarScale,
      z
    );
  }

  function fromScenePosition(vector) {
    const scale = localState.venueScale;
    return {
      x: vector.x / scale.planarScale + scale.width / 2,
      y: vector.y / scale.planarScale + scale.depth / 2,
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
    localState.entityMap.forEach((entity, entityKey) => {
      const isSelected = entityKey === localState.selectedEntityKey;
      entity.bodyMaterial.emissive?.setHex(isSelected ? 0x2563eb : 0x000000);
      entity.bodyMaterial.emissiveIntensity = isSelected ? 0.85 : 0.0;
      if (entity.helperMaterial) {
        entity.helperMaterial.opacity = isSelected ? 0.22 : 0.08;
      }
      if (entity.coneMaterial) {
        entity.coneMaterial.opacity = isSelected ? 0.34 : entity.baseConeOpacity;
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

    const entityKey = selection.type === 'fixture' ? selection.fixtureId : 'video_wall';
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
      orbitControls.enabled = true;
      orbitControls.enableRotate = true;
      orbitControls.enablePan = false;
      orbitControls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
      orbitControls.mouseButtons.RIGHT = THREE.MOUSE.ROTATE;
      renderer.domElement.style.cursor = 'grab';
      transformControls.enabled = false;
      return;
    }

    if (localState.interactionMode === 'pan') {
      orbitControls.enabled = true;
      orbitControls.enableRotate = false;
      orbitControls.enablePan = true;
      orbitControls.mouseButtons.LEFT = THREE.MOUSE.PAN;
      orbitControls.mouseButtons.RIGHT = THREE.MOUSE.PAN;
      renderer.domElement.style.cursor = 'move';
      transformControls.enabled = false;
      return;
    }

    orbitControls.enabled = false;
    orbitControls.enableRotate = false;
    orbitControls.enablePan = false;
    orbitControls.mouseButtons.LEFT = THREE.MOUSE.ROTATE;
    orbitControls.mouseButtons.RIGHT = THREE.MOUSE.PAN;
    renderer.domElement.style.cursor = 'default';
    transformControls.enabled = true;
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
    setSelection(entity.type === 'fixture' ? { type: 'fixture', fixtureId: entity.fixture.id } : { type: 'video_wall' });
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
    if (viewName === 'perspective') {
      localState.activeCamera = perspectiveCamera;
      perspectiveCamera.position.set(scale.worldWidth, -scale.worldDepth * 1.15, scale.heightFocus * 1.45);
      perspectiveCamera.up.set(0, 0, 1);
      perspectiveCamera.lookAt(0, 0, scale.heightFocus * 0.45);
      orbitControls.enableRotate = true;
    } else if (viewName === 'front') {
      localState.activeCamera = orthoCamera;
      orthoCamera.position.set(0, -scale.worldDepth * 1.6, scale.heightFocus);
      orthoCamera.up.set(0, 0, 1);
      orthoCamera.lookAt(0, 0, scale.heightFocus);
      orbitControls.enableRotate = false;
    } else if (viewName === 'side') {
      localState.activeCamera = orthoCamera;
      orthoCamera.position.set(scale.worldWidth * 1.6, 0, scale.heightFocus);
      orthoCamera.up.set(0, 0, 1);
      orthoCamera.lookAt(0, 0, scale.heightFocus);
      orbitControls.enableRotate = false;
    } else {
      localState.activeCamera = orthoCamera;
      orthoCamera.position.set(0, 0, scale.maxDimension * 3.2);
      orthoCamera.up.set(0, 1, 0);
      orthoCamera.lookAt(0, 0, 0);
      orbitControls.enableRotate = false;
    }
    orbitControls.object = localState.activeCamera;
    orbitControls.enableZoom = true;
    orbitControls.update();
    transformControls.camera = localState.activeCamera;
    syncInteractionMode();
  }

  function setInteractionMode(mode) {
    localState.interactionMode = mode;
    syncInteractionMode();
  }

  function createFixtureEntity(fixture) {
    const group = new THREE.Group();
    group.position.copy(toScenePosition(fixture.x, fixture.y, fixture.z));
    group.rotation.set(fixture.rotation_x || 0, fixture.rotation_y || 0, fixture.rotation_z || 0);
    group.userData = { entityKey: fixture.id };

    const bodyMaterial = new THREE.MeshStandardMaterial({
      color: fixture.is_manual ? 0xf59e0b : 0xef4444,
      metalness: 0.08,
      roughness: 0.56,
    });
    const body = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.34, 0.28), bodyMaterial);
    body.userData = { entityKey: fixture.id };
    group.add(body);

    const helperMaterial = new THREE.MeshBasicMaterial({
      color: 0x8ec5ff,
      transparent: true,
      opacity: 0.08,
      depthWrite: false,
    });
    const helperMesh = new THREE.Mesh(new THREE.SphereGeometry(0.42, 16, 16), helperMaterial);
    helperMesh.userData = { entityKey: fixture.id };
    group.add(helperMesh);

    const coneLength = 3.8;
    const coneRadius = 0.9;
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
    coneMesh.rotation.x = -Math.PI / 2;
    coneMesh.position.z = coneLength / 2;
    coneMesh.userData = { entityKey: fixture.id };
    group.add(coneMesh);

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
    const wallWidth = Math.max(videoWall.width * localState.venueScale.planarScale, 0.8);
    const wallDepth = Math.max(videoWall.depth * localState.venueScale.planarScale, 0.1);
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
      baseConeOpacity: 0,
    });
  }

  function createFurniture(sceneObject) {
    const group = new THREE.Group();
    group.position.copy(toScenePosition(sceneObject.x, sceneObject.y, sceneObject.z));
    group.rotation.set(
      sceneObject.rotation_x || 0,
      sceneObject.rotation_y || 0,
      sceneObject.rotation_z || 0
    );

    if (sceneObject.kind === 'dj_table') {
      const table = new THREE.Mesh(
        new THREE.BoxGeometry(
          Math.max(sceneObject.width * localState.venueScale.planarScale, 0.25),
          Math.max(sceneObject.depth * localState.venueScale.planarScale, 0.12),
          Math.max(sceneObject.height, 0.2)
        ),
        new THREE.MeshStandardMaterial({
          color: 0x2d1b16,
          metalness: 0.04,
          roughness: 0.9,
        })
      );
      group.add(table);
    } else if (sceneObject.kind === 'dj_cutout') {
      const cutout = new THREE.Mesh(
        new THREE.PlaneGeometry(
          Math.max(sceneObject.width * localState.venueScale.planarScale, 0.2),
          Math.max(sceneObject.height, 0.2)
        ),
        new THREE.MeshStandardMaterial({
          color: 0x111111,
          transparent: true,
          opacity: 0.88,
          side: THREE.DoubleSide,
        })
      );
      group.add(cutout);
    }

    sceneContent.add(group);
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

    const floorObject = getSceneObject(venueSnapshot, 'floor');
    if (floorObject) {
      floorMesh.position.copy(toScenePosition(floorObject.x, floorObject.y, floorObject.z));
      floorMesh.rotation.set(
        floorObject.rotation_x || 0,
        floorObject.rotation_y || 0,
        floorObject.rotation_z || 0
      );
      gridHelper.position.copy(toScenePosition(floorObject.x, floorObject.y, 0));
      gridHelper.rotation.set(
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
    gridHelper.scale.set(
      localState.venueScale.worldWidth / 12,
      localState.venueScale.worldDepth / 12,
      1
    );

    createVideoWallEntity(venueSnapshot.video_wall);
    venueSnapshot.scene_objects
      .filter((sceneObject) => sceneObject.kind === 'dj_table' || sceneObject.kind === 'dj_cutout')
      .forEach(createFurniture);
    venueSnapshot.fixtures.forEach(createFixtureEntity);
    resizeRenderer();
    setView(localState.currentView);
  }

  transformControls.addEventListener('dragging-changed', (event) => {
    orbitControls.enabled = !event.value;
  });

  transformControls.addEventListener('mouseUp', async () => {
    if (!localState.selectedEntityKey) {
      return;
    }
    const entity = localState.entityMap.get(localState.selectedEntityKey);
    if (!entity) {
      return;
    }

    const domainPosition = fromScenePosition(entity.group.position);
    const rotation = entity.group.rotation;
    if (entity.type === 'fixture') {
      await onFixtureTransform({
        fixtureId: entity.fixture.id,
        x: domainPosition.x,
        y: domainPosition.y,
        z: domainPosition.z,
        rotation_x: rotation.x,
        rotation_y: rotation.y,
        rotation_z: rotation.z,
      });
    } else {
      await onVideoWallTransform({
        x: domainPosition.x,
        y: domainPosition.y,
        z: domainPosition.z,
      });
    }
  });

  renderer.domElement.addEventListener('pointerdown', onPointerDown);
  renderer.domElement.addEventListener('contextmenu', onContextMenu);
  window.addEventListener('resize', resizeRenderer);

  resizeRenderer();
  setView('top');
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
    setView,
    setSelection,
    setInteractionMode,
    destroy() {
      localState.destroyed = true;
      renderer.domElement.removeEventListener('pointerdown', onPointerDown);
      renderer.domElement.removeEventListener('contextmenu', onContextMenu);
      window.removeEventListener('resize', resizeRenderer);
      transformControls.detach();
      renderer.dispose();
      viewportEl.replaceChildren();
    },
  };
}
