import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { AdminItemSummary } from '../../core/models/marketplace-item.model';
import { MarketplaceAdminService } from '../../core/services/marketplace-admin.service';

@Component({
  selector: 'app-admin-marketplace',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, CurrencyPipe, DatePipe],
  templateUrl: './admin-marketplace.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './admin-marketplace.component.css'
})
export class AdminMarketplaceComponent implements OnInit {
  private readonly formBuilder = inject(FormBuilder);
  private readonly marketplaceAdminService = inject(MarketplaceAdminService);

  readonly items = signal<AdminItemSummary[]>([]);
  readonly isLoading = signal(false);
  readonly errorMessage = signal('');

  readonly editingId = signal<string | null>(null);
  readonly isSaving = signal(false);
  readonly saveError = signal('');
  readonly isUploadingImage = signal(false);
  readonly imageUrl = signal<string | null>(null);

  readonly pendingIds = signal<Set<string>>(new Set());
  readonly rowErrors = signal<Record<string, string>>({});

  itemForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(200)]],
    description: ['', [Validators.required]],
    priceDollars: [0, [Validators.required, Validators.min(0)]],
    sizesText: ['One Size', [Validators.required]]
  });

  ngOnInit(): void {
    this.loadItems();
  }

  loadItems(): void {
    this.isLoading.set(true);
    this.errorMessage.set('');

    this.marketplaceAdminService
      .listAllItems()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: items => this.items.set(items),
        error: () => this.errorMessage.set('Unable to load items. Please try again.')
      });
  }

  startEdit(item: AdminItemSummary): void {
    this.editingId.set(item.id);
    this.imageUrl.set(item.imageUrl);
    this.itemForm.setValue({
      name: item.name,
      description: item.description,
      priceDollars: item.priceCents / 100,
      sizesText: item.variants
        .slice()
        .sort((a, b) => a.sortOrder - b.sortOrder)
        .map(variant => variant.label)
        .join(', ')
    });
    this.saveError.set('');
  }

  cancelEdit(): void {
    this.editingId.set(null);
    this.imageUrl.set(null);
    this.itemForm.reset({ name: '', description: '', priceDollars: 0, sizesText: 'One Size' });
    this.saveError.set('');
  }

  onImageSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }

    this.isUploadingImage.set(true);

    this.marketplaceAdminService
      .uploadImage(file)
      .pipe(finalize(() => this.isUploadingImage.set(false)))
      .subscribe({
        next: response => this.imageUrl.set(response.url),
        error: () => this.saveError.set('Unable to upload image. Please try again.')
      });
  }

  submit(): void {
    this.saveError.set('');

    if (this.itemForm.invalid) {
      this.itemForm.markAllAsTouched();
      return;
    }

    const { name, description, priceDollars, sizesText } = this.itemForm.getRawValue();
    const editingId = this.editingId();
    const existingItem = this.items().find(item => item.id === editingId);
    const existingStockByLabel = new Map(
      (existingItem?.variants ?? []).map(variant => [variant.label.trim().toLowerCase(), variant.stockStatus])
    );

    const labels = Array.from(
      new Set(
        sizesText
          .split(',')
          .map(label => label.trim())
          .filter(label => label.length > 0)
      )
    );

    const payload = {
      name,
      description,
      priceCents: Math.round(priceDollars * 100),
      imageUrl: this.imageUrl(),
      variants: labels.map((label, index) => ({
        label,
        sortOrder: index,
        stockStatus: existingStockByLabel.get(label.toLowerCase()) ?? 'in_stock'
      }))
    };

    this.isSaving.set(true);

    const request$ = editingId
      ? this.marketplaceAdminService.updateItem(editingId, payload)
      : this.marketplaceAdminService.createItem(payload);

    request$.pipe(finalize(() => this.isSaving.set(false))).subscribe({
      next: () => {
        this.cancelEdit();
        this.loadItems();
      },
      error: () => this.saveError.set('Unable to save this item. Please try again.')
    });
  }

  toggleActive(item: AdminItemSummary): void {
    this.setRowError(item.id, '');
    this.pendingIds.update(pending => new Set(pending).add(item.id));

    const request$ = item.isActive
      ? this.marketplaceAdminService.deactivateItem(item.id)
      : this.marketplaceAdminService.activateItem(item.id);

    request$
      .pipe(
        finalize(() => {
          this.pendingIds.update(pending => {
            const next = new Set(pending);
            next.delete(item.id);
            return next;
          });
        })
      )
      .subscribe({
        next: updated => {
          this.items.update(items =>
            items.map(existing => (existing.id === updated.id ? updated : existing))
          );
        },
        error: () => this.setRowError(item.id, 'That action failed. Please try again.')
      });
  }

  deleteItem(item: AdminItemSummary): void {
    if (!confirm(`Delete "${item.name}"? This cannot be undone.`)) {
      return;
    }

    this.setRowError(item.id, '');
    this.pendingIds.update(pending => new Set(pending).add(item.id));

    this.marketplaceAdminService
      .deleteItem(item.id)
      .pipe(
        finalize(() => {
          this.pendingIds.update(pending => {
            const next = new Set(pending);
            next.delete(item.id);
            return next;
          });
        })
      )
      .subscribe({
        next: () => {
          this.items.update(items => items.filter(existing => existing.id !== item.id));
        },
        error: () =>
          this.setRowError(item.id, 'This item has order history; deactivate it instead.')
      });
  }

  isPending(itemId: string): boolean {
    return this.pendingIds().has(itemId);
  }

  rowError(itemId: string): string {
    return this.rowErrors()[itemId] ?? '';
  }

  hasError(controlName: keyof typeof this.itemForm.controls): boolean {
    const control = this.itemForm.controls[controlName];
    return control.invalid && (control.touched || control.dirty);
  }

  private setRowError(itemId: string, message: string): void {
    this.rowErrors.update(errors => ({ ...errors, [itemId]: message }));
  }
}
