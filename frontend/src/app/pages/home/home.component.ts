import { CurrencyPipe, DecimalPipe, NgFor, NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { CatalogSection, PartCategory, ProductSummary } from '../../core/models/catalog.model';
import { BuildService } from '../../core/services/build.service';
import { BuildsApiService } from '../../core/services/builds-api.service';
import { CatalogService } from '../../core/services/catalog.service';
import { CompatibilityBannerComponent } from '../../shared/components/compatibility-banner/compatibility-banner.component';
import { LoadingSpinnerComponent } from '../../shared/components/loading-spinner/loading-spinner.component';
import { PartCardComponent } from '../../shared/components/part-card/part-card.component';
import { Ar15ViewerComponent } from './ar15-viewer/ar15-viewer.component';

const SECTION_LABELS: Record<CatalogSection, string> = {
  upper: 'Upper Parts',
  lower: 'Lower Parts',
  stock: 'Stock Parts',
  optics: 'Optics',
  accessories: 'Accessories'
};

const SECTION_ORDER: CatalogSection[] = ['upper', 'lower', 'stock', 'optics', 'accessories'];

export type HomeScene = 'desert' | 'forest' | 'pasture';

const SCENE_STORAGE_KEY = 'wd_home_scene';

interface SceneConfig {
  label: string;
  image: string;
}

const SCENE_CONFIG: Record<HomeScene, SceneConfig> = {
  desert: { label: 'Desert', image: '/assets/images/scenery/red-rock-desert.jpg' },
  forest: { label: 'Forest', image: '/assets/images/scenery/alpine-forest-lake.jpg' },
  pasture: { label: 'Pasture', image: '/assets/images/scenery/olive-grove-golden-hour.jpg' }
};

const SCENE_ORDER: HomeScene[] = ['desert', 'forest', 'pasture'];

function isHomeScene(value: string | null): value is HomeScene {
  return value === 'desert' || value === 'forest' || value === 'pasture';
}

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    NgFor,
    NgIf,
    CurrencyPipe,
    DecimalPipe,
    RouterLink,
    Ar15ViewerComponent,
    PartCardComponent,
    CompatibilityBannerComponent,
    LoadingSpinnerComponent
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HomeComponent implements OnInit {
  private readonly catalogService = inject(CatalogService);
  private readonly buildsApi = inject(BuildsApiService);
  private readonly router = inject(Router);
  readonly buildService = inject(BuildService);

  readonly categories = signal<PartCategory[]>([]);
  readonly webglUnavailable = signal(false);

  readonly scene = signal<HomeScene>(this.readStoredScene());
  readonly sceneOrder = SCENE_ORDER;
  readonly sceneConfig = SCENE_CONFIG;
  readonly sceneImage = computed(() => SCENE_CONFIG[this.scene()].image);

  readonly isLoadingCategories = signal(false);

  readonly activeCategorySlug = signal<string | null>(null);
  readonly activeProducts = signal<ProductSummary[]>([]);
  readonly isLoadingProducts = signal(false);

  readonly isSharing = signal(false);
  readonly shareError = signal('');

  readonly sections = computed(() =>
    SECTION_ORDER.map(section => ({
      section,
      label: SECTION_LABELS[section],
      categories: this.categories().filter(category => category.section === section)
    })).filter(group => group.categories.length > 0)
  );

  readonly activeCategory = computed(() =>
    this.categories().find(category => category.slug === this.activeCategorySlug()) ?? null
  );

  readonly selectedCategorySlugs = computed(() => {
    const byCategory = this.buildService.byCategory();
    return this.categories()
      .filter(category => byCategory.has(category.id))
      .map(category => category.slug);
  });

  readonly buildProgress = computed(() => {
    const total = this.categories().length;
    if (!total) return { percent: 0, filled: 0, total: 0 };
    const filled = this.selectedCategorySlugs().length;
    return { percent: Math.round((filled / total) * 100), filled, total };
  });

  ngOnInit(): void {
    this.isLoadingCategories.set(true);
    this.catalogService
      .listCategories()
      .pipe(finalize(() => this.isLoadingCategories.set(false)))
      .subscribe({
        next: categories => this.categories.set(categories)
      });
  }

  selectedProductFor(category: PartCategory): ProductSummary | null {
    return this.buildService.byCategory().get(category.id)?.product ?? null;
  }

  openCategory(slug: string): void {
    this.activeCategorySlug.set(slug);
    this.isLoadingProducts.set(true);
    this.catalogService
      .listProducts({ category: slug, limit: 8, sort: 'newest' })
      .pipe(finalize(() => this.isLoadingProducts.set(false)))
      .subscribe({
        next: page => this.activeProducts.set(page.items)
      });
  }

  onViewerCategoryClick(slug: string): void {
    this.openCategory(slug);
    document.getElementById('active-category-picker')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  addToBuild(product: ProductSummary): void {
    this.buildService.setPart(product.categoryId, product);
  }

  removeFromBuild(categoryId: string): void {
    this.buildService.removePart(categoryId);
  }

  shareBuild(): void {
    const parts = this.buildService.parts();
    if (!parts.length) return;

    this.isSharing.set(true);
    this.shareError.set('');
    this.buildsApi
      .createBuildShare(parts.map(part => ({ productId: part.product.id, quantity: part.quantity })))
      .pipe(finalize(() => this.isSharing.set(false)))
      .subscribe({
        next: response => this.router.navigate(['/builder/share', response.slug]),
        error: () => this.shareError.set('Unable to share this build right now.')
      });
  }

  clearBuild(): void {
    this.buildService.clear();
  }

  setScene(scene: HomeScene): void {
    this.scene.set(scene);
    try {
      localStorage.setItem(SCENE_STORAGE_KEY, scene);
    } catch {
      // localStorage unavailable (e.g. private browsing) -- scene choice just won't persist
    }
  }

  private readStoredScene(): HomeScene {
    try {
      const stored = localStorage.getItem(SCENE_STORAGE_KEY);
      return isHomeScene(stored) ? stored : 'desert';
    } catch {
      return 'desert';
    }
  }
}
