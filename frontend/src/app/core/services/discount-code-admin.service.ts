import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { DiscountCode, DiscountType } from '../models/discount-code.model';

export interface CreateDiscountCodePayload {
  code: string;
  discountType: DiscountType;
  value: number;
  expiresAt: string | null;
  maxRedemptions: number | null;
}

export interface UpdateDiscountCodePayload {
  discountType: DiscountType;
  value: number;
  expiresAt: string | null;
  maxRedemptions: number | null;
}

@Injectable({
  providedIn: 'root'
})
export class DiscountCodeAdminService {
  constructor(private readonly http: HttpClient) {}

  listAll(): Observable<DiscountCode[]> {
    return this.http.get<DiscountCode[]>('/api/admin/discount-codes');
  }

  create(payload: CreateDiscountCodePayload): Observable<DiscountCode> {
    return this.http.post<DiscountCode>('/api/admin/discount-codes', payload);
  }

  update(id: string, payload: UpdateDiscountCodePayload): Observable<DiscountCode> {
    return this.http.patch<DiscountCode>(`/api/admin/discount-codes/${id}`, payload);
  }

  deactivate(id: string): Observable<DiscountCode> {
    return this.http.post<DiscountCode>(`/api/admin/discount-codes/${id}/deactivate`, {});
  }

  activate(id: string): Observable<DiscountCode> {
    return this.http.post<DiscountCode>(`/api/admin/discount-codes/${id}/activate`, {});
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`/api/admin/discount-codes/${id}`);
  }
}
