import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, of, tap } from 'rxjs';

import { WishlistItemSummary } from '../models/wishlist-item.model';
import { AuthService } from './auth.service';

const WISHLIST_STORAGE_KEY = 'wd_wishlist';

@Injectable({
  providedIn: 'root'
})
export class WishlistService {
  private readonly itemIdsSignal = signal<string[]>([]);

  readonly itemIds = this.itemIdsSignal.asReadonly();

  constructor(
    private readonly http: HttpClient,
    private readonly auth: AuthService
  ) {}

  isWishlisted(itemId: string): boolean {
    return this.itemIdsSignal().includes(itemId);
  }

  load(): Observable<string[]> {
    if (this.auth.isAuthenticated) {
      return this.http.get<WishlistItemSummary[]>('/api/marketplace/wishlist').pipe(
        map(entries => entries.map(entry => entry.marketplaceItemId)),
        tap(itemIds => this.itemIdsSignal.set(itemIds))
      );
    }

    const itemIds = this.readStoredIds();
    this.itemIdsSignal.set(itemIds);
    return of(itemIds);
  }

  add(itemId: string): Observable<void> {
    if (this.auth.isAuthenticated) {
      return this.http.post('/api/marketplace/wishlist', { itemId }).pipe(
        tap(() =>
          this.itemIdsSignal.update(ids => (ids.includes(itemId) ? ids : [...ids, itemId]))
        ),
        map(() => void 0)
      );
    }

    const ids = this.readStoredIds();
    if (!ids.includes(itemId)) {
      const updated = [...ids, itemId];
      this.persistStoredIds(updated);
      this.itemIdsSignal.set(updated);
    }
    return of(void 0);
  }

  remove(itemId: string): Observable<void> {
    if (this.auth.isAuthenticated) {
      return this.http.delete(`/api/marketplace/wishlist/${itemId}`).pipe(
        tap(() => this.itemIdsSignal.update(ids => ids.filter(id => id !== itemId))),
        map(() => void 0)
      );
    }

    const updated = this.readStoredIds().filter(id => id !== itemId);
    this.persistStoredIds(updated);
    this.itemIdsSignal.set(updated);
    return of(void 0);
  }

  toggle(itemId: string): Observable<void> {
    return this.isWishlisted(itemId) ? this.remove(itemId) : this.add(itemId);
  }

  private readStoredIds(): string[] {
    const raw = localStorage.getItem(WISHLIST_STORAGE_KEY);
    if (!raw) {
      return [];
    }

    try {
      return JSON.parse(raw) as string[];
    } catch {
      return [];
    }
  }

  private persistStoredIds(ids: string[]): void {
    localStorage.setItem(WISHLIST_STORAGE_KEY, JSON.stringify(ids));
  }
}
