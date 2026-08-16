import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { HeroVideoComponent } from '../../shared/components/hero-video/hero-video.component';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-terms',
  imports: [HeroVideoComponent],
  templateUrl: './terms.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './terms.component.css'
})
export class TermsComponent {
  private readonly seoService = inject(SeoService);

  constructor() {
    this.seoService.updatePage(
      'Terms of Service | WD Web Solutions',
      'Read the WD Web Solutions terms of service governing use of our website and services.'
    );
  }
}
