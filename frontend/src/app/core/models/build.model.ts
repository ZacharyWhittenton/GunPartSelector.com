import { ProductSummary } from './catalog.model';

export interface BuildPart {
  categoryId: string;
  product: ProductSummary;
  quantity: number;
}

export type CompatibilitySeverity = 'error' | 'warning';

export interface CompatibilityIssue {
  dimension: string;
  label: string;
  severity: CompatibilitySeverity;
  values: { value: string; partNames: string[] }[];
}

export interface BuildShareItem {
  product: ProductSummary;
  quantity: number;
}

export interface BuildShareResponse {
  slug: string;
  name: string | null;
  createdAt: string;
  items: BuildShareItem[];
}
