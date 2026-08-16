import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, tap } from 'rxjs';

import { AuthUser } from '../models/user.model';

export interface RegisterPayload {
  emailAddress: string;
  fullName: string;
  password: string;
}

export interface LoginPayload {
  emailAddress: string;
  password: string;
}

interface AuthApiResponse {
  accessToken: string;
  tokenType: string;
  user: AuthUser;
}

const TOKEN_STORAGE_KEY = 'asp_access_token';
const USER_STORAGE_KEY = 'asp_current_user';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly currentUserSignal = signal<AuthUser | null>(this.readStoredUser());

  readonly currentUser = this.currentUserSignal.asReadonly();

  constructor(private readonly http: HttpClient) {}

  get isAuthenticated(): boolean {
    return this.currentUserSignal() !== null;
  }

  get token(): string | null {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  }

  register(payload: RegisterPayload): Observable<AuthUser> {
    return this.http
      .post<AuthApiResponse>('/api/auth/register', payload)
      .pipe(
        tap(response => this.storeSession(response)),
        map(response => response.user)
      );
  }

  login(payload: LoginPayload): Observable<AuthUser> {
    return this.http
      .post<AuthApiResponse>('/api/auth/login', payload)
      .pipe(
        tap(response => this.storeSession(response)),
        map(response => response.user)
      );
  }

  logout(): void {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
    this.currentUserSignal.set(null);
  }

  private storeSession(response: AuthApiResponse): void {
    localStorage.setItem(TOKEN_STORAGE_KEY, response.accessToken);
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(response.user));
    this.currentUserSignal.set(response.user);
  }

  private readStoredUser(): AuthUser | null {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    if (!raw) {
      return null;
    }

    try {
      return JSON.parse(raw) as AuthUser;
    } catch {
      return null;
    }
  }
}
