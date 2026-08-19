import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import {
  PaginatedResponse,
  PartCategory,
  ProductDetail,
  ProductFacets,
  ProductQuery,
  ProductSummary
} from '../models/catalog.model';

@Injectable({
  providedIn: 'root'
})
export class CatalogService {
  constructor(private readonly http: HttpClient) {}

  listCategories(): Observable<PartCategory[]> {
    return this.http.get<PartCategory[]>('/api/catalog/categories');
  }

  getCategory(slug: string): Observable<PartCategory> {
    return this.http.get<PartCategory>(`/api/catalog/categories/${slug}`);
  }

  getCategoryFacets(slug: string): Observable<ProductFacets> {
    return this.http.get<ProductFacets>(`/api/catalog/categories/${slug}/facets`);
  }

  listProducts(query: ProductQuery = {}): Observable<PaginatedResponse<ProductSummary>> {
    let params = new HttpParams();
    if (query.category) params = params.set('category', query.category);
    if (query.priceMin != null) params = params.set('priceMin', query.priceMin);
    if (query.priceMax != null) params = params.set('priceMax', query.priceMax);
    if (query.stock) params = params.set('stock', query.stock);
    if (query.sort) params = params.set('sort', query.sort);
    if (query.limit != null) params = params.set('limit', query.limit);
    if (query.offset != null) params = params.set('offset', query.offset);
    for (const brand of query.brand ?? []) params = params.append('brand', brand);
    for (const retailer of query.retailer ?? []) params = params.append('retailer', retailer);
    for (const tag of query.tag ?? []) params = params.append('tag', tag);

    return this.http.get<PaginatedResponse<ProductSummary>>('/api/catalog/products', { params });
  }

  getProduct(slug: string): Observable<ProductDetail> {
    return this.http.get<ProductDetail>(`/api/catalog/products/${slug}`);
  }
}
