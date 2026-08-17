import { Injectable, computed, signal } from '@angular/core';

import { CartLine } from '../models/cart.model';
import { ItemSummary } from '../models/marketplace-item.model';

const CART_STORAGE_KEY = 'wd_cart';

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
    this.linesSignal().reduce(
      (total, line) => total + line.item.priceCents * line.quantity,
      0
    )
  );

  addLine(item: ItemSummary, variantId: string, variantLabel: string, quantity = 1): void {
    const lines = [...this.linesSignal()];
    const existing = lines.find(
      line => line.item.id === item.id && line.variantId === variantId
    );

    if (existing) {
      existing.quantity += quantity;
    } else {
      lines.push({ item, variantId, variantLabel, quantity });
    }

    this.updateLines(lines);
  }

  updateQuantity(itemId: string, variantId: string, quantity: number): void {
    if (quantity < 1) {
      this.removeLine(itemId, variantId);
      return;
    }

    const lines = this.linesSignal().map(line =>
      line.item.id === itemId && line.variantId === variantId ? { ...line, quantity } : line
    );
    this.updateLines(lines);
  }

  removeLine(itemId: string, variantId: string): void {
    this.updateLines(
      this.linesSignal().filter(
        line => !(line.item.id === itemId && line.variantId === variantId)
      )
    );
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
