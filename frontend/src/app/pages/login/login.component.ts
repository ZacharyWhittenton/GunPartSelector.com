import { ChangeDetectionStrategy, Component, inject, isDevMode, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { AuthService } from '../../core/services/auth.service';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './login.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './login.component.css'
})
export class LoginComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly seoService = inject(SeoService);

  readonly isSubmitting = signal(false);
  readonly errorMessage = signal('');
  readonly showDevLogin = isDevMode();

  loginForm = this.formBuilder.nonNullable.group({
    emailAddress: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]]
  });

  constructor() {
    this.seoService.updatePage(
      'Log In | GunPartSelector.com',
      'Log in to your GunPartSelector.com account to manage orders and saved builds.'
    );
  }

  submitLoginForm(): void {
    this.errorMessage.set('');

    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);

    this.authService
      .login(this.loginForm.getRawValue())
      .pipe(finalize(() => this.isSubmitting.set(false)))
      .subscribe({
        next: () => this.router.navigateByUrl('/'),
        error: error => {
          this.errorMessage.set(
            error.status === 401
              ? 'Incorrect email address or password.'
              : 'Unable to log in. Please try again.'
          );
        }
      });
  }

  hasError(controlName: keyof typeof this.loginForm.controls): boolean {
    const control = this.loginForm.controls[controlName];
    return control.invalid && (control.touched || control.dirty);
  }

  /** Dev-only shortcuts (see showDevLogin) so testing role-gated pages doesn't
   * require remembering seed credentials. No password ever touches this file --
   * see AuthService.devLogin and the backend's /auth/dev-login route. */
  quickLoginAsAdmin(): void {
    this.quickLogin('admin');
  }

  quickLoginAsCustomer(): void {
    this.quickLogin('customer');
  }

  continueAsVisitor(): void {
    this.authService.logout();
    this.router.navigateByUrl('/');
  }

  private quickLogin(role: 'admin' | 'customer'): void {
    this.errorMessage.set('');
    this.isSubmitting.set(true);
    this.authService
      .devLogin(role)
      .pipe(finalize(() => this.isSubmitting.set(false)))
      .subscribe({
        next: () => this.router.navigateByUrl('/'),
        error: () =>
          this.errorMessage.set(
            'Demo account not seeded yet -- run the seed scripts in data/seeds/.'
          )
      });
  }
}
