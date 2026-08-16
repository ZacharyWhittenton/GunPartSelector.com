import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ItemSummary } from '../../core/models/marketplace-item.model';
import { CartService } from '../../core/services/cart.service';
import { MarketplaceService } from '../../core/services/marketplace.service';
import { SeoService } from '../../core/services/seo.service';
import { WishlistService } from '../../core/services/wishlist.service';

@Component({
  selector: 'app-wishlist',
  standalone: true,
  imports: [RouterLink, CurrencyPipe],
  templateUrl: './wishlist.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './wishlist.component.css'
})
export class WishlistComponent implements OnInit {
  private readonly marketplaceService = inject(MarketplaceService);
  private readonly cartService = inject(CartService);
  private readonly wishlistService = inject(WishlistService);
  private readonly seoService = inject(SeoService);

  private readonly allItems = signal<ItemSummary[]>([]);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');

  readonly wishlistedItems = computed(() => {
    const ids = new Set(this.wishlistService.itemIds());
    return this.allItems().filter(item => ids.has(item.id));
  });

  ngOnInit(): void {
    this.seoService.updatePage(
      'Wishlist | WD Web Solutions',
      'View and manage the items you have saved to your wishlist with WD Web Solutions.'
    );

    this.isLoading.set(true);
    this.errorMessage.set('');

    this.wishlistService.load().subscribe({
      error: () => this.errorMessage.set('Unable to load your wishlist.')
    });

    this.marketplaceService
      .listItems()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: items => this.allItems.set(items),
        error: () => this.errorMessage.set('Unable to load your wishlist.')
      });
  }

  addToCart(item: ItemSummary): void {
    this.cartService.addItem(item);
  }

  remove(itemId: string): void {
    this.wishlistService.remove(itemId).subscribe({ error: () => {} });
  }
}
