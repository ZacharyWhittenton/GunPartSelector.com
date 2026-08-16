import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { DiscountCode, DiscountType } from '../../core/models/discount-code.model';
import { DiscountCodeAdminService } from '../../core/services/discount-code-admin.service';

@Component({
  selector: 'app-admin-discount-codes',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, DatePipe],
  templateUrl: './admin-discount-codes.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './admin-discount-codes.component.css'
})
export class AdminDiscountCodesComponent implements OnInit {
  private readonly formBuilder = inject(FormBuilder);
  private readonly discountCodeAdminService = inject(DiscountCodeAdminService);

  readonly codes = signal<DiscountCode[]>([]);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');

  readonly editingId = signal<string | null>(null);
  readonly isSaving = signal(false);
  readonly saveError = signal('');

  readonly pendingIds = signal<Set<string>>(new Set());
  readonly rowErrors = signal<Record<string, string>>({});

  codeForm = this.formBuilder.nonNullable.group({
    code: ['', [Validators.required, Validators.maxLength(40)]],
    discountType: ['percent' as DiscountType, [Validators.required]],
    percentValue: [10, [Validators.min(1), Validators.max(100)]],
    amountDollars: [5, [Validators.min(0.01)]],
    expiresAt: [''],
    maxRedemptions: [null as number | null]
  });

  ngOnInit(): void {
    this.loadCodes();
  }

  loadCodes(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.discountCodeAdminService
      .listAll()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: codes => this.codes.set(codes),
        error: () => this.errorMessage.set('Unable to load discount codes. Please try again.')
      });
  }

  startEdit(code: DiscountCode): void {
    this.editingId.set(code.id);
    this.codeForm.setValue({
      code: code.code,
      discountType: code.discountType,
      percentValue: code.discountType === 'percent' ? code.value : 10,
      amountDollars: code.discountType === 'fixed' ? code.value / 100 : 5,
      expiresAt: code.expiresAt ? code.expiresAt.slice(0, 10) : '',
      maxRedemptions: code.maxRedemptions
    });
    this.codeForm.controls.code.disable();
    this.saveError.set('');
  }

  cancelEdit(): void {
    this.editingId.set(null);
    this.codeForm.reset({
      code: '',
      discountType: 'percent',
      percentValue: 10,
      amountDollars: 5,
      expiresAt: '',
      maxRedemptions: null
    });
    this.codeForm.controls.code.enable();
    this.saveError.set('');
  }

  submit(): void {
    this.saveError.set('');

    if (this.codeForm.invalid) {
      this.codeForm.markAllAsTouched();
      return;
    }

    const { code, discountType, percentValue, amountDollars, expiresAt, maxRedemptions } =
      this.codeForm.getRawValue();
    const value = discountType === 'percent' ? percentValue : Math.round(amountDollars * 100);
    const expiresAtIso = expiresAt ? new Date(`${expiresAt}T23:59:59`).toISOString() : null;

    this.isSaving.set(true);

    const editingId = this.editingId();
    const request$ = editingId
      ? this.discountCodeAdminService.update(editingId, {
          discountType,
          value,
          expiresAt: expiresAtIso,
          maxRedemptions
        })
      : this.discountCodeAdminService.create({
          code,
          discountType,
          value,
          expiresAt: expiresAtIso,
          maxRedemptions
        });

    request$.pipe(finalize(() => this.isSaving.set(false))).subscribe({
      next: () => {
        this.cancelEdit();
        this.loadCodes();
      },
      error: error => {
        if (error?.status === 409) {
          this.saveError.set('A discount code with that code already exists.');
        } else if (error?.status === 422) {
          this.saveError.set('Invalid discount value for this discount type.');
        } else {
          this.saveError.set('Unable to save this discount code. Please try again.');
        }
      }
    });
  }

  toggleActive(code: DiscountCode): void {
    this.setRowError(code.id, '');
    this.pendingIds.update(pending => new Set(pending).add(code.id));

    const request$ = code.isActive
      ? this.discountCodeAdminService.deactivate(code.id)
      : this.discountCodeAdminService.activate(code.id);

    request$
      .pipe(
        finalize(() => {
          this.pendingIds.update(pending => {
            const next = new Set(pending);
            next.delete(code.id);
            return next;
          });
        })
      )
      .subscribe({
        next: updated => {
          this.codes.update(codes =>
            codes.map(existing => (existing.id === updated.id ? updated : existing))
          );
        },
        error: () => this.setRowError(code.id, 'That action failed. Please try again.')
      });
  }

  deleteCode(code: DiscountCode): void {
    if (!confirm(`Delete discount code "${code.code}"? This cannot be undone.`)) {
      return;
    }

    this.setRowError(code.id, '');
    this.pendingIds.update(pending => new Set(pending).add(code.id));

    this.discountCodeAdminService
      .delete(code.id)
      .pipe(
        finalize(() => {
          this.pendingIds.update(pending => {
            const next = new Set(pending);
            next.delete(code.id);
            return next;
          });
        })
      )
      .subscribe({
        next: () => {
          this.codes.update(codes => codes.filter(existing => existing.id !== code.id));
        },
        error: () => this.setRowError(code.id, 'Unable to delete that discount code.')
      });
  }

  isPending(id: string): boolean {
    return this.pendingIds().has(id);
  }

  rowError(id: string): string {
    return this.rowErrors()[id] ?? '';
  }

  hasError(controlName: keyof typeof this.codeForm.controls): boolean {
    const control = this.codeForm.controls[controlName];
    return control.invalid && (control.touched || control.dirty);
  }

  formatValue(code: DiscountCode): string {
    return code.discountType === 'percent'
      ? `${code.value}% off`
      : `$${(code.value / 100).toFixed(2)} off`;
  }

  private setRowError(id: string, message: string): void {
    this.rowErrors.update(errors => ({ ...errors, [id]: message }));
  }
}
