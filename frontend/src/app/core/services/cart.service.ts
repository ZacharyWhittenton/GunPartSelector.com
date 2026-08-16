import { Injectable, computed, signal } from '@angular/core';

import { ItemSummary } from '../models/marketplace-item.model';

export interface CartLine {
  itemId: string;
  name: string;
  slug: string;
  priceCents: number;
  imageUrl: string | null;
  quantity: number;
}

const CART_STORAGE_KEY = 'wd_cart';
const MAX_LINE_QUANTITY = 20;

@Injectable({
  providedIn: 'root'
})
export class CartService {
  private readonly linesSignal = signal<CartLine[]>(this.readStoredLines());

  readonly lines = this.linesSignal.asReadonly();

  readonly itemCount = computed(() =>
    this.linesSignal().reduce((total, line) => total + line.quantity, 0)
  );

  readonly totalCents = computed(() =>
    this.linesSignal().reduce((total, line) => total + line.priceCents * line.quantity, 0)
  );

  addItem(item: ItemSummary, quantity = 1): void {
    const lines = [...this.linesSignal()];
    const existing = lines.find(line => line.itemId === item.id);

    if (existing) {
      existing.quantity = Math.min(existing.quantity + quantity, MAX_LINE_QUANTITY);
    } else {
      lines.push({
        itemId: item.id,
        name: item.name,
        slug: item.slug,
        priceCents: item.priceCents,
        imageUrl: item.imageUrl,
        quantity: Math.min(Math.max(quantity, 1), MAX_LINE_QUANTITY)
      });
    }

    this.updateLines(lines);
  }

  updateQuantity(itemId: string, quantity: number): void {
    const clamped = Math.min(Math.max(quantity, 1), MAX_LINE_QUANTITY);
    const lines = this.linesSignal().map(line =>
      line.itemId === itemId ? { ...line, quantity: clamped } : line
    );
    this.updateLines(lines);
  }

  removeItem(itemId: string): void {
    this.updateLines(this.linesSignal().filter(line => line.itemId !== itemId));
  }

  clear(): void {
    this.updateLines([]);
  }

  private updateLines(lines: CartLine[]): void {
    this.linesSignal.set(lines);
    localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(lines));
  }

  private readStoredLines(): CartLine[] {
    const raw = localStorage.getItem(CART_STORAGE_KEY);
    if (!raw) {
      return [];
    }

    try {
      return JSON.parse(raw) as CartLine[];
    } catch {
      return [];
    }
  }
}
