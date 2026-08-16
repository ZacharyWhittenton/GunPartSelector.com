import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { AuthService } from '../../core/services/auth.service';
import { SeoService } from '../../core/services/seo.service';

function passwordsMatchValidator(control: AbstractControl): ValidationErrors | null {
  const password = control.get('password')?.value;
  const confirmPassword = control.get('confirmPassword')?.value;
  return password === confirmPassword ? null : { passwordsMismatch: true };
}

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './register.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './register.component.css'
})
export class RegisterComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly seoService = inject(SeoService);

  readonly isSubmitting = signal(false);
  readonly errorMessage = signal('');

  registerForm = this.formBuilder.nonNullable.group(
    {
      fullName: ['', [Validators.required, Validators.maxLength(200)]],
      emailAddress: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      confirmPassword: ['', [Validators.required]]
    },
    { validators: passwordsMatchValidator }
  );

  constructor() {
    this.seoService.updatePage(
      'Create Account | WD Web Solutions',
      'Create a WD Web Solutions account to book consultations, track orders, and more.'
    );
  }

  submitRegisterForm(): void {
    this.errorMessage.set('');

    if (this.registerForm.invalid) {
      this.registerForm.markAllAsTouched();
      return;
    }

    this.isSubmitting.set(true);

    const { fullName, emailAddress, password } = this.registerForm.getRawValue();

    this.authService
      .register({ fullName, emailAddress, password })
      .pipe(finalize(() => this.isSubmitting.set(false)))
      .subscribe({
        next: () => this.router.navigateByUrl('/'),
        error: error => {
          this.errorMessage.set(
            error.status === 409
              ? 'An account with this email address already exists.'
              : 'Unable to create your account. Please try again.'
          );
        }
      });
  }

  hasError(controlName: keyof typeof this.registerForm.controls): boolean {
    const control = this.registerForm.controls[controlName];
    return control.invalid && (control.touched || control.dirty);
  }

  get passwordsMismatch(): boolean {
    const confirmPassword = this.registerForm.controls.confirmPassword;
    return (
      this.registerForm.hasError('passwordsMismatch') &&
      (confirmPassword.touched || confirmPassword.dirty)
    );
  }
}
