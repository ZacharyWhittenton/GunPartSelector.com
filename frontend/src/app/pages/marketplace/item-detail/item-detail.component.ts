import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ItemSummary } from '../../../core/models/marketplace-item.model';
import { CartService } from '../../../core/services/cart.service';
import { MarketplaceService } from '../../../core/services/marketplace.service';
import { SeoService } from '../../../core/services/seo.service';
import { WishlistService } from '../../../core/services/wishlist.service';

@Component({
  selector: 'app-item-detail',
  standalone: true,
  imports: [RouterLink, FormsModule, CurrencyPipe],
  templateUrl: './item-detail.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './item-detail.component.css'
})
export class ItemDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly marketplaceService = inject(MarketplaceService);
  private readonly cartService = inject(CartService);
  private readonly wishlistService = inject(WishlistService);
  private readonly seoService = inject(SeoService);

  readonly item = signal<ItemSummary | null>(null);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly wasAdded = signal(false);

  quantity = 1;

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug');
    if (!slug) {
      this.router.navigateByUrl('/marketplace');
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    this.marketplaceService
      .getItem(slug)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: item => {
          this.item.set(item);
          this.seoService.updatePage(
            `${item.name} | WD Web Solutions`,
            item.description,
            item.imageUrl ?? undefined
          );
        },
        error: () => this.errorMessage.set('That item could not be found.')
      });

    this.wishlistService.load().subscribe({ error: () => {} });
  }

  addToCart(): void {
    const item = this.item();
    if (!item) {
      return;
    }

    this.cartService.addItem(item, Math.max(this.quantity, 1));
    this.wasAdded.set(true);
    setTimeout(() => this.wasAdded.set(false), 1500);
  }

  isWishlisted(): boolean {
    const item = this.item();
    return item ? this.wishlistService.isWishlisted(item.id) : false;
  }

  toggleWishlist(): void {
    const item = this.item();
    if (!item) {
      return;
    }
    this.wishlistService.toggle(item.id).subscribe({ error: () => {} });
  }
}
