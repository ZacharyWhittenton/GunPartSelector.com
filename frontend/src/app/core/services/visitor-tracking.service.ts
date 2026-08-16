import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

const SESSION_STORAGE_KEY = 'wd_analytics_session';
const ADMIN_PATH_PREFIX = '/admin';

function generateId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function loadOrCreateSessionId(): string {
  const existing = localStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) {
    return existing;
  }
  const created = generateId();
  localStorage.setItem(SESSION_STORAGE_KEY, created);
  return created;
}

function isTrackablePath(path: string): boolean {
  return !path.startsWith(ADMIN_PATH_PREFIX);
}

function labelForElement(element: Element | null): string | null {
  let target = element;
  for (let depth = 0; target && depth < 5; depth += 1) {
    const explicitLabel = target.getAttribute?.('data-analytics-label');
    if (explicitLabel) {
      return explicitLabel;
    }
    if (target.tagName === 'A' || target.tagName === 'BUTTON') {
      const text = target.textContent?.trim();
      return text ? text.slice(0, 60) : target.tagName.toLowerCase();
    }
    target = target.parentElement;
  }
  return element?.tagName?.toLowerCase() ?? null;
}

@Injectable({ providedIn: 'root' })
export class VisitorTrackingService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private initialized = false;
  private readonly sessionId = loadOrCreateSessionId();

  init(): void {
    if (this.initialized) {
      return;
    }
    this.initialized = true;

    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe(event => this.trackPageView(event.urlAfterRedirects));

    document.addEventListener('click', event => this.trackClick(event));
  }

  private trackPageView(path: string): void {
    if (!isTrackablePath(path)) {
      return;
    }

    this.http
      .post('/api/analytics/pageview', {
        path,
        referrer: document.referrer || null,
        sessionId: this.sessionId
      })
      .subscribe({ error: () => {} });
  }

  private trackClick(event: MouseEvent): void {
    const path = this.router.url;
    if (!isTrackablePath(path)) {
      return;
    }

    const target = event.target as Element | null;
    const xPercent = (event.pageX / document.documentElement.scrollWidth) * 100;
    const yPercent = (event.pageY / document.documentElement.scrollHeight) * 100;

    this.http
      .post('/api/analytics/click', {
        path,
        xPercent: Math.min(100, Math.max(0, xPercent)),
        yPercent: Math.min(100, Math.max(0, yPercent)),
        elementLabel: labelForElement(target),
        sessionId: this.sessionId
      })
      .subscribe({ error: () => {} });
  }
}
