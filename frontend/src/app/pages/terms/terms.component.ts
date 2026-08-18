import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { PageHeroComponent } from '../../shared/components/page-hero/page-hero.component';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-terms',
  imports: [PageHeroComponent],
  templateUrl: './terms.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './terms.component.css'
})
export class TermsComponent {
  private readonly seoService = inject(SeoService);

  constructor() {
    this.seoService.updatePage(
      'Terms of Service | GunPartSelector.com',
      'Read the GunPartSelector.com terms of service governing use of our website.'
    );
  }
}
