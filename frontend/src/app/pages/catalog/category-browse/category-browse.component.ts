import { NgFor, NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize, switchMap } from 'rxjs';

import { ProductFacets, ProductQuery, ProductSort, ProductSummary } from '../../../core/models/catalog.model';
import { BuildService } from '../../../core/services/build.service';
import { CatalogService } from '../../../core/services/catalog.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageContainerComponent } from '../../../shared/components/page-container/page-container.component';
import { FacetSidebarComponent } from '../../../shared/components/facet-sidebar/facet-sidebar.component';
import { PartCardComponent } from '../../../shared/components/part-card/part-card.component';

const PAGE_SIZE = 24;

@Component({
  selector: 'app-category-browse',
  standalone: true,
  imports: [NgFor, NgIf, RouterLink, LoadingSpinnerComponent, PageContainerComponent, FacetSidebarComponent, PartCardComponent],
  templateUrl: './category-browse.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CategoryBrowseComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly catalogService = inject(CatalogService);
  private readonly buildService = inject(BuildService);

  readonly categorySlug = signal('');
  readonly categoryName = signal('');
  readonly products = signal<ProductSummary[]>([]);
  readonly total = signal(0);
  readonly facets = signal<ProductFacets | null>(null);
  readonly query = signal<ProductQuery>({ limit: PAGE_SIZE, offset: 0, sort: 'newest' });
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly addedSlug = signal<string | null>(null);

  ngOnInit(): void {
    this.route.paramMap
      .pipe(
        switchMap(params => {
          const slug = params.get('categorySlug') ?? '';
          this.categorySlug.set(slug);
          this.query.set({ ...this.query(), category: slug, offset: 0 });
          this.isLoading.set(true);

          this.catalogService.getCategory(slug).subscribe({
            next: category => this.categoryName.set(category.name)
          });
          this.catalogService.getCategoryFacets(slug).subscribe({
            next: facets => this.facets.set(facets)
          });

          return this.catalogService.listProducts(this.query());
        }),
        finalize(() => this.isLoading.set(false))
      )
      .subscribe({
        next: page => {
          this.products.set(page.items);
          this.total.set(page.total);
        },
        error: () => this.errorMessage.set('Unable to load products. Please try again.')
      });
  }

  onQueryChange(next: ProductQuery): void {
    this.query.set({ ...next, category: this.categorySlug(), limit: PAGE_SIZE });
    this.reload();
  }

  onSortChange(sort: ProductSort): void {
    this.query.set({ ...this.query(), sort, offset: 0 });
    this.reload();
  }

  nextPage(): void {
    const current = this.query();
    const offset = (current.offset ?? 0) + PAGE_SIZE;
    if (offset >= this.total()) return;
    this.query.set({ ...current, offset });
    this.reload();
  }

  previousPage(): void {
    const current = this.query();
    const offset = Math.max((current.offset ?? 0) - PAGE_SIZE, 0);
    this.query.set({ ...current, offset });
    this.reload();
  }

  addToBuild(product: ProductSummary): void {
    this.buildService.setPart(product.categoryId, product);
    this.addedSlug.set(product.slug);
    setTimeout(() => {
      if (this.addedSlug() === product.slug) this.addedSlug.set(null);
    }, 1500);
  }

  private reload(): void {
    this.isLoading.set(true);
    this.catalogService
      .listProducts(this.query())
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: page => {
          this.products.set(page.items);
          this.total.set(page.total);
        },
        error: () => this.errorMessage.set('Unable to load products. Please try again.')
      });
  }
}
