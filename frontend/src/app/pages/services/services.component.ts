import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { SeoService } from '../../core/services/seo.service';
import { PageContainerComponent } from '../../shared/components/page-container/page-container.component';
import { PageHeroComponent } from '../../shared/components/page-hero/page-hero.component';
import { ScrollRevealDirective } from '../../shared/directives/scroll-reveal.directive';

interface SupportTopic {
  question: string;
  answer: string;
}

const SUPPORT_TOPICS: SupportTopic[] = [
  {
    question: 'Do you sell firearms or parts directly?',
    answer:
      "No. GunPartSelector.com is a build configurator and price comparison tool. Every \"Buy\" link takes you to the retailer's own site, and your purchase, shipping, and payment happen there — not with us."
  },
  {
    question: 'How do FFL transfers work?',
    answer:
      'Some parts are regulated and must ship to a licensed FFL (Federal Firearms License) holder rather than directly to your address. The retailer you buy from will walk you through their specific transfer process at checkout.'
  },
  {
    question: 'Something is wrong with an order I placed.',
    answer:
      "Since orders are placed and fulfilled by the retailer, order status, shipping issues, returns, and warranty claims all go through them directly — reach out to the retailer's own customer support."
  },
  {
    question: 'Need help planning a build?',
    answer:
      "Start with the builder on our home page — it flags caliber, buffer-tube, handguard, and gas-system mismatches as you add parts. If you're stuck on something the compatibility checker doesn't cover, send us a message."
  }
];

@Component({
  selector: 'app-services',
  standalone: true,
  imports: [RouterLink, PageContainerComponent, PageHeroComponent, ScrollRevealDirective],
  templateUrl: './services.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './services.component.css'
})
export class ServicesComponent {
  readonly topics = SUPPORT_TOPICS;

  constructor(private seoService: SeoService) {
    this.seoService.updatePage(
      'Support | GunPartSelector.com',
      'Answers about FFL transfers, orders, and getting help planning your AR-15 build.'
    );
  }
}
