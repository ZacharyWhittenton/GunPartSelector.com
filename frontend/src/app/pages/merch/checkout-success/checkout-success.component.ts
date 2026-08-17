import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { OrderSummary } from '../../../core/models/order.model';
import { CartService } from '../../../core/services/cart.service';
import { MarketplaceService } from '../../../core/services/marketplace.service';
import { SeoService } from '../../../core/services/seo.service';
import { PageContainerComponent } from '../../../shared/components/page-container/page-container.component';

@Component({
  selector: 'app-checkout-success',
  standalone: true,
  imports: [RouterLink, CurrencyPipe, PageContainerComponent],
  templateUrl: './checkout-success.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CheckoutSuccessComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly marketplaceService = inject(MarketplaceService);
  private readonly cartService = inject(CartService);
  private readonly seoService = inject(SeoService);

  readonly order = signal<OrderSummary | null>(null);
  readonly isLoading = signal(true);
  readonly notFound = signal(false);

  ngOnInit(): void {
    this.seoService.updatePage('Order Confirmed | GunPartSelector.com', 'Thanks for your order.');

    const sessionId = this.route.snapshot.queryParamMap.get('session_id');
    if (!sessionId) {
      this.notFound.set(true);
      this.isLoading.set(false);
      return;
    }

    this.marketplaceService
      .getOrderBySession(sessionId)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: order => {
          this.order.set(order);
          this.cartService.clear();
        },
        error: () => this.notFound.set(true)
      });
  }
}
