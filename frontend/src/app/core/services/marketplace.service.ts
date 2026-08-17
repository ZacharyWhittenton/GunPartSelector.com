import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { ItemSummary } from '../models/marketplace-item.model';
import { OrderSummary } from '../models/order.model';

export interface CheckoutLine {
  itemId: string;
  variantId: string;
  quantity: number;
}

export interface CheckoutResponse {
  checkoutUrl: string;
}

@Injectable({
  providedIn: 'root'
})
export class MarketplaceService {
  constructor(private readonly http: HttpClient) {}

  listItems(): Observable<ItemSummary[]> {
    return this.http.get<ItemSummary[]>('/api/marketplace/items');
  }

  getItem(slug: string): Observable<ItemSummary> {
    return this.http.get<ItemSummary>(`/api/marketplace/items/${slug}`);
  }

  checkout(lines: CheckoutLine[], discountCode?: string): Observable<CheckoutResponse> {
    return this.http.post<CheckoutResponse>('/api/marketplace/checkout', {
      items: lines,
      discountCode: discountCode || null
    });
  }

  listMyOrders(): Observable<OrderSummary[]> {
    return this.http.get<OrderSummary[]>('/api/marketplace/orders/mine');
  }

  getOrderBySession(sessionId: string): Observable<OrderSummary> {
    return this.http.get<OrderSummary>(`/api/marketplace/orders/by-session/${sessionId}`);
  }
}
