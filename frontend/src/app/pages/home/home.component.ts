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
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HomeComponent implements OnInit {
  private readonly catalogService = inject(CatalogService);
  private readonly buildsApi = inject(BuildsApiService);
  private readonly router = inject(Router);
  readonly buildService = inject(BuildService);

  readonly categories = signal<PartCategory[]>([]);
  readonly webglUnavailable = signal(false);

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
}
