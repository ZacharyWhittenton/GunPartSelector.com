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

interface PartMeshConfig {
  categorySlug: string;
  build: () => THREE.Mesh[];
}

type MaterialKind = 'metal' | 'polymer' | 'glass';

// Matte anodized aluminum / phosphate-finish tones rather than raw silvery grey --
// real AR-15 receivers and barrels read much darker than bare metal.
const COLOR_NEUTRAL_METAL = 0x35383d;
const COLOR_NEUTRAL_POLYMER = 0x1f2225;
const COLOR_SELECTED = 0xc0262f;
const COLOR_HOVER = 0xe06068;
const COLOR_DETAIL_METAL = 0x26282c;
const COLOR_DETAIL_POLYMER = 0x1a1c1f;

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

/** Static, non-interactive detail meshes that flesh out the silhouette (magazine, trigger
 * guard, rail ridges, sights) but aren't tied to a pickable catalog category. */
function buildDetailMeshes(): THREE.Mesh[] {
  const meshes: THREE.Mesh[] = [];

  // Magazine: tapered polymer PMAG-style body hanging from the magwell.
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
  meshes.push(magazine);

  // Trigger guard: thin extruded loop in front of the trigger.
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

  // Front sight post, near the muzzle end of the handguard.
  meshes.push(box(4.9, 0.42, 0, 0.1, 0.4, 0.1));
  // Rear flip sight, atop the upper receiver.
  meshes.push(box(-1.0, 0.38, 0, 0.16, 0.22, 0.14));

  // Picatinny rail ridges along the top of the upper receiver + handguard.
  for (let i = 0; i < 9; i++) {
    meshes.push(box(-0.75 + i * 0.24, 0.34, 0, 0.05, 0.06, 0.42));
  }
  for (let i = 0; i < 10; i++) {
    meshes.push(box(1.9 + i * 0.32, 0.29, 0, 0.06, 0.05, 0.4));
  }

  // M-LOK slots along the underside of the handguard.
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
  { categorySlug: 'foregrip', build: () => [box(2.6, -0.62, 0, 0.22, 0.4, 0.22)] },
  {
    categorySlug: 'upper-receiver',
    build: () => [box(0.3, 0.05, 0, 2.2, 0.55, 0.5)]
  },
  { categorySlug: 'charging-handle', build: () => [box(-0.55, 0.38, 0, 0.35, 0.12, 0.2)] },
  { categorySlug: 'bolt-carrier-group', build: () => [box(0.05, 0.05, 0.3, 1.6, 0.2, 0.08)] },
  { categorySlug: 'optic-mount', build: () => [box(0.15, 0.36, 0, 0.9, 0.12, 0.35)] },
  { categorySlug: 'optic', build: () => [tube(0.15, 0.72, 0, 0.9, 0.16)] },
  {
    categorySlug: 'lower-receiver',
    build: () => [
      box(-1.6, -0.15, 0, 1.6, 0.6, 0.5),
      box(-2.05, -0.42, 0, 0.55, 0.22, 0.56, -0.28)
    ]
  },
  { categorySlug: 'trigger', build: () => [box(-1.85, -0.62, 0, 0.14, 0.35, 0.14)] },
  { categorySlug: 'pistol-grip', build: () => [box(-2.55, -0.95, 0, 0.3, 0.75, 0.4, 0.35)] },
  { categorySlug: 'buffer-tube', build: () => [tube(-3.55, -0.05, 0, 1.5, 0.18, 0.18, 12)] },
  { categorySlug: 'buffer-kit', build: () => [tube(-4.35, -0.05, 0, 0.35, 0.21, 0.21, 12)] },
  {
    categorySlug: 'stock-brace',
    build: () => [
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
  'optic-mount',
  'lower-receiver',
  'trigger',
  'buffer-tube',
  'buffer-kit'
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
  private readonly meshesBySlug = new Map<string, { mesh: THREE.Mesh; kind: MaterialKind }[]>();
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
    this.applySelectionColors();
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

    // Soft contact shadow beneath the rifle so it reads as grounded rather than floating.
    const shadowTexture = this.createRadialShadowTexture();
    const shadowMaterial = new THREE.MeshBasicMaterial({
      map: shadowTexture,
      transparent: true,
      opacity: 0.45,
      depthWrite: false
    });
    const shadow = new THREE.Mesh(new THREE.PlaneGeometry(11, 3.2), shadowMaterial);
    shadow.rotation.x = -Math.PI / 2;
    shadow.position.set(1.5, -1.3, 0);
    this.scene.add(shadow);

    for (const config of PART_CONFIGS) {
      const kind = materialKindFor(config.categorySlug);
      const meshes = config.build();
      const entries: { mesh: THREE.Mesh; kind: MaterialKind }[] = [];
      for (const mesh of meshes) {
        mesh.material = this.createMaterial(kind, COLOR_NEUTRAL_METAL);
        mesh.userData['categorySlug'] = config.categorySlug;
        this.scene.add(mesh);
        this.clickableMeshes.push(mesh);
        this.allMeshes.push(mesh);
        entries.push({ mesh, kind });
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

    this.resizeObserver = new ResizeObserver(() => this.handleResize());
    this.resizeObserver.observe(host);
    this.handleResize();

    host.addEventListener('pointermove', this.onPointerMove);
    host.addEventListener('pointerdown', this.onPointerDown);

    this.animate();
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
    const gradient = ctx.createRadialGradient(
      size / 2,
      size / 2,
      0,
      size / 2,
      size / 2,
      size / 2
    );
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
      let color = COLOR_NEUTRAL_METAL;
      let usePolymerBase = false;
      if (slug === this.hoveredSlug) {
        color = COLOR_HOVER;
      } else if (selected.has(slug)) {
        color = COLOR_SELECTED;
      } else {
        usePolymerBase = true;
      }

      for (const { mesh, kind } of entries) {
        const material = mesh.material as THREE.MeshPhysicalMaterial;
        if (usePolymerBase && kind === 'polymer') {
          material.color.setHex(COLOR_NEUTRAL_POLYMER);
        } else if (usePolymerBase && kind === 'glass') {
          // glass parts keep their fixed lens color regardless of selection
        } else {
          material.color.setHex(color);
        }
      }
    }
  }
}
