import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { BuildShareResponse } from '../../core/models/build.model';
import { BuildsApiService } from '../../core/services/builds-api.service';
import { SeoService } from '../../core/services/seo.service';
import { PageContainerComponent } from '../../shared/components/page-container/page-container.component';

interface FeaturedBuildMeta {
  slug: string;
  blurb: string;
}

const FEATURED_BUILDS: FeaturedBuildMeta[] = [
  {
    slug: 'kthwjc9rjw',
    blurb: 'A do-everything mid-length 5.56 carbine built around mil-spec parts.'
  },
  {
    slug: 'qenrvom373',
    blurb: 'A compact .300 Blackout pistol build with an SBA3 brace.'
  },
  {
    slug: '26zreyr54i',
    blurb: 'A rifle-length 6.5 Grendel build set up for distance.'
  }
];

export interface FeaturedBuild extends FeaturedBuildMeta {
  build: BuildShareResponse;
  totalPriceCents: number;
  totalWeightOz: number;
}

@Component({
  selector: 'app-gallery',
  standalone: true,
  imports: [RouterLink, CurrencyPipe, PageContainerComponent],
  templateUrl: './gallery.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './gallery.component.css'
})
export class GalleryComponent implements OnInit {
  private readonly buildsApi = inject(BuildsApiService);
  private readonly seoService = inject(SeoService);

  readonly featuredBuilds = signal<FeaturedBuild[]>([]);
  readonly isLoading = signal(false);

  ngOnInit(): void {
    this.seoService.updatePage(
      'Featured Builds | GunPartSelector.com',
      'Real AR-15 builds assembled with GunPartSelector.com, from duty carbines to precision rifles.'
    );

    this.isLoading.set(true);
    forkJoin(FEATURED_BUILDS.map(meta => this.buildsApi.getBuildBySlug(meta.slug))).subscribe({
      next: builds => {
        this.featuredBuilds.set(
          builds.map((build, index) => ({
            ...FEATURED_BUILDS[index],
            build,
            totalPriceCents: build.items.reduce(
              (sum, item) => sum + item.product.priceCents * item.quantity,
              0
            ),
            totalWeightOz: build.items.reduce(
              (sum, item) => sum + item.product.weightOz * item.quantity,
              0
            )
          }))
        );
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false)
    });
  }
}
