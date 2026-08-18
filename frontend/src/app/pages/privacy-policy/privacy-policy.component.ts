import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { PageHeroComponent } from '../../shared/components/page-hero/page-hero.component';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-privacy-policy',
  imports: [PageHeroComponent],
  templateUrl: './privacy-policy.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './privacy-policy.component.css'
})
export class PrivacyPolicyComponent {
  private readonly seoService = inject(SeoService);

  constructor() {
    this.seoService.updatePage(
      'Privacy Policy | GunPartSelector.com',
      'Read the GunPartSelector.com privacy policy to learn how we collect, use, and protect your information.'
    );
  }
}
