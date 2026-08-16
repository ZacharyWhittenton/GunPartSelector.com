import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ItemSummary } from '../../core/models/marketplace-item.model';
import { CartService } from '../../core/services/cart.service';
import { MarketplaceService } from '../../core/services/marketplace.service';
import { SeoService } from '../../core/services/seo.service';
import { WishlistService } from '../../core/services/wishlist.service';
import { HeroVideoComponent } from '../../shared/components/hero-video/hero-video.component';

@Component({
  selector: 'app-marketplace',
  standalone: true,
  imports: [RouterLink, CurrencyPipe, HeroVideoComponent],
  templateUrl: './marketplace.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './marketplace.component.css'
})
export class MarketplaceComponent implements OnInit {
  private readonly marketplaceService = inject(MarketplaceService);
  private readonly cartService = inject(CartService);
  private readonly wishlistService = inject(WishlistService);
  private readonly seoService = inject(SeoService);

  readonly items = signal<ItemSummary[]>([]);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly addedItemId = signal<string | null>(null);

  ngOnInit(): void {
    this.seoService.updatePage(
      'Marketplace | WD Web Solutions',
      'Browse and purchase website design and development services and products from WD Web Solutions.'
    );

    this.isLoading.set(true);
    this.errorMessage.set('');

    this.marketplaceService
      .listItems()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: items => this.items.set(items),
        error: () => this.errorMessage.set('Unable to load the marketplace. Please try again.')
      });

    this.wishlistService.load().subscribe({ error: () => {} });
  }

  addToCart(item: ItemSummary): void {
    this.cartService.addItem(item);
    this.addedItemId.set(item.id);
    setTimeout(() => {
      if (this.addedItemId() === item.id) {
        this.addedItemId.set(null);
      }
    }, 1500);
  }

  isWishlisted(itemId: string): boolean {
    return this.wishlistService.isWishlisted(itemId);
  }

  toggleWishlist(item: ItemSummary): void {
    this.wishlistService.toggle(item.id).subscribe({ error: () => {} });
  }
}
