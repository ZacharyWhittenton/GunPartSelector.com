import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { AccountNote, AccountStatus, AdminUserSummary } from '../models/admin.model';
import { UserRole } from '../models/user.model';

@Injectable({
  providedIn: 'root'
})
export class AdminService {
  constructor(private readonly http: HttpClient) {}

  listUsers(): Observable<AdminUserSummary[]> {
    return this.http.get<AdminUserSummary[]>('/api/admin/users');
  }

  updateRole(userId: string, role: UserRole): Observable<AdminUserSummary> {
    return this.http.patch<AdminUserSummary>(`/api/admin/users/${userId}/role`, { role });
  }

  updateStatus(userId: string, status: AccountStatus): Observable<AdminUserSummary> {
    return this.http.patch<AdminUserSummary>(`/api/admin/users/${userId}/status`, { status });
  }

  listNotes(userId: string): Observable<AccountNote[]> {
    return this.http.get<AccountNote[]>(`/api/admin/users/${userId}/notes`);
  }

  addNote(userId: string, body: string): Observable<AccountNote> {
    return this.http.post<AccountNote>(`/api/admin/users/${userId}/notes`, { body });
  }
}
