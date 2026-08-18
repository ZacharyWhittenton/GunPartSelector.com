import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { ItemSummary } from '../../../core/models/marketplace-item.model';
import { MarketplaceService } from '../../../core/services/marketplace.service';
import { SeoService } from '../../../core/services/seo.service';
import { PageContainerComponent } from '../../../shared/components/page-container/page-container.component';
import { PageHeroComponent } from '../../../shared/components/page-hero/page-hero.component';

@Component({
  selector: 'app-merch-list',
  standalone: true,
  imports: [RouterLink, CurrencyPipe, PageContainerComponent, PageHeroComponent],
  templateUrl: './merch-list.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MerchListComponent implements OnInit {
  private readonly marketplaceService = inject(MarketplaceService);
  private readonly seoService = inject(SeoService);

  readonly items = signal<ItemSummary[]>([]);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');

  ngOnInit(): void {
    this.seoService.updatePage(
      'Store | GunPartSelector.com',
      'GunPartSelector.com hoodies and t-shirts.'
    );

    this.isLoading.set(true);
    this.marketplaceService
      .listItems()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: items => this.items.set(items),
        error: () => this.errorMessage.set('Unable to load the store right now.')
      });
  }
}
