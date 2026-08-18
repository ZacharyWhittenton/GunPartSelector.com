import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { SeoService } from '../../core/services/seo.service';
import { PageContainerComponent } from '../../shared/components/page-container/page-container.component';
import { PageHeroComponent } from '../../shared/components/page-hero/page-hero.component';
import { ScrollRevealDirective } from '../../shared/directives/scroll-reveal.directive';

@Component({
  selector: 'app-about',
  standalone: true,
  imports: [RouterLink, PageContainerComponent, PageHeroComponent, ScrollRevealDirective],
  templateUrl: './about.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './about.component.css'
})
export class AboutComponent {
  constructor(private seoService: SeoService) {
    this.seoService.updatePage(
      'About | GunPartSelector.com',
      'GunPartSelector.com is a build configurator for AR-15 platform rifles: browse parts by category, check compatibility, and assemble your build.'
    );
  }
}
