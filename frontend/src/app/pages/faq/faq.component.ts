import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { SeoService } from '../../core/services/seo.service';
import { PageContainerComponent } from '../../shared/components/page-container/page-container.component';
import { PageHeroComponent } from '../../shared/components/page-hero/page-hero.component';
import { ScrollRevealDirective } from '../../shared/directives/scroll-reveal.directive';

interface FaqEntry {
  question: string;
  answer: string;
}

interface FaqGroup {
  label: string;
  entries: FaqEntry[];
}

const FAQ_GROUPS: FaqGroup[] = [
  {
    label: 'The Basics',
    entries: [
      {
        question: 'What is GunPartSelector.com?',
        answer:
          'GunPartSelector.com is a build configurator for AR-15 platform rifles. Browse parts by category, add them to a build, and we flag compatibility issues (caliber, buffer tube, handguard interface, gas system, muzzle thread) before you buy anything.'
      },
      {
        question: 'Do you sell parts directly?',
        answer:
          'No. GunPartSelector.com is an affiliate site — "Add to Build" and product links send you to the retailer that actually stocks the part to complete your purchase. We don’t hold inventory, process payments for parts, or ship anything ourselves.'
      },
      {
        question: 'Do I need an account to use the builder?',
        answer:
          'No. Browsing the catalog and building in the 3D configurator works without signing in — your build is saved in your browser. Creating an account lets you save builds across devices and view your merch store order history.'
      }
    ]
  },
  {
    label: 'The Builder',
    entries: [
      {
        question: 'How does compatibility checking work?',
        answer:
          'Every part carries spec tags (caliber, buffer tube diameter, handguard mounting interface, gas system length, muzzle thread pattern). As you add parts to a build, we compare tags across everything you’ve picked and flag mismatches — errors for things that physically won’t fit together, warnings for things that will work but aren’t ideal.'
      },
      {
        question: 'Is the 3D model an exact match for the parts I pick?',
        answer:
          'The 3D model is a representative AR-15 for visualizing and clicking through categories, not a live render of your exact parts. Selecting a category highlights the matching region on the model, but swapping brands won’t change its shape or finish.'
      },
      {
        question: 'Can I save or share a build?',
        answer:
          'Yes — click "Share Build" once you’ve added at least one part. That generates a link you can bookmark, send to a friend, or bring to a gunsmith, without needing to create an account.'
      },
      {
        question: 'What if a category is missing a part I need?',
        answer:
          'Our catalog is curated, not exhaustive, and it’s still growing. If you can’t find what you’re after, let us know on the Contact page — that’s exactly the kind of feedback that shapes what we add next.'
      }
    ]
  },
  {
    label: 'Orders & Legal',
    entries: [
      {
        question: 'Where does my order actually go?',
        answer:
          'Parts purchases route through the retailer linked on that product. Merch store orders (apparel) are handled directly through our own checkout. Order confirmations and shipping updates for merch come from us; parts purchases are confirmed and shipped by the retailer you were sent to.'
      },
      {
        question: 'Do you ship firearms or regulated parts?',
        answer:
          'GunPartSelector.com doesn’t ship anything classified as a firearm. Any part that requires FFL transfer or age/ID verification is handled by the retailer’s own checkout and shipping process, subject to their policies and your local laws.'
      },
      {
        question: 'Can you give me legal advice on what’s legal to build?',
        answer:
          'No — firearm regulations vary by state and change often, and we’re not positioned to give legal advice. Confirm anything you’re unsure about with a qualified professional or your local authorities before you build or buy.'
      }
    ]
  },
  {
    label: 'Support',
    entries: [
      {
        question: 'Something on the site looks wrong — who do I tell?',
        answer:
          'Reach out through the Contact page with what you saw and where. Whether it’s a broken link, a wrong spec, or a part that’s no longer available, that’s the fastest way to get it fixed.'
      },
      {
        question: 'Do you offer installation help or gunsmithing?',
        answer:
          'Not directly. Check the Guides section for build walkthroughs and buying advice — for hands-on installation or gunsmithing work, we’d recommend a local professional.'
      }
    ]
  }
];

@Component({
  selector: 'app-faq',
  standalone: true,
  imports: [RouterLink, PageContainerComponent, PageHeroComponent, ScrollRevealDirective],
  templateUrl: './faq.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FaqComponent {
  readonly groups = FAQ_GROUPS;
  readonly openKey = signal<string | null>(null);

  constructor(private seoService: SeoService) {
    this.seoService.updatePage(
      'FAQ | GunPartSelector.com',
      'Answers to common questions about the AR-15 build configurator, compatibility checking, orders, and the affiliate model behind GunPartSelector.com.'
    );
  }

  keyFor(groupIndex: number, entryIndex: number): string {
    return `${groupIndex}-${entryIndex}`;
  }

  toggle(key: string): void {
    this.openKey.set(this.openKey() === key ? null : key);
  }

  isOpen(key: string): boolean {
    return this.openKey() === key;
  }
}
