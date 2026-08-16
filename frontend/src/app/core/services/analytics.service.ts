import { Injectable, inject } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

import { GA_MEASUREMENT_ID } from '../config/analytics.config';

declare global {
  interface Window {
    dataLayer?: unknown[];
  }
}

@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private readonly router = inject(Router);
  private initialized = false;

  init(): void {
    if (this.initialized || !GA_MEASUREMENT_ID) {
      return;
    }
    this.initialized = true;

    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`;
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    const gtag = (...args: unknown[]) => window.dataLayer!.push(args);
    gtag('js', new Date());
    // Page views are reported per route change below instead of once on load,
    // since gtag's automatic pageview doesn't see Angular's client-side navigation.
    gtag('config', GA_MEASUREMENT_ID, { send_page_view: false });

    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe(event => {
        gtag('event', 'page_view', { page_path: event.urlAfterRedirects });
      });
  }
}
