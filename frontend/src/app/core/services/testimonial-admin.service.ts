import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { TestimonialDetail, TestimonialStatus } from '../models/testimonial.model';

@Injectable({
  providedIn: 'root'
})
export class TestimonialAdminService {
  constructor(private readonly http: HttpClient) {}

  listAll(status?: TestimonialStatus): Observable<TestimonialDetail[]> {
    const url = status
      ? `/api/admin/testimonials?status=${status}`
      : '/api/admin/testimonials';
    return this.http.get<TestimonialDetail[]>(url);
  }

  approve(id: string): Observable<TestimonialDetail> {
    return this.http.post<TestimonialDetail>(`/api/admin/testimonials/${id}/approve`, {});
  }

  reject(id: string): Observable<TestimonialDetail> {
    return this.http.post<TestimonialDetail>(`/api/admin/testimonials/${id}/reject`, {});
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`/api/admin/testimonials/${id}`);
  }
}
