import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { adminGuard } from './admin.guard';
import { AuthService } from '../services/auth.service';
import { AuthUser } from '../models/user.model';

describe('adminGuard', () => {
  const adminUser: AuthUser = {
    id: '9a53d09a-f258-4b09-9fb3-ef6df4c2f9fd',
    emailAddress: 'admin@example.com',
    fullName: 'Admin Person',
    role: 'admin'
  };

  const customerUser: AuthUser = {
    ...adminUser,
    role: 'customer'
  };

  function configure(currentUser: AuthUser | null): void {
    const authServiceStub = {
      currentUser: () => currentUser
    };

    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: AuthService, useValue: authServiceStub }]
    });
  }

  it('allows admins through', () => {
    configure(adminUser);

    const result = TestBed.runInInjectionContext(() =>
      adminGuard({} as never, { url: '/admin' } as never)
    );

    expect(result).toBe(true);
  });

  it('redirects unauthenticated visitors to login', () => {
    configure(null);

    const result = TestBed.runInInjectionContext(() =>
      adminGuard({} as never, { url: '/admin' } as never)
    );

    expect(result).not.toBe(true);
  });

  it('redirects non-admin users away', () => {
    configure(customerUser);

    const result = TestBed.runInInjectionContext(() =>
      adminGuard({} as never, { url: '/admin' } as never)
    );

    expect(result).not.toBe(true);
  });
});
