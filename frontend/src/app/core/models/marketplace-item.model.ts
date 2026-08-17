export type VariantStockStatus = 'in_stock' | 'out_of_stock';

export interface ItemVariantSummary {
  id: string;
  label: string;
  sortOrder: number;
  stockStatus: VariantStockStatus;
}

export interface ItemSummary {
  id: string;
  name: string;
  slug: string;
  description: string;
  priceCents: number;
  imageUrl: string | null;
  variants: ItemVariantSummary[];
}

export interface AdminItemSummary extends ItemSummary {
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}
