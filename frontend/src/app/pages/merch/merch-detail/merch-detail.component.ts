import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ItemSummary, ItemVariantSummary } from '../../../core/models/marketplace-item.model';
import { CartService } from '../../../core/services/cart.service';
import { MarketplaceService } from '../../../core/services/marketplace.service';
import { SeoService } from '../../../core/services/seo.service';
import { PageContainerComponent } from '../../../shared/components/page-container/page-container.component';

@Component({
  selector: 'app-merch-detail',
  standalone: true,
  imports: [RouterLink, CurrencyPipe, PageContainerComponent],
  templateUrl: './merch-detail.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MerchDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly marketplaceService = inject(MarketplaceService);
  private readonly cartService = inject(CartService);
  private readonly seoService = inject(SeoService);

  readonly item = signal<ItemSummary | null>(null);
  readonly isLoading = signal(false);
  readonly notFound = signal(false);
  readonly selectedVariantId = signal<string | null>(null);
  readonly justAdded = signal(false);

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug') ?? '';
    this.isLoading.set(true);

    this.marketplaceService
      .getItem(slug)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: item => {
          this.item.set(item);
          this.seoService.updatePage(`${item.name} | GunPartSelector.com`, item.description);
          const firstInStock = item.variants.find(v => v.stockStatus === 'in_stock');
          this.selectedVariantId.set(firstInStock?.id ?? null);
        },
        error: () => this.notFound.set(true)
      });
  }

  selectVariant(variant: ItemVariantSummary): void {
    if (variant.stockStatus === 'out_of_stock') return;
    this.selectedVariantId.set(variant.id);
  }

  addToCart(): void {
    const item = this.item();
    const variantId = this.selectedVariantId();
    if (!item || !variantId) return;

    const variant = item.variants.find(v => v.id === variantId);
    if (!variant) return;

    this.cartService.addLine(item, variant.id, variant.label);
    this.justAdded.set(true);
    setTimeout(() => this.justAdded.set(false), 2000);
  }

  goToCart(): void {
    this.router.navigateByUrl('/cart');
  }
}
