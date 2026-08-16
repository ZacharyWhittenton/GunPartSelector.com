import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { ClickPoint, PageViewSummary } from '../models/site-analytics.model';

@Injectable({
  providedIn: 'root'
})
export class SiteAnalyticsAdminService {
  constructor(private readonly http: HttpClient) {}

  getTopPages(days = 30): Observable<PageViewSummary[]> {
    const params = new HttpParams().set('days', days);
    return this.http.get<PageViewSummary[]>('/api/admin/analytics/pages', { params });
  }

  getHeatmap(path: string, days = 30): Observable<ClickPoint[]> {
    const params = new HttpParams().set('path', path).set('days', days);
    return this.http.get<ClickPoint[]>('/api/admin/analytics/heatmap', { params });
  }
}
