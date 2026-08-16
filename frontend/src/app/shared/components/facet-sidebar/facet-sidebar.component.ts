import { KeyValuePipe, NgFor, NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';

import { ProductFacets, ProductQuery } from '../../../core/models/catalog.model';

@Component({
  selector: 'app-facet-sidebar',
  standalone: true,
  imports: [NgFor, NgIf, KeyValuePipe],
  templateUrl: './facet-sidebar.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FacetSidebarComponent {
  @Input() facets: ProductFacets | null = null;
  @Input() query: ProductQuery = {};
  @Output() queryChange = new EventEmitter<ProductQuery>();

  toggleBrand(brand: string): void {
    const current = this.query.brand ?? [];
    const next = current.includes(brand)
      ? current.filter(b => b !== brand)
      : [...current, brand];
    this.queryChange.emit({ ...this.query, brand: next.length ? next : undefined, offset: 0 });
  }

  toggleTag(prefix: string, value: string): void {
    const tag = `${prefix}:${value}`;
    const current = this.query.tag ?? [];
    const next = current.includes(tag) ? current.filter(t => t !== tag) : [...current, tag];
    this.queryChange.emit({ ...this.query, tag: next.length ? next : undefined, offset: 0 });
  }

  isBrandSelected(brand: string): boolean {
    return (this.query.brand ?? []).includes(brand);
  }

  isTagSelected(prefix: string, value: string): boolean {
    return (this.query.tag ?? []).includes(`${prefix}:${value}`);
  }

  setPriceMin(value: string): void {
    const cents = value ? Math.round(Number(value) * 100) : undefined;
    this.queryChange.emit({ ...this.query, priceMin: cents, offset: 0 });
  }

  setPriceMax(value: string): void {
    const cents = value ? Math.round(Number(value) * 100) : undefined;
    this.queryChange.emit({ ...this.query, priceMax: cents, offset: 0 });
  }

  toggleInStockOnly(checked: boolean): void {
    this.queryChange.emit({ ...this.query, stock: checked ? 'in_stock' : undefined, offset: 0 });
  }

  clearAll(): void {
    this.queryChange.emit({ category: this.query.category, sort: this.query.sort, offset: 0 });
  }
}
