import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { HeroVideoComponent } from '../../shared/components/hero-video/hero-video.component';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-privacy-policy',
  imports: [HeroVideoComponent],
  templateUrl: './privacy-policy.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './privacy-policy.component.css'
})
export class PrivacyPolicyComponent {
  private readonly seoService = inject(SeoService);

  constructor() {
    this.seoService.updatePage(
      'Privacy Policy | WD Web Solutions',
      'Read the WD Web Solutions privacy policy to learn how we collect, use, and protect your information.'
    );
  }
}
