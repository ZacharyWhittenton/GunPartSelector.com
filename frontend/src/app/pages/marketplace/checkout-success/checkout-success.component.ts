import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { OrderSummary } from '../../../core/models/order.model';
import { CartService } from '../../../core/services/cart.service';
import { MarketplaceService } from '../../../core/services/marketplace.service';
import { SeoService } from '../../../core/services/seo.service';

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 15;

@Component({
  selector: 'app-checkout-success',
  standalone: true,
  imports: [RouterLink, CurrencyPipe],
  templateUrl: './checkout-success.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './checkout-success.component.css'
})
export class CheckoutSuccessComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly marketplaceService = inject(MarketplaceService);
  private readonly cartService = inject(CartService);
  private readonly seoService = inject(SeoService);

  readonly order = signal<OrderSummary | null>(null);
  readonly errorMessage = signal('');
  readonly attempts = signal(0);

  private pollHandle: ReturnType<typeof setTimeout> | null = null;
  private cartCleared = false;

  ngOnInit(): void {
    this.seoService.updatePage(
      'Order Confirmation | WD Web Solutions',
      'Your order confirmation from WD Web Solutions.'
    );

    const sessionId = this.route.snapshot.queryParamMap.get('session_id');
    if (!sessionId) {
      this.errorMessage.set('Missing checkout session.');
      return;
    }

    this.poll(sessionId);
  }

  ngOnDestroy(): void {
    if (this.pollHandle) {
      clearTimeout(this.pollHandle);
    }
  }

  private poll(sessionId: string): void {
    this.marketplaceService.getOrderBySession(sessionId).subscribe({
      next: order => {
        this.order.set(order);

        if (!this.cartCleared && order.status !== 'open') {
          this.cartService.clear();
          this.cartCleared = true;
        }

        if (order.status === 'open' && this.attempts() < MAX_POLL_ATTEMPTS) {
          this.attempts.update(count => count + 1);
          this.pollHandle = setTimeout(() => this.poll(sessionId), POLL_INTERVAL_MS);
        }
      },
      error: () => {
        if (this.attempts() < MAX_POLL_ATTEMPTS) {
          this.attempts.update(count => count + 1);
          this.pollHandle = setTimeout(() => this.poll(sessionId), POLL_INTERVAL_MS);
        } else {
          this.errorMessage.set('Unable to confirm your order right now.');
        }
      }
    });
  }
}
