import { ChangeDetectionStrategy, Component } from '@angular/core';

import { RESOURCES } from '../../core/data/resources.data';
import { SeoService } from '../../core/services/seo.service';
import { PageContainerComponent } from '../../shared/components/page-container/page-container.component';
import { PageHeroComponent } from '../../shared/components/page-hero/page-hero.component';
import { ScrollRevealDirective } from '../../shared/directives/scroll-reveal.directive';

@Component({
  selector: 'app-resources',
  standalone: true,
  imports: [PageContainerComponent, PageHeroComponent, ScrollRevealDirective],
  templateUrl: './resources.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './resources.component.css'
})
export class ResourcesComponent {
  readonly resources = RESOURCES;

  constructor(private seoService: SeoService) {
    this.seoService.updatePage(
      'Buying Guides | GunPartSelector.com',
      'Caliber selection, compatibility basics, and other guides for planning an AR-15 build.'
    );
  }
}
