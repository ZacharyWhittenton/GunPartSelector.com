import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthService, LoginPayload, RegisterPayload } from './auth.service';
import { AuthUser } from '../models/user.model';

describe('AuthService', () => {
  let service: AuthService;
  let http: HttpTestingController;

  const user: AuthUser = {
    id: '9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd',
    emailAddress: 'taylor@example.com',
    fullName: 'Taylor Client',
    role: 'customer'
  };

  beforeEach(() => {
    localStorage.clear();

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        provideHttpClient(),
        provideHttpClientTesting()
      ]
    });

    service = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    localStorage.clear();
  });

  it('starts unauthenticated when no session is stored', () => {
    expect(service.isAuthenticated).toBe(false);
    expect(service.currentUser()).toBeNull();
  });

  it('registers a user and persists the session', () => {
    const payload: RegisterPayload = {
      emailAddress: user.emailAddress,
      fullName: user.fullName,
      password: 'super-secret-1'
    };
    let result: AuthUser | undefined;

    service.register(payload).subscribe(response => (result = response));

    const request = http.expectOne('/api/auth/register');
    expect(request.request.method).toBe('POST');
    request.flush({ accessToken: 'token-123', tokenType: 'bearer', user });

    expect(result).toEqual(user);
    expect(service.isAuthenticated).toBe(true);
    expect(service.token).toBe('token-123');
  });

  it('logs a user in and persists the session', () => {
    const payload: LoginPayload = {
      emailAddress: user.emailAddress,
      password: 'super-secret-1'
    };
    let result: AuthUser | undefined;

    service.login(payload).subscribe(response => (result = response));

    const request = http.expectOne('/api/auth/login');
    expect(request.request.method).toBe('POST');
    request.flush({ accessToken: 'token-456', tokenType: 'bearer', user });

    expect(result).toEqual(user);
    expect(service.currentUser()).toEqual(user);
  });

  it('clears the session on logout', () => {
    service.login({ emailAddress: user.emailAddress, password: 'super-secret-1' }).subscribe();
    http.expectOne('/api/auth/login').flush({ accessToken: 'token-789', tokenType: 'bearer', user });

    service.logout();

    expect(service.isAuthenticated).toBe(false);
    expect(service.token).toBeNull();
  });
});
