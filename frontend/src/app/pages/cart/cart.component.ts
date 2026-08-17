import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { CartService } from '../../core/services/cart.service';
import { CheckoutLine, MarketplaceService } from '../../core/services/marketplace.service';
import { SeoService } from '../../core/services/seo.service';
import { PageContainerComponent } from '../../shared/components/page-container/page-container.component';

@Component({
  selector: 'app-cart',
  standalone: true,
  imports: [RouterLink, CurrencyPipe, FormsModule, PageContainerComponent],
  templateUrl: './cart.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CartComponent {
  private readonly cartService = inject(CartService);
  private readonly marketplaceService = inject(MarketplaceService);
  private readonly seoService = inject(SeoService);

  readonly lines = this.cartService.lines;
  readonly itemCount = this.cartService.itemCount;
  readonly totalCents = this.cartService.totalCents;

  readonly isCheckingOut = signal(false);
  readonly errorMessage = signal('');
  discountCode = '';

  constructor() {
    this.seoService.updatePage('Cart | GunPartSelector.com', 'Review your cart before checkout.');
  }

  updateQuantity(itemId: string, variantId: string, quantity: number): void {
    this.cartService.updateQuantity(itemId, variantId, quantity);
  }

  removeLine(itemId: string, variantId: string): void {
    this.cartService.removeLine(itemId, variantId);
  }

  checkout(): void {
    this.errorMessage.set('');
    this.isCheckingOut.set(true);

    const checkoutLines: CheckoutLine[] = this.lines().map(line => ({
      itemId: line.item.id,
      variantId: line.variantId,
      quantity: line.quantity
    }));

    this.marketplaceService
      .checkout(checkoutLines, this.discountCode.trim() || undefined)
      .pipe(finalize(() => this.isCheckingOut.set(false)))
      .subscribe({
        next: response => {
          window.location.href = response.checkoutUrl;
        },
        error: error => {
          if (error?.status === 503) {
            this.errorMessage.set(
              "Store checkout isn't configured yet. Check back soon."
            );
          } else if (error?.status === 409) {
            this.errorMessage.set(
              error?.error?.detail ?? 'One of the items in your cart is no longer available.'
            );
          } else {
            this.errorMessage.set('Something went wrong starting checkout. Please try again.');
          }
        }
      });
  }
}
