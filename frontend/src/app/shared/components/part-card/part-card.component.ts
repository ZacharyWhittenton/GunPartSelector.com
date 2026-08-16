import { CurrencyPipe, NgFor, NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ProductSummary } from '../../../core/models/catalog.model';
import { StockStatusBadgeComponent } from '../stock-status-badge/stock-status-badge.component';

@Component({
  selector: 'app-part-card',
  standalone: true,
  imports: [CurrencyPipe, NgFor, NgIf, RouterLink, StockStatusBadgeComponent],
  templateUrl: './part-card.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PartCardComponent {
  @Input({ required: true }) product!: ProductSummary;
  @Input() categorySlug = '';
  @Input() selected = false;
  @Output() addToBuild = new EventEmitter<ProductSummary>();

  onAddToBuild(event: Event): void {
    event.preventDefault();
    event.stopPropagation();
    this.addToBuild.emit(this.product);
  }
}
