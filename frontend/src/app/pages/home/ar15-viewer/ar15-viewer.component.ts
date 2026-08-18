import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild
} from '@angular/core';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

interface PartMeshConfig {
  categorySlug: string;
  build: () => THREE.Mesh[];
}

type MaterialKind = 'metal' | 'polymer' | 'glass';

interface ClickableEntry {
  mesh: THREE.Mesh;
  neutralColor: THREE.Color;
  recolorable: boolean;
  /** True for hitboxes with no real visual counterpart -- fully transparent until
   * hovered/selected, so an oversized pick region never renders as a mismatched
   * floating shape. Raycasting still works on invisible geometry; only colorWrite/
   * depthWrite are toggled, not `mesh.visible` (which the raycaster does respect). */
  hiddenWhenNeutral?: boolean;
}

const MODEL_URL = '/assets/models/uar15/scene.gltf';
const TARGET_LENGTH = 9.5;

// Matte anodized aluminum / phosphate-finish tones rather than raw silvery grey --
// real AR-15 receivers and barrels read much darker than bare metal. Used for the
// procedural stand-in parts (categories the loaded model doesn't include) and as the
// full fallback rifle if the model fails to load.
const COLOR_NEUTRAL_METAL = 0x35383d;
const COLOR_NEUTRAL_POLYMER = 0x1f2225;
const COLOR_SELECTED = 0xc0262f;
const COLOR_HOVER = 0xe06068;
const COLOR_DETAIL_METAL = 0x26282c;
const COLOR_DETAIL_POLYMER = 0x1a1c1f;

/** Real, named meshes in the loaded model mapped onto pickable catalog categories.
 * Node names come from the source glTF (see /assets/models/uar15/license.txt), with
 * spaces/dots sanitized to underscores -- GLTFLoader sanitizes node names on parse
 * (three.js PropertyBinding.sanitizeNodeName) so "uar15 trigga_0" becomes
 * "uar15_trigga_0" and "10.5in" becomes "105in" by the time nodes are traversed. */
const GLTF_PART_NODE_TO_CATEGORY: Record<string, string> = {
  uar15_trigga_0: 'trigger',
  uar15_charging_handle_4: 'charging-handle',
  uar15_lower_9: 'lower-receiver',
  uar15_105in_barrel_10: 'barrel',
  uar15_upper_11: 'upper-receiver',
  uar15_flash_hider_12: 'muzzle-device',
  uar15_grip_15: 'pistol-grip',
  uar15_stock_16: 'stock-brace',
  uar15_handguard_17: 'handguard',
  'ar15_30rnd_mag_(zbroyar)_14': 'magazine',
  // Single mesh spanning both the front and rear sight positions.
  uar15_iron_sight_18: 'optic'
};

/** Extra real meshes kept for visual richness but not tied to a pickable category. */
const GLTF_DETAIL_NODE_NAMES = [
  'uar15_selector_1',
  'uar15_mag_catch_2',
  'uar15_dust_cover_3',
  'uar15_bolt_catch_5',
  'uar15_bolt_6'
];

/** Categories the loaded model has no part for -- built procedurally and anchored to
 * the loaded model's own geometry once it's known, rather than guessed coordinates. */
const STANDIN_CATEGORIES = new Set(['bolt-carrier-group', 'gas-system']);

/** Edge-bevel radius as a fraction of a part's smallest dimension, clamped so tiny
 * detail meshes (rail ridges, M-LOK slots) don't round away into blobs while large
 * receivers/grips get a visible, light-catching chamfer like a machined part would. */
function bevelRadiusFor(w: number, h: number, d: number): number {
  const smallest = Math.min(w, h, d);
  return Math.min(0.03, Math.max(0.006, smallest * 0.12));
}

function box(
  x: number,
  y: number,
  z: number,
  w: number,
  h: number,
  d: number,
  rotZ = 0
): THREE.Mesh {
  const radius = bevelRadiusFor(w, h, d);
  const mesh = new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 2, radius));
  mesh.position.set(x, y, z);
  mesh.rotation.z = rotZ;
  return mesh;
}

function tube(
  x: number,
  y: number,
  z: number,
  length: number,
  radius: number,
  radiusEnd = radius,
  radialSegments = 28
): THREE.Mesh {
  const mesh = new THREE.Mesh(
    new THREE.CylinderGeometry(radiusEnd, radius, length, radialSegments)
  );
  mesh.rotation.z = Math.PI / 2;
  mesh.position.set(x, y, z);
  return mesh;
}

/** Curved box magazine, shared by the fallback rifle's clickable "magazine" category. */
function buildMagazineMesh(): THREE.Mesh {
  const magShape = new THREE.Shape();
  magShape.moveTo(-0.17, 0);
  magShape.lineTo(0.17, 0);
  magShape.lineTo(0.13, -1.05);
  magShape.quadraticCurveTo(0.1, -1.2, -0.02, -1.22);
  magShape.quadraticCurveTo(-0.15, -1.2, -0.17, -1.05);
  magShape.closePath();
  const magazine = new THREE.Mesh(
    new THREE.ExtrudeGeometry(magShape, { depth: 0.34, bevelEnabled: true, bevelSize: 0.015, bevelThickness: 0.015, bevelSegments: 2 })
  );
  magazine.geometry.translate(0, 0, -0.17);
  magazine.position.set(-1.78, -0.42, 0);
  magazine.rotation.z = -0.12;
  magazine.scale.set(1.15, 1.15, 1.15);
  return magazine;
}

/** Static, non-interactive detail meshes for the fallback procedural rifle (trigger
 * guard, rail ridges, sights) used only if the real model fails to load. */
function buildDetailMeshes(): THREE.Mesh[] {
  const meshes: THREE.Mesh[] = [];

  const guardShape = new THREE.Shape();
  guardShape.absarc(0, 0, 0.24, Math.PI * 0.15, Math.PI * 1.02, false);
  const guardHole = new THREE.Path();
  guardHole.absarc(0, 0, 0.15, 0, Math.PI * 2, false);
  guardShape.holes.push(guardHole);
  const triggerGuard = new THREE.Mesh(
    new THREE.ExtrudeGeometry(guardShape, { depth: 0.1, bevelEnabled: false })
  );
  triggerGuard.geometry.translate(0, 0, -0.05);
  triggerGuard.position.set(-1.85, -0.68, 0);
  meshes.push(triggerGuard);

  meshes.push(box(4.9, 0.42, 0, 0.1, 0.4, 0.1));
  meshes.push(box(-1.0, 0.38, 0, 0.16, 0.22, 0.14));

  for (let i = 0; i < 9; i++) {
    meshes.push(box(-0.75 + i * 0.24, 0.34, 0, 0.05, 0.06, 0.42));
  }
  for (let i = 0; i < 10; i++) {
    meshes.push(box(1.9 + i * 0.32, 0.29, 0, 0.06, 0.05, 0.4));
  }
  for (let i = 0; i < 7; i++) {
    meshes.push(box(2.0 + i * 0.34, -0.27, 0, 0.16, 0.04, 0.06));
  }

  for (const mesh of meshes) {
    mesh.userData['detailOnly'] = true;
  }

  return meshes;
}

const PART_CONFIGS: PartMeshConfig[] = [
  {
    categorySlug: 'muzzle-device',
    build: () => [tube(8.55, 0, 0, 0.4, 0.16, 0.13), tube(8.85, 0, 0, 0.25, 0.13, 0.13, 8)]
  },
  { categorySlug: 'barrel', build: () => [tube(6.3, 0, 0, 4.2, 0.11)] },
  { categorySlug: 'handguard', build: () => [tube(3.4, 0, 0, 3.4, 0.28, 0.28, 8)] },
  { categorySlug: 'upper-receiver', build: () => [box(0.3, 0.05, 0, 2.2, 0.55, 0.5)] },
  { categorySlug: 'charging-handle', build: () => [box(-0.55, 0.38, 0, 0.35, 0.12, 0.2)] },
  { categorySlug: 'bolt-carrier-group', build: () => [box(0.05, 0.05, 0.3, 1.6, 0.2, 0.08)] },
  {
    categorySlug: 'optic',
    build: () => [box(0.15, 0.36, 0, 0.9, 0.12, 0.35), tube(0.15, 0.72, 0, 0.9, 0.16)]
  },
  { categorySlug: 'gas-system', build: () => [tube(2.1, 0.14, 0, 0.65, 0.05), box(1.85, 0.16, 0, 0.14, 0.14, 0.16)] },
  { categorySlug: 'magazine', build: () => [buildMagazineMesh()] },
  {
    categorySlug: 'lower-receiver',
    build: () => [
      box(-1.6, -0.15, 0, 1.6, 0.6, 0.5),
      box(-2.05, -0.42, 0, 0.55, 0.22, 0.56, -0.28)
    ]
  },
  { categorySlug: 'trigger', build: () => [box(-1.85, -0.62, 0, 0.14, 0.35, 0.14)] },
  { categorySlug: 'pistol-grip', build: () => [box(-2.55, -0.95, 0, 0.3, 0.75, 0.4, 0.35)] },
  {
    categorySlug: 'stock-brace',
    build: () => [
      tube(-3.55, -0.05, 0, 1.5, 0.18, 0.18, 12),
      tube(-4.35, -0.05, 0, 0.35, 0.21, 0.21, 12),
      box(-4.72, -0.05, 0, 0.34, 0.34, 0.42),
      box(-5.1, -0.28, 0, 0.42, 0.62, 0.5)
    ]
  }
];

const METAL_CATEGORIES = new Set([
  'muzzle-device',
  'barrel',
  'handguard',
  'upper-receiver',
  'charging-handle',
  'bolt-carrier-group',
  'lower-receiver',
  'trigger',
  'gas-system'
]);

function materialKindFor(categorySlug: string): MaterialKind {
  if (categorySlug === 'optic') return 'glass';
  if (METAL_CATEGORIES.has(categorySlug)) return 'metal';
  return 'polymer';
}

@Component({
  selector: 'app-ar15-viewer',
  standalone: true,
  imports: [],
  template: `<div #host class="h-full w-full"></div>`,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class Ar15ViewerComponent implements AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('host', { static: true }) hostRef!: ElementRef<HTMLDivElement>;

  @Input() selectedCategorySlugs: string[] = [];
  @Input() activeCategorySlug: string | null = null;
  @Output() categoryClick = new EventEmitter<string>();
  @Output() webglUnavailable = new EventEmitter<void>();

  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private renderer!: THREE.WebGLRenderer;
  private controls!: OrbitControls;
  private readonly meshesBySlug = new Map<string, ClickableEntry[]>();
  private readonly clickableMeshes: THREE.Mesh[] = [];
  private readonly allMeshes: THREE.Mesh[] = [];
  private readonly raycaster = new THREE.Raycaster();
  private readonly pointer = new THREE.Vector2();
  private hoveredSlug: string | null = null;
  private resizeObserver?: ResizeObserver;
  private frameId = 0;
  private initialized = false;
  private pmremGenerator?: THREE.PMREMGenerator;
  private surfaceNoiseTexture?: THREE.Texture;

  ngAfterViewInit(): void {
    try {
      this.initScene();
    } catch (error) {
      console.error('3D viewer unavailable:', error);
      this.webglUnavailable.emit();
      return;
    }
    this.initialized = true;

    this.loadRealModel()
      .catch(error => {
        console.warn('Falling back to the procedural rifle -- real model failed to load:', error);
        this.buildProceduralFallback();
      })
      .finally(() => {
        this.applySelectionColors();
        this.animate();
      });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (!this.initialized) return;
    if (changes['selectedCategorySlugs']) {
      this.applySelectionColors();
    }
  }

  ngOnDestroy(): void {
    cancelAnimationFrame(this.frameId);
    this.resizeObserver?.disconnect();
    this.renderer?.dispose();
    this.controls?.dispose();
    this.pmremGenerator?.dispose();
    this.surfaceNoiseTexture?.dispose();
    for (const mesh of this.allMeshes) {
      mesh.geometry.dispose();
      (mesh.material as THREE.Material).dispose();
    }
  }

  private initScene(): void {
    const host = this.hostRef.nativeElement;

    this.scene = new THREE.Scene();
    this.scene.background = null;

    this.camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    this.camera.position.set(2, 3.4, 9);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    host.appendChild(this.renderer.domElement);

    this.pmremGenerator = new THREE.PMREMGenerator(this.renderer);
    this.scene.environment = this.pmremGenerator.fromScene(new RoomEnvironment(), 0.04).texture;
    this.surfaceNoiseTexture = this.createSurfaceNoiseTexture();

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.autoRotate = true;
    this.controls.autoRotateSpeed = 0.6;
    this.controls.minDistance = 5;
    this.controls.maxDistance = 16;
    this.controls.maxPolarAngle = Math.PI * 0.65;
    this.controls.target.set(0, 0, 0);
    this.controls.zoomSpeed = 0.6;

    const ambient = new THREE.AmbientLight(0xffffff, 0.5);
    const key = new THREE.DirectionalLight(0xffffff, 1.6);
    key.position.set(5, 6, 6);
    const fill = new THREE.DirectionalLight(0x88a4ff, 0.5);
    fill.position.set(-6, 2, -4);
    const rim = new THREE.DirectionalLight(0xffb066, 0.6);
    rim.position.set(-2, -3, 5);
    this.scene.add(ambient, key, fill, rim);

    const shadowTexture = this.createRadialShadowTexture();
    const shadowMaterial = new THREE.MeshBasicMaterial({
      map: shadowTexture,
      transparent: true,
      opacity: 0.45,
      depthWrite: false
    });
    const shadow = new THREE.Mesh(new THREE.PlaneGeometry(11, 3.2), shadowMaterial);
    shadow.rotation.x = -Math.PI / 2;
    shadow.position.set(0, -1.3, 0);
    this.scene.add(shadow);

    this.resizeObserver = new ResizeObserver(() => this.handleResize());
    this.resizeObserver.observe(host);
    this.handleResize();

    host.addEventListener('pointermove', this.onPointerMove);
    host.addEventListener('pointerdown', this.onPointerDown);
    host.addEventListener('pointerenter', this.onPointerEnter);
    host.addEventListener('pointerleave', this.onPointerLeave);
  }

  /** Loads the real licensed AR-15 model, maps its named parts onto pickable
   * categories, and builds procedural stand-ins (anchored to the model's own
   * geometry) for the categories it doesn't include. */
  private async loadRealModel(): Promise<void> {
    const loader = new GLTFLoader();
    const gltf = await loader.loadAsync(MODEL_URL);
    const root = gltf.scene;

    // Normalize to a consistent on-screen size/position regardless of the source
    // file's native scale, so camera/lighting tuned for one model still work for
    // any future swap.
    root.updateMatrixWorld(true);
    const rawBox = new THREE.Box3().setFromObject(root);
    const rawSize = rawBox.getSize(new THREE.Vector3());
    const scale = TARGET_LENGTH / Math.max(rawSize.x, 0.001);
    root.scale.setScalar(scale);
    root.updateMatrixWorld(true);

    const scaledBox = new THREE.Box3().setFromObject(root);
    const center = scaledBox.getCenter(new THREE.Vector3());
    root.position.sub(center);
    root.updateMatrixWorld(true);

    this.scene.add(root);

    const namedGroups = new Map<string, THREE.Object3D>();
    root.traverse(node => {
      if (namedGroups.has(node.name)) return;
      namedGroups.set(node.name, node);
    });

    // The source file includes extra decorative nodes (a spare/empty magazine, loose
    // cartridge cases) we don't curate into a category or a detail mesh. Strip them
    // so nothing unexpected renders -- otherwise they show up as un-styled, oddly
    // placed geometry alongside the parts we do control.
    const keepNodeNames = new Set([
      ...Object.keys(GLTF_PART_NODE_TO_CATEGORY),
      ...GLTF_DETAIL_NODE_NAMES
    ]);
    const sceneRoot = namedGroups.get('GLTF_SceneRootNode');
    if (sceneRoot) {
      for (const child of [...sceneRoot.children]) {
        if (!keepNodeNames.has(child.name)) {
          sceneRoot.remove(child);
        }
      }
    }

    const meshesInGroup = (group: THREE.Object3D): THREE.Mesh[] => {
      const found: THREE.Mesh[] = [];
      group.traverse(node => {
        if ((node as THREE.Mesh).isMesh) found.push(node as THREE.Mesh);
      });
      return found;
    };

    const boundsByCategory = new Map<string, THREE.Box3>();

    for (const [nodeName, categorySlug] of Object.entries(GLTF_PART_NODE_TO_CATEGORY)) {
      const group = namedGroups.get(nodeName);
      if (!group) continue;

      const entries: ClickableEntry[] = [];
      for (const mesh of meshesInGroup(group)) {
        // GLTFLoader shares one material instance across every mesh that references the
        // same glTF material index (e.g. the grip, stock, and magazine all use the
        // "polymer" material) -- clone it per-mesh so recoloring one selected part
        // doesn't bleed onto every other part sharing that material.
        mesh.material = (mesh.material as THREE.MeshStandardMaterial).clone();
        this.applySharedSurfaceDetail(mesh.material as THREE.MeshStandardMaterial);
        const neutralColor = (mesh.material as THREE.MeshStandardMaterial).color.clone();
        mesh.userData['categorySlug'] = categorySlug;
        this.clickableMeshes.push(mesh);
        this.allMeshes.push(mesh);
        entries.push({ mesh, neutralColor, recolorable: true });
      }
      this.meshesBySlug.set(categorySlug, entries);
      boundsByCategory.set(categorySlug, new THREE.Box3().setFromObject(group));
    }

    for (const nodeName of GLTF_DETAIL_NODE_NAMES) {
      const group = namedGroups.get(nodeName);
      if (!group) continue;
      for (const mesh of meshesInGroup(group)) {
        this.allMeshes.push(mesh);
      }
      // Not a pickable category itself, but its bounds anchor the BCG hitbox to
      // where the ejection port actually is, rather than the upper receiver's full
      // bounding box (which is taller than the visible body and throws off centering).
      if (nodeName === 'uar15_dust_cover_3') {
        boundsByCategory.set('dust-cover', new THREE.Box3().setFromObject(group));
      }
    }

    this.buildStandinParts(boundsByCategory);
  }

  /** Builds procedural parts for categories the loaded model has no mesh for,
   * positioned from the real geometry's own bounding boxes instead of guessed
   * coordinates, so they stay correctly anchored regardless of model proportions. */
  private buildStandinParts(boundsByCategory: Map<string, THREE.Box3>): void {
    const upper = boundsByCategory.get('upper-receiver');
    const handguard = boundsByCategory.get('handguard');
    const barrel = boundsByCategory.get('barrel');

    const addStandin = (
      categorySlug: string,
      mesh: THREE.Mesh,
      options?: { hiddenWhenNeutral?: boolean }
    ): void => {
      const kind = materialKindFor(categorySlug);
      const material = this.createMaterial(kind, COLOR_NEUTRAL_METAL);
      mesh.material = material;
      mesh.userData['categorySlug'] = categorySlug;
      this.scene.add(mesh);
      this.clickableMeshes.push(mesh);
      this.allMeshes.push(mesh);
      const hiddenWhenNeutral = options?.hiddenWhenNeutral ?? false;
      if (hiddenWhenNeutral) {
        (material as THREE.MeshStandardMaterial).colorWrite = false;
        (material as THREE.MeshStandardMaterial).depthWrite = false;
      }
      this.meshesBySlug.set(categorySlug, [
        {
          mesh,
          neutralColor: (material as THREE.MeshStandardMaterial).color.clone(),
          recolorable: kind !== 'glass',
          hiddenWhenNeutral
        }
      ]);
    };

    if (upper) {
      const centerX = (upper.min.x + upper.max.x) / 2;
      const centerZ = (upper.min.z + upper.max.z) / 2;
      const height = upper.max.y - upper.min.y;
      // Nested fully inside the receiver's solid shell, this hit target was reachable
      // only through whatever incidental gaps exist in the mesh -- a sliver so thin it
      // read as "can't select the BCG at all". An earlier fix extended it past the
      // shell's own outer surface so raycasting always hits it first regardless of
      // rotation, but that meant a visible box floating outside the gun. Raycasting
      // doesn't care whether a mesh actually renders any pixels, so keep it fully
      // transparent (colorWrite/depthWrite off) until hovered or selected instead --
      // full coverage with nothing visible to look wrong.
      //
      // Center vertically on the dust cover (the ejection port opening) rather than
      // the upper receiver's own bounding box -- that box is taller than the visible
      // body (it includes other tall features further along the rail), so centering
      // on it left the hitbox floating above the gun instead of over the receiver.
      const dustCover = boundsByCategory.get('dust-cover');
      const yCenter = dustCover ? (dustCover.min.y + dustCover.max.y) / 2 : (upper.min.y + upper.max.y) / 2;
      const ySpan = dustCover ? dustCover.max.y - dustCover.min.y + height * 0.15 : height * 0.4;
      const margin = height * 0.03;
      addStandin(
        'bolt-carrier-group',
        box(centerX, yCenter, centerZ, (upper.max.x - upper.min.x) * 0.65, ySpan, upper.max.z - upper.min.z + margin * 2),
        { hiddenWhenNeutral: true }
      );
    }

    if (handguard && barrel) {
      const height = handguard.max.y - handguard.min.y;
      const gasX = THREE.MathUtils.lerp(handguard.min.x, handguard.max.x, 0.82);
      const barrelY = (barrel.min.y + barrel.max.y) / 2;
      addStandin('gas-system', tube(gasX, barrelY, 0, height * 1.6, height * 0.16));
    }
  }

  private applySharedSurfaceDetail(material: THREE.MeshStandardMaterial): void {
    material.roughnessMap = this.surfaceNoiseTexture ?? null;
    material.bumpMap = this.surfaceNoiseTexture ?? null;
    material.bumpScale = 0.004;
    material.envMapIntensity = 1;
    material.needsUpdate = true;
  }

  /** Full procedural rifle, used only if the licensed model fails to load. */
  private buildProceduralFallback(): void {
    for (const config of PART_CONFIGS) {
      const kind = materialKindFor(config.categorySlug);
      const meshes = config.build();
      const entries: ClickableEntry[] = [];
      for (const mesh of meshes) {
        mesh.material = this.createMaterial(kind, COLOR_NEUTRAL_METAL);
        mesh.userData['categorySlug'] = config.categorySlug;
        this.scene.add(mesh);
        this.clickableMeshes.push(mesh);
        this.allMeshes.push(mesh);
        entries.push({
          mesh,
          neutralColor: new THREE.Color(COLOR_NEUTRAL_METAL),
          recolorable: kind !== 'glass'
        });
      }
      this.meshesBySlug.set(config.categorySlug, entries);
    }

    for (const mesh of buildDetailMeshes()) {
      const isPolymerDetail = mesh.position.x < -1.5 && mesh.position.y < -0.2;
      mesh.material = this.createMaterial(
        isPolymerDetail ? 'polymer' : 'metal',
        isPolymerDetail ? COLOR_DETAIL_POLYMER : COLOR_DETAIL_METAL
      );
      this.scene.add(mesh);
      this.allMeshes.push(mesh);
    }
  }

  private createMaterial(kind: MaterialKind, color: number): THREE.Material {
    if (kind === 'glass') {
      return new THREE.MeshPhysicalMaterial({
        color: 0x0c0f12,
        roughness: 0.15,
        metalness: 0.1,
        clearcoat: 1,
        clearcoatRoughness: 0.08,
        envMapIntensity: 1.2,
        side: THREE.DoubleSide
      });
    }
    if (kind === 'polymer') {
      return new THREE.MeshPhysicalMaterial({
        color,
        roughness: 0.75,
        metalness: 0.05,
        clearcoat: 0.15,
        clearcoatRoughness: 0.4,
        envMapIntensity: 0.6,
        roughnessMap: this.surfaceNoiseTexture,
        bumpMap: this.surfaceNoiseTexture,
        bumpScale: 0.006,
        side: THREE.DoubleSide
      });
    }
    return new THREE.MeshPhysicalMaterial({
      color,
      roughness: 0.38,
      metalness: 0.75,
      clearcoat: 0.25,
      clearcoatRoughness: 0.3,
      envMapIntensity: 1,
      roughnessMap: this.surfaceNoiseTexture,
      bumpMap: this.surfaceNoiseTexture,
      bumpScale: 0.004,
      side: THREE.DoubleSide
    });
  }

  /** Small tiled grayscale noise applied as a roughness/bump map so machined-metal and
   * polymer surfaces catch light unevenly instead of reading as flat plastic. */
  private createSurfaceNoiseTexture(): THREE.Texture {
    const size = 128;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d')!;
    const imageData = ctx.createImageData(size, size);
    for (let i = 0; i < imageData.data.length; i += 4) {
      const value = 165 + Math.floor(Math.random() * 60);
      imageData.data[i] = value;
      imageData.data[i + 1] = value;
      imageData.data[i + 2] = value;
      imageData.data[i + 3] = 255;
    }
    ctx.putImageData(imageData, 0, 0);
    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(6, 6);
    return texture;
  }

  private createRadialShadowTexture(): THREE.Texture {
    const size = 256;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d')!;
    const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    gradient.addColorStop(0, 'rgba(0,0,0,0.9)');
    gradient.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  private animate = (): void => {
    this.frameId = requestAnimationFrame(this.animate);
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  };

  private handleResize(): void {
    const host = this.hostRef.nativeElement;
    const width = host.clientWidth || 1;
    const height = host.clientHeight || 1;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }

  private onPointerMove = (event: PointerEvent): void => {
    const hit = this.pick(event);
    const slug = hit?.userData['categorySlug'] as string | undefined;
    if (slug === this.hoveredSlug) return;

    this.hoveredSlug = slug ?? null;
    this.applySelectionColors();
    this.hostRef.nativeElement.style.cursor = slug ? 'pointer' : 'grab';
  };

  private onPointerDown = (event: PointerEvent): void => {
    const hit = this.pick(event);
    const slug = hit?.userData['categorySlug'] as string | undefined;
    if (slug) {
      this.categoryClick.emit(slug);
    }
  };

  // Auto-rotation makes precise clicking impossible -- by the time a user notices
  // they're hovering the part they want, it has already spun past. Pause it while
  // the pointer is over the model and resume once they look away.
  private onPointerEnter = (): void => {
    this.controls.autoRotate = false;
  };

  private onPointerLeave = (): void => {
    this.controls.autoRotate = true;
    this.hoveredSlug = null;
    this.applySelectionColors();
    this.hostRef.nativeElement.style.cursor = 'grab';
  };

  private pick(event: PointerEvent): THREE.Mesh | null {
    const rect = this.hostRef.nativeElement.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.pointer, this.camera);
    const intersections = this.raycaster.intersectObjects(this.clickableMeshes, false);
    return (intersections[0]?.object as THREE.Mesh) ?? null;
  }

  private applySelectionColors(): void {
    const selected = new Set(this.selectedCategorySlugs);
    for (const [slug, entries] of this.meshesBySlug.entries()) {
      let color: THREE.Color | null = null;
      if (slug === this.hoveredSlug) {
        color = new THREE.Color(COLOR_HOVER);
      } else if (selected.has(slug)) {
        color = new THREE.Color(COLOR_SELECTED);
      }

      for (const entry of entries) {
        if (!entry.recolorable) continue;
        const material = entry.mesh.material as THREE.MeshStandardMaterial;
        material.color.copy(color ?? entry.neutralColor);
        if (entry.hiddenWhenNeutral) {
          material.colorWrite = color !== null;
          material.depthWrite = color !== null;
        }
      }
    }
  }
}
