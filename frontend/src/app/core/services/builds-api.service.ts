import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { BuildShareResponse } from '../models/build.model';

export interface CreateBuildShareItem {
  productId: string;
  quantity: number;
}

@Injectable({
  providedIn: 'root'
})
export class BuildsApiService {
  constructor(private readonly http: HttpClient) {}

  createBuildShare(items: CreateBuildShareItem[], name?: string): Observable<BuildShareResponse> {
    return this.http.post<BuildShareResponse>('/api/builds', {
      name: name || null,
      items
    });
  }

  getBuildBySlug(slug: string): Observable<BuildShareResponse> {
    return this.http.get<BuildShareResponse>(`/api/builds/${slug}`);
  }
}
