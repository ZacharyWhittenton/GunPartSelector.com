import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { CartService } from '../../core/services/cart.service';
import { MarketplaceService } from '../../core/services/marketplace.service';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-cart',
  standalone: true,
  imports: [RouterLink, FormsModule, CurrencyPipe],
  templateUrl: './cart.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './cart.component.css'
})
export class CartComponent {
  private readonly cartService = inject(CartService);
  private readonly marketplaceService = inject(MarketplaceService);
  private readonly seoService = inject(SeoService);

  readonly lines = this.cartService.lines;
  readonly totalCents = this.cartService.totalCents;

  readonly isCheckingOut = signal(false);
  readonly errorMessage = signal('');
  readonly discountCode = signal('');

  constructor() {
    this.seoService.updatePage(
      'Your Cart | WD Web Solutions',
      'Review your cart and check out securely with WD Web Solutions.'
    );
  }

  updateQuantity(itemId: string, quantity: number): void {
    if (quantity < 1) {
      this.cartService.removeItem(itemId);
      return;
    }
    this.cartService.updateQuantity(itemId, quantity);
  }

  removeItem(itemId: string): void {
    this.cartService.removeItem(itemId);
  }

  checkout(): void {
    this.errorMessage.set('');
    this.isCheckingOut.set(true);

    const lines = this.lines().map(line => ({ itemId: line.itemId, quantity: line.quantity }));

    this.marketplaceService
      .checkout(lines, this.discountCode().trim())
      .pipe(finalize(() => this.isCheckingOut.set(false)))
      .subscribe({
        next: response => {
          window.location.href = response.checkoutUrl;
        },
        error: error => {
          if (error.status === 400) {
            this.errorMessage.set('That discount code is invalid or expired.');
          } else if (error.status === 503) {
            this.errorMessage.set('Checkout is not available yet. Please check back soon.');
          } else {
            this.errorMessage.set('Unable to start checkout. Please try again.');
          }
        }
      });
  }
}
