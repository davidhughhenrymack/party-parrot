export function createNoopSceneController(
  viewportEl,
  message = '3D viewport disabled in test mode.',
) {
  if (viewportEl && message != null) {
    viewportEl.textContent = message;
  }
  return {
    applyBootstrap() {},
    setView() {},
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
  onVideoWallTransform,
}) {
  const localState = {
    activeVenue: null,
    activeCamera: null,
    selectedObject: null,
    objectMap: new Map(),
    destroyed: false,
  };

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0f14);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  viewportEl.replaceChildren(renderer.domElement);

  const perspectiveCamera = new THREE.PerspectiveCamera(50, 1, 0.1, 5000);
  const orthoCamera = new THREE.OrthographicCamera(-400, 400, 250, -250, 0.1, 5000);
  localState.activeCamera = perspectiveCamera;

  const orbitControls = new OrbitControls(localState.activeCamera, renderer.domElement);
  orbitControls.enableDamping = true;

  const transformControls = new TransformControls(localState.activeCamera, renderer.domElement);
  transformControls.setMode('translate');
  scene.add(transformControls);

  scene.add(new THREE.AmbientLight(0xffffff, 0.8));
  const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
  directionalLight.position.set(100, 200, 100);
  scene.add(directionalLight);

  const gridHelper = new THREE.GridHelper(1200, 24, 0x335577, 0x223344);
  gridHelper.rotation.x = Math.PI / 2;
  scene.add(gridHelper);

  const floorMesh = new THREE.Mesh(
    new THREE.BoxGeometry(600, 8, 450),
    new THREE.MeshStandardMaterial({ color: 0x13202d, metalness: 0.1, roughness: 0.85 })
  );
  floorMesh.position.set(250, 225, -4);
  scene.add(floorMesh);

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  function resizeRenderer() {
    const width = viewportEl.clientWidth;
    const height = viewportEl.clientHeight;
    renderer.setSize(width, height);
    perspectiveCamera.aspect = width / height || 1;
    perspectiveCamera.updateProjectionMatrix();
    const frustumWidth = 800;
    const frustumHeight = frustumWidth / (width / height || 1);
    orthoCamera.left = -frustumWidth / 2;
    orthoCamera.right = frustumWidth / 2;
    orthoCamera.top = frustumHeight / 2;
    orthoCamera.bottom = -frustumHeight / 2;
    orthoCamera.updateProjectionMatrix();
  }

  function clearSelection() {
    localState.selectedObject = null;
    transformControls.detach();
    onSelectionChange(null);
  }

  function selectObject(object) {
    localState.selectedObject = object;
    if (!object) {
      clearSelection();
      return;
    }

    if (object.userData.entityType === 'fixture') {
      transformControls.attach(object);
      onSelectionChange({ type: 'fixture', fixture: object.userData.fixture });
    } else if (object.userData.entityType === 'video_wall') {
      transformControls.attach(object);
      onSelectionChange({ type: 'video_wall' });
    }
  }

  function updatePointer(event) {
    const bounds = renderer.domElement.getBoundingClientRect();
    pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
    pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
    raycaster.setFromCamera(pointer, localState.activeCamera);
  }

  function onPointerDown(event) {
    updatePointer(event);
    const objects = Array.from(localState.objectMap.values());
    const hits = raycaster.intersectObjects(objects, false);
    if (hits.length === 0) {
      clearSelection();
      return;
    }
    selectObject(hits[0].object);
  }

  function onContextMenu(event) {
    event.preventDefault();
    updatePointer(event);
    const fixtureObjects = Array.from(localState.objectMap.values()).filter(
      (object) => object.userData.entityType === 'fixture'
    );
    const hits = raycaster.intersectObjects(fixtureObjects, false);
    if (hits.length === 0) {
      return;
    }
    const object = hits[0].object;
    selectObject(object);
    onFixtureContextMenu({
      fixture: object.userData.fixture,
      x: event.clientX + 8,
      y: event.clientY + 8,
    });
  }

  function setView(viewName) {
    if (viewName === 'perspective') {
      localState.activeCamera = perspectiveCamera;
      perspectiveCamera.position.set(550, -500, 420);
      perspectiveCamera.up.set(0, 0, 1);
      perspectiveCamera.lookAt(250, 225, 40);
    } else if (viewName === 'side') {
      localState.activeCamera = orthoCamera;
      orthoCamera.position.set(250, -650, 120);
      orthoCamera.up.set(0, 0, 1);
      orthoCamera.lookAt(250, 225, 60);
    } else {
      localState.activeCamera = orthoCamera;
      orthoCamera.position.set(250, 225, 850);
      orthoCamera.up.set(0, 1, 0);
      orthoCamera.lookAt(250, 225, 0);
    }
    orbitControls.object = localState.activeCamera;
    orbitControls.update();
    transformControls.camera = localState.activeCamera;
  }

  function applyBootstrap(activeVenue) {
    localState.activeVenue = activeVenue;
    localState.objectMap.forEach((object) => scene.remove(object));
    localState.objectMap.clear();
    clearSelection();

    if (!activeVenue) {
      return;
    }

    const scale = 30;
    floorMesh.scale.set(activeVenue.floor_width / 20, activeVenue.floor_depth / 15, 1);
    floorMesh.position.set(
      (activeVenue.floor_width * scale) / 2,
      (activeVenue.floor_depth * scale) / 2,
      -4
    );

    const videoWall = activeVenue.video_wall;
    const videoWallMesh = new THREE.Mesh(
      new THREE.BoxGeometry(videoWall.width * scale / 5, videoWall.depth * scale / 5, videoWall.height * scale / 5),
      new THREE.MeshStandardMaterial({ color: videoWall.locked ? 0x365314 : 0x2563eb })
    );
    videoWallMesh.position.set(videoWall.x, videoWall.y, videoWall.z);
    videoWallMesh.userData = { entityType: 'video_wall' };
    scene.add(videoWallMesh);
    localState.objectMap.set('video_wall', videoWallMesh);

    activeVenue.fixtures.forEach((fixture) => {
      const geometry = new THREE.BoxGeometry(36, 24, 24);
      const material = new THREE.MeshStandardMaterial({
        color: fixture.is_manual ? 0xf59e0b : 0xef4444,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(fixture.x, fixture.y, fixture.z);
      mesh.rotation.set(
        fixture.rotation_x || 0,
        fixture.rotation_y || 0,
        fixture.rotation_z || 0
      );
      mesh.userData = {
        entityType: 'fixture',
        fixtureId: fixture.id,
        fixture,
      };
      scene.add(mesh);
      localState.objectMap.set(fixture.id, mesh);
    });
  }

  transformControls.addEventListener('dragging-changed', (event) => {
    orbitControls.enabled = !event.value;
  });

  transformControls.addEventListener('mouseUp', async () => {
    if (!localState.selectedObject || !localState.activeVenue) {
      return;
    }

    const { userData, position, rotation } = localState.selectedObject;
    if (userData.entityType === 'fixture') {
      await onFixtureTransform({
        fixtureId: userData.fixtureId,
        x: position.x,
        y: position.y,
        z: position.z,
        rotation_x: rotation.x,
        rotation_y: rotation.y,
        rotation_z: rotation.z,
      });
    } else if (userData.entityType === 'video_wall') {
      await onVideoWallTransform({
        x: position.x,
        y: position.y,
        z: position.z,
      });
    }
  });

  renderer.domElement.addEventListener('pointerdown', onPointerDown);
  renderer.domElement.addEventListener('contextmenu', onContextMenu);
  window.addEventListener('resize', resizeRenderer);

  resizeRenderer();
  setView('top');

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
