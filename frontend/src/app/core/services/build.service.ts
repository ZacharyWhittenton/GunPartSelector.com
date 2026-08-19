import { Injectable, computed, signal } from '@angular/core';

import { BuildPart, CompatibilityIssue } from '../models/build.model';
import { ProductSummary } from '../models/catalog.model';

const BUILD_STORAGE_KEY = 'wd_build';

export type WeightUnit = 'oz' | 'lb' | 'kg';

interface CompatibilityDimension {
  prefix: string;
  label: string;
  severity: 'error' | 'warning';
}

const COMPATIBILITY_DIMENSIONS: CompatibilityDimension[] = [
  { prefix: 'platform', label: 'Receiver platform', severity: 'error' },
  { prefix: 'caliber', label: 'Caliber', severity: 'error' },
  { prefix: 'buffertube', label: 'Buffer tube spec', severity: 'error' },
  { prefix: 'handguard', label: 'Handguard interface', severity: 'error' },
  { prefix: 'thread', label: 'Muzzle thread pattern', severity: 'error' },
  { prefix: 'gassystem', label: 'Gas system length', severity: 'warning' }
];

function tagValue(tags: string[], prefix: string): string | null {
  const match = tags.find(tag => tag.startsWith(`${prefix}:`));
  return match ? match.slice(prefix.length + 1) : null;
}

@Injectable({
  providedIn: 'root'
})
export class BuildService {
  private readonly partsSignal = signal<BuildPart[]>(this.readStoredParts());
  private readonly weightUnitSignal = signal<WeightUnit>('oz');

  readonly parts = this.partsSignal.asReadonly();
  readonly weightUnit = this.weightUnitSignal.asReadonly();

  readonly itemCount = computed(() => this.partsSignal().length);

  readonly totalPriceCents = computed(() =>
    this.partsSignal().reduce((total, part) => total + part.product.priceCents * part.quantity, 0)
  );

  readonly totalWeightOz = computed(() =>
    this.partsSignal().reduce((total, part) => total + part.product.weightOz * part.quantity, 0)
  );

  readonly totalWeightDisplay = computed(() => {
    const oz = this.totalWeightOz();
    const unit = this.weightUnitSignal();
    if (unit === 'lb') return { value: oz / 16, unit: 'lb' as const };
    if (unit === 'kg') return { value: oz * 0.0283495, unit: 'kg' as const };
    return { value: oz, unit: 'oz' as const };
  });

  readonly byCategory = computed(() => {
    const map = new Map<string, BuildPart>();
    for (const part of this.partsSignal()) {
      map.set(part.categoryId, part);
    }
    return map;
  });

  readonly compatibilityIssues = computed<CompatibilityIssue[]>(() => {
    const parts = this.partsSignal();
    const issues: CompatibilityIssue[] = [];

    for (const dimension of COMPATIBILITY_DIMENSIONS) {
      const grouped = new Map<string, string[]>();
      for (const part of parts) {
        const value = tagValue(part.product.attributeTags, dimension.prefix);
        if (value === null) continue;
        const names = grouped.get(value) ?? [];
        names.push(`${part.product.brand} ${part.product.name}`);
        grouped.set(value, names);
      }

      if (grouped.size > 1) {
        issues.push({
          dimension: dimension.prefix,
          label: dimension.label,
          severity: dimension.severity,
          values: Array.from(grouped.entries()).map(([value, partNames]) => ({ value, partNames }))
        });
      }
    }

    return issues;
  });

  readonly hasErrors = computed(() =>
    this.compatibilityIssues().some(issue => issue.severity === 'error')
  );

  setPart(categoryId: string, product: ProductSummary): void {
    const parts = this.partsSignal().filter(part => part.categoryId !== categoryId);
    parts.push({ categoryId, product, quantity: 1 });
    this.updateParts(parts);
  }

  removePart(categoryId: string): void {
    this.updateParts(this.partsSignal().filter(part => part.categoryId !== categoryId));
  }

  toggleWeightUnit(): void {
    const order: WeightUnit[] = ['oz', 'lb', 'kg'];
    const next = order[(order.indexOf(this.weightUnitSignal()) + 1) % order.length];
    this.weightUnitSignal.set(next);
  }

  clear(): void {
    this.updateParts([]);
  }

  private updateParts(parts: BuildPart[]): void {
    this.partsSignal.set(parts);
    localStorage.setItem(BUILD_STORAGE_KEY, JSON.stringify(parts));
  }

  private readStoredParts(): BuildPart[] {
    const raw = localStorage.getItem(BUILD_STORAGE_KEY);
    if (!raw) {
      return [];
    }

    try {
      return JSON.parse(raw) as BuildPart[];
    } catch {
      return [];
    }
  }
}
