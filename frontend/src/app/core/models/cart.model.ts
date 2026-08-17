import { ItemSummary } from './marketplace-item.model';

export interface CartLine {
  item: ItemSummary;
  variantId: string;
  variantLabel: string;
  quantity: number;
}
