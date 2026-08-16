import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { OrderStatus, OrderSummary } from '../../../core/models/order.model';
import { CsvExportService } from '../../../core/services/csv-export.service';
import { MarketplaceAdminService } from '../../../core/services/marketplace-admin.service';

@Component({
  selector: 'app-admin-marketplace-orders',
  standalone: true,
  imports: [RouterLink, CurrencyPipe, DatePipe],
  templateUrl: './admin-marketplace-orders.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './admin-marketplace-orders.component.css'
})
export class AdminMarketplaceOrdersComponent implements OnInit {
  private readonly marketplaceAdminService = inject(MarketplaceAdminService);
  private readonly csvExportService = inject(CsvExportService);

  readonly orders = signal<OrderSummary[]>([]);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly statusFilter = signal<OrderStatus | ''>('');
  readonly statusOptions: (OrderStatus | '')[] = ['', 'open', 'paid', 'expired', 'cancelled'];

  ngOnInit(): void {
    this.loadOrders();
  }

  loadOrders(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    const status = this.statusFilter() || undefined;

    this.marketplaceAdminService
      .listAllOrders(status)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: orders => this.orders.set(orders),
        error: () => this.errorMessage.set('Unable to load orders. Please try again.')
      });
  }

  onFilterChange(status: OrderStatus | ''): void {
    this.statusFilter.set(status);
    this.loadOrders();
  }

  exportCsv(): void {
    const headers = ['Order ID', 'Status', 'Items', 'Total', 'Placed At'];
    const rows = this.orders().map(order => [
      order.id,
      order.status,
      order.items.map(item => `${item.itemName} x${item.quantity}`).join('; '),
      (order.totalCents / 100).toFixed(2),
      order.createdAt
    ]);

    this.csvExportService.download('orders.csv', headers, rows);
  }
}
