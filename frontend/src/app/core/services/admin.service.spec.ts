import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AdminService } from './admin.service';
import { AdminUserSummary } from '../models/admin.model';

describe('AdminService', () => {
  let service: AdminService;
  let http: HttpTestingController;

  const user: AdminUserSummary = {
    id: '9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd',
    emailAddress: 'taylor@example.com',
    fullName: 'Taylor Client',
    role: 'customer',
    status: 'active',
    createdAt: '2026-08-08T12:00:00Z',
    lastLoginAt: null
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        AdminService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });

    service = TestBed.inject(AdminService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
  });

  it('lists users', () => {
    let result: AdminUserSummary[] | undefined;

    service.listUsers().subscribe(response => (result = response));

    const request = http.expectOne('/api/admin/users');
    expect(request.request.method).toBe('GET');
    request.flush([user]);

    expect(result).toEqual([user]);
  });

  it('updates a user role', () => {
    service.updateRole(user.id, 'admin').subscribe();

    const request = http.expectOne(`/api/admin/users/${user.id}/role`);
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({ role: 'admin' });
    request.flush({ ...user, role: 'admin' });
  });

  it('updates a user status', () => {
    service.updateStatus(user.id, 'suspended').subscribe();

    const request = http.expectOne(`/api/admin/users/${user.id}/status`);
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({ status: 'suspended' });
    request.flush({ ...user, status: 'suspended' });
  });

  it('adds a note', () => {
    service.addNote(user.id, 'Called about a quote.').subscribe();

    const request = http.expectOne(`/api/admin/users/${user.id}/notes`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ body: 'Called about a quote.' });
    request.flush({
      id: '11111111-1111-1111-1111-111111111111',
      authorName: 'Admin Person',
      body: 'Called about a quote.',
      createdAt: '2026-08-08T12:00:00Z'
    });
  });
});
