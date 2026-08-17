import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { AdminItemSummary, VariantStockStatus } from '../models/marketplace-item.model';
import { OrderStatus, OrderSummary } from '../models/order.model';

export interface VariantWritePayload {
  label: string;
  sortOrder: number;
  stockStatus: VariantStockStatus;
}

export interface ItemWritePayload {
  name: string;
  description: string;
  priceCents: number;
  imageUrl: string | null;
  variants: VariantWritePayload[];
}

export interface ImageUploadResponse {
  url: string;
}

@Injectable({
  providedIn: 'root'
})
export class MarketplaceAdminService {
  constructor(private readonly http: HttpClient) {}

  listAllItems(): Observable<AdminItemSummary[]> {
    return this.http.get<AdminItemSummary[]>('/api/admin/marketplace/items');
  }

  createItem(payload: ItemWritePayload): Observable<AdminItemSummary> {
    return this.http.post<AdminItemSummary>('/api/admin/marketplace/items', payload);
  }

  updateItem(id: string, payload: ItemWritePayload): Observable<AdminItemSummary> {
    return this.http.patch<AdminItemSummary>(`/api/admin/marketplace/items/${id}`, payload);
  }

  deactivateItem(id: string): Observable<AdminItemSummary> {
    return this.http.post<AdminItemSummary>(`/api/admin/marketplace/items/${id}/deactivate`, {});
  }

  activateItem(id: string): Observable<AdminItemSummary> {
    return this.http.post<AdminItemSummary>(`/api/admin/marketplace/items/${id}/activate`, {});
  }

  deleteItem(id: string): Observable<void> {
    return this.http.delete<void>(`/api/admin/marketplace/items/${id}`);
  }

  uploadImage(file: File): Observable<ImageUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ImageUploadResponse>('/api/admin/marketplace/items/images', formData);
  }

  listAllOrders(status?: OrderStatus): Observable<OrderSummary[]> {
    const url = status
      ? `/api/admin/marketplace/orders?status=${status}`
      : '/api/admin/marketplace/orders';
    return this.http.get<OrderSummary[]>(url);
  }
}
