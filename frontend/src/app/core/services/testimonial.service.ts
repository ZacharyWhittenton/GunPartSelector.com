import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { TestimonialDetail, TestimonialSummary } from '../models/testimonial.model';

export interface SubmitTestimonialPayload {
  rating: number;
  body: string;
}

@Injectable({
  providedIn: 'root'
})
export class TestimonialService {
  constructor(private readonly http: HttpClient) {}

  listApproved(limit?: number): Observable<TestimonialSummary[]> {
    const url = limit ? `/api/testimonials?limit=${limit}` : '/api/testimonials';
    return this.http.get<TestimonialSummary[]>(url);
  }

  getMine(): Observable<TestimonialDetail | null> {
    return this.http.get<TestimonialDetail | null>('/api/testimonials/mine');
  }

  submitMine(payload: SubmitTestimonialPayload): Observable<TestimonialDetail> {
    return this.http.post<TestimonialDetail>('/api/testimonials/mine', payload);
  }
}
