import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { OrderSummary } from '../../core/models/order.model';
import { AuthService } from '../../core/services/auth.service';
import { MarketplaceService } from '../../core/services/marketplace.service';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-account',
  standalone: true,
  imports: [RouterLink, CurrencyPipe, DatePipe],
  templateUrl: './account.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './account.component.css'
})
export class AccountComponent implements OnInit {
  private readonly marketplaceService = inject(MarketplaceService);
  private readonly authService = inject(AuthService);
  private readonly seoService = inject(SeoService);

  readonly isAuthenticated = this.authService.isAuthenticated;
  readonly currentUser = this.authService.currentUser;

  readonly orders = signal<OrderSummary[]>([]);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');

  ngOnInit(): void {
    this.seoService.updatePage(
      'My Account | GunPartSelector.com',
      'View your order history and saved builds.'
    );

    if (this.isAuthenticated) {
      this.loadOrders();
    }
  }

  loadOrders(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.marketplaceService
      .listMyOrders()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: orders => this.orders.set(orders),
        error: () => this.errorMessage.set('Unable to load your orders. Please try again.')
      });
  }
}
