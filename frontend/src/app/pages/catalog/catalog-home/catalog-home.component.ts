import { NgFor, NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { CatalogSection, PartCategory } from '../../../core/models/catalog.model';
import { CatalogService } from '../../../core/services/catalog.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageContainerComponent } from '../../../shared/components/page-container/page-container.component';

const SECTION_LABELS: Record<CatalogSection, string> = {
  upper: 'Upper Parts',
  lower: 'Lower Parts',
  stock: 'Stock Parts',
  optics: 'Optics',
  accessories: 'Accessories'
};

const SECTION_ORDER: CatalogSection[] = ['upper', 'lower', 'stock', 'optics', 'accessories'];

@Component({
  selector: 'app-catalog-home',
  standalone: true,
  imports: [NgFor, NgIf, RouterLink, LoadingSpinnerComponent, PageContainerComponent],
  templateUrl: './catalog-home.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CatalogHomeComponent implements OnInit {
  private readonly catalogService = inject(CatalogService);

  readonly categories = signal<PartCategory[]>([]);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');

  readonly sections = computed(() =>
    SECTION_ORDER.map(section => ({
      section,
      label: SECTION_LABELS[section],
      categories: this.categories().filter(category => category.section === section)
    })).filter(group => group.categories.length > 0)
  );

  ngOnInit(): void {
    this.isLoading.set(true);
    this.catalogService
      .listCategories()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: categories => this.categories.set(categories),
        error: () => this.errorMessage.set('Unable to load parts catalog. Please try again.')
      });
  }
}
