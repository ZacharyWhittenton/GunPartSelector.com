export interface ItemSummary {
  id: string;
  name: string;
  slug: string;
  description: string;
  priceCents: number;
  imageUrl: string | null;
}

export interface AdminItemSummary extends ItemSummary {
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}
