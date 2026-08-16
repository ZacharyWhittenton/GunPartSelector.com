import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { LeadDetail, LeadNote, LeadStatus } from '../models/lead.model';

@Injectable({
  providedIn: 'root'
})
export class LeadAdminService {
  constructor(private readonly http: HttpClient) {}

  listAll(status?: LeadStatus): Observable<LeadDetail[]> {
    const url = status
      ? `/api/admin/contact-requests?status=${status}`
      : '/api/admin/contact-requests';
    return this.http.get<LeadDetail[]>(url);
  }

  updateStatus(id: string, status: LeadStatus): Observable<LeadDetail> {
    return this.http.patch<LeadDetail>(`/api/admin/contact-requests/${id}/status`, { status });
  }

  updateFollowUp(id: string, followUpAt: string | null): Observable<LeadDetail> {
    return this.http.patch<LeadDetail>(`/api/admin/contact-requests/${id}/follow-up`, {
      followUpAt
    });
  }

  listNotes(leadId: string): Observable<LeadNote[]> {
    return this.http.get<LeadNote[]>(`/api/admin/contact-requests/${leadId}/notes`);
  }

  addNote(leadId: string, body: string): Observable<LeadNote> {
    return this.http.post<LeadNote>(`/api/admin/contact-requests/${leadId}/notes`, { body });
  }
}
