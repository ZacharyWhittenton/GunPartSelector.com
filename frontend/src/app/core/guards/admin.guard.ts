import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../services/auth.service';

export const adminGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const currentUser = authService.currentUser();

  if (!currentUser) {
    return router.createUrlTree(['/login']);
  }

  if (currentUser.role !== 'admin') {
    return router.createUrlTree(['/']);
  }

  return true;
};
