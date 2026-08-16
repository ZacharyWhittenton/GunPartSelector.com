import { CurrencyPipe, NgFor, NgIf } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { BuildShareResponse } from '../../../core/models/build.model';
import { BuildsApiService } from '../../../core/services/builds-api.service';
import { BuildService } from '../../../core/services/build.service';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { PageContainerComponent } from '../../../shared/components/page-container/page-container.component';

@Component({
  selector: 'app-build-share',
  standalone: true,
  imports: [NgFor, NgIf, CurrencyPipe, RouterLink, LoadingSpinnerComponent, PageContainerComponent],
  templateUrl: './build-share.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class BuildShareComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly buildsApi = inject(BuildsApiService);
  private readonly buildService = inject(BuildService);

  readonly build = signal<BuildShareResponse | null>(null);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly copied = signal(false);

  readonly totalPriceCents = () =>
    (this.build()?.items ?? []).reduce((sum, item) => sum + item.product.priceCents * item.quantity, 0);

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug') ?? '';
    this.isLoading.set(true);
    this.buildsApi
      .getBuildBySlug(slug)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: build => this.build.set(build),
        error: () => this.errorMessage.set('This build could not be found.')
      });
  }

  copyLink(): void {
    navigator.clipboard?.writeText(window.location.href);
    this.copied.set(true);
    setTimeout(() => this.copied.set(false), 1500);
  }

  loadIntoMyBuilder(): void {
    const build = this.build();
    if (!build) return;
    this.buildService.clear();
    for (const item of build.items) {
      this.buildService.setPart(item.product.categoryId, item.product);
    }
  }
}
