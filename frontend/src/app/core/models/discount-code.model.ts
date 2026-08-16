export type DiscountType = 'percent' | 'fixed';

export interface DiscountCode {
  id: string;
  code: string;
  discountType: DiscountType;
  value: number;
  isActive: boolean;
  expiresAt: string | null;
  maxRedemptions: number | null;
  redemptionCount: number;
  createdAt: string;
  updatedAt: string;
}
