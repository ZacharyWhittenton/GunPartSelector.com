import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

import { StockStatus } from '../../../core/models/catalog.model';

@Component({
  selector: 'app-stock-status-badge',
  standalone: true,
  imports: [],
  templateUrl: './stock-status-badge.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class StockStatusBadgeComponent {
  @Input({ required: true }) status!: StockStatus;

  get label(): string {
    if (this.status === 'in_stock') return 'In Stock';
    if (this.status === 'out_of_stock') return 'Out of Stock';
    return 'Unknown';
  }
}
