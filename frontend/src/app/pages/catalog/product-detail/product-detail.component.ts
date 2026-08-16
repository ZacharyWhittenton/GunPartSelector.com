import { CurrencyPipe, NgFor, NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ProductDetail } from '../../../core/models/catalog.model';
import { BuildService } from '../../../core/services/build.service';
import { CatalogService } from '../../../core/services/catalog.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageContainerComponent } from '../../../shared/components/page-container/page-container.component';
import { StockStatusBadgeComponent } from '../../../shared/components/stock-status-badge/stock-status-badge.component';

@Component({
  selector: 'app-product-detail',
  standalone: true,
  imports: [
    NgFor,
    NgIf,
    CurrencyPipe,
    RouterLink,
    LoadingSpinnerComponent,
    PageContainerComponent,
    StockStatusBadgeComponent
  ],
  templateUrl: './product-detail.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ProductDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly catalogService = inject(CatalogService);
  private readonly buildService = inject(BuildService);

  readonly categorySlug = signal('');
  readonly product = signal<ProductDetail | null>(null);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly added = signal(false);

  ngOnInit(): void {
    this.categorySlug.set(this.route.snapshot.paramMap.get('categorySlug') ?? '');
    const productSlug = this.route.snapshot.paramMap.get('productSlug') ?? '';

    this.isLoading.set(true);
    this.catalogService
      .getProduct(productSlug)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: product => this.product.set(product),
        error: () => this.errorMessage.set('This part could not be found.')
      });
  }

  addToBuild(): void {
    const product = this.product();
    if (!product) return;
    this.buildService.setPart(product.categoryId, product);
    this.added.set(true);
  }
}
