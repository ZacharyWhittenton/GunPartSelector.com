import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { DashboardSummary } from '../models/dashboard.model';

@Injectable({
  providedIn: 'root'
})
export class DashboardAdminService {
  constructor(private readonly http: HttpClient) {}

  getSummary(): Observable<DashboardSummary> {
    return this.http.get<DashboardSummary>('/api/admin/dashboard/summary');
  }
}
